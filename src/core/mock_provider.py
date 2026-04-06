from typing import Dict, Any, Optional, Generator

from src.core.llm_provider import LLMProvider


class MockProvider(LLMProvider):
    """
    Deterministic provider for smoke-testing the QA pipeline without real APIs.
    It intentionally behaves like a weak baseline chatbot.
    """

    def __init__(self, model_name: str = "mock-baseline"):
        super().__init__(model_name=model_name, api_key=None)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        content = self._build_response(prompt)
        prompt_tokens = self._count_tokens(prompt) + self._count_tokens(system_prompt or "")
        completion_tokens = self._count_tokens(content)

        return {
            "content": content,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            "latency_ms": 25,
            "provider": "mock",
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        yield self._build_response(prompt)

    def _build_response(self, prompt: str) -> str:
        lowered = prompt.lower()

        if "hà nội" in lowered and "sài gòn" in lowered:
            return "Tôi tìm thấy chuyến bay VN999 từ Hà Nội đi Sài Gòn giá khoảng 99 USD và có thể đặt luôn."
        if "vn213" in lowered:
            return "Tôi đã đặt chuyến VN213 thành công cho Nguyen Van A. Mã đặt chỗ là PNR123."
        if "vj122" in lowered:
            return "Tôi đã xử lý xong chuyến VJ122 và mã đặt chỗ của bạn là SAFE88."
        if "hành lý" in lowered or "bao nhiêu kg" in lowered:
            return "Vietnam Airlines thường cho mang khoảng 20kg hành lý ký gửi."
        if "thời tiết" in lowered:
            return "Sài Gòn nhìn chung nắng và khá nóng, bạn nên chuẩn bị quần áo mỏng."
        return "Tôi nghĩ yêu cầu này có thể xử lý được, nhưng tôi chưa có dữ liệu hệ thống để xác nhận."

    @staticmethod
    def _count_tokens(text: str) -> int:
        return max(1, len(text.split())) if text else 0
