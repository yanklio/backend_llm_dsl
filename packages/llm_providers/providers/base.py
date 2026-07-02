"""Base provider interface for LLM integrations.

Defines the abstract interface that all LLM providers must implement,
along with common utilities for tracking generation metrics.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from langchain_core.messages import BaseMessage

from packages.llm_providers.core.response_parser import clean_llm_response

TOKEN_USAGE_KEYS = {
    "input_tokens": ("prompt_tokens", "input_tokens"),
    "output_tokens": ("completion_tokens", "output_tokens"),
    "total_tokens": ("total_tokens",),
}


@dataclass
class GenerationResult:
    """Result of an LLM generation request.

    Attributes:
        content: Generated text content
        provider: Name of the provider that generated the content
        duration_seconds: Time taken for generation in seconds
        input_tokens: Number of input tokens (if available)
        output_tokens: Number of output tokens (if available)
        total_tokens: Total tokens used (if available)
        model_name: Name of the model used (if available)
        raw_content: Original provider response before parser cleanup (if changed)
    """

    content: str
    provider: str
    duration_seconds: float
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    model_name: Optional[str] = None
    raw_content: Optional[str] = None


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    MODEL_NAME = "unknown"

    def __init__(
        self,
        temperature: float = 0.1,
        timeout: int = 120,
        model_name: Optional[str] = None,
    ):
        """Initialize the provider.

        Args:
            temperature: Temperature for generation (0.0-2.0)
            timeout: Timeout in seconds for API calls
            model_name: Optional model override for this provider instance
        """
        self.temperature = temperature
        self.timeout = timeout
        self._model_name = model_name or self.MODEL_NAME

    @property
    @abstractmethod
    def id(self) -> str:
        """Unique identifier for the provider (e.g., 'groq')."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Display name for the provider."""
        pass

    @property
    def model_name(self) -> str:
        """Exact model identifier used by this provider."""
        return self._model_name

    @abstractmethod
    def generate(self, messages: list[BaseMessage]) -> GenerationResult:
        """Generate content from messages.

        Args:
            messages: List of conversation messages

        Returns:
            GenerationResult with content and statistics
        """
        pass

    def _track_generation(self, llm_invoke_func, messages: list[BaseMessage]) -> GenerationResult:
        """Helper to measure time and capture standard LangChain usage metadata.

        Most providers can use this if they implement standard LangChain invoke.

        Args:
            llm_invoke_func: LangChain LLM invoke function
            messages: List of conversation messages

        Returns:
            GenerationResult with tracked metrics
        """
        start_time = time.perf_counter()
        response = llm_invoke_func(messages)
        duration_seconds = round(time.perf_counter() - start_time, 2)
        usage = _extract_usage_metadata(response)

        token_stats = {
            field_name: _resolve_usage_value(usage, candidate_keys)
            for field_name, candidate_keys in TOKEN_USAGE_KEYS.items()
        }

        return GenerationResult(
            content=clean_llm_response(str(response.content)),
            provider=self.name,
            duration_seconds=duration_seconds,
            input_tokens=token_stats["input_tokens"],
            output_tokens=token_stats["output_tokens"],
            total_tokens=token_stats["total_tokens"],
            model_name=self.model_name,
        )


def _extract_usage_metadata(response: Any) -> dict:
    """Extract token usage metadata from a LangChain response object."""
    if hasattr(response, "response_metadata") and "token_usage" in response.response_metadata:
        return response.response_metadata["token_usage"]
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        return response.usage_metadata
    return {}


def _resolve_usage_value(usage: dict[str, Any], candidate_keys: tuple[str, ...]) -> Any:
    """Return the first available token usage value for the given keys."""
    for key in candidate_keys:
        if key in usage:
            return usage[key]
    return None
