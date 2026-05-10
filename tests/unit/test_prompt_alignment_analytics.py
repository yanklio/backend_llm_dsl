"""Tests for prompt-alignment analytics export fields."""

from src.experiments.export_analytics import _flatten_record, _group_rows


def _record_with_alignment(score: int) -> dict:
    """Build a minimal flattened-record fixture with a prompt-alignment result."""
    return {
        "provider": "openrouter",
        "model_name": "openai/gpt-oss-20b:free",
        "approach": "dsl",
        "test_case": "TEST_CASE_1",
        "tier": "simple",
        "prompt_version": "full-app-scaffold-v1",
        "prompt_hash": "abc",
        "generation": {
            "success": True,
            "metrics": {
                "total_time": 1,
                "llm_time": 1,
                "dsl_time": 0,
                "input_tokens": 1,
                "output_tokens": 1,
                "total_tokens": 2,
            },
        },
        "validation": {
            "overall_valid": True,
            "syntactic": {"valid": True, "error_count": 0, "total_files": 1, "errors": []},
            "runtime": {"valid": True, "install_success": True, "build_success": True, "start_success": True},
        },
        "prompt_alignment": {
            "provider": "openrouter",
            "model_name": "openai/gpt-oss-120b",
            "prompt_version": "prompt-alignment-v1",
            "prompt_hash": "judgehash",
            "metrics": {"duration_seconds": 2, "input_tokens": 3, "output_tokens": 4, "total_tokens": 7},
            "source_files": {"count": 1, "total_characters": 42},
            "result": {
                "alignment_score": score,
                "missing_requirements": ["PUT /users/:id"],
                "extra_features": [],
                "rationale": "Mostly aligned.",
            },
        },
    }


def test_flatten_record_includes_prompt_alignment_columns() -> None:
    """It should expose prompt-alignment result fields in record exports."""
    flattened = _flatten_record(_record_with_alignment(4), {"run_id": "run-1"}, 1)

    assert flattened["alignment_model_name"] == "openai/gpt-oss-120b"
    assert flattened["alignment_score"] == 4
    assert flattened["alignment_missing_requirements_count"] == 1
    assert flattened["alignment_rationale"] == "Mostly aligned."


def test_group_rows_averages_present_alignment_scores_only() -> None:
    """It should summarize judged records without treating missing scores as zero."""
    judged = _flatten_record(_record_with_alignment(4), {"run_id": "run-1"}, 1)
    unjudged = {**judged, "alignment_score": ""}

    rows = _group_rows([judged, unjudged], ("approach",))

    assert rows[0]["alignment_scored_records"] == 1
    assert rows[0]["avg_alignment_score"] == 4.0
