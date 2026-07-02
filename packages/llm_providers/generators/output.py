"""Logging helpers for LLM generation results."""

from pathlib import Path

from packages.llm_providers import GenerationResult
from packages.llm_providers.core.response_parser import clean_llm_response, try_parse_json
from packages.shared import logger

RUN_INSTRUCTIONS = ["npm install", "npm run start:dev"]


def parse_generated_files(result: GenerationResult) -> tuple[GenerationResult, dict]:
    """Clean and parse an LLM JSON file-map response."""
    result.raw_content = result.content
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
        logger.info(f"Tokens: {result.total_tokens} (In: {result.input_tokens}, Out: {result.output_tokens})")


def log_run_instructions(output_dir: str) -> None:
    """Log the standard commands for running a generated NestJS project."""
    logger.success("Done! Run with:")
    logger.info(f"  cd {output_dir}")
    for instruction in RUN_INSTRUCTIONS:
        logger.info(f"  {instruction}")
