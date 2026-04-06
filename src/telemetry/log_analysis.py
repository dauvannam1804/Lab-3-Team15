import json
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional


def load_events(log_path: str) -> List[Dict[str, Any]]:
    """Loads JSON events from a log file, skipping non-JSON lines."""
    events: List[Dict[str, Any]] = []
    with open(log_path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and "event" in payload and "data" in payload:
                events.append(payload)
    return events


def summarize_events(events: List[Dict[str, Any]], run_id: Optional[str] = None) -> Dict[str, Any]:
    """Aggregates case and metric events into a report-friendly summary."""
    case_results: List[Dict[str, Any]] = []
    llm_metrics: List[Dict[str, Any]] = []

    for event in events:
        data = event.get("data", {})
        if run_id and data.get("run_id") != run_id:
            context = data.get("context", {})
            if context.get("run_id") != run_id:
                continue

        if event["event"] == "CASE_RESULT":
            case_results.append(data)
        elif event["event"] == "LLM_METRIC":
            llm_metrics.append(data)

    runner_summary: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "cases_total": 0,
            "success": 0,
            "failure": 0,
            "blocked": 0,
            "avg_case_latency_ms": 0.0,
            "total_case_latency_ms": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "llm_requests": 0,
            "failure_types": Counter(),
        }
    )

    for result in case_results:
        runner = result["runner"]
        bucket = runner_summary[runner]
        bucket["cases_total"] += 1
        bucket[result["status"]] += 1
        bucket["total_case_latency_ms"] += result.get("latency_ms", 0)
        if result.get("failure_type"):
            bucket["failure_types"][result["failure_type"]] += 1

    for metric in llm_metrics:
        context = metric.get("context", {})
        runner = context.get("runner", "unscoped")
        bucket = runner_summary[runner]
        bucket["prompt_tokens"] += metric.get("prompt_tokens", 0)
        bucket["completion_tokens"] += metric.get("completion_tokens", 0)
        bucket["total_tokens"] += metric.get("total_tokens", 0)
        bucket["llm_requests"] += 1

    failures: List[Dict[str, Any]] = []
    for result in case_results:
        if result["status"] != "success":
            failures.append(
                {
                    "runner": result["runner"],
                    "test_case_id": result["test_case_id"],
                    "test_name": result["test_name"],
                    "failure_type": result.get("failure_type"),
                    "notes": result.get("notes"),
                }
            )

    by_runner: Dict[str, Dict[str, Any]] = {}
    for runner, bucket in runner_summary.items():
        cases_total = bucket["cases_total"]
        avg_latency = 0.0 if cases_total == 0 else bucket["total_case_latency_ms"] / cases_total
        by_runner[runner] = {
            "cases_total": cases_total,
            "success": bucket["success"],
            "failure": bucket["failure"],
            "blocked": bucket["blocked"],
            "avg_case_latency_ms": round(avg_latency, 2),
            "prompt_tokens": bucket["prompt_tokens"],
            "completion_tokens": bucket["completion_tokens"],
            "total_tokens": bucket["total_tokens"],
            "llm_requests": bucket["llm_requests"],
            "failure_types": dict(bucket["failure_types"]),
        }

    return {
        "run_id": run_id,
        "case_results": case_results,
        "failures": failures,
        "by_runner": by_runner,
    }


def write_summary(summary: Dict[str, Any], output_path: str):
    """Writes a machine-readable summary JSON file."""
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)


def format_summary(summary: Dict[str, Any]) -> str:
    """Builds a short human-readable summary for console usage."""
    lines = []
    run_id = summary.get("run_id")
    if run_id:
        lines.append(f"Run ID: {run_id}")

    by_runner = summary.get("by_runner", {})
    if not by_runner:
        lines.append("No matching telemetry events found.")
        return "\n".join(lines)

    lines.append("Runner summary:")
    for runner, bucket in by_runner.items():
        lines.append(
            "- "
            f"{runner}: "
            f"cases={bucket['cases_total']}, "
            f"success={bucket['success']}, "
            f"failure={bucket['failure']}, "
            f"blocked={bucket['blocked']}, "
            f"avg_case_latency_ms={bucket['avg_case_latency_ms']}, "
            f"total_tokens={bucket['total_tokens']}, "
            f"llm_requests={bucket['llm_requests']}"
        )

    failures = summary.get("failures", [])
    if failures:
        lines.append("Failures:")
        for failure in failures:
            lines.append(
                "- "
                f"{failure['runner']} / {failure['test_case_id']}: "
                f"{failure.get('failure_type') or 'unknown'}"
            )

    return "\n".join(lines)
