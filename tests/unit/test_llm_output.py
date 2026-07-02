"""Tests for LLM output logging helpers."""

from unittest.mock import patch

from packages.llm_providers import GenerationResult
from packages.llm_providers.generators.output import (
    RUN_INSTRUCTIONS,
    log_generation_statistics,
    log_json_parse_failure,
    log_run_instructions,
    parse_generated_files,
)


class TestConstants:
    """Tests for module-level constants."""

    def test_run_instructions(self):
        assert RUN_INSTRUCTIONS == ["npm install", "npm run start:dev"]


class TestParseGeneratedFiles:
    """Tests for parse_generated_files function."""

    def test_clean_and_parse_json(self):
        result = GenerationResult(
            content='{"files": {"a.ts": "code"}}',
            provider="test",
            duration_seconds=1.0,
        )
        with (
            patch("packages.llm_providers.generators.output.clean_llm_response") as mock_clean,
            patch("packages.llm_providers.generators.output.try_parse_json") as mock_parse,
        ):
            mock_clean.return_value = '{"files": {"a.ts": "code"}}'
            mock_parse.return_value = {"files": {"a.ts": "code"}}
            parsed_result, parsed_dict = parse_generated_files(result)

        mock_clean.assert_called_once_with('{"files": {"a.ts": "code"}}')
        assert parsed_result.content == '{"files": {"a.ts": "code"}}'
        assert parsed_dict == {"files": {"a.ts": "code"}}


class TestLogJsonParseFailure:
    """Tests for log_json_parse_failure function."""

    def test_logs_error_and_writes_debug_file(self):
        error = ValueError("bad json")
        with (
            patch("packages.llm_providers.generators.output.Path") as mock_path,
            patch("packages.llm_providers.generators.output.logger") as mock_logger,
        ):
            mock_instance = mock_path.return_value
            log_json_parse_failure("some content", error)

        mock_instance.write_text.assert_called_once_with("some content")
        assert mock_logger.error.call_count >= 2


class TestLogGenerationStatistics:
    """Tests for log_generation_statistics function."""

    def test_logs_provider_time_and_tokens(self):
        result = GenerationResult(
            content="test",
            provider="gemini",
            duration_seconds=1.5,
            total_tokens=100,
            input_tokens=50,
            output_tokens=50,
        )
        with patch("packages.llm_providers.generators.output.logger") as mock_logger:
            log_generation_statistics(result)

        mock_logger.info.assert_any_call("=== Generation Statistics ===")
        mock_logger.info.assert_any_call("Provider: gemini")
        mock_logger.info.assert_any_call("Time: 1.50s")
        mock_logger.info.assert_any_call("Tokens: 100 (In: 50, Out: 50)")

    def test_skips_token_line_when_none(self):
        result = GenerationResult(
            content="test",
            provider="gemini",
            duration_seconds=0.5,
        )
        with patch("packages.llm_providers.generators.output.logger") as mock_logger:
            log_generation_statistics(result)

        mock_logger.info.assert_any_call("=== Generation Statistics ===")
        mock_logger.info.assert_any_call("Provider: gemini")
        token_calls = [c for c in mock_logger.info.call_args_list if "Tokens:" in str(c)]
        assert len(token_calls) == 0


class TestLogRunInstructions:
    """Tests for log_run_instructions function."""

    def test_logs_cd_and_npm_instructions(self):
        with patch("packages.llm_providers.generators.output.logger") as mock_logger:
            log_run_instructions("./my_project")

        mock_logger.success.assert_called_once_with("Done! Run with:")
        mock_logger.info.assert_any_call("  cd ./my_project")
        mock_logger.info.assert_any_call("  npm install")
        mock_logger.info.assert_any_call("  npm run start:dev")
