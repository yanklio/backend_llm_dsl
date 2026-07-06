"""Tests for prompt-alignment experiment record integration."""

import time
from unittest.mock import patch

from apps.experiments.runner import (
    _build_result_record,
    _run_generation_with_timeout,
    _run_prompt_alignment,
)
from packages.llm_providers.evaluation.prompt_alignment import DEFAULT_ALIGNMENT_MODEL
from packages.shared.exceptions import JSONParseException


def test_build_result_record_includes_prompt_alignment_when_present() -> None:
    """It should persist prompt-alignment data separately from validation."""
    alignment = {"result": {"alignment_score": 5}}

    record = _build_result_record(
        "TEST_CASE_1",
        "simple",
        "dsl",
        "openrouter",
        {"success": True, "metrics": {}},
        {"overall_valid": True},
        "run-1",
        1,
        alignment,
    )

    assert record["prompt_alignment"] == alignment
    assert record["validation"] == {"overall_valid": True}


def test_run_prompt_alignment_records_generation_failure_without_llm_call() -> None:
    """It should record a judge error when generation produced no code."""
    alignment = _run_prompt_alignment(
        case_data={"requirement": "Create users", "endpoints": ["GET /users"]},
        generation={"success": False},
        provider="openrouter",
        model_name=DEFAULT_ALIGNMENT_MODEL,
    )

    assert alignment["model_name"] == DEFAULT_ALIGNMENT_MODEL
    assert alignment["result"] is None
    assert alignment["error"] == "generation_failed"


def test_run_prompt_alignment_records_judge_json_parse_failure() -> None:
    """It should keep benchmark runs alive when judge output is invalid JSON."""
    with patch(
        "apps.experiments.runner.evaluate_prompt_alignment",
        side_effect=JSONParseException("bad judge json", code="JSON001"),
    ):
        alignment = _run_prompt_alignment(
            case_data={"requirement": "Create users", "endpoints": ["GET /users"]},
            generation={"success": True},
            provider="openrouter",
            model_name=DEFAULT_ALIGNMENT_MODEL,
        )

    assert alignment["model_name"] == DEFAULT_ALIGNMENT_MODEL
    assert alignment["result"] is None
    assert "bad judge json" in alignment["error"]


def test_run_prompt_alignment_records_judge_timeout() -> None:
    """It should keep benchmark runs alive when judging exceeds its timeout."""

    def slow_alignment(**_kwargs):
        time.sleep(2)

    with patch("apps.experiments.runner.evaluate_prompt_alignment", side_effect=slow_alignment):
        alignment = _run_prompt_alignment(
            case_data={"requirement": "Create users", "endpoints": ["GET /users"]},
            generation={"success": True},
            provider="openrouter",
            model_name=DEFAULT_ALIGNMENT_MODEL,
            timeout_seconds=1,
        )

    assert alignment["model_name"] == DEFAULT_ALIGNMENT_MODEL
    assert alignment["result"] is None
    assert "prompt alignment timed out after 1s" in alignment["error"]


def test_run_generation_with_timeout_records_failure() -> None:
    """It should convert a blocked generation cell into an error payload."""

    def slow_generation(*_args, **_kwargs):
        time.sleep(2)

    with patch.dict("apps.experiments.runner.APPROACH_RUNNERS", {"raw": slow_generation}):
        generation = _run_generation_with_timeout(
            case_name="TEST_CASE_1",
            case_data={"requirement": "Create users"},
            current_approach="raw",
            provider="openrouter",
            model_name="openai/gpt-oss-20b",
            timeout_seconds=1,
        )

    assert generation["success"] is False
    assert generation["stage"] == "timeout"
    assert generation["metrics"]["provider_id"] == "openrouter"
    assert "generation timed out after 1s" in generation["error"]
