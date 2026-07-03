"""Tests for prompt-alignment experiment record integration."""

from apps.experiments.runner import _build_result_record, _run_prompt_alignment
from packages.llm_providers.evaluation.prompt_alignment import DEFAULT_ALIGNMENT_MODEL


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
