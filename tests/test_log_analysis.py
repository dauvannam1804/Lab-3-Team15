import os
import sys


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from src.telemetry.log_analysis import format_summary, summarize_events


def test_summarize_events_groups_metrics_and_failures():
    events = [
        {
            "event": "CASE_RESULT",
            "data": {
                "run_id": "run-1",
                "runner": "baseline",
                "test_case_id": "TC1",
                "test_name": "Flight search",
                "status": "success",
                "latency_ms": 120,
            },
        },
        {
            "event": "CASE_RESULT",
            "data": {
                "run_id": "run-1",
                "runner": "agent",
                "test_case_id": "TC1",
                "test_name": "Flight search",
                "status": "blocked",
                "latency_ms": 0,
                "failure_type": "agent_not_implemented",
                "notes": "still skeleton",
            },
        },
        {
            "event": "LLM_METRIC",
            "data": {
                "provider": "mock",
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
                "latency_ms": 25,
                "context": {
                    "run_id": "run-1",
                    "runner": "baseline",
                    "test_case_id": "TC1",
                },
            },
        },
        {
            "event": "CASE_RESULT",
            "data": {
                "run_id": "run-2",
                "runner": "baseline",
                "test_case_id": "TC9",
                "test_name": "Ignored",
                "status": "failure",
                "latency_ms": 999,
            },
        },
    ]

    summary = summarize_events(events, run_id="run-1")

    assert summary["by_runner"]["baseline"]["cases_total"] == 1
    assert summary["by_runner"]["baseline"]["total_tokens"] == 15
    assert summary["by_runner"]["agent"]["blocked"] == 1
    assert summary["by_runner"]["agent"]["failure_types"]["agent_not_implemented"] == 1
    assert len(summary["failures"]) == 1
    assert summary["failures"][0]["runner"] == "agent"


def test_format_summary_contains_runner_lines():
    summary = {
        "run_id": "run-42",
        "by_runner": {
            "baseline": {
                "cases_total": 5,
                "success": 5,
                "failure": 0,
                "blocked": 0,
                "avg_case_latency_ms": 55.2,
                "total_tokens": 120,
                "llm_requests": 5,
            }
        },
        "failures": [],
    }

    text = format_summary(summary)

    assert "Run ID: run-42" in text
    assert "baseline: cases=5" in text
    assert "total_tokens=120" in text
