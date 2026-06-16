"""Tests for the abstract BaseProvider and GenerationResult dataclass."""

from abc import ABC
from unittest.mock import MagicMock, patch

import pytest

from src.llm.providers.base import (
    TOKEN_USAGE_KEYS,
    BaseProvider,
    GenerationResult,
    _extract_usage_metadata,
    _resolve_usage_value,
)

# ── Helper concrete subclass ──────────────────────────────────────────


class ConcreteProvider(BaseProvider):
    """Minimal concrete subclass for testing abstract behaviour."""

    MODEL_NAME = "test-model"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.llm = MagicMock()

    @property
    def id(self) -> str:
        return "test"

    @property
    def name(self) -> str:
        return "Test Provider"

    def generate(self, messages):
        return self._track_generation(self.llm.invoke, messages)


# ── Tests ─────────────────────────────────────────────────────────────


class TestBaseProviderAbstract:
    """Tests for abstract base class constraints."""

    def test_cannot_instantiate_directly(self):
        """BaseProvider cannot be instantiated directly because it is abstract."""
        with pytest.raises(TypeError):
            BaseProvider()

    def test_is_abstract_class(self):
        """BaseProvider inherits from ABC."""
        assert issubclass(BaseProvider, ABC)

    def test_abstract_methods_exist(self):
        """BaseProvider declares abstract properties/methods."""
        abstract = {
            name for name, method in BaseProvider.__dict__.items() if getattr(method, "__isabstractmethod__", False)
        }
        assert "id" in abstract
        assert "name" in abstract
        assert "generate" in abstract


class TestConcreteProvider:
    """Tests for BaseProvider functionality via ConcreteProvider."""

    @patch("src.llm.providers.base.clean_llm_response")
    def test_name_property(self, _mock_clean):
        """Name property returns the provider display name."""
        provider = ConcreteProvider(temperature=0.5, timeout=30)
        assert provider.name == "Test Provider"

    @patch("src.llm.providers.base.clean_llm_response")
    def test_model_name_default(self, _mock_clean):
        """model_name defaults to the class MODEL_NAME."""
        provider = ConcreteProvider()
        assert provider.model_name == "test-model"

    @patch("src.llm.providers.base.clean_llm_response")
    def test_model_name_override(self, _mock_clean):
        """model_name can be overridden via constructor."""
        provider = ConcreteProvider(model_name="custom-name")
        assert provider.model_name == "custom-name"

    @patch("src.llm.providers.base.clean_llm_response")
    def test_id_property(self, _mock_clean):
        """Id property returns the provider identifier."""
        provider = ConcreteProvider()
        assert provider.id == "test"

    @patch("src.llm.providers.base.clean_llm_response")
    def test_llm_attribute_set(self, _mock_clean):
        """Concrete provider has an llm attribute (proxy for _get_model)."""
        provider = ConcreteProvider()
        assert hasattr(provider, "llm")

    @patch("src.llm.providers.base.clean_llm_response", return_value="cleaned")
    @patch("src.llm.providers.base.time.perf_counter", side_effect=[1.0, 3.5])
    def test_track_generation_with_response_metadata(
        self,
        mock_time,
        mock_clean,
    ):
        """_track_generation returns a GenerationResult with correct fields."""
        provider = ConcreteProvider()

        mock_response = MagicMock()
        mock_response.content = "raw output"
        mock_response.response_metadata = {
            "token_usage": {
                "prompt_tokens": 5,
                "completion_tokens": 10,
                "total_tokens": 15,
            },
        }

        mock_invoke = MagicMock(return_value=mock_response)
        messages = [MagicMock()]
        result = provider._track_generation(mock_invoke, messages)

        mock_invoke.assert_called_once_with(messages)
        mock_clean.assert_called_once_with("raw output")
        assert result.content == "cleaned"
        assert result.provider == "Test Provider"
        assert result.duration_seconds == 2.5
        assert result.input_tokens == 5
        assert result.output_tokens == 10
        assert result.total_tokens == 15
        assert result.model_name == "test-model"

    @patch("src.llm.providers.base.clean_llm_response", return_value="cleaned")
    @patch("src.llm.providers.base.time.perf_counter", side_effect=[10.0, 10.2])
    def test_track_generation_with_usage_metadata(
        self,
        mock_time,
        mock_clean,
    ):
        """_track_generation falls back to usage_metadata when response_metadata is absent."""
        provider = ConcreteProvider()

        mock_response = MagicMock()
        mock_response.content = "output"
        mock_response.usage_metadata = {
            "input_tokens": 7,
            "output_tokens": 14,
            "total_tokens": 21,
        }
        del mock_response.response_metadata  # ensure no response_metadata path

        mock_invoke = MagicMock(return_value=mock_response)
        messages = [MagicMock()]
        result = provider._track_generation(mock_invoke, messages)

        assert result.duration_seconds == 0.2
        assert result.input_tokens == 7
        assert result.output_tokens == 14
        assert result.total_tokens == 21

    @patch("src.llm.providers.base.clean_llm_response", return_value="cleaned")
    @patch("src.llm.providers.base.time.perf_counter", side_effect=[0.0, 0.5])
    def test_track_generation_no_token_metadata(
        self,
        mock_time,
        mock_clean,
    ):
        """_track_generation sets token fields to None when metadata is missing."""
        provider = ConcreteProvider()

        mock_response = MagicMock()
        mock_response.content = "no tokens"
        del mock_response.response_metadata
        del mock_response.usage_metadata

        mock_invoke = MagicMock(return_value=mock_response)
        result = provider._track_generation(mock_invoke, [MagicMock()])

        assert result.content == "cleaned"
        assert result.input_tokens is None
        assert result.output_tokens is None
        assert result.total_tokens is None

    @patch("src.llm.providers.base.clean_llm_response", return_value="cleaned")
    @patch("src.llm.providers.base.time.perf_counter", side_effect=[0.0, 0.5])
    def test_generate_delegates_to_track_generation(
        self,
        mock_time,
        mock_clean,
    ):
        """ConcreteProvider.generate calls _track_generation correctly."""
        provider = ConcreteProvider()

        mock_response = MagicMock()
        mock_response.content = "gen output"
        mock_response.response_metadata = {
            "token_usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
        }
        provider.llm.invoke = MagicMock(return_value=mock_response)

        messages = [MagicMock()]
        result = provider.generate(messages)

        provider.llm.invoke.assert_called_once_with(messages)
        assert result.content == "cleaned"


