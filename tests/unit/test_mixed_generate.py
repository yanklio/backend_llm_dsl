"""Tests for mixed generation statistics."""

from types import SimpleNamespace

from packages.llm_providers.generators.mixed_generate import _build_mixed_statistics


def test_build_mixed_statistics_combines_phase_metrics() -> None:
    """It should preserve per-phase metrics and expose combined totals."""
    blueprint_result = SimpleNamespace(
        duration_seconds=1.5,
        input_tokens=10,
        output_tokens=4,
        total_tokens=14,
        provider="OpenRouter (phase1)",
    )
    code_result = SimpleNamespace(
        duration_seconds=2.0,
        input_tokens=8,
        output_tokens=20,
        total_tokens=28,
        provider="OpenRouter (phase2)",
    )

    stats = _build_mixed_statistics(blueprint_result, code_result)

    assert stats["phase1_duration"] == 1.5
    assert stats["phase2_duration"] == 2.0
    assert stats["total_duration_seconds"] == 3.5
    assert stats["phase1_input_tokens"] == 10
    assert stats["phase1_output_tokens"] == 4
    assert stats["phase1_total_tokens"] == 14
    assert stats["phase2_input_tokens"] == 8
    assert stats["phase2_output_tokens"] == 20
    assert stats["phase2_total_tokens"] == 28
    assert stats["input_tokens"] == 18
    assert stats["output_tokens"] == 24
    assert stats["total_tokens"] == 42
    assert stats["provider"] == "OpenRouter (phase2)"


def test_build_mixed_statistics_treats_missing_tokens_as_zero() -> None:
    """It should normalize nullable token fields to zero."""
    blueprint_result = SimpleNamespace(
        duration_seconds=1.0,
        input_tokens=None,
        output_tokens=None,
        total_tokens=None,
        provider="OpenRouter (phase1)",
    )
    code_result = SimpleNamespace(
        duration_seconds=2.0,
        input_tokens=5,
        output_tokens=None,
        total_tokens=5,
        provider="OpenRouter (phase2)",
    )

    stats = _build_mixed_statistics(blueprint_result, code_result)

    assert stats["phase1_input_tokens"] == 0
    assert stats["phase1_output_tokens"] == 0
    assert stats["phase1_total_tokens"] == 0
    assert stats["phase2_input_tokens"] == 5
    assert stats["phase2_output_tokens"] == 0
    assert stats["phase2_total_tokens"] == 5
    assert stats["input_tokens"] == 5
    assert stats["output_tokens"] == 0
    assert stats["total_tokens"] == 5
