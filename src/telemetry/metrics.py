from collections import Counter
from typing import Dict, Any, Optional
from src.telemetry.logger import logger

class PerformanceTracker:
    """
    Tracking industry-standard metrics for LLMs.
    """
    def __init__(self):
        self.session_metrics = []

    def track_request(
        self,
        provider: str,
        model: str,
        usage: Dict[str, int],
        latency_ms: int,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Logs a single request metric to our telemetry.
        """
        metric = {
            "provider": provider,
            "model": model,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "latency_ms": latency_ms,
            "cost_estimate": self._calculate_cost(model, usage) # Mock cost calculation
        }
        if context:
            metric["context"] = context
        self.session_metrics.append(metric)
        logger.log_event("LLM_METRIC", metric)

    def _calculate_cost(self, model: str, usage: Dict[str, int]) -> float:
        """
        TODO: Implement real pricing logic.
        For now, returns a dummy constant.
        """
        return (usage.get("total_tokens", 0) / 1000) * 0.01

    def reset_session(self):
        """Clears in-memory metrics collected during the current process."""
        self.session_metrics.clear()

    def summarize(self, run_id: Optional[str] = None) -> Dict[str, Any]:
        """Builds a compact summary for the current process metrics."""
        scoped_metrics = []
        for metric in self.session_metrics:
            context = metric.get("context", {})
            if run_id and context.get("run_id") != run_id:
                continue
            scoped_metrics.append(metric)

        if not scoped_metrics:
            return {
                "requests": 0,
                "avg_latency_ms": 0.0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_tokens": 0,
                "total_cost_estimate": 0.0,
                "providers": {},
            }

        total_prompt_tokens = sum(metric["prompt_tokens"] for metric in scoped_metrics)
        total_completion_tokens = sum(metric["completion_tokens"] for metric in scoped_metrics)
        total_tokens = sum(metric["total_tokens"] for metric in scoped_metrics)
        total_latency_ms = sum(metric["latency_ms"] for metric in scoped_metrics)
        total_cost_estimate = sum(metric["cost_estimate"] for metric in scoped_metrics)

        providers = Counter(metric["provider"] for metric in scoped_metrics)

        return {
            "requests": len(scoped_metrics),
            "avg_latency_ms": round(total_latency_ms / len(scoped_metrics), 2),
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_tokens": total_tokens,
            "total_cost_estimate": round(total_cost_estimate, 6),
            "providers": dict(providers),
        }

# Global tracker instance
tracker = PerformanceTracker()
