"""Unified CLI entry point for the NestJS code generator."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.generator_nestjs.generate import main as dsl_generate_main
from packages.llm_providers.generators.dsl_generate import natural_language_to_yaml, save_blueprint
from packages.llm_providers.generators.output import log_generation_statistics
from packages.shared import logger


def cmd_generate(args: argparse.Namespace) -> None:
    """DSL pipeline: NL -> blueprint -> generated code."""
    logger.start("Generating YAML blueprint from description...")
    result = natural_language_to_yaml(args.description, provider=args.model)
    log_generation_statistics(result)

    save_blueprint(result.content, args.blueprint)
    logger.success(f"Blueprint saved to {args.blueprint}")

    logger.start("Generating NestJS code from blueprint...")
    try:
        dsl_generate_main(args.blueprint, args.project)
        logger.success(f"Code generated in {args.project}/")
    except Exception as e:
        logger.error(f"Code generation failed: {e}")
        sys.exit(1)


def cmd_generate_raw(args: argparse.Namespace) -> None:
    """Raw pipeline: NL -> LLM file map -> generated code."""
    from packages.llm_providers.generators.raw_generate import generate_code_files, save_files

    logger.start("Generating code directly via LLM...")
    result, files = generate_code_files(args.description, args.project, provider=args.model)
    log_generation_statistics(result)
    save_files(files, args.project)
    logger.success(f"Code generated in {args.project}/")


def cmd_generate_mixed(args: argparse.Namespace) -> None:
    """Mixed pipeline: NL -> blueprint -> LLM file map -> generated code."""
    from packages.llm_providers.generators.mixed_generate import mixed_generate, save_mixed_files

    logger.start("Running mixed pipeline...")
    result = mixed_generate(
        description=args.description,
        output_dir=args.project,
        blueprint_path=args.blueprint,
        primary_model=args.model,
    )

    if result["success"]:
        save_mixed_files(result["files"], args.project)
        logger.success(f"Code generated in {args.project}/")
    else:
        logger.error(f"Generation failed: {result.get('error')}")
        sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="NestJS AI Generator - transform natural language into NestJS code",
    )
    parser.add_argument(
        "-m",
        "--model",
        default=None,
        help="LLM provider (gemini, groq, ollama, openrouter)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # dsl
    dsl_parser = subparsers.add_parser("dsl", help="DSL pipeline: NL -> blueprint -> templates")
    dsl_parser.add_argument("description", help="Natural language description")
    dsl_parser.add_argument("-b", "--blueprint", default="./blueprint.yaml")
    dsl_parser.add_argument("-p", "--project", default="./nest_project")

    # raw
    raw_parser = subparsers.add_parser("raw", help="Raw pipeline: NL -> LLM file map")
    raw_parser.add_argument("description", help="Natural language description")
    raw_parser.add_argument("-p", "--project", default="./nest_project")

    # mixed
    mixed_parser = subparsers.add_parser("mixed", help="Mixed pipeline: NL -> blueprint -> LLM file map")
    mixed_parser.add_argument("description", help="Natural language description")
    mixed_parser.add_argument("-b", "--blueprint", default="./mixed_blueprint.yaml")
    mixed_parser.add_argument("-p", "--project", default="./nest_project")

    return parser


def main() -> None:
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "dsl":
        cmd_generate(args)
    elif args.command == "raw":
        cmd_generate_raw(args)
    elif args.command == "mixed":
        cmd_generate_mixed(args)


if __name__ == "__main__":
    main()
