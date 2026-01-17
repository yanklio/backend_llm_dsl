
import os
from typing import List, Optional

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage

from src.shared import logger
from .providers import (
    BaseProvider, 
    GenerationResult,
    GroqProvider, 
    OpenRouterProvider, 
    GeminiProvider, 
    OllamaProvider
)

load_dotenv()

class LLMClient:
    """
    Manages multiple LLM providers with fallback support.
    """

    def __init__(self, temperature: float = 0.1):
        self.temperature = temperature
        self.providers: List[BaseProvider] = []
        self._setup_providers()

    def _setup_providers(self):
        """Setup providers based on availability and configure them."""
        
        # 1. Groq
        try:
            self.providers.append(GroqProvider(self.temperature))
            logger.info("✓ Groq provider configured")
        except Exception as e:
            logger.warn(f"Groq setup failed: {e}")

        # 2. OpenRouter
        try:
            self.providers.append(OpenRouterProvider(self.temperature))
            logger.info("✓ OpenRouter provider configured")
        except Exception as e:
            logger.warn(f"OpenRouter setup failed: {e}")

        # 3. Google Gemini
        try:
            self.providers.append(GeminiProvider(self.temperature))
            logger.info("✓ Google Gemini provider configured")
        except Exception as e:
            logger.warn(f"Gemini setup failed: {e}")

        # 4. Ollama (Local)
        try:
            self.providers.append(OllamaProvider(self.temperature))
            logger.info("✓ Ollama (local) provider configured")
        except Exception:
            pass # Silent fail for optional local provider

        if not self.providers:
            logger.error("❌ No LLM providers configured!")
            logger.info("Please set one of these environment variables:")
            logger.info("  - GROQ_API_KEY")
            logger.info("  - OPENROUTER_API_KEY")
            logger.info("  - GOOGLE_API_KEY")
            logger.info("Or install Ollama locally")

    def generate(self, messages: List[BaseMessage], primary_provider_id: Optional[str] = None) -> GenerationResult:
        """
        Generate content using available providers.
        
        Args:
            messages: List of conversation messages.
            primary_provider_id: ID of the provider to try first (groq, openrouter, gemini, ollama).
        """
        if not self.providers:
            raise Exception("No LLM providers available")

        # Create execution order
        execution_list = self.providers.copy()
        
        # If primary provider requested, move it to front
        if primary_provider_id:
            primary = next((p for p in execution_list if p.id == primary_provider_id), None)
            if primary:
                execution_list.remove(primary)
                execution_list.insert(0, primary)
            else:
                logger.warn(f"Requested primary provider '{primary_provider_id}' not found/configured.")

        for i, provider in enumerate(execution_list):
            try:
                logger.info(f"Trying provider: {provider.name}")
                return provider.generate(messages)

            except Exception as e:
                logger.warning(f"✗ {provider.name} failed: {e}")
                if i < len(execution_list) - 1:
                    logger.info("Trying next provider...")
        
        raise Exception("All providers failed to generate content")
