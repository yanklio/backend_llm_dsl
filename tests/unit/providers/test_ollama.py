"""Tests for OllamaProvider."""

from unittest.mock import MagicMock, patch

import pytest

MODEL_NAME = "llama3.1"


class TestOllamaProviderModelName:
    """Tests for the MODEL_NAME constant."""

    def test_model_name_constant(self):
        from src.llm.providers.ollama import OllamaProvider

        assert OllamaProvider.MODEL_NAME == MODEL_NAME


class TestOllamaProviderInit:
    """Tests for OllamaProvider construction."""

    @patch("src.llm.providers.ollama.requests.get")
    @patch("src.llm.providers.ollama.ChatOllama")
    def test_instantiation_with_defaults(self, mock_chat, mock_get):
        mock_get.return_value = MagicMock()
        from src.llm.providers.ollama import OllamaProvider

        provider = OllamaProvider()
        assert provider.temperature == 0.1
        assert provider.timeout == 120
        assert provider.model_name == MODEL_NAME
        mock_chat.assert_called_once_with(
            model=MODEL_NAME,
            temperature=0.1,
            timeout=120,
        )

    @patch("src.llm.providers.ollama.requests.get")
    @patch("src.llm.providers.ollama.ChatOllama")
    def test_instantiation_with_custom_values(self, mock_chat, mock_get):
        mock_get.return_value = MagicMock()
        from src.llm.providers.ollama import OllamaProvider

        provider = OllamaProvider(temperature=0.5, timeout=60)
        assert provider.temperature == 0.5
        assert provider.timeout == 60
        mock_chat.assert_called_once_with(
            model=MODEL_NAME,
            temperature=0.5,
            timeout=60,
        )

    @patch("src.llm.providers.ollama.requests.get")
    @patch("src.llm.providers.ollama.ChatOllama")
    def test_model_name_override(self, mock_chat, mock_get):
        mock_get.return_value = MagicMock()
        from src.llm.providers.ollama import OllamaProvider

        provider = OllamaProvider(model_name="mistral")
        assert provider.model_name == "mistral"

    @patch("src.llm.providers.ollama.requests.get")
    @patch("src.llm.providers.ollama.ChatOllama")
    def test_connection_refused_raises_connection_error(self, mock_chat, mock_get):
        mock_get.side_effect = ConnectionError("Ollama is not running")
        from src.llm.providers.ollama import OllamaProvider

        with pytest.raises(ConnectionError, match="Ollama is not running on localhost:11434"):
            OllamaProvider()


class TestOllamaProviderInheritance:
    """Tests for OllamaProvider class hierarchy."""

    @patch("src.llm.providers.ollama.requests.get")
    @patch("src.llm.providers.ollama.ChatOllama")
    def test_inherits_from_base_provider(self, mock_chat, mock_get):
        mock_get.return_value = MagicMock()
        from src.llm.providers.base import BaseProvider
        from src.llm.providers.ollama import OllamaProvider

        assert issubclass(OllamaProvider, BaseProvider)

    @patch("src.llm.providers.ollama.requests.get")
    @patch("src.llm.providers.ollama.ChatOllama")
    def test_id_property(self, mock_chat, mock_get):
        mock_get.return_value = MagicMock()
        from src.llm.providers.ollama import OllamaProvider

        provider = OllamaProvider()
        assert provider.id == "ollama"

    @patch("src.llm.providers.ollama.requests.get")
    @patch("src.llm.providers.ollama.ChatOllama")
    def test_name_property(self, mock_chat, mock_get):
        mock_get.return_value = MagicMock()
        from src.llm.providers.ollama import OllamaProvider

        provider = OllamaProvider()
        assert provider.name == f"Ollama ({MODEL_NAME})"


class TestOllamaProviderLlm:
    """Tests for OllamaProvider.llm attribute."""

    @patch("src.llm.providers.ollama.requests.get")
    @patch("src.llm.providers.ollama.ChatOllama")
    def test_llm_set_from_chat_constructor(self, mock_chat, mock_get):
        mock_get.return_value = MagicMock()
        from src.llm.providers.ollama import OllamaProvider

        provider = OllamaProvider()
        assert provider.llm is mock_chat.return_value
