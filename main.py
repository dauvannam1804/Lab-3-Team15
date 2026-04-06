import argparse
import importlib
import os
import sys
import re
import time

# Make sure src/ is importable when running from the project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is listed in requirements.txt
    load_dotenv = None

from src.core.gemini_provider import GeminiProvider
from src.agent.agent import ReActAgent, _FLIGHT_KEYWORDS
from src.tools.flight_tools import FLIGHT_TOOLS

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
GEMINI_MODEL = "gemini-2.5-flash"   # Free tier: 5 req/min → sleep added below
DELAY_BETWEEN_CALLS = 15            # seconds – avoids rate-limit between baseline & agent
DELAY_BETWEEN_CASES = 20            # seconds – avoids rate-limit between test cases
MAX_RETRIES = 3                     # retry on 429 / quota errors

# ──────────────────────────────────────────────
# Test Cases
# ──────────────────────────────────────────────
# DB: HAN→SGN 2026-04-10: VN213($120,5 seats) | VJ122($75,0 seats) | QH501($95,6 seats)
#     HAN→DAD 2026-04-11: VN345($150,3 seats) | VJ567($90,2 seats)
#     Weather: SGN=Sunny32° | HAN=Rainy22° | DAD=Cloudy28° | PQC=Sunny34°
#     Policies: Vietnam Airlines=12kg+23kg | Vietjet=7kg no check | Bamboo=10kg+20kg
TEST_CASES = [
    {
        "id": 1,
        "label": "TC1 – Out-of-scope guardrail (tourism question)",
        # Both Baseline & Agent should reject immediately (0 LLM tokens)
        "prompt": "Gợi ý cho tôi địa điểm du lịch Đà Nẵng.",
    },
    {
        "id": 2,
        "label": "TC2 – Latency comparison: simple 1-tool query",
        # ★ LATENCY TEST: both Baseline and Agent must answer this.
        # Baseline: 1 LLM call, may hallucinate prices.
        # Agent   : 1 LLM call + search_flights() tool + 1 LLM call → accurate.
        # Compare: Baseline latency (fast, wrong) vs Agent latency (slower, correct).
        "prompt": "Có chuyến bay nào từ Hà Nội đi Sài Gòn vào ngày 2026-04-10 không? Liệt kê giá và số ghế trống.",
    },
    {
        "id": 3,
        "label": "TC3 – Multi-step: search then book cheapest available",
        # Agent: search_flights → pick cheapest with seats (QH501 $95) → book_flight
        # Baseline: cannot actually book, will hallucinate PNR.
        "prompt": (
            "Tìm chuyến bay rẻ nhất còn chỗ từ HAN đến SGN ngày 2026-04-10 "
            "rồi đặt vé cho hành khách 'Tran Thi B', liên hệ '0977777777'."
        ),
    },
    {
        "id": 4,
        "label": "TC4 – Failure handling: book sold-out flight VJ122",
        # Agent: book_flight(VJ122) → Error 'no available seats' → tells user
        # Baseline: likely hallucinates a PNR.
        "prompt": "Đặt vé chuyến VJ122 cho hành khách 'Pham Van D', liên hệ '0922222222'.",
    },
    {
        "id": 5,
        "label": "TC5 – Baggage policy lookup (1 tool)",
        # Agent: get_baggage_policy('Bamboo Airways') → exact policy from DB
        # Baseline: generic answer, may be wrong.
        "prompt": "Bay Bamboo Airways được mang bao nhiêu kg hành lý xách tay và ký gửi?",
    },
]


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
SEP = "─" * 64

