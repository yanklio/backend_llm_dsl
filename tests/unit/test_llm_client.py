"""Tests for LLM client module."""

from unittest.mock import MagicMock, patch

import pytest

from packages.llm_providers.core.client import LLMClient, _provider_registry, get_default_model_name, get_provider
from packages.shared.exceptions import LLMException


class TestProviderRegistry:
    """Tests for _provider_registry()."""

    def test_returns_dict_with_all_four_keys(self):
        """Verify the registry maps all four expected provider IDs."""
        registry = _provider_registry()
        assert set(registry.keys()) == {"gemini", "groq", "ollama", "openrouter"}

    def test_values_are_classes(self):
        """Each registry entry is a class (not an instance)."""
        registry = _provider_registry()
        for provider_id, cls in registry.items():
            assert isinstance(cls, type), f"{provider_id} must be a class type"


class TestGetDefaultModelName:
    """Tests for get_default_model_name()."""

    MODEL_NAMES = {
        "gemini": "gemma-4-31b-it",
        "groq": "llama-3.3-70b-versatile",
        "ollama": "llama3.1",
        "openrouter": "openai/gpt-oss-20b:free",
    }

    @patch("packages.llm_providers.core.client._provider_registry")
    def test_returns_model_name_for_valid_provider(self, mock_registry):
        """get_default_model_name returns MODEL_NAME from the provider class."""
        mock_class = MagicMock()
        mock_class.MODEL_NAME = "test-model-v1"
        mock_registry.return_value = {"gemini": mock_class}
        assert get_default_model_name("gemini") == "test-model-v1"

    @patch("packages.llm_providers.core.client._provider_registry")
    def test_returns_unknown_for_invalid_provider(self, mock_registry):
        """get_default_model_name returns 'unknown' for unrecognised provider."""
        mock_registry.return_value = {"gemini": MagicMock()}
        assert get_default_model_name("nonexistent") == "unknown"

    @patch("packages.llm_providers.core.client._provider_registry")
    def test_returns_model_name_for_each_provider(self, mock_registry):
        """Verify each known provider returns its own MODEL_NAME."""
        mock_registry.return_value = {
            pid: type(f"Mock{pid}", (), {"MODEL_NAME": name}) for pid, name in self.MODEL_NAMES.items()
        }
        for pid, expected in self.MODEL_NAMES.items():
            assert get_default_model_name(pid) == expected


class TestGetProvider:
    """Tests for get_provider()."""

    @patch("packages.llm_providers.core.client._provider_registry")
    def test_returns_provider_instance(self, mock_registry):
        """get_provider constructs and returns the correct provider."""
        mock_class = MagicMock()
        mock_class.return_value = MagicMock()
        mock_registry.return_value = {"gemini": mock_class}
        result = get_provider("gemini", 0.3, 60)
        mock_class.assert_called_once_with(0.3, 60, model_name=None)
        assert result is mock_class.return_value

    @patch("packages.llm_providers.core.client._provider_registry")
    def test_raises_llm_exception_for_invalid_provider(self, mock_registry):
        """get_provider raises LLM001 for unknown provider ID."""
        mock_registry.return_value = {"gemini": MagicMock()}
        with pytest.raises(LLMException) as exc_info:
            get_provider("bad_provider", 0.1, 120)
        assert exc_info.value.code == "LLM001"

    @patch("packages.llm_providers.core.client._provider_registry")
    def test_passes_model_name_override(self, mock_registry):
        """get_provider passes model_name to the provider constructor."""
        mock_class = MagicMock()
        mock_class.return_value = MagicMock()
        mock_registry.return_value = {"gemini": mock_class}
        get_provider("gemini", 0.1, 120, model_name="custom-model")
        mock_class.assert_called_once_with(0.1, 120, model_name="custom-model")