class TestTOKEN_USAGE_KEYS:
    """Tests for the TOKEN_USAGE_KEYS constant."""

    def test_has_expected_keys(self):
        assert set(TOKEN_USAGE_KEYS.keys()) == {"input_tokens", "output_tokens", "total_tokens"}

    def test_key_precedence(self):
        """input_tokens tries prompt_tokens first, then input_tokens."""
        assert TOKEN_USAGE_KEYS["input_tokens"] == ("prompt_tokens", "input_tokens")
        assert TOKEN_USAGE_KEYS["output_tokens"] == ("completion_tokens", "output_tokens")
        assert TOKEN_USAGE_KEYS["total_tokens"] == ("total_tokens",)


class TestExtractUsageMetadata:
    """Tests for _extract_usage_metadata()."""

    def test_returns_token_usage_from_response_metadata(self):
        """Preferred path: response.response_metadata['token_usage']."""
        response = MagicMock()
        response.response_metadata = {"token_usage": {"prompt_tokens": 5}}
        assert _extract_usage_metadata(response) == {"prompt_tokens": 5}

    def test_returns_usage_metadata_when_no_response_metadata(self):
        """Fallback path: response.usage_metadata."""
        response = MagicMock()
        response.usage_metadata = {"input_tokens": 3}
        del response.response_metadata
        assert _extract_usage_metadata(response) == {"input_tokens": 3}

    def test_returns_empty_dict_when_none_available(self):
        """No metadata found returns {}."""
        response = MagicMock()
        del response.response_metadata
        del response.usage_metadata
        assert _extract_usage_metadata(response) == {}

    def test_response_metadata_without_token_usage(self):
        """response_metadata exists but has no token_usage key."""
        response = MagicMock(spec=[])
        response.response_metadata = {"other": "data"}
        assert _extract_usage_metadata(response) == {}


class TestResolveUsageValue:
    """Tests for _resolve_usage_value()."""

    def test_returns_first_matching_key(self):
        usage = {"prompt_tokens": 10, "input_tokens": 20}
        assert _resolve_usage_value(usage, ("prompt_tokens", "input_tokens")) == 10

    def test_returns_second_key_when_first_missing(self):
        usage = {"input_tokens": 20}
        assert _resolve_usage_value(usage, ("prompt_tokens", "input_tokens")) == 20

    def test_returns_none_when_no_keys_match(self):
        usage = {"other": 99}
        assert _resolve_usage_value(usage, ("prompt_tokens", "input_tokens")) is None

    def test_returns_none_for_empty_dict(self):
        assert _resolve_usage_value({}, ("key1", "key2")) is None

    def test_returns_none_for_empty_keys(self):
        assert _resolve_usage_value({"a": 1}, ()) is None


class TestGenerationResult:
    """Tests for the GenerationResult dataclass."""

    def test_default_fields(self):
        """Required fields populated; optional fields default to None."""
        result = GenerationResult(
            content="hello",
            provider="test",
            duration_seconds=1.5,
        )
        assert result.content == "hello"
        assert result.provider == "test"
        assert result.duration_seconds == 1.5
        assert result.input_tokens is None
        assert result.output_tokens is None
        assert result.total_tokens is None
        assert result.model_name is None

    def test_all_fields_explicit(self):
        """All dataclass fields can be set explicitly."""
        result = GenerationResult(
            content="full",
            provider="gemini",
            duration_seconds=2.25,
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
            model_name="gemini-pro",
        )
        assert result.content == "full"
        assert result.provider == "gemini"
        assert result.duration_seconds == 2.25
        assert result.input_tokens == 10
        assert result.output_tokens == 20
        assert result.total_tokens == 30
        assert result.model_name == "gemini-pro"

    def test_repr(self):
        """Dataclass provides a useful repr."""
        result = GenerationResult("a", "b", 0.5)
        assert "GenerationResult" in repr(result)
        assert "content=" in repr(result)

    def test_equality(self):
        """Two identical dataclass instances compare equal."""
        a = GenerationResult("text", "p", 1.0)
        b = GenerationResult("text", "p", 1.0)
        assert a == b

    def test_inequality(self):
        """Different field values produce unequal instances."""
        a = GenerationResult("text", "p", 1.0)
        b = GenerationResult("other", "p", 1.0)
        assert a != b
