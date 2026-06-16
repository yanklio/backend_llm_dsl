"""Tests for GroqProvider."""

from unittest.mock import patch

import pytest

MODEL_NAME = "llama-3.3-70b-versatile"


class TestGroqProviderModelName:
    """Tests for the MODEL_NAME constant."""

    def test_model_name_constant(self):
        from src.llm.providers.groq import GroqProvider

        assert GroqProvider.MODEL_NAME == MODEL_NAME


class TestGroqProviderInit:
    """Tests for GroqProvider construction."""

    @patch("src.llm.providers.groq.os.getenv")
    @patch("src.llm.providers.groq.ChatGroq")
    def test_instantiation_with_defaults(self, mock_chat, mock_getenv):
        mock_getenv.return_value = "groq-key-123"
        from src.llm.providers.groq import GroqProvider

        provider = GroqProvider()
        assert provider.temperature == 0.1
        assert provider.timeout == 120
        assert provider.model_name == MODEL_NAME
        mock_chat.assert_called_once_with(
            model=MODEL_NAME,
            api_key="groq-key-123",
            temperature=0.1,
            timeout=120,
            request_timeout=120,
        )

    @patch("src.llm.providers.groq.os.getenv")
    @patch("src.llm.providers.groq.ChatGroq")
    def test_instantiation_with_custom_values(self, mock_chat, mock_getenv):
        mock_getenv.return_value = "groq-key-123"
        from src.llm.providers.groq import GroqProvider

        provider = GroqProvider(temperature=0.3, timeout=30)
        assert provider.temperature == 0.3
        assert provider.timeout == 30
        mock_chat.assert_called_once_with(
            model=MODEL_NAME,
            api_key="groq-key-123",
            temperature=0.3,
            timeout=30,
            request_timeout=30,
        )

    @patch("src.llm.providers.groq.os.getenv")
    @patch("src.llm.providers.groq.ChatGroq")
    def test_model_name_override(self, mock_chat, mock_getenv):
        mock_getenv.return_value = "groq-key-123"
        from src.llm.providers.groq import GroqProvider

        provider = GroqProvider(model_name="llama-4")
        assert provider.model_name == "llama-4"

    @patch("src.llm.providers.groq.os.getenv")
    @patch("src.llm.providers.groq.ChatGroq")
    def test_missing_api_key_raises_value_error(self, mock_chat, mock_getenv):
        mock_getenv.return_value = None
        from src.llm.providers.groq import GroqProvider

        with pytest.raises(ValueError, match="GROQ_API_KEY not found"):
            GroqProvider()


class TestGroqProviderInheritance:
    """Tests for GroqProvider class hierarchy."""

    @patch("src.llm.providers.groq.os.getenv")
    @patch("src.llm.providers.groq.ChatGroq")
    def test_inherits_from_base_provider(self, mock_chat, mock_getenv):
        mock_getenv.return_value = "fake-key"
        from src.llm.providers.base import BaseProvider
        from src.llm.providers.groq import GroqProvider

        assert issubclass(GroqProvider, BaseProvider)

    @patch("src.llm.providers.groq.os.getenv")
    @patch("src.llm.providers.groq.ChatGroq")
    def test_id_property(self, mock_chat, mock_getenv):
        mock_getenv.return_value = "fake-key"
        from src.llm.providers.groq import GroqProvider

        provider = GroqProvider()
        assert provider.id == "groq"

    @patch("src.llm.providers.groq.os.getenv")
    @patch("src.llm.providers.groq.ChatGroq")
    def test_name_property(self, mock_chat, mock_getenv):
        mock_getenv.return_value = "fake-key"
        from src.llm.providers.groq import GroqProvider

        provider = GroqProvider()
        assert provider.name == f"Groq ({MODEL_NAME})"


class TestGroqProviderLlm:
    """Tests for GroqProvider.llm attribute."""

    @patch("src.llm.providers.groq.os.getenv")
    @patch("src.llm.providers.groq.ChatGroq")
    def test_llm_set_from_chat_constructor(self, mock_chat, mock_getenv):
        mock_getenv.return_value = "fake-key"
        from src.llm.providers.groq import GroqProvider

        provider = GroqProvider()
        assert provider.llm is mock_chat.return_value
