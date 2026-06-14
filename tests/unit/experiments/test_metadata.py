"""Smoke tests for experiment metadata module."""

from src.experiments.metadata import (
    APPROACH_PROMPT_SOURCES,
    PROMPT_VERSION,
    PROVIDER_MODELS,
    build_run_metadata,
    model_name_for_provider,
    prompt_hash_for,
    record_identity,
    resume_key,
    short_hash,
)


class TestMetadataConstants:
    """Verify metadata constants are well-formed."""

    def test_prompt_version_is_string(self):
        assert isinstance(PROMPT_VERSION, str)
        assert len(PROMPT_VERSION) > 0

    def test_provider_models_has_all_keys(self):
        for pid in ["gemini", "groq", "ollama", "openrouter"]:
            assert pid in PROVIDER_MODELS
            assert isinstance(PROVIDER_MODELS[pid], str)

    def test_approach_prompt_sources_has_all_keys(self):
        for approach in ["dsl", "raw", "mixed"]:
            assert approach in APPROACH_PROMPT_SOURCES
            assert len(APPROACH_PROMPT_SOURCES[approach]) > 0


class TestMetadataFunctions:
    """Verify metadata helper functions return expected types."""

    def test_short_hash(self):
        result = short_hash("hello")
        assert isinstance(result, str)
        assert len(result) == 10

    def test_short_hash_custom_length(self):
        result = short_hash("hello", length=6)
        assert len(result) == 6

    def test_model_name_for_provider_known(self):
        name = model_name_for_provider("gemini")
        assert isinstance(name, str)
        assert len(name) > 0

    def test_model_name_for_provider_unknown(self):
        assert model_name_for_provider("nonexistent") == "unknown"

    def test_prompt_hash_for_dsl(self):
        result = prompt_hash_for("dsl")
        assert isinstance(result, str)

    def test_build_run_metadata(self):
        meta = build_run_metadata("openrouter", ["dsl", "raw"])
        assert meta["provider"] == "openrouter"
        assert meta["approaches"] == ["dsl", "raw"]
        assert "run_id" in meta
        assert "prompt_hashes" in meta

    def test_record_identity(self):
        identity = record_identity(
            provider="groq",
            approach="raw",
            test_case="TEST_CASE_1",
            tier="simple",
        )
        assert identity["provider"] == "groq"
        assert identity["approach"] == "raw"
        assert identity["test_case"] == "TEST_CASE_1"
        assert identity["tier"] == "simple"

    def test_resume_key(self):
        record = {
            "test_case": "TC1",
            "approach": "dsl",
            "provider": "gemini",
            "model_name": "gemma",
            "prompt_hash": "abc123",
        }
        key = resume_key(record)
        assert key == ("TC1", "dsl", "gemini", "gemma", "abc123")
