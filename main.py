import argparse
import importlib
import os
import sys
from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is listed in requirements.txt
    load_dotenv = None

from src.agent.agent import ReActAgent
from src.core.llm_provider import LLMProvider
from src.core.mock_provider import MockProvider
from src.telemetry.log_analysis import format_summary, load_events, summarize_events, write_summary
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker


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
    TestCase(
    case_id="TC6",
    name="Out-of-domain adversarial query",
        prompt="So sánh giúp tôi triết lý của chủ nghĩa khắc kỷ với Phật giáo, và cho lời khuyên về cách áp dụng vào cuộc sống hiện đại.",
        expected_behavior="Nhận diện đây là câu hỏi ngoài domain (không liên quan đến flight/booking/weather/baggage)."
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Lab 3 baseline/agent QA scenarios and summarize telemetry."
    )
    parser.add_argument(
        "--mode",
        choices=["baseline", "agent_v1", "agent_v2", "all"],
        default="agent_v2",
        help="Which runner(s) to execute.",
    )
    parser.add_argument(
        "--provider",
        choices=["auto", "openai", "google", "gemini", "local", "mock"],
        default="auto",
        help="LLM provider to use. 'mock' is useful for smoke tests without API access.",
    )
    parser.add_argument("--model", default=None, help="Override the model name when supported.")
    parser.add_argument(
        "--cases",
        default="all",
        help="Comma-separated case IDs (e.g. TC1,TC3) or 'all'.",
    )
    parser.add_argument(
        "--tools-module",
        default="src.tools.flight_tools",
        help="Python module that exposes agent tools.",
    )
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Skip execution and only analyze an existing log file.",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Log file to analyze. Defaults to today's log file.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional run_id filter. When omitted for execution, a new run_id is generated.",
    )
    return parser.parse_args()


def maybe_load_env():
    if load_dotenv is not None:
        load_dotenv()


def _clean_env_value(value: Optional[str]) -> str:
    if value is None:
        return ""
    return value.strip().strip("\"'").strip()


def _is_placeholder_secret(value: str) -> bool:
    normalized = _clean_env_value(value).lower()
    return normalized in {
        "",
        "your_openai_api_key_here",
        "your_gemini_api_key_here",
    }


def _infer_auto_provider(model_name: str) -> str:
    normalized_model = model_name.lower()
    openai_key = _clean_env_value(os.getenv("OPENAI_API_KEY"))
    gemini_key = _clean_env_value(os.getenv("GEMINI_API_KEY"))

    if normalized_model.startswith("gemini") and not _is_placeholder_secret(gemini_key):
        return "gemini"
    if normalized_model.startswith(("gpt", "o1", "o3", "o4")) and not _is_placeholder_secret(openai_key):
        return "openai"
    if not _is_placeholder_secret(gemini_key):
        return "gemini"
    if not _is_placeholder_secret(openai_key):
        return "openai"
    return "mock"


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
    if "agent could not complete the task within the maximum number of steps" in normalized:
        return "failure", "max_steps_reached", "Agent timed out (max steps reached) without giving a Final Answer."
    return "success", None, None


def run_agent_case(
    run_id: str,
    provider: LLMProvider,
    case: TestCase,
    tools: List[Dict[str, Any]],
    tools_issue: Optional[str],
    version: str = "v2",
) -> CaseOutcome:
    runner_name = f"agent_{version}"
    log_case_start(run_id, runner_name, case, provider)

    if tools_issue:
        return finalize_case(
            CaseOutcome(
                run_id=run_id,
                runner=runner_name,
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
        agent = ReActAgent(llm=provider, tools=tools, version=version)
        context = {
            "run_id": run_id,
            "runner": runner_name,
            "test_case_id": case.case_id,
            "test_name": case.name,
        }
        response = agent.run(case.prompt, context=context)
        latency_ms = int((perf_counter() - started_at) * 1000)
        status, failure_type, notes = classify_agent_response(response)
        return finalize_case(
            CaseOutcome(
                run_id=run_id,
                runner=runner_name,
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
        print(f"Error in {runner_name} case {case.case_id}: {exc}")
        logger.log_event(
            "CASE_ERROR",
            {
                "run_id": run_id,
                "runner": runner_name,
                "test_case_id": case.case_id,
                "failure_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        return finalize_case(
            CaseOutcome(
                run_id=run_id,
                runner=runner_name,
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
    
    # Determine modes to run
    modes_to_run = [args.mode]
    if args.mode == "all":
        modes_to_run = ["baseline", "agent_v1", "agent_v2"]

    # Load tools if any agent mode is requested
    if any(m.startswith("agent_") for m in modes_to_run):
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
            "modes": modes_to_run,
            "provider": provider_name,
            "model": provider.model_name,
            "cases": [case.case_id for case in selected_cases],
        },
    )

    outcomes: List[CaseOutcome] = []
    
    for mode in modes_to_run:
        print(f"\n>>> Running mode: {mode}")
        if mode == "baseline":
            for case in selected_cases:
                outcomes.append(run_baseline_case(run_id, provider, case))
        elif mode.startswith("agent_"):
            version = mode.split("_")[1]
            for case in selected_cases:
                outcomes.append(run_agent_case(run_id, provider, case, tools, tools_issue, version=version))

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


if __name__ == "__main__":
    sys.exit(main())
