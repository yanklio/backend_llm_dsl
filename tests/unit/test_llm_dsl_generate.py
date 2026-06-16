"""Tests for LLM DSL generation entry point."""

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.llm.dsl_generate import DSL_REQUEST_TEMPLATE, natural_language_to_yaml, save_blueprint


class TestConstants:
    """Verify DSL generation module constants."""

    def test_dsl_request_template_constant(self):
        assert DSL_REQUEST_TEMPLATE == "Create a NestJS application for: {description}"


class TestNaturalLanguageToYaml:
    """Verify natural_language_to_yaml function."""

    def test_creates_messages_with_correct_content(self):
        mock_result = SimpleNamespace(
            content="raw yaml",
            provider="openrouter",
            duration_seconds=1.0,
            total_tokens=10,
            input_tokens=5,
            output_tokens=5,
        )
        with (
            patch("src.llm.dsl_generate.LLMClient") as MockClient,
            patch("src.llm.dsl_generate.clean_llm_response") as mock_clean,
        ):
            mock_instance = MagicMock()
            mock_instance.generate.return_value = mock_result
            MockClient.return_value = mock_instance
            mock_clean.return_value = "cleaned yaml"

            result = natural_language_to_yaml("test app", "gemini")

        MockClient.assert_called_once_with(provider_id="gemini", temperature=0.1)
        call_args = mock_instance.generate.call_args[0][0]
        assert len(call_args) == 2
        assert call_args[0].type == "system"
        assert call_args[1].type == "human"
        assert call_args[1].content == "Create a NestJS application for: test app"
        assert result.content == "cleaned yaml"

    def test_calls_clean_llm_response_on_result(self):
        mock_result = SimpleNamespace(
            content="raw yaml",
            provider="openrouter",
            duration_seconds=1.0,
            total_tokens=10,
            input_tokens=5,
            output_tokens=5,
        )
        with (
            patch("src.llm.dsl_generate.LLMClient") as MockClient,
            patch("src.llm.dsl_generate.clean_llm_response") as mock_clean,
        ):
            mock_instance = MagicMock()
            mock_instance.generate.return_value = mock_result
            MockClient.return_value = mock_instance
            mock_clean.return_value = "cleaned"

            result = natural_language_to_yaml("test app")

        mock_clean.assert_called_once_with("raw yaml")
        assert result.content == "cleaned"

    def test_default_provider(self):
        mock_result = SimpleNamespace(
            content="yaml",
            provider="openrouter",
            duration_seconds=1.0,
            total_tokens=10,
            input_tokens=5,
            output_tokens=5,
        )
        with (
            patch("src.llm.dsl_generate.LLMClient") as MockClient,
            patch("src.llm.dsl_generate.clean_llm_response") as mock_clean,
        ):
            mock_instance = MagicMock()
            mock_instance.generate.return_value = mock_result
            MockClient.return_value = mock_instance
            mock_clean.return_value = "yaml"

            natural_language_to_yaml("test app")

        MockClient.assert_called_once_with(provider_id="openrouter", temperature=0.1)


class TestSaveBlueprint:
    """Verify save_blueprint function."""

    def test_writes_yaml_to_file(self, temp_dir):
        blueprint_path = str(temp_dir / "output.yaml")
        save_blueprint("key: value\n", blueprint_path)
        content = (temp_dir / "output.yaml").read_text()
        assert content == "key: value\n"

    def test_default_path(self):
        with patch("builtins.open", MagicMock()) as mock_open:
            save_blueprint("content")
            mock_open.assert_called_once_with("./blueprint.yaml", "w")


class TestMain:
    """Verify main CLI entry point."""

    def test_invokes_natural_language_to_yaml_and_save(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["prog", "my api", "-b", "out.yaml", "-m", "groq"])
        result = SimpleNamespace(
            content="yaml",
            provider="groq",
            duration_seconds=0.5,
            total_tokens=5,
            input_tokens=2,
            output_tokens=3,
        )
        with (
            patch("src.llm.dsl_generate.natural_language_to_yaml") as mock_nl,
            patch("src.llm.dsl_generate.save_blueprint") as mock_save,
            patch("src.llm.dsl_generate.log_generation_statistics"),
            patch("src.llm.dsl_generate.logger"),
        ):
            mock_nl.return_value = result
            from src.llm.dsl_generate import main

            main()

        mock_nl.assert_called_once_with("my api", "groq")
        mock_save.assert_called_once_with("yaml", "out.yaml")

    def test_exits_on_exception(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["prog", "my api"])
        with (
            patch("src.llm.dsl_generate.natural_language_to_yaml", side_effect=Exception("fail")),
            patch("src.llm.dsl_generate.logger"),
        ):
            from src.llm.dsl_generate import main

            with pytest.raises(SystemExit) as exc:
                main()
        assert exc.value.code == 1