def print_section(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def safe_call(fn, *args, retries: int = MAX_RETRIES) -> str:
    """
    Call fn(*args) with automatic retry on rate-limit (429 / ResourceExhausted).
    Returns error string if all retries exhausted.
    """
    for attempt in range(1, retries + 1):
        try:
            return fn(*args)
        except Exception as e:
            err_str = str(e)
            # Detect quota / rate-limit errors
            if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str or "quota" in err_str.lower():
                # Try to parse retry-after from the message
                wait = 45  # default wait
                import re
                m = re.search(r"retry in (\d+)", err_str)
                if m:
                    wait = int(m.group(1)) + 5
                print(f"\n   ⏳  Rate limit hit (attempt {attempt}/{retries}). Waiting {wait}s …")
                time.sleep(wait)
            else:
                # Non-recoverable error
                return f"[ERROR] {e}"
    return "[ERROR] Max retries exceeded due to rate limiting."


# ──────────────────────────────────────────────
# Guardrail helper (shared with agent.py)
# ──────────────────────────────────────────────
OUT_OF_SCOPE_MSG = (
    "Xin lỗi, tôi chỉ hỗ trợ các yêu cầu liên quan đến đặt vé máy bay, "
    "tra cứu chuyến bay, thời tiết điểm đến và quy định hành lý. "
    "Vui lòng đặt câu hỏi phù hợp với dịch vụ này."
)

def is_flight_related(text: str) -> bool:
    """Reuse the same keyword list as agent.py to keep behaviour consistent."""
    lowered = text.lower()
    if re.search(r"\b(vn|vj|qh|pa)\d{2,4}\b", lowered):
        return True
    return any(kw in lowered for kw in _FLIGHT_KEYWORDS)


def run_baseline_chatbot(llm: GeminiProvider, prompt: str) -> str:
    """Plain LLM call with NO tools – simulates a naive chatbot."""
    # Apply same guardrail so Baseline also rejects off-topic questions
    if not is_flight_related(prompt):
        return OUT_OF_SCOPE_MSG
    system = "You are a helpful flight booking assistant. Answer the user's question."
    response = llm.generate(f"User: {prompt}", system_prompt=system)
    return response.get("content", "").strip()


def run_react_agent(agent: ReActAgent, prompt: str) -> str:
    return agent.run(prompt)


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌  GEMINI_API_KEY not found in .env. Please set it and retry.")
        sys.exit(1)

    llm   = GeminiProvider(model_name=GEMINI_MODEL, api_key=api_key)
    agent = ReActAgent(llm=llm, tools=FLIGHT_TOOLS, max_steps=7)

    print(f"\n{'═'*64}")
    print(f"  Lab 3 – ReAct Agent demo  |  Model: {GEMINI_MODEL}")
    print(f"  ⚠  Free-tier: sleeping {DELAY_BETWEEN_CALLS}s between calls to avoid 429")
    print(f"{'═'*64}")

    latency_report = []   # collect rows for summary table

    for idx, tc in enumerate(TEST_CASES):
        print_section(f"Test Case {tc['id']}: {tc['label']}")
        print(f"📝 Prompt: {tc['prompt']}\n")

        out_of_scope = not is_flight_related(tc["prompt"])

        # Baseline Chatbot
        print("🤖 [Baseline Chatbot]  (plain LLM – no tools)")
        t0 = time.time()
        baseline_ans = safe_call(run_baseline_chatbot, llm, tc["prompt"])
        baseline_ms = int((time.time() - t0) * 1000)
        print(f"   → {baseline_ans}")
        print(f"   ⏱  Latency: {baseline_ms} ms\n")

        # Guardrail short-circuit
        if out_of_scope:
            print("🚫 [ReAct Agent]  Guardrail triggered – skipping (0 tokens, ~0 ms).")
            print(f"   → {OUT_OF_SCOPE_MSG}")
            print(f"   ⏱  Latency: 0 ms  (no LLM call)\n")
            latency_report.append((tc["id"], tc["label"], baseline_ms, 0, "GUARDRAIL"))
            if idx < len(TEST_CASES) - 1:
                print(f"   ⏳  Sleeping {DELAY_BETWEEN_CASES}s …")
                time.sleep(DELAY_BETWEEN_CASES)
            continue

        # Sleep to avoid rate limit
        print(f"   ⏳  Sleeping {DELAY_BETWEEN_CALLS}s before Agent call …")
        time.sleep(DELAY_BETWEEN_CALLS)

        # ReAct Agent
        print("🧠 [ReAct Agent]  (Thought → Action → Observation loop)")
        t0 = time.time()
        agent_ans = safe_call(run_react_agent, agent, tc["prompt"])
        agent_ms = int((time.time() - t0) * 1000)
        print(f"   → {agent_ans}")
        print(f"   ⏱  Latency: {agent_ms} ms\n")

        latency_report.append((tc["id"], tc["label"], baseline_ms, agent_ms, "OK"))

        if idx < len(TEST_CASES) - 1:
            print(f"   ⏳  Sleeping {DELAY_BETWEEN_CASES}s …")
            time.sleep(DELAY_BETWEEN_CASES)

    # Latency Summary Table
    print(f"\n{'═'*64}")
    print("  📊  LATENCY COMPARISON SUMMARY")
    print(f"{'─'*64}")
    print(f"  {'TC':<4} {'Baseline':>10} {'Agent':>10}  Delta  Note")
    print(f"{'─'*64}")
    for row in latency_report:
        tc_id, label, b_ms, a_ms, status = row
        short = (label[:32] + "…") if len(label) > 32 else label
        if status == "GUARDRAIL":
            print(f"  TC{tc_id:<3} {b_ms:>8} ms {'0 ms':>10}  {'N/A':>6}  Guardrail – {short}")
        else:
            delta = a_ms - b_ms
            sign = "+" if delta >= 0 else ""
            print(f"  TC{tc_id:<3} {b_ms:>8} ms {a_ms:>8} ms  {sign}{delta:>5} ms  {short}")
    print(f"{'═'*64}")
    print("  ✅  Done. Check logs/ for full trace data.")
    print(f"{'═'*64}\n")


if __name__ == "__main__":
    sys.exit(main())
