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
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from src.core.gemini_provider import GeminiProvider
from src.agent.agent import ReActAgent
from src.tools.flight_tools import search_flights, book_flight, get_weather, get_baggage_policy, get_tool_definitions

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
            "Cho tôi xem danh sách chuyến bay từ Hà Nội (HAN) đến Sài Gòn (SGN) "
            "vào ngày 2026-04-10."
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
            "Tìm chuyến bay rẻ nhất còn chỗ từ HAN đến SGN ngày 2026-04-10, "
            "rồi đặt vé cho hành khách 'Le Thi C', liên hệ '0911111111'."
        ),
    },
    {
        "id": 3,
        "label": "TC3 – Failure handling: book a sold-out flight",
        # Expected: book_flight(VJ122, ...) → Error "no available seats"
        # Agent should NOT hallucinate a PNR, must tell user flight is full.
        "prompt": (
            "Đặt vé chuyến VJ122 (Vietjet Air, HAN→SGN 10:30) "
            "cho hành khách 'Pham Van D', liên hệ '0922222222'."
        ),
    },
    {
        "id": 4,
        "label": "TC4 – Baggage policy lookup (1 tool call)",
        # Expected: get_baggage_policy("Bamboo Airways")
        # → "Hành lý xách tay 10 kg, ký gửi miễn phí 20 kg."
        "prompt": (
            "Tôi sắp bay Bamboo Airways. "
            "Cho tôi biết quy định hành lý xách tay và ký gửi của hãng này."
        ),
    },
    {
        "id": 5,
        "label": "TC5 – Weather + search combo (bonus: 2 tools)",
        # Expected:
        #   Step1: get_weather("DAD") → Cloudy 28°C
        #   Step2: search_flights(HAN,DAD,2026-04-11) → VN345 & VJ567
        #   Agent summarises weather AND available flights together.
        "prompt": (
            "Tôi muốn bay từ Hà Nội (HAN) đến Đà Nẵng (DAD) ngày 2026-04-11. "
            "Thời tiết Đà Nẵng hôm đó thế nào và có những chuyến bay nào?"
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


def run_baseline_chatbot(llm: GeminiProvider, prompt: str) -> str:
    """Plain LLM call with NO tools – simulates a naive chatbot."""
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
    agent = ReActAgent(llm=llm, tools=get_tool_definitions(), max_steps=7)

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
