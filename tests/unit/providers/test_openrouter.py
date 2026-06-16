"""Tests for OpenRouterProvider."""

from unittest.mock import patch

import pytest

MODEL_NAME = "openai/gpt-oss-20b:free"


class TestOpenRouterProviderModelName:
    """Tests for the MODEL_NAME constant."""

    def test_model_name_constant(self):
        from src.llm.providers.openrouter import OpenRouterProvider

        assert OpenRouterProvider.MODEL_NAME == MODEL_NAME


class TestOpenRouterProviderInit:
    """Tests for OpenRouterProvider construction."""

    @patch("src.llm.providers.openrouter.os.getenv")
    @patch("src.llm.providers.openrouter.ChatOpenAI")
    def test_instantiation_with_defaults(self, mock_chat, mock_getenv):
        mock_getenv.return_value = "or-key-456"
        from src.llm.providers.openrouter import OpenRouterProvider

        provider = OpenRouterProvider()
        assert provider.temperature == 0.1
        assert provider.timeout == 120
        assert provider.model_name == MODEL_NAME
        mock_chat.assert_called_once_with(
            model=MODEL_NAME,
            api_key="or-key-456",
            base_url="https://openrouter.ai/api/v1",
            temperature=0.1,
            timeout=120,
            request_timeout=120,
        )

    @patch("src.llm.providers.openrouter.os.getenv")
    @patch("src.llm.providers.openrouter.ChatOpenAI")
    def test_instantiation_with_custom_values(self, mock_chat, mock_getenv):
        mock_getenv.return_value = "or-key-456"
        from src.llm.providers.openrouter import OpenRouterProvider

        provider = OpenRouterProvider(temperature=0.8, timeout=15)
        assert provider.temperature == 0.8
        assert provider.timeout == 15
        mock_chat.assert_called_once_with(
            model=MODEL_NAME,
            api_key="or-key-456",
            base_url="https://openrouter.ai/api/v1",
            temperature=0.8,
            timeout=15,
            request_timeout=15,
        )

    @patch("src.llm.providers.openrouter.os.getenv")
    @patch("src.llm.providers.openrouter.ChatOpenAI")
    def test_model_name_override(self, mock_chat, mock_getenv):
        mock_getenv.return_value = "or-key-456"
        from src.llm.providers.openrouter import OpenRouterProvider

        provider = OpenRouterProvider(model_name="gpt-4")
        assert provider.model_name == "gpt-4"

    @patch("src.llm.providers.openrouter.os.getenv")
    @patch("src.llm.providers.openrouter.ChatOpenAI")
    def test_missing_api_key_raises_value_error(self, mock_chat, mock_getenv):
        mock_getenv.return_value = None
        from src.llm.providers.openrouter import OpenRouterProvider

        with pytest.raises(ValueError, match="OPENROUTER_API_KEY not found"):
            OpenRouterProvider()


class TestOpenRouterProviderInheritance:
    """Tests for OpenRouterProvider class hierarchy."""

    @patch("src.llm.providers.openrouter.os.getenv")
    @patch("src.llm.providers.openrouter.ChatOpenAI")
    def test_inherits_from_base_provider(self, mock_chat, mock_getenv):
        mock_getenv.return_value = "fake-key"
        from src.llm.providers.base import BaseProvider
        from src.llm.providers.openrouter import OpenRouterProvider

        assert issubclass(OpenRouterProvider, BaseProvider)

    @patch("src.llm.providers.openrouter.os.getenv")
    @patch("src.llm.providers.openrouter.ChatOpenAI")
    def test_id_property(self, mock_chat, mock_getenv):
        mock_getenv.return_value = "fake-key"
        from src.llm.providers.openrouter import OpenRouterProvider

        provider = OpenRouterProvider()
        assert provider.id == "openrouter"

    @patch("src.llm.providers.openrouter.os.getenv")
    @patch("src.llm.providers.openrouter.ChatOpenAI")
    def test_name_property(self, mock_chat, mock_getenv):
        mock_getenv.return_value = "fake-key"
        from src.llm.providers.openrouter import OpenRouterProvider

        provider = OpenRouterProvider()
        assert provider.name == f"OpenRouter ({MODEL_NAME})"


class TestOpenRouterProviderLlm:
    """Tests for OpenRouterProvider.llm attribute."""

    @patch("src.llm.providers.openrouter.os.getenv")
    @patch("src.llm.providers.openrouter.ChatOpenAI")
    def test_llm_set_from_chat_constructor(self, mock_chat, mock_getenv):
        mock_getenv.return_value = "fake-key"
        from src.llm.providers.openrouter import OpenRouterProvider

        provider = OpenRouterProvider()
        assert provider.llm is mock_chat.return_value