class TestLLMClientInit:
    """Tests for LLMClient.__init__()."""

    @patch("packages.llm_providers.core.client.logger")
    @patch("packages.llm_providers.core.client.get_provider")
    @patch("packages.llm_providers.core.client.get_config")
    def test_uses_config_values_by_default(self, mock_get_config, mock_get_provider, mock_logger):
        """Default constructor reads temperature/timeout from config."""
        mock_get_config.return_value.llm.temperature = 0.42
        mock_get_config.return_value.llm.timeout = 99
        client = LLMClient()
        assert client.temperature == 0.42
        assert client.timeout == 99
        assert client.provider_id == "openrouter"
        mock_get_provider.assert_called_once_with("openrouter", 0.42, 99, model_name=None)

    @patch("packages.llm_providers.core.client.logger")
    @patch("packages.llm_providers.core.client.get_provider")
    @patch("packages.llm_providers.core.client.get_config")
    def test_custom_temperature_and_timeout(self, mock_get_config, mock_get_provider, mock_logger):
        """Constructor uses explicit temperature/timeout over config."""
        mock_get_config.return_value.llm.temperature = 0.1
        mock_get_config.return_value.llm.timeout = 120
        client = LLMClient(temperature=0.9, timeout=30)
        assert client.temperature == 0.9
        assert client.timeout == 30

    @patch("packages.llm_providers.core.client.logger")
    @patch("packages.llm_providers.core.client.get_provider")
    @patch("packages.llm_providers.core.client.get_config")
    def test_custom_provider_id(self, mock_get_config, mock_get_provider, mock_logger):
        """Constructor accepts a different provider_id."""
        client = LLMClient(provider_id="groq")
        assert client.provider_id == "groq"
        args, kwargs = mock_get_provider.call_args
        assert args[0] == "groq"

    @patch("packages.llm_providers.core.client.logger")
    @patch("packages.llm_providers.core.client.get_provider")
    @patch("packages.llm_providers.core.client.get_config")
    def test_custom_model_name(self, mock_get_config, mock_get_provider, mock_logger):
        """Constructor passes model_name to get_provider."""
        LLMClient(model_name="my-custom-model")
        mock_get_provider.assert_called_once_with(
            "openrouter",
            mock_get_config.return_value.llm.temperature,
            mock_get_config.return_value.llm.timeout,
            model_name="my-custom-model",
        )

    @patch("packages.llm_providers.core.client.logger")
    @patch("packages.llm_providers.core.client.get_provider")
    @patch("packages.llm_providers.core.client.get_config")
    def test_raises_for_invalid_provider(self, mock_get_config, mock_get_provider, mock_logger):
        """__init__ propagates LLMException from get_provider."""
        mock_get_provider.side_effect = LLMException("bad provider", code="LLM001")
        with pytest.raises(LLMException) as exc_info:
            LLMClient(provider_id="invalid")
        assert exc_info.value.code == "LLM001"


class TestLLMClientGenerate:
    """Tests for LLMClient.generate()."""

    @patch("packages.llm_providers.core.client.logger")
    @patch("packages.llm_providers.core.client.get_provider")
    @patch("packages.llm_providers.core.client.get_config")
    def test_generate_returns_generation_result(self, mock_get_config, mock_get_provider, mock_logger):
        """generate() returns the result from provider.generate()."""
        mock_provider = MagicMock()
        mock_provider.name = "TestProvider"
        mock_get_provider.return_value = mock_provider

        mock_result = MagicMock()
        mock_provider.generate.return_value = mock_result

        client = LLMClient()
        messages = [MagicMock()]
        result = client.generate(messages)

        mock_provider.generate.assert_called_once_with(messages)
        assert result is mock_result

    @patch("packages.llm_providers.core.client.logger")
    @patch("packages.llm_providers.core.client.get_provider")
    @patch("packages.llm_providers.core.client.get_config")
    def test_reraises_provider_error_as_llm_exception(self, mock_get_config, mock_get_provider, mock_logger):
        """When provider.generate raises, client.generate raises LLM002."""
        mock_provider = MagicMock()
        mock_provider.name = "TestProvider"
        mock_get_provider.return_value = mock_provider
        mock_provider.generate.side_effect = ValueError("API failure")

        client = LLMClient()
        with pytest.raises(LLMException) as exc_info:
            client.generate([MagicMock()])

        assert exc_info.value.code == "LLM002"
        assert "TestProvider failed: API failure" in str(exc_info.value)
        assert exc_info.value.context["provider"] == "openrouter"
