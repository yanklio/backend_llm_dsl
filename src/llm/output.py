"""Shared output, parsing, and file-writing helpers for LLM generation."""

import json
from pathlib import Path
from typing import Any

from src.llm import GenerationResult
from src.llm.response_parser import clean_llm_response, try_parse_json
from src.shared import logger

ESCAPE_SEQUENCE_REPLACEMENTS = {
    "\\n": "\n",
    "\\t": "\t",
    '\\"': '"',
    "\\\\": "\\",
}
RUN_INSTRUCTIONS = ["npm install", "npm run start:dev"]


def parse_generated_files(result: GenerationResult) -> tuple[GenerationResult, dict[str, Any]]:
    """Clean and parse an LLM JSON file-map response."""
    cleaned_content = clean_llm_response(result.content)
    result.content = cleaned_content
    return result, try_parse_json(cleaned_content)


def log_json_parse_failure(cleaned_content: str, error: Exception) -> None:
    """Log detailed diagnostics for an invalid JSON LLM response."""
    debug_file = Path("/tmp/llm_response_debug.json")
    debug_file.write_text(cleaned_content)

    logger.error("Failed to parse LLM response as JSON")
    logger.error(f"Parse error: {error}")
    logger.error(f"Saved malformed response to {debug_file}")
    logger.error("First 2000 chars of cleaned response:")
    logger.error(cleaned_content[:2000])
    logger.error("Last 500 chars of cleaned response:")
    logger.error(cleaned_content[-500:])


def log_generation_statistics(result: GenerationResult) -> None:
    """Log standard provider, duration, and token statistics."""
    logger.info("=== Generation Statistics ===")
    logger.info(f"Provider: {result.provider}")
    logger.info(f"Time: {result.duration_seconds:.2f}s")
    if result.total_tokens:
        logger.info(
            f"Tokens: {result.total_tokens} (In: {result.input_tokens}, Out: {result.output_tokens})"
        )


def log_run_instructions(output_dir: str) -> None:
    """Log the standard commands for running a generated NestJS project."""
    logger.success("Done! Run with:")
    logger.info(f"  cd {output_dir}")
    for instruction in RUN_INSTRUCTIONS:
        logger.info(f"  {instruction}")


def prepare_file_content(content: Any, file_path: str) -> str:
    """Prepare generated file content for writing to disk."""
    if isinstance(content, (dict, list)):
        return json.dumps(content, indent=2)

    if isinstance(content, str) and _has_many_literal_escapes(content):
        logger.warn(f"Detected literal escape sequences in {file_path}, fixing...")
        for source, target in ESCAPE_SEQUENCE_REPLACEMENTS.items():
            content = content.replace(source, target)

    return content


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


def _has_many_literal_escapes(content: str) -> bool:
    """Detect when a string likely contains over-escaped content."""
    return "\\n" in content and content.count("\\n") > content.count("\n") * 2


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
