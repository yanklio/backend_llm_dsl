"""File-writing helpers for LLM-generated code output."""

import json
from pathlib import Path
from typing import Any

from src.shared import logger

ESCAPE_SEQUENCE_REPLACEMENTS = {
    "\\n": "\n",
    "\\t": "\t",
    '\\"': '"',
    "\\\\": "\\",
}


def _has_many_literal_escapes(content: str) -> bool:
    """Detect when a string likely contains over-escaped content."""
    return "\\n" in content and content.count("\\n") > content.count("\n") * 2


def prepare_file_content(content: Any, file_path: str) -> str:
    """Prepare generated file content for writing to disk."""
    if isinstance(content, (dict, list)):
        return json.dumps(content, indent=2)

    if isinstance(content, str) and _has_many_literal_escapes(content):
        logger.warn(f"Detected literal escape sequences in {file_path}, fixing...")
        for source, target in ESCAPE_SEQUENCE_REPLACEMENTS.items():
            content = content.replace(source, target)

    return content


def _write_generated_file(output_path: Path, file_path: str, content: Any) -> bool:
    """Write one generated file and report whether it succeeded."""
    try:
        full_path = output_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(prepare_file_content(content, file_path), encoding="utf-8")
        logger.success(f"Saved {file_path}")
        return True
    except Exception as exc:
        logger.error(f"Failed to save {file_path}: {exc}")
        return False


def save_generated_files(files: dict[str, Any], output_dir: str) -> int:
    """Write a generated file map to disk and return the saved file count."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    logger.start(f"Saving files to {output_dir}...")

    saved_count = 0
    for file_path, content in files.items():
        if _write_generated_file(output_path, file_path, content):
            saved_count += 1

    logger.end(f"Saved {saved_count}/{len(files)} files")
    return saved_count
