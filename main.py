import argparse
import importlib
import os
import sys
<<<<<<< HEAD
<<<<<<< HEAD
import re
import time
=======
from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4
>>>>>>> 6a63230f4bdc83f001bfe87a1d4e68ff3e416de9
=======
import re
import time

# Make sure src/ is importable when running from the project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
>>>>>>> f802a557054a2e097ec44a6ff883d60c0ba2994c

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is listed in requirements.txt
    load_dotenv = None

<<<<<<< HEAD
<<<<<<< HEAD
from dotenv import load_dotenv
load_dotenv()

from src.core.gemini_provider import GeminiProvider
from src.agent.agent import ReActAgent, _FLIGHT_KEYWORDS
from src.tools.flight_tools import FLIGHT_TOOLS
=======
from src.agent.agent import ReActAgent
from src.core.llm_provider import LLMProvider
from src.core.mock_provider import MockProvider
from src.telemetry.log_analysis import format_summary, load_events, summarize_events, write_summary
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker
>>>>>>> 6a63230f4bdc83f001bfe87a1d4e68ff3e416de9
=======
from src.core.gemini_provider import GeminiProvider
from src.agent.agent import ReActAgent, _FLIGHT_KEYWORDS
from src.tools.flight_tools import FLIGHT_TOOLS
>>>>>>> f802a557054a2e097ec44a6ff883d60c0ba2994c

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
GEMINI_MODEL = "gemini-2.5-flash"   # Free tier: 5 req/min → sleep added below
DELAY_BETWEEN_CALLS = 15            # seconds – avoids rate-limit between baseline & agent
DELAY_BETWEEN_CASES = 20            # seconds – avoids rate-limit between test cases
MAX_RETRIES = 3                     # retry on 429 / quota errors

<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> f802a557054a2e097ec44a6ff883d60c0ba2994c
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
<<<<<<< HEAD
=======
@dataclass(frozen=True)
class TestCase:
    case_id: str
    name: str
    prompt: str
    expected_behavior: str


@dataclass
class CaseOutcome:
    run_id: str
    runner: str
    test_case_id: str
    test_name: str
    provider: str
    model: str
    status: str
    latency_ms: int
    response: str
    expected_behavior: str
    failure_type: Optional[str] = None
    notes: Optional[str] = None


