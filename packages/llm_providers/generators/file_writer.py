"""File-writing helpers for LLM-generated code output."""

import json
from pathlib import Path
from typing import Any

from packages.shared import logger
from packages.shared.exceptions import FileWriteException

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


def resolve_generated_file_path(output_root: str | Path, generated_path: str) -> Path:
    """Resolve an LLM-generated path safely under the chosen output root.

    Args:
        output_root: Absolute or relative root directory chosen by the caller.
        generated_path: Relative generated child path from the LLM file map.

    Returns:
        Resolved absolute destination path.

    Raises:
        FileWriteException: If the generated path escapes the output root.
    """
    root = Path(output_root).expanduser().resolve()
    candidate = Path(generated_path)
    if candidate.is_absolute():
        raise FileWriteException(
            f"Generated file path must be relative: {generated_path}",
            code="WRITE001",
            context={"path": generated_path},
        )
    if ".." in candidate.parts:
        raise FileWriteException(
            f"Generated file path may not contain '..': {generated_path}",
            code="WRITE001",
            context={"path": generated_path},
        )

    resolved = (root / candidate).resolve(strict=False)
    if resolved != root and root not in resolved.parents:
        raise FileWriteException(
            f"Generated file path escapes output root: {generated_path}",
            code="WRITE001",
            context={"path": generated_path, "output_root": str(root)},
        )
    return resolved


def _write_generated_file(output_path: Path, file_path: str, content: Any) -> None:
    """Write one generated file, raising when validation or writing fails."""
    full_path = resolve_generated_file_path(output_path, file_path)
    try:
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(prepare_file_content(content, file_path), encoding="utf-8")
        logger.success(f"Saved {file_path}")
    except FileWriteException:
        raise
    except Exception as exc:
        logger.error(f"Failed to save {file_path}: {exc}")
        raise FileWriteException(
            f"Failed to save generated file {file_path}: {exc}",
            code="WRITE002",
            context={"path": file_path},
        ) from exc


def save_generated_files(files: dict[str, Any], output_dir: str) -> int:
    """Write a generated file map to disk and return the saved file count."""
    output_path = Path(output_dir).expanduser().resolve()
    resolved_files = [(file_path, resolve_generated_file_path(output_path, file_path)) for file_path in files]
    output_path.mkdir(parents=True, exist_ok=True)
    logger.start(f"Saving files to {output_dir}...")

    saved_count = 0
    for file_path, _resolved_path in resolved_files:
        _write_generated_file(output_path, file_path, files[file_path])
        saved_count += 1

    logger.end(f"Saved {saved_count}/{len(files)} files")
    return saved_count
