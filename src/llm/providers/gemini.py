"""Google Gemini LLM provider implementation."""

import os

from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .base import BaseProvider, GenerationResult


class GeminiProvider(BaseProvider):
    """Google Gemini LLM provider using Gemini 2.0 Flash model.

    Provides fast and efficient inference using Google's Gemini models.
    """

    MODEL_NAME = "gemma-4-31b-it"

    def __init__(
        self,
        temperature: float = 0.1,
        timeout: int = 120,
        model_name: str | None = None,
    ):
        """Initialize Gemini provider.

        Args:
            temperature: Generation temperature (0.0-2.0)
            timeout: Timeout in seconds for API calls
            model_name: Optional model override

        Raises:
            ValueError: If GOOGLE_API_KEY environment variable is not set
        """
        super().__init__(temperature, timeout, model_name=model_name)
        if not os.getenv("GOOGLE_API_KEY"):
            raise ValueError("GOOGLE_API_KEY not found")

        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            temperature=temperature,
            timeout=timeout,
        )

    @property
    def id(self) -> str:
        """Provider identifier."""
        return "gemini"

    @property
    def name(self) -> str:
        """Human-readable provider name."""
        return f"Google Gemini ({self.MODEL_NAME})"

    def generate(self, messages: list[BaseMessage]) -> GenerationResult:
        """Generate content using Gemini."""
        return self._track_generation(self.llm.invoke, messages)
