from typing import Optional

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage

from src.shared import logger
from src.shared.config import get_config
from src.shared.exceptions import (
    LLMConnectionException,
    LLMException,
    LLMProviderException,
    LLMTimeoutException,
)

from .providers import (
    BaseProvider,
    GeminiProvider,
    GenerationResult,
    GroqProvider,
    OllamaProvider,
    OpenRouterProvider,
)

load_dotenv()


def _try_add_provider(
    providers: list[BaseProvider],
    provider_class: type[BaseProvider],
    name: str,
    temperature: Optional[float],
    timeout: Optional[int],
) -> None:
    """Try to instantiate and add a provider, handling exceptions gracefully.

    Args:
        providers: List to add provider to.
        provider_class: The provider class to instantiate.
        name: Human-readable name for logging.
        temperature: Temperature setting.
        timeout: Timeout setting.
    """
    try:
        providers.append(provider_class(temperature, timeout))
        logger.info(f"✓ {name} provider configured")
    except (ValueError, ConnectionError) as e:
        logger.warn(f"{name} setup failed: {e}")
    except Exception as e:
        logger.warn(f"{name} setup failed with unexpected error: {e}")


class LLMClient:
    """Manages multiple LLM providers with fallback support."""

    def __init__(self, temperature: Optional[float] = None, timeout: Optional[int] = None):
        """Initialize the LLM client.

        Args:
            temperature: Temperature setting for LLM generation (uses config default if None)
            timeout: Timeout in seconds for API calls (uses config default if None)
        """
        config = get_config()
        self.temperature = temperature if temperature is not None else config.llm.temperature
        self.timeout = timeout if timeout is not None else config.llm.timeout
        self.providers: list[BaseProvider] = []
        self._setup_providers()

    def _setup_providers(self) -> None:
        """Setup providers based on availability and configure them."""
        _try_add_provider(self.providers, GroqProvider, "Groq", self.temperature, self.timeout)
        _try_add_provider(
            self.providers, OpenRouterProvider, "OpenRouter", self.temperature, self.timeout
        )
        _try_add_provider(
            self.providers, GeminiProvider, "Google Gemini", self.temperature, self.timeout
        )
        _try_add_provider(
            self.providers, OllamaProvider, "Ollama (local)", self.temperature, self.timeout
        )

        if not self.providers:
            logger.error("❌ No LLM providers configured!")
            logger.info("Please set one of these environment variables:")
            logger.info("  - GROQ_API_KEY")
            logger.info("  - OPENROUTER_API_KEY")
            logger.info("  - GOOGLE_API_KEY")
            logger.info("Or install Ollama locally")

    def generate(
        self, messages: list[BaseMessage], primary_provider_id: Optional[str] = None
    ) -> GenerationResult:
        """Generate content using available providers.

        Args:
            messages: List of conversation messages.
            primary_provider_id: ID of the provider to try first (groq, openrouter, gemini, ollama).

        Returns:
            GenerationResult: The generated content and metadata.

        Raises:
            LLMException: If no providers are available
            LLMException: If all providers fail to generate content
        """
        if not self.providers:
            raise LLMException(
                "No LLM providers available", code="LLM001", context={"configured_providers": 0}
            )

        execution_list = self.providers.copy()

        if primary_provider_id:
            primary = next((p for p in execution_list if p.id == primary_provider_id), None)
            if primary:
                execution_list.remove(primary)
                execution_list.insert(0, primary)
            else:
                logger.warn(
                    f"Requested primary provider '{primary_provider_id}' not found/configured."
                )

        last_error = None
        for i, provider in enumerate(execution_list):
            try:
                logger.info(f"Trying provider: {provider.name}")
                return provider.generate(messages)

            except TimeoutError as e:
                last_error = LLMTimeoutException(
                    f"{provider.name} timed out after {self.timeout}s: {e}",
                    code="LLM002",
                    context={"provider": provider.id, "timeout": self.timeout},
                )
                logger.warn(f"✗ {provider.name} timed out: {e}")
                if i < len(execution_list) - 1:
                    logger.info("Trying next provider...")

            except ConnectionError as e:
                last_error = LLMConnectionException(
                    f"{provider.name} connection failed: {e}",
                    code="LLM003",
                    context={"provider": provider.id},
                )
                logger.warn(f"✗ {provider.name} connection failed: {e}")
                if i < len(execution_list) - 1:
                    logger.info("Trying next provider...")

            except Exception as e:
                last_error = LLMProviderException(
                    f"{provider.name} failed: {e}",
                    code="LLM004",
                    context={"provider": provider.id, "error": str(e)},
                )
                logger.warn(f"✗ {provider.name} failed: {e}")
                if i < len(execution_list) - 1:
                    logger.info("Trying next provider...")

        raise LLMException(
            "All providers failed to generate content",
            code="LLM005",
            context={
                "tried_providers": [p.id for p in execution_list],
                "last_error": str(last_error) if last_error else None,
            },
        )