TEST_CASES: List[TestCase] = [
    TestCase(
        case_id="TC1",
        name="Flight search",
        prompt="Bạn có tuyến bay nào từ Hà Nội đi Sài Gòn vào ngày 10/04/2026 không?",
        expected_behavior="Trả đúng các chuyến bay khả dụng theo mock_db.json.",
    ),
    TestCase(
        case_id="TC2",
        name="Booking multi-step",
        prompt="Tôi chọn chuyến bay VN213. Bạn hãy đặt vé giúp tôi cho hành khách 'Nguyen Van A' nhé.",
        expected_behavior="Trích xuất mã chuyến bay, gọi book_flight và trả về PNR.",
    ),
    TestCase(
        case_id="TC3",
        name="Sold-out failure handling",
        prompt="Đặt cho tôi chuyến VJ122.",
        expected_behavior="Phát hiện hết chỗ và báo lại thay vì bịa PNR.",
    ),
    TestCase(
        case_id="TC4",
        name="Baggage policy lookup",
        prompt="Bay của Vietnam Airlines được mang bao nhiêu kg hành lý?",
        expected_behavior="Dùng get_baggage_policy để trả lời đúng theo JSON policy.",
    ),
    TestCase(
        case_id="TC5",
        name="Weather side-context",
        prompt="Tôi chuẩn bị bay vào Sài Gòn, thời tiết ở đó ra sao?",
        expected_behavior="Dùng get_weather và chèn thông tin thời tiết hợp ngữ cảnh.",
    ),
>>>>>>> 6a63230f4bdc83f001bfe87a1d4e68ff3e416de9
=======
>>>>>>> f802a557054a2e097ec44a6ff883d60c0ba2994c
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


<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> f802a557054a2e097ec44a6ff883d60c0ba2994c
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
<<<<<<< HEAD
=======
def _clean_env_value(value: Optional[str]) -> str:
    if value is None:
        return ""
    return value.strip().strip("\"'").strip()
>>>>>>> 6a63230f4bdc83f001bfe87a1d4e68ff3e416de9
=======
>>>>>>> f802a557054a2e097ec44a6ff883d60c0ba2994c


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

<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> f802a557054a2e097ec44a6ff883d60c0ba2994c
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
<<<<<<< HEAD
=======
def resolve_provider(provider_name: str, model_name: Optional[str]) -> Tuple[LLMProvider, str]:
    default_model = _clean_env_value(os.getenv("DEFAULT_MODEL")) or "gpt-4o"
    selected_model = _clean_env_value(model_name) or default_model
    selected = _clean_env_value(provider_name).lower()
    default_provider = _clean_env_value(os.getenv("DEFAULT_PROVIDER")).lower()

    if selected == "auto":
        selected = default_provider or _infer_auto_provider(selected_model)

    if selected == "openai" and selected_model.lower().startswith("gemini"):
        selected = "gemini"
    elif selected in {"google", "gemini"} and selected_model.lower().startswith(("gpt", "o1", "o3", "o4")):
        selected = "openai"

    if selected == "mock":
        model = selected_model or "mock-baseline"
        return MockProvider(model_name=model), selected

    if selected == "openai":
        api_key = _clean_env_value(os.getenv("OPENAI_API_KEY"))
        if _is_placeholder_secret(api_key):
            raise RuntimeError("OPENAI_API_KEY is missing. Use --provider mock for smoke tests.")
        from src.core.openai_provider import OpenAIProvider

        return OpenAIProvider(model_name=selected_model, api_key=api_key), selected

    if selected in {"google", "gemini"}:
        api_key = _clean_env_value(os.getenv("GEMINI_API_KEY"))
        if _is_placeholder_secret(api_key):
            raise RuntimeError("GEMINI_API_KEY is missing. Use --provider mock for smoke tests.")
        from src.core.gemini_provider import GeminiProvider

        return GeminiProvider(
            model_name=selected_model,
            api_key=api_key,
        ), selected

    if selected == "local":
        model_path = os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")
        from src.core.local_provider import LocalProvider

        return LocalProvider(model_path=model_path), selected

    raise RuntimeError(f"Unsupported provider '{selected}'.")


def load_tools(module_name: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        return [], f"Tools module '{module_name}' was not found: {exc}"
    except Exception as exc:  # pragma: no cover - depends on user modules
        return [], f"Tools module '{module_name}' failed to import: {exc}"

    for factory_name in ("get_tools", "build_tools", "create_tools", "get_tool_definitions"):
        factory = getattr(module, factory_name, None)
        if callable(factory):
            tools = factory()
            if not isinstance(tools, list):
                return [], f"{module_name}.{factory_name}() must return a list."
            return tools, None

    tools = getattr(module, "TOOLS", None)
    if isinstance(tools, list):
        return tools, None

    return [], (
        f"Tools module '{module_name}' does not expose get_tools(), build_tools(), "
        "create_tools(), get_tool_definitions() or a TOOLS list."
    )


def select_cases(case_selector: str) -> List[TestCase]:
    if case_selector.strip().lower() == "all":
        return TEST_CASES

    selected_ids = {part.strip().upper() for part in case_selector.split(",") if part.strip()}
    matched = [case for case in TEST_CASES if case.case_id in selected_ids]
    missing = selected_ids.difference({case.case_id for case in matched})
    if missing:
        raise RuntimeError(f"Unknown test case IDs: {', '.join(sorted(missing))}")
    return matched


def provider_label(provider: LLMProvider) -> str:
    name = provider.__class__.__name__
    if name.endswith("Provider"):
        name = name[: -len("Provider")]
    return name.lower()


def log_case_start(run_id: str, runner: str, case: TestCase, provider: LLMProvider):
    logger.log_event(
        "CASE_START",
        {
            "run_id": run_id,
            "runner": runner,
            "test_case_id": case.case_id,
            "test_name": case.name,
            "provider": provider_label(provider),
            "model": provider.model_name,
            "prompt": case.prompt,
        },
    )


def finalize_case(outcome: CaseOutcome) -> CaseOutcome:
    logger.log_event("CASE_RESULT", asdict(outcome))
    return outcome


def run_baseline_case(run_id: str, provider: LLMProvider, case: TestCase) -> CaseOutcome:
    log_case_start(run_id, "baseline", case, provider)

    started_at = perf_counter()
    try:
        result = provider.generate(case.prompt)
        latency_ms = int((perf_counter() - started_at) * 1000)
        tracker.track_request(
            provider=result.get("provider", provider_label(provider)),
            model=provider.model_name,
            usage=result.get("usage", {}),
            latency_ms=result.get("latency_ms", latency_ms),
            context={
                "run_id": run_id,
                "runner": "baseline",
                "test_case_id": case.case_id,
                "test_name": case.name,
            },
        )
        return finalize_case(
            CaseOutcome(
                run_id=run_id,
                runner="baseline",
                test_case_id=case.case_id,
                test_name=case.name,
                provider=result.get("provider", provider_label(provider)),
                model=provider.model_name,
                status="success",
                latency_ms=latency_ms,
                response=result.get("content", ""),
                expected_behavior=case.expected_behavior,
                notes="Direct chatbot baseline run with no external tools.",
            )
        )
    except Exception as exc:  # pragma: no cover - depends on runtime provider
        latency_ms = int((perf_counter() - started_at) * 1000)
        logger.log_event(
            "CASE_ERROR",
            {
                "run_id": run_id,
                "runner": "baseline",
                "test_case_id": case.case_id,
                "failure_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        return finalize_case(
            CaseOutcome(
                run_id=run_id,
                runner="baseline",
                test_case_id=case.case_id,
                test_name=case.name,
                provider=provider_label(provider),
                model=provider.model_name,
                status="failure",
                latency_ms=latency_ms,
                response="",
                expected_behavior=case.expected_behavior,
                failure_type=type(exc).__name__,
                notes=str(exc),
            )
        )


def classify_agent_response(response: str) -> Tuple[str, Optional[str], Optional[str]]:
    normalized = response.strip().lower()
    if not normalized:
        return "blocked", "empty_response", "Agent returned an empty response."
    if "not implemented" in normalized or "fill in the todos" in normalized:
        return "blocked", "agent_not_implemented", "src/agent/agent.py is still in skeleton state."
    if normalized.startswith("tool ") and normalized.endswith(" not found."):
        return "failure", "tool_not_found", response.strip()
    return "success", None, None


def run_agent_case(
    run_id: str,
    provider: LLMProvider,
    case: TestCase,
    tools: List[Dict[str, Any]],
    tools_issue: Optional[str],
) -> CaseOutcome:
    log_case_start(run_id, "agent", case, provider)

    if tools_issue:
        return finalize_case(
            CaseOutcome(
                run_id=run_id,
                runner="agent",
                test_case_id=case.case_id,
                test_name=case.name,
                provider=provider_label(provider),
                model=provider.model_name,
                status="blocked",
                latency_ms=0,
                response="",
                expected_behavior=case.expected_behavior,
                failure_type="tools_unavailable",
                notes=tools_issue,
            )
        )

    started_at = perf_counter()
    try:
        agent = ReActAgent(llm=provider, tools=tools)
        response = agent.run(case.prompt)
        latency_ms = int((perf_counter() - started_at) * 1000)
        status, failure_type, notes = classify_agent_response(response)
        return finalize_case(
            CaseOutcome(
                run_id=run_id,
                runner="agent",
                test_case_id=case.case_id,
                test_name=case.name,
                provider=provider_label(provider),
                model=provider.model_name,
                status=status,
                latency_ms=latency_ms,
                response=response,
                expected_behavior=case.expected_behavior,
                failure_type=failure_type,
                notes=notes,
            )
        )
    except Exception as exc:  # pragma: no cover - depends on agent/tool implementation
        latency_ms = int((perf_counter() - started_at) * 1000)
        logger.log_event(
            "CASE_ERROR",
            {
                "run_id": run_id,
                "runner": "agent",
                "test_case_id": case.case_id,
                "failure_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        return finalize_case(
            CaseOutcome(
                run_id=run_id,
                runner="agent",
                test_case_id=case.case_id,
                test_name=case.name,
                provider=provider_label(provider),
                model=provider.model_name,
                status="failure",
                latency_ms=latency_ms,
                response="",
                expected_behavior=case.expected_behavior,
                failure_type=type(exc).__name__,
                notes=str(exc),
            )
        )


def print_outcomes(outcomes: List[CaseOutcome]):
    print("Case results:")
    for outcome in outcomes:
        detail = (
            f"- {outcome.runner} / {outcome.test_case_id} ({outcome.test_name}) -> "
            f"{outcome.status} in {outcome.latency_ms}ms"
        )
        if outcome.failure_type:
            detail += f" [{outcome.failure_type}]"
        print(detail)


def build_summary(log_file: str, run_id: Optional[str]) -> Dict[str, Any]:
    events = load_events(log_file)
    summary = summarize_events(events, run_id=run_id)
    summary["log_file"] = log_file
    tracker_summary = tracker.summarize(run_id=run_id)
    if tracker_summary["requests"] > 0:
        summary["tracker"] = tracker_summary
    return summary


def analyze_existing_log(log_file: str, run_id: Optional[str]) -> int:
    if not os.path.exists(log_file):
        print(f"Log file not found: {log_file}")
        return 1

    summary = build_summary(log_file, run_id)
    print(format_summary(summary))
    return 0


def main() -> int:
    args = parse_args()
    maybe_load_env()

    if args.analyze_only:
        log_file = args.log_file or logger.get_log_file()
        return analyze_existing_log(log_file, args.run_id)

    run_id = args.run_id or f"lab3-{uuid4().hex[:8]}"
    tracker.reset_session()

    try:
        provider, provider_name = resolve_provider(args.provider, args.model)
    except Exception as exc:
        logger.log_event(
            "RUN_BLOCKED",
            {
                "run_id": run_id,
                "reason": str(exc),
                "provider": args.provider,
            },
        )
        print(str(exc))
        return 1

    try:
        selected_cases = select_cases(args.cases)
    except Exception as exc:
        print(str(exc))
        return 1

    tools: List[Dict[str, Any]] = []
    tools_issue: Optional[str] = None
    if args.mode in {"agent", "both"}:
        tools, tools_issue = load_tools(args.tools_module)
        if tools_issue:
            logger.log_event(
                "TOOLS_BLOCKED",
                {
                    "run_id": run_id,
                    "module": args.tools_module,
                    "reason": tools_issue,
                },
            )

    logger.log_event(
        "RUN_START",
        {
            "run_id": run_id,
            "mode": args.mode,
            "provider": provider_name,
            "model": provider.model_name,
            "cases": [case.case_id for case in selected_cases],
        },
    )

    outcomes: List[CaseOutcome] = []
    if args.mode in {"baseline", "both"}:
        for case in selected_cases:
            outcomes.append(run_baseline_case(run_id, provider, case))

    if args.mode in {"agent", "both"}:
        for case in selected_cases:
            outcomes.append(run_agent_case(run_id, provider, case, tools, tools_issue))

    logger.log_event(
        "RUN_END",
        {
            "run_id": run_id,
            "total_cases": len(outcomes),
            "statuses": {
                "success": sum(1 for outcome in outcomes if outcome.status == "success"),
                "failure": sum(1 for outcome in outcomes if outcome.status == "failure"),
                "blocked": sum(1 for outcome in outcomes if outcome.status == "blocked"),
            },
        },
    )

    log_file = logger.get_log_file()
    summary = build_summary(log_file, run_id)
    summary_path = os.path.join("logs", f"summary-{run_id}.json")
    write_summary(summary, summary_path)

    print_outcomes(outcomes)
    print("")
    print(format_summary(summary))
    print(f"Summary written to: {summary_path}")
    return 0
>>>>>>> 6a63230f4bdc83f001bfe87a1d4e68ff3e416de9
=======
>>>>>>> f802a557054a2e097ec44a6ff883d60c0ba2994c


if __name__ == "__main__":
    sys.exit(main())
