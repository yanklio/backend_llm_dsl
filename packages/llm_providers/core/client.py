from typing import Optional

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage

from packages.shared import logger
from packages.shared.config import get_config
from packages.shared.exceptions import LLMException

from ..providers import (
    BaseProvider,
    GenerationResult,
)

load_dotenv()


def _provider_registry() -> dict[str, type[BaseProvider]]:
    """Return the mapping of provider IDs to provider classes."""
    from ..providers import GeminiProvider, GroqProvider, OllamaProvider, OpenRouterProvider

    return {
        "gemini": GeminiProvider,
        "groq": GroqProvider,
        "ollama": OllamaProvider,
        "openrouter": OpenRouterProvider,
    }


def get_default_model_name(provider_id: str) -> str:
    """Return the default model name for a provider, or 'unknown'."""
    providers = _provider_registry()
    if provider_id not in providers:
        return "unknown"
    return providers[provider_id].MODEL_NAME


def get_provider(
    provider_id: str,
    temperature: float,
    timeout: int,
    model_name: Optional[str] = None,
) -> BaseProvider:
    """Get provider by ID."""
    providers = _provider_registry()

    if provider_id not in providers:
        raise LLMException(
            f"Unknown provider: {provider_id}. Available: {list(providers.keys())}",
            code="LLM001",
        )

    return providers[provider_id](temperature, timeout, model_name=model_name)


class LLMClient:
    """LLM client with single provider (no fallbacks)."""

    def __init__(
        self,
        provider_id: str = "openrouter",
        temperature: Optional[float] = None,
        timeout: Optional[int] = None,
        model_name: Optional[str] = None,
    ):
        """Initialize LLM client.

        Args:
            provider_id: Provider to use (gemini, groq, ollama, openrouter)
            temperature: Generation temperature
            timeout: Timeout in seconds
            model_name: Optional provider model override
        """
        config = get_config()
        self.temperature = temperature if temperature is not None else config.llm.temperature
        self.timeout = timeout if timeout is not None else config.llm.timeout
        self.provider_id = provider_id
        self.provider = get_provider(
            provider_id,
            self.temperature,
            self.timeout,
            model_name=model_name,
        )
        logger.info(f"✓ Using {self.provider.name}")

    def generate(self, messages: list[BaseMessage]) -> GenerationResult:
        """Generate content using the configured provider.

        Args:
            messages: List of conversation messages.

        Returns:
            GenerationResult: The generated content and metadata.

        Raises:
            LLMException: If generation fails
        """
        try:
            logger.info(f"Using provider: {self.provider.name}")
            return self.provider.generate(messages)
        except Exception as e:
            raise LLMException(
                f"{self.provider.name} failed: {e}",
                code="LLM002",
                context={"provider": self.provider_id, "error": str(e)},
            )
