"""Tests for GeminiProvider."""

from unittest.mock import patch

import pytest

MODEL_NAME = "gemma-4-31b-it"


class TestGeminiProviderModelName:
    """Tests for the MODEL_NAME constant."""

    def test_model_name_constant(self):
        from packages.llm_providers.providers.gemini import GeminiProvider

        assert GeminiProvider.MODEL_NAME == MODEL_NAME


class TestGeminiProviderInit:
    """Tests for GeminiProvider construction."""

    @patch("packages.llm_providers.providers.gemini.os.getenv")
    @patch("packages.llm_providers.providers.gemini.ChatGoogleGenerativeAI")
    def test_instantiation_with_defaults(self, mock_chat, mock_getenv):
        mock_getenv.return_value = "fake-key"
        from packages.llm_providers.providers.gemini import GeminiProvider

        provider = GeminiProvider()
        assert provider.temperature == 0.1
        assert provider.timeout == 120
        assert provider.model_name == MODEL_NAME
        mock_chat.assert_called_once_with(
            model=MODEL_NAME,
            temperature=0.1,
            timeout=120,
        )

    @patch("packages.llm_providers.providers.gemini.os.getenv")
    @patch("packages.llm_providers.providers.gemini.ChatGoogleGenerativeAI")
    def test_instantiation_with_custom_values(self, mock_chat, mock_getenv):
        mock_getenv.return_value = "fake-key"
        from packages.llm_providers.providers.gemini import GeminiProvider

        provider = GeminiProvider(temperature=0.7, timeout=45)
        assert provider.temperature == 0.7
        assert provider.timeout == 45
        mock_chat.assert_called_once_with(
            model=MODEL_NAME,
            temperature=0.7,
            timeout=45,
        )

    @patch("packages.llm_providers.providers.gemini.os.getenv")
    @patch("packages.llm_providers.providers.gemini.ChatGoogleGenerativeAI")
    def test_model_name_override(self, mock_chat, mock_getenv):
        mock_getenv.return_value = "fake-key"
        from packages.llm_providers.providers.gemini import GeminiProvider

        provider = GeminiProvider(model_name="custom-model")
        assert provider.model_name == "custom-model"
        mock_chat.assert_called_once_with(
            model="custom-model",
            temperature=0.1,
            timeout=120,
        )

    @patch("packages.llm_providers.providers.gemini.os.getenv")
    @patch("packages.llm_providers.providers.gemini.ChatGoogleGenerativeAI")
    def test_missing_api_key_raises_value_error(self, mock_chat, mock_getenv):
        mock_getenv.return_value = None
        from packages.llm_providers.providers.gemini import GeminiProvider

        with pytest.raises(ValueError, match="GOOGLE_API_KEY not found"):
            GeminiProvider()


class TestGeminiProviderInheritance:
    """Tests for GeminiProvider class hierarchy."""

    @patch("packages.llm_providers.providers.gemini.os.getenv")
    @patch("packages.llm_providers.providers.gemini.ChatGoogleGenerativeAI")
    def test_inherits_from_base_provider(self, mock_chat, mock_getenv):
        mock_getenv.return_value = "fake-key"
        from packages.llm_providers.providers.base import BaseProvider
        from packages.llm_providers.providers.gemini import GeminiProvider

        assert issubclass(GeminiProvider, BaseProvider)

    @patch("packages.llm_providers.providers.gemini.os.getenv")
    @patch("packages.llm_providers.providers.gemini.ChatGoogleGenerativeAI")
    def test_id_property(self, mock_chat, mock_getenv):
        mock_getenv.return_value = "fake-key"
        from packages.llm_providers.providers.gemini import GeminiProvider

        provider = GeminiProvider()
        assert provider.id == "gemini"

    @patch("packages.llm_providers.providers.gemini.os.getenv")
    @patch("packages.llm_providers.providers.gemini.ChatGoogleGenerativeAI")
    def test_name_property(self, mock_chat, mock_getenv):
        mock_getenv.return_value = "fake-key"
        from packages.llm_providers.providers.gemini import GeminiProvider

        provider = GeminiProvider()
        assert provider.name == f"Google Gemini ({MODEL_NAME})"


class TestGeminiProviderLlm:
    """Tests for GeminiProvider.llm attribute."""

    @patch("packages.llm_providers.providers.gemini.os.getenv")
    @patch("packages.llm_providers.providers.gemini.ChatGoogleGenerativeAI")
    def test_llm_set_from_chat_constructor(self, mock_chat, mock_getenv):
        mock_getenv.return_value = "fake-key"
        from packages.llm_providers.providers.gemini import GeminiProvider

        provider = GeminiProvider()
        assert provider.llm is mock_chat.return_value
