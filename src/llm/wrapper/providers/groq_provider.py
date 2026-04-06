"""Groq LLM provider implementation."""

import os

from langchain_core.messages import BaseMessage
from langchain_groq import ChatGroq

from src.shared import logger
from .base import BaseProvider, GenerationResult


class GroqProvider(BaseProvider):
    """Groq LLM provider using Llama 3.3 70B model.

    Provides fast inference using Groq's optimized LLM infrastructure.
    """

    def __init__(self, temperature: float = 0.1, timeout: int = 120):
        """Initialize Groq provider.

        Args:
            temperature: Generation temperature (0.0-2.0)
            timeout: Timeout in seconds for API calls

        Raises:
            ValueError: If GROQ_API_KEY environment variable is not set
        """
        super().__init__(temperature, timeout)
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found")

        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=api_key,
            temperature=temperature,
            timeout=timeout,
            request_timeout=timeout,
        )

    @property
    def id(self) -> str:
        """Provider identifier."""
        return "groq"

    @property
    def name(self) -> str:
        """Human-readable provider name."""
        return "Groq (Llama 3.1 8B Instant)"

    def generate(self, messages: list[BaseMessage]) -> GenerationResult:
        """Generate content using Groq."""
        return self._track_generation(self.llm.invoke, messages)
