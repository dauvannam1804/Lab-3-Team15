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

from src.core.openai_provider import OpenAIProvider
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

import src.agent.agent as agent_module

if not hasattr(st.session_state, 'mem_logger'):
    st.session_state.mem_logger = MemoryLogger(logger_module.logger)
    logger_module.logger = st.session_state.mem_logger
    agent_module.logger = st.session_state.mem_logger

mem_logger = st.session_state.mem_logger
# Make sure patch holds on rerun
agent_module.logger = mem_logger
logger_module.logger = mem_logger

# -------------------------------------------------------------------------------------
# Streamlit UI Config
# -------------------------------------------------------------------------------------
st.set_page_config(page_title="ReAct Agent Demo", page_icon="✈️", layout="wide")

st.markdown("""
<style>
/* CSS cho Metrics Container */
[data-testid="stMetric"] { 
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
    padding: 10px 15px; /* Giảm padding để tiết kiệm diện tích */
    border-radius: 12px; 
    box-shadow: 0 4px 15px rgba(0,250,154,0.15); 
    border-left: 6px solid #00fa9a; 
    border-right: 1px solid #333;
    border-top: 1px solid #333;
    border-bottom: 1px solid #333;
}
/* CSS làm nổ bần bật các chữ TTFT (s), Latency (s), Tokens */
[data-testid="stMetricLabel"] * {
    color: #ffb703 !important; 
    font-size: 18px !important; 
    font-weight: 900 !important;
    text-transform: uppercase;
    text-shadow: 0 0 5px rgba(255, 183, 3, 0.6);
}
[data-testid="stMetricValue"] * {
    color: #00ffcc !important; 
    font-size: 26px !important;
    font-weight: 900 !important;
    text-shadow: 0 0 10px rgba(0, 255, 204, 0.4);
}
.output-box { background: #0d0d0d; padding: 20px; border-radius: 10px; font-family: 'Consolas', monospace; font-size: 15px; line-height: 1.6; color: #f1f1f1; border: 1px solid #333; border-top: 3px solid #e63946;}
.status-success { color: #00fa9a; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("✈️ Continuous Flight Booking Agent vs Baseline Chatbot")
st.markdown("Kiểm thử nghiệm thu trực quan song song. Nhập câu hỏi bên dưới để bắt đầu luồng hội thoại!")

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
    
    prompt_tokens = len(prompt) // 4
    comp_tokens = len(full_text) // 4 
    total_tokens = prompt_tokens + comp_tokens
    
    return full_text, ttft, total_latency, total_tokens

def run_agent(agent, prompt):
    mem_logger.clear()
    
    t0 = time.time()
    final_answer = agent.run(prompt)
    total_latency = time.time() - t0
    
    first_llm_event = next((e for e in mem_logger.events if e["event"] == "LLM_RESPONSE"), None)
    ttft = (first_llm_event["timestamp"] - t0) if first_llm_event else total_latency
        
    total_tokens, prompt_tokens, comp_tokens = 0, 0, 0
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

api_key = os.getenv("OPENAI_API_KEY")
if not api_key or api_key == "your_openai_api_key_here":
    st.error("🔑 Vui lòng thiết lập biến môi trường OPENAI_API_KEY trong file .env")
    st.stop()
    
llm = OpenAIProvider(model_name="gpt-4o", api_key=api_key)
tools = get_tools()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Hiển thị lịch sử Chat liên tục
for i, turn in enumerate(st.session_state.chat_history):
    st.chat_message("user", avatar="🧑‍💻").write(turn["user"])
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### 🤖 Baseline Chatbot Response")
        m1, m2, m3 = st.columns(3)
        m1.metric("TTFT (s)", f"{turn['b_ttft']:.2f}")
        m2.metric("Latency (s)", f"{turn['b_lat']:.2f}")
        m3.metric("Tokens", turn['b_toks'])
        st.markdown(f"<div class='output-box'>{turn['b_ans']}</div><br>", unsafe_allow_html=True)
        
    with c2:
        st.markdown("##### 🧠 ReAct Agent Response")
        a1, a2, a3 = st.columns(3)
        a1.metric("TTFT (s)", f"{turn['a_ttft']:.2f}")
        a2.metric("Latency (s)", f"{turn['a_lat']:.2f}")
        a3.metric("Tokens", turn['a_toks'])
        st.markdown(f"<div class='output-box'>{turn['a_ans']}</div><br>", unsafe_allow_html=True)

# Khung input liên tục ở đáy màn hình
if prompt := st.chat_input("VD: Tìm giúp mình chuyến bay từ Hà Nội đi Đà Nẵng..."):
    # Render user message ngay lập tức
    st.chat_message("user", avatar="🧑‍💻").write(prompt)
    
    # Chuẩn bị block chờ
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### 🤖 Baseline Chatbot Response")
        with st.spinner("Đang tư duy trực tiếp..."):
            b_ans, b_ttft, b_lat, b_toks = run_baseline_stream(llm, prompt)
    with c2:
        st.markdown("##### 🧠 ReAct Agent Response")
        with st.spinner("Đang duyệt thought-action loop..."):
            agent = ReActAgent(llm=llm, tools=tools, max_steps=5)
            a_ans, a_ttft, a_lat, a_toks = run_agent(agent, prompt)
            
    # Lưu vào session_state (tự động rerun và render lại)
    st.session_state.chat_history.append({
        "user": prompt,
        "b_ans": b_ans, "b_ttft": b_ttft, "b_lat": b_lat, "b_toks": b_toks,
        "a_ans": a_ans, "a_ttft": a_ttft, "a_lat": a_lat, "a_toks": a_toks
    })
    st.rerun()
