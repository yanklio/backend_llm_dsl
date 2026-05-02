"""Experiment identity and prompt metadata helpers."""

import hashlib
from datetime import datetime, timezone
from typing import Any

from src.llm.mixed_generate import MIXED_REQUEST_TEMPLATE
from src.llm.prompts import RAW_CODE_SYSTEM_PROMPT, SYSTEM_PROMPT
from src.llm.providers.gemini import GeminiProvider
from src.llm.providers.groq import GroqProvider
from src.llm.providers.ollama import OllamaProvider
from src.llm.providers.openrouter import OpenRouterProvider
from src.llm.raw_generate import RAW_REQUEST_TEMPLATE

PROMPT_VERSION = "full-app-scaffold-v1"
PROVIDER_MODELS = {
    "gemini": GeminiProvider.MODEL_NAME,
    "groq": GroqProvider.MODEL_NAME,
    "ollama": OllamaProvider.MODEL_NAME,
    "openrouter": OpenRouterProvider.MODEL_NAME,
}
APPROACH_PROMPT_SOURCES = {
    "dsl": [SYSTEM_PROMPT],
    "raw": [RAW_CODE_SYSTEM_PROMPT, RAW_REQUEST_TEMPLATE],
    "mixed": [SYSTEM_PROMPT, RAW_CODE_SYSTEM_PROMPT, MIXED_REQUEST_TEMPLATE],
}


def short_hash(value: str, length: int = 10) -> str:
    """Return a stable short SHA-256 hash for a string value."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def model_name_for_provider(provider: str) -> str:
    """Return the configured exact model name for a provider ID."""
    return PROVIDER_MODELS.get(provider, "unknown")


def prompt_hash_for(approach: str) -> str:
    """Return a stable hash of prompt text used by one approach."""
    prompt_text = "\n---PROMPT-PART---\n".join(APPROACH_PROMPT_SOURCES[approach])
    return short_hash(f"{PROMPT_VERSION}\n{prompt_text}")


def run_id_for(provider: str, approaches: list[str], created_at: str) -> str:
    """Create a readable timestamped run ID with a short identity hash."""
    timestamp = datetime.fromisoformat(created_at).strftime("%Y%m%d_%H%M%S")
    identity_hash = short_hash(f"{created_at}:{provider}:{','.join(approaches)}", length=8)
    return f"{timestamp}_{identity_hash}"


def build_run_metadata(provider: str, approaches: list[str]) -> dict[str, Any]:
    """Build metadata saved alongside every experiment run."""
    created_at = datetime.now(timezone.utc).isoformat()
    return {
        "run_id": run_id_for(provider, approaches, created_at),
        "created_at": created_at,
        "provider": provider,
        "model_name": model_name_for_provider(provider),
        "approaches": approaches,
        "prompt_version": PROMPT_VERSION,
        "prompt_hashes": {
            approach: prompt_hash_for(approach) for approach in approaches
        },
    }


def record_identity(
    *,
    provider: str,
    approach: str,
    test_case: str,
    tier: str,
) -> dict[str, str]:
    """Build identity metadata used for result records and resume keys."""
    return {
        "provider": provider,
        "model_name": model_name_for_provider(provider),
        "approach": approach,
        "test_case": test_case,
        "tier": tier,
        "prompt_version": PROMPT_VERSION,
        "prompt_hash": prompt_hash_for(approach),
    }


def resume_key(record: dict[str, Any]) -> tuple[str, ...]:
    """Return the identity tuple used to decide whether a run is already complete."""
    return (
        record.get("test_case", ""),
        record.get("approach", ""),
        record.get("provider", ""),
        record.get("model_name", ""),
        record.get("prompt_hash", ""),
    )
