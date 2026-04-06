import os
import sys
import time
import json
import streamlit as st
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv

# Try to load env
load_dotenv()

from src.core.gemini_provider import GeminiProvider
from src.agent.agent import ReActAgent
from src.tools.flight_tools import get_tools
import src.telemetry.logger as logger_module
import src.telemetry.metrics as metrics_module

# -------------------------------------------------------------------------------------
# Hook Loggers to get live metrics inside Streamlit memory!
# -------------------------------------------------------------------------------------
class MemoryLogger:
    def __init__(self, original_logger):
        self._orig = original_logger
        self.events = []
    
    def log_event(self, event_type, data):
        self.events.append({"event": event_type, "data": data, "timestamp": time.time()})
        self._orig.log_event(event_type, data)
        
    def info(self, msg): self._orig.info(msg)
    def error(self, msg, exc_info=True): self._orig.error(msg, exc_info)
    def get_log_file(self): return self._orig.get_log_file()
    
    def clear(self):
        self.events = []

if not hasattr(st.session_state, 'mem_logger'):
    st.session_state.mem_logger = MemoryLogger(logger_module.logger)
    logger_module.logger = st.session_state.mem_logger

mem_logger = st.session_state.mem_logger

# -------------------------------------------------------------------------------------
# Streamlit UI Config
# -------------------------------------------------------------------------------------
st.set_page_config(page_title="ReAct Agent Demo", page_icon="✈️", layout="wide")

st.markdown("""
<style>
[data-testid="stMetric"] { 
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
    padding: 15px 20px; 
    border-radius: 12px; 
    box-shadow: 0 4px 15px rgba(0,250,154,0.15); 
    border-left: 6px solid #00fa9a; 
    border-right: 1px solid #333;
    border-top: 1px solid #333;
    border-bottom: 1px solid #333;
}
[data-testid="stMetricLabel"] > div > div > p {
    color: #ffb703 !important; 
    font-size: 17px !important; 
    font-weight: 800 !important;
    text-transform: uppercase;
}
[data-testid="stMetricValue"] > div {
    color: #00ffcc !important; 
    font-size: 32px !important;
    font-weight: 900 !important;
    text-shadow: 0 0 10px rgba(0, 255, 204, 0.4);
}
.output-box { background: #0d0d0d; padding: 20px; border-radius: 10px; min-height: 200px; max-height: 400px; overflow-y: auto; font-family: 'Consolas', monospace; font-size: 15px; line-height: 1.6; color: #f1f1f1; border: 1px solid #333; border-top: 3px solid #e63946;}
.status-success { color: #00fa9a; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("✈️ Flight Booking Agent vs Baseline Chatbot")
st.markdown("Tiến hành chạy mô phỏng nghiệm thu **Time-to-First-Token (TTFT)**, **Latency**, và **Tokens Usage** giữa Chatbot thông thường và ReAct Agent.")

# -------------------------------------------------------------------------------------
# Helper execution
# -------------------------------------------------------------------------------------
def run_baseline_stream(llm, prompt):
    start_time = time.time()
    ttft = 0
    full_text = ""
    system_prompt = "You are a helpful flight booking assistant. Answer the user's question."
    
    stream_gen = llm.stream(f"User: {prompt}", system_prompt=system_prompt)
    
    try:
        for i, chunk in enumerate(stream_gen):
            if i == 0:
                ttft = time.time() - start_time
            full_text += chunk
    except Exception as e:
        full_text = f"Error: {str(e)}"
        
    total_latency = time.time() - start_time
    
    # Đoán token dở chừng (Vì stream API không trả về usage chính xác trong Gemini Provider bản đơn giản của Lab)
    # Ta sẽ estimate prompt/completion length = chars / 4
    prompt_tokens = len(prompt) // 4
    comp_tokens = len(full_text) // 4 
    total_tokens = prompt_tokens + comp_tokens
    
    return full_text, ttft, total_latency, total_tokens


def run_agent(agent, prompt):
    mem_logger.clear()
    
    t0 = time.time()
    final_answer = agent.run(prompt)
    total_latency = time.time() - t0
    
    # Tính TTFT: Thời điểm bắt được sự kiện LLM_RESPONSE đầu tiên
    first_llm_event = next((e for e in mem_logger.events if e["event"] == "LLM_RESPONSE"), None)
    if first_llm_event:
        ttft = first_llm_event["timestamp"] - t0
    else:
        ttft = total_latency
        
    # Tính tổng Tokens
    total_tokens = 0
    prompt_tokens = 0
    comp_tokens = 0
    for e in mem_logger.events:
        if e["event"] == "LLM_RESPONSE":
            usage = e["data"].get("usage", {})
            prompt_tokens += usage.get("prompt_tokens", 0)
            comp_tokens += usage.get("completion_tokens", 0)
            total_tokens += usage.get("total_tokens", 0)
            
    return final_answer, ttft, total_latency, total_tokens

# -------------------------------------------------------------------------------------
# App Body
# -------------------------------------------------------------------------------------

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("🔑 Vui lòng thiết lập biến môi trường GEMINI_API_KEY trong file .env")
    st.stop()
    
llm = GeminiProvider(model_name="gemini-2.5-flash", api_key=api_key)
tools = get_tools()
err = None  # Or remove err parameter entirely

user_input = st.text_input("Gõ câu hỏi để test nghiệm thu hệ thống:", placeholder="VD: Tìm giúp mình chuyến bay từ Hà Nội đi Đà Nẵng...")

if st.button("🚀 Chạy So Sánh", type="primary") and user_input:
    col1, col2 = st.columns(2)
    
    # ==========================
    # CỘT 1: BASELINE CHATBOT
    # ==========================
    with col1:
        st.subheader("🤖 Baseline Chatbot")
        with st.spinner("Đang chạy trực tiếp không qua quy trình Thought-Action..."):
            base_ans, base_ttft, base_lat, base_toks = run_baseline_stream(llm, user_input)
            
        m1, m2, m3 = st.columns(3)
        m1.metric("TTFT (s)", f"{base_ttft:.2f}")
        m2.metric("Latency (s)", f"{base_lat:.2f}")
        m3.metric("Tokens", base_toks)
        
        st.markdown(f"<div class='output-box'>{base_ans}</div>", unsafe_allow_html=True)
        
    # ==========================
    # CỘT 2: REACT AGENT
    # ==========================
    with col2:
        st.subheader("🧠 ReAct Agent")
        
        if err:
            st.error(err)
        else:
            with st.spinner("Đang tư duy và sử dụng Tool định tuyến (ReAct Loop)..."):
                agent = ReActAgent(llm=llm, tools=tools, max_steps=5)
                ag_ans, ag_ttft, ag_lat, ag_toks = run_agent(agent, user_input)
                
            a1, a2, a3 = st.columns(3)
            a1.metric("TTFT (s)", f"{ag_ttft:.2f}")
            a2.metric("Latency (s)", f"{ag_lat:.2f}")
            a3.metric("Tokens", ag_toks)
            
            st.markdown(f"<div class='output-box'>{ag_ans}</div>", unsafe_allow_html=True)
