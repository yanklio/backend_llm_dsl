from typing import Optional

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage

from src.shared import logger
from src.shared.config import get_config
from src.shared.exceptions import LLMException

from .providers import (
    BaseProvider,
    GenerationResult,
)

load_dotenv()


def get_provider(provider_id: str, temperature: float, timeout: int) -> BaseProvider:
    """Get provider by ID."""
    from .providers import (
        GeminiProvider,
        GroqProvider,
        OllamaProvider,
        OpenRouterProvider,
    )
    
    providers = {
        "gemini": GeminiProvider,
        "groq": GroqProvider,
        "ollama": OllamaProvider,
        "openrouter": OpenRouterProvider,
    }
    
    if provider_id not in providers:
        raise LLMException(
            f"Unknown provider: {provider_id}. Available: {list(providers.keys())}",
            code="LLM001",
        )
    
    return providers[provider_id](temperature, timeout)


class LLMClient:
    """LLM client with single provider (no fallbacks)."""

    def __init__(
        self,
        provider_id: str = "gemini",
        temperature: Optional[float] = None,
        timeout: Optional[int] = None,
    ):
        """Initialize LLM client.

        Args:
            provider_id: Provider to use (gemini, groq, ollama, openrouter)
            temperature: Generation temperature
            timeout: Timeout in seconds
        """
        config = get_config()
        self.temperature = temperature if temperature is not None else config.llm.temperature
        self.timeout = timeout if timeout is not None else config.llm.timeout
        self.provider_id = provider_id
        self.provider = get_provider(provider_id, self.temperature, self.timeout)
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
