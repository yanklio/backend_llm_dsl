"""Base provider interface for LLM integrations.

Defines the abstract interface that all LLM providers must implement,
along with common utilities for tracking generation metrics.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from langchain_core.messages import BaseMessage

from src.shared.utils import clean_llm_response


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
    """

    content: str
    provider: str
    duration_seconds: float
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    model_name: Optional[str] = None


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, temperature: float = 0.1, timeout: int = 120):
        """Initialize the provider.

        Args:
            temperature: Temperature for generation (0.0-2.0)
            timeout: Timeout in seconds for API calls
        """
        self.temperature = temperature
        self.timeout = timeout

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
        start_time = time.time()
        response = llm_invoke_func(messages)
        end_time = time.time()

        content = str(response.content)

        # Clean markdown using shared utility
        content = clean_llm_response(content)

        # Extract Usage Metadata
        usage = {}
        if hasattr(response, "response_metadata") and "token_usage" in response.response_metadata:
            usage = response.response_metadata["token_usage"]
        elif hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = response.usage_metadata

        input_tokens = usage.get("prompt_tokens") or usage.get("input_tokens")
        output_tokens = usage.get("completion_tokens") or usage.get("output_tokens")
        total_tokens = usage.get("total_tokens")

        return GenerationResult(
            content=content,
            provider=self.name,
            duration_seconds=round(end_time - start_time, 2),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )
