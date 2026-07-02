"""Experiment identity and prompt metadata helpers."""

import hashlib
import platform
import subprocess
from datetime import datetime, timezone
from typing import Any

from packages.llm_providers.core.client import get_default_model_name
from packages.llm_providers.core.prompts import (
    RAW_CODE_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    TEXTUAL_DSL_SPEC_REFERENCE,
    TEXTUAL_FEWSHOT_EXAMPLES,
)
from packages.llm_providers.generators.mixed_generate import MIXED_REQUEST_TEMPLATE
from packages.llm_providers.generators.raw_generate import RAW_REQUEST_TEMPLATE

PROMPT_VERSION = "full-app-scaffold-v1"
PROMPT_VERSIONS = {
    "dsl": "yaml-blueprint-v1",
    "raw": "raw-file-map-v1",
    "mixed": "mixed-blueprint-file-map-v1",
    "textual-gen-baseline": "textual-baseline-v1",
    "textual-gen-spec": "textual-spec-v1",
    "textual-gen-fewshot": "textual-fewshot-v1",
}
PROVIDER_IDS = ["gemini", "groq", "ollama", "openrouter"]
PROVIDER_MODELS = {pid: get_default_model_name(pid) for pid in PROVIDER_IDS}
APPROACH_PROMPT_SOURCES = {
    "dsl": [SYSTEM_PROMPT],
    "raw": [RAW_CODE_SYSTEM_PROMPT, RAW_REQUEST_TEMPLATE],
    "mixed": [SYSTEM_PROMPT, RAW_CODE_SYSTEM_PROMPT, MIXED_REQUEST_TEMPLATE],
    "textual-gen-baseline": ["Generate a textual DSL specification for the requested NestJS backend."],
    "textual-gen-spec": [TEXTUAL_DSL_SPEC_REFERENCE],
    "textual-gen-fewshot": [TEXTUAL_DSL_SPEC_REFERENCE, TEXTUAL_FEWSHOT_EXAMPLES],
}


def short_hash(value: str, length: int = 10) -> str:
    """Return a stable short SHA-256 hash for a string value."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def model_name_for_provider(provider: str) -> str:
    """Return the configured exact model name for a provider ID."""
    return PROVIDER_MODELS.get(provider, "unknown")


def prompt_version_for(approach: str) -> str:
    """Return the prompt version for an approach."""
    return PROMPT_VERSIONS[approach]


def prompt_hash_for(approach: str) -> str:
    """Return a stable hash of prompt text used by one approach."""
    prompt_text = "\n---PROMPT-PART---\n".join(APPROACH_PROMPT_SOURCES[approach])
    return short_hash(f"{prompt_version_for(approach)}\n{prompt_text}")


def _command_output(command: list[str]) -> str:
    try:
        return subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "unknown"


def run_id_for(provider: str, approaches: list[str], created_at: str) -> str:
    """Create a readable timestamped run ID with a short identity hash."""
    timestamp = datetime.fromisoformat(created_at).strftime("%Y%m%d_%H%M%S")
    identity_hash = short_hash(f"{created_at}:{provider}:{','.join(approaches)}", length=8)
    return f"{timestamp}_{identity_hash}"


def build_run_metadata(
    provider: str,
    approaches: list[str],
    repetitions: int = 1,
    case_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Build metadata saved alongside every experiment run."""
    created_at = datetime.now(timezone.utc).isoformat()
    return {
        "run_id": run_id_for(provider, approaches, created_at),
        "created_at": created_at,
        "git_commit": _command_output(["git", "rev-parse", "HEAD"]),
        "working_tree_dirty": bool(_command_output(["git", "status", "--porcelain"])),
        "provider": provider,
        "model_name": model_name_for_provider(provider),
        "temperature": 0.1,
        "repetitions": repetitions,
        "approaches": approaches,
        "selected_test_cases": case_ids or [],
        "prompt_versions": {approach: prompt_version_for(approach) for approach in approaches},
        "prompt_hashes": {approach: prompt_hash_for(approach) for approach in approaches},
        "python_version": platform.python_version(),
        "node_version": _command_output(["node", "--version"]),
        "npm_version": _command_output(["npm", "--version"]),
    }


def record_identity(
    *,
    provider: str,
    approach: str,
    test_case: str,
    tier: str,
    repetition: int = 1,
) -> dict[str, Any]:
    """Build identity metadata used for result records and resume keys."""
    return {
        "provider": provider,
        "model_name": model_name_for_provider(provider),
        "approach": approach,
        "test_case": test_case,
        "tier": tier,
        "prompt_version": prompt_version_for(approach),
        "prompt_hash": prompt_hash_for(approach),
        "repetition": repetition,
    }


def resume_key(record: dict[str, Any]) -> tuple[str, ...]:
    """Return the identity tuple used to decide whether a run is already complete."""
    key = (
        record.get("test_case", ""),
        record.get("approach", ""),
        record.get("provider", ""),
        record.get("model_name", ""),
        record.get("prompt_hash", ""),
    )
    if "repetition" not in record:
        return key
    return (*key, str(record.get("repetition", "")))
