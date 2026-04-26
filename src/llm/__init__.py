"""LLM generation entry points and provider abstractions."""

from .client import LLMClient
from .providers import GenerationResult

__all__ = ["LLMClient", "GenerationResult"]
