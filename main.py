"""
main.py – Entry point for Lab 3: ReAct Agent Demo & Evaluation
=============================================================
Runs 5 test cases against:
  1. Baseline Chatbot (plain LLM, no tools)
  2. ReAct Agent      (Thought-Action-Observation loop with flight tools)

Usage:
    python main.py
"""

import os
import sys
import re
import time

# Make sure src/ is importable when running from the project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

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
# 5 Test Cases – grounded in mock_db.json
# ──────────────────────────────────────────────
#
# DB snapshot (key data):
#  HAN→SGN 2026-04-10: VN213($120,5 seats) | VJ122($75,0 seats) | QH501($95,7 seats)
#  HAN→DAD 2026-04-11: VN345($150,3 seats) | VJ567($90,2 seats)
#  HAN→PQC 2026-04-13: VN890($200,6 seats)
#  SGN→HAN 2026-04-12: VN678($115,4 seats) | QH302($102,1 seat)
#  Weather : SGN=Sunny32° | HAN=Rainy22° | DAD=Cloudy28° | PQC=Sunny34°
#  Policies: VN=12kg carry-on+23kg check | VJ=7kg no check | QH=10kg+20kg
TEST_CASES = [
    {
        "id": 1,
        "label": "TC1 – Search flights (1 tool call)",
        # Expected: Agent calls search_flights(HAN,SGN,2026-04-10)
        # → returns VN213 $120, VJ122 $75 (hết chỗ), QH501 $95
        "prompt": (
            "Gợi ý cho tôi địa điểm du lịch Đà NẴNG "
        ),
    },
    {
        "id": 2,
        "label": "TC2 – Book cheapest available (2 tool calls: search → book)",
        # Expected:
        #   Step1: search_flights(HAN,SGN,2026-04-10) → VJ122 hết chỗ nên bỏ qua
        #   Step2: book_flight(QH501, "Le Thi C", "0911111111")  ← $95, còn 7 chỗ
        #   → returns PNR code
        "prompt": (
            "Các sinh tồn ở Hà Nội "
        ),
    },
    {
        "id": 3,
        "label": "TC3 – Failure handling: book a sold-out flight",
        # Expected: book_flight(VJ122, ...) → Error "no available seats"
        # Agent should NOT hallucinate a PNR, must tell user flight is full.
        "prompt": (
            "các món ăn ở HCM"
        ),
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

    for idx, tc in enumerate(TEST_CASES):
        print_section(f"Test Case {tc['id']}: {tc['label']}")
        print(f"📝 Prompt: {tc['prompt']}\n")

        # ── Baseline Chatbot ────────────────────────────────────────
        print("🤖 [Baseline Chatbot]  (plain LLM – no tools)")
        baseline_ans = safe_call(run_baseline_chatbot, llm, tc["prompt"])
        print(f"   → {baseline_ans}\n")

        # ── Skip sleep + Agent if out of scope ──────────────────────
        if not is_flight_related(tc["prompt"]):
            print("🚫 [ReAct Agent]  Guardrail triggered – skipping (0 tokens).")
            print(f"   → {OUT_OF_SCOPE_MSG}\n")
            if idx < len(TEST_CASES) - 1:
                print(f"   ⏳  Sleeping {DELAY_BETWEEN_CASES}s before next test case …")
                time.sleep(DELAY_BETWEEN_CASES)
            continue

        # Pause between baseline and agent to stay under rate limit
        print(f"   ⏳  Sleeping {DELAY_BETWEEN_CALLS}s before Agent call …")
        time.sleep(DELAY_BETWEEN_CALLS)

        # ── ReAct Agent ─────────────────────────────────────────────
        print("🧠 [ReAct Agent]  (Thought → Action → Observation loop)")
        agent_ans = safe_call(run_react_agent, agent, tc["prompt"])
        print(f"   → {agent_ans}\n")

        # Pause between test cases (skip after last one)
        if idx < len(TEST_CASES) - 1:
            print(f"   ⏳  Sleeping {DELAY_BETWEEN_CASES}s before next test case …")
            time.sleep(DELAY_BETWEEN_CASES)

    print(f"\n{'═'*64}")
    print("  ✅  All test cases completed. Check logs/ for trace data.")
    print(f"{'═'*64}\n")


if __name__ == "__main__":
    main()
