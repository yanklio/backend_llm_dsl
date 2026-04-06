"""OpenRouter LLM provider implementation."""

import os

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from .base import BaseProvider, GenerationResult


class OpenRouterProvider(BaseProvider):
    """OpenRouter LLM provider using Gemini 2.0 Flash (free tier).

    Provides access to various LLM models through OpenRouter's unified API.
    """
    def __init__(self, temperature: float = 0.1, timeout: int = 120):
        """Initialize OpenRouter provider.

        Args:
            temperature: Generation temperature (0.0-2.0)
            timeout: Timeout in seconds for API calls

        Raises:
            ValueError: If OPENROUTER_API_KEY environment variable is not set
        """
        super().__init__(temperature, timeout)
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found")

        self.llm = ChatOpenAI(
            model="google/gemini-2.0-flash:free",
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=temperature,
            timeout=timeout,
            request_timeout=timeout,
        )

    @property
    def id(self) -> str:
        """Provider identifier."""
        return "openrouter"

    @property
    def name(self) -> str:
        """Human-readable provider name."""
        return "OpenRouter (Gemini Free)"

    def generate(self, messages: list[BaseMessage]) -> GenerationResult:
        """Generate content using OpenRouter."""
        return self._track_generation(self.llm.invoke, messages)
