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
        is_react = system_prompt and ("react" in system_prompt.lower() or "thought:" in system_prompt.lower())
        content = self._build_response(prompt, is_react=is_react)
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
        is_react = system_prompt and ("react" in system_prompt.lower() or "thought:" in system_prompt.lower())
        yield self._build_response(prompt, is_react=is_react)

    def _build_response(self, prompt: str, is_react: bool = False) -> str:
        lowered = prompt.lower()
        base_res = "Tôi nghĩ yêu cầu này có thể xử lý được, nhưng tôi chưa có dữ liệu hệ thống để xác nhận."
        if "hà nội" in lowered and "sài gòn" in lowered:
            base_res = "Tôi tìm thấy chuyến bay VN999 từ Hà Nội đi Sài Gòn giá khoảng 99 USD và có thể đặt luôn."
        elif "vn213" in lowered:
            base_res = "Tôi đã đặt chuyến VN213 thành công cho Nguyen Van A. Mã đặt chỗ là PNR123."
        elif "vj122" in lowered:
            base_res = "Tôi đã xử lý xong chuyến VJ122 và mã đặt chỗ của bạn là SAFE88."
        elif "hành lý" in lowered or "bao nhiêu kg" in lowered:
            base_res = "Vietnam Airlines thường cho mang khoảng 20kg hành lý ký gửi."
        elif "thời tiết" in lowered:
            base_res = "Sài Gòn nhìn chung nắng và khá nóng, bạn nên chuẩn bị quần áo mỏng."

        if is_react or "thought:" in lowered:
            return f"Thought: Tôi đã nhận được yêu cầu.\nFinal Answer: {base_res}"
        return base_res

    @staticmethod
    def _count_tokens(text: str) -> int:
        return max(1, len(text.split())) if text else 0
