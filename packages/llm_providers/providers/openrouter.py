"""OpenRouter LLM provider implementation."""

import os

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from .base import BaseProvider, GenerationResult


class OpenRouterProvider(BaseProvider):
    """OpenRouter LLM provider using the free gpt-oss-20b variant.

    Provides access to various LLM models through OpenRouter's unified API.
    """

    MODEL_NAME = "openai/gpt-oss-20b:free"

<<<<<<<< HEAD:packages/llm_providers/providers/openrouter.py
    def __init__(
        self,
        temperature: float = 0.1,
        timeout: int = 120,
        model_name: str | None = None,
    ):
========
    def __init__(self, temperature: float = 0.1, timeout: int = 120):
>>>>>>>> origin/main:packages/llm_providers/generators/providers/openrouter.py
        """Initialize OpenRouter provider.

        Args:
            temperature: Generation temperature (0.0-2.0)
            timeout: Timeout in seconds for API calls
            model_name: Optional OpenRouter model override

        Raises:
            ValueError: If OPENROUTER_API_KEY environment variable is not set
        """
        super().__init__(temperature, timeout, model_name=model_name)
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found")

        self.llm = ChatOpenAI(
<<<<<<<< HEAD:packages/llm_providers/providers/openrouter.py
            model=self.model_name,
========
            model=self.MODEL_NAME,
>>>>>>>> origin/main:packages/llm_providers/generators/providers/openrouter.py
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
<<<<<<<< HEAD:packages/llm_providers/providers/openrouter.py
        return f"OpenRouter ({self.model_name})"
========
        return f"OpenRouter ({self.MODEL_NAME})"
>>>>>>>> origin/main:packages/llm_providers/generators/providers/openrouter.py

    def generate(self, messages: list[BaseMessage]) -> GenerationResult:
        """Generate content using OpenRouter."""
        return self._track_generation(self.llm.invoke, messages)
