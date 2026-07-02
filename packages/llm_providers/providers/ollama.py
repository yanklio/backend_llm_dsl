"""Ollama local LLM provider implementation."""

import requests
from langchain_core.messages import BaseMessage
from langchain_ollama import ChatOllama

from .base import BaseProvider, GenerationResult


class OllamaProvider(BaseProvider):
    """Ollama local LLM provider using Llama 3.1 model.

    Provides local LLM inference using Ollama running on localhost.
    """

    MODEL_NAME = "llama3.1"

    def __init__(
        self,
        temperature: float = 0.1,
        timeout: int = 120,
        model_name: str | None = None,
    ):
        """Initialize Ollama provider.

        Args:
            temperature: Generation temperature (0.0-2.0)
            timeout: Timeout in seconds for API calls
            model_name: Optional model override

        Raises:
            ConnectionError: If Ollama is not running on localhost:11434
        """
        super().__init__(temperature, timeout, model_name=model_name)

        # Check connection eagerly
        try:
            requests.get("http://localhost:11434", timeout=1)
        except Exception:
            raise ConnectionError("Ollama is not running on localhost:11434")

        self.llm = ChatOllama(
            model=self.model_name,
            temperature=temperature,
            timeout=timeout,
        )

    @property
    def id(self) -> str:
        """Provider identifier."""
        return "ollama"

    @property
    def name(self) -> str:
        """Human-readable provider name."""
        return f"Ollama ({self.model_name})"

    def generate(self, messages: list[BaseMessage]) -> GenerationResult:
        """Generate content using Ollama."""
        return self._track_generation(self.llm.invoke, messages)
