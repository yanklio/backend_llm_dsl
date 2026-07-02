"""Unified CLI entry point for the NestJS code generator."""

import argparse
from pathlib import Path

import yaml

from apps.experiments.runner import run_experiments
from packages.dsl_core.compiler import compile_file
from packages.generator_nestjs.generate import generate_from_file
from packages.generator_nestjs.generate import main as dsl_generate_main
from packages.llm_providers.generators.dsl_generate import natural_language_to_yaml, save_blueprint
from packages.llm_providers.generators.output import log_generation_statistics
from packages.shared import logger


def cmd_generate(args: argparse.Namespace) -> None:
    """Backward-compatible DSL pipeline command."""
    result = natural_language_to_yaml(args.description, provider=args.model)
    log_generation_statistics(result)
    save_blueprint(result.content, args.blueprint)
    try:
        dsl_generate_main(args.blueprint, args.project)
    except Exception as exc:
        logger.error(f"Code generation failed: {exc}")
        raise SystemExit(1) from exc


def cmd_generate_raw(args: argparse.Namespace) -> None:
    """Backward-compatible raw pipeline command."""
    from packages.llm_providers.generators.raw_generate import generate_code_files, save_files

    result, files = generate_code_files(args.description, args.project, provider=args.model)
    log_generation_statistics(result)
    save_files(files, args.project)


def cmd_generate_mixed(args: argparse.Namespace) -> None:
    """Backward-compatible mixed pipeline command."""
    from packages.llm_providers.generators.mixed_generate import mixed_generate, save_mixed_files

    result = mixed_generate(
        description=args.description,
        output_dir=args.project,
        blueprint_path=args.blueprint,
        primary_model=args.model,
    )
    if not result["success"]:
        logger.error(f"Generation failed: {result.get('error')}")
        raise SystemExit(1)
    save_mixed_files(result["files"], args.project)


def cmd_compile(args: argparse.Namespace) -> None:
    """Compile textual DSL to YAML blueprint."""
    blueprint = compile_file(args.input)
    text = yaml.safe_dump(blueprint, sort_keys=False)
    if args.output:
        Path(args.output).write_text(text)
    else:
        print(text)


def cmd_validate(args: argparse.Namespace) -> None:
    """Validate textual DSL syntax and semantics."""
    compile_file(args.input)
    logger.success("DSL is valid")


def cmd_generate_file(args: argparse.Namespace) -> None:
    """Generate a NestJS project from a .dsl or YAML file."""
    generate_from_file(args.input, args.output)


def cmd_generate_prompt(args: argparse.Namespace) -> None:
    """Generate a YAML blueprint from a natural-language requirement."""
    result = natural_language_to_yaml(args.requirement, provider=args.provider)
    log_generation_statistics(result)
    save_blueprint(result.content, args.output)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(description="Generate runnable NestJS application scaffolds.")
    parser.add_argument("-m", "--model", default=None, help="LLM provider")
    subparsers = parser.add_subparsers(dest="command", required=True)

    dsl_parser = subparsers.add_parser("dsl")
    dsl_parser.add_argument("description")
    dsl_parser.add_argument("-b", "--blueprint", default="./blueprint.yaml")
    dsl_parser.add_argument("-p", "--project", default="./nest_project")
    dsl_parser.set_defaults(func=cmd_generate)

    raw_parser = subparsers.add_parser("raw")
    raw_parser.add_argument("description")
    raw_parser.add_argument("-p", "--project", default="./nest_project")
    raw_parser.set_defaults(func=cmd_generate_raw)

    mixed_parser = subparsers.add_parser("mixed")
    mixed_parser.add_argument("description")
    mixed_parser.add_argument("-b", "--blueprint", default="./mixed_blueprint.yaml")
    mixed_parser.add_argument("-p", "--project", default="./nest_project")
    mixed_parser.set_defaults(func=cmd_generate_mixed)

    compile_parser = subparsers.add_parser("compile")
    compile_parser.add_argument("input")
    compile_parser.add_argument("--output", "-o")
    compile_parser.set_defaults(func=cmd_compile)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("input")
    validate_parser.set_defaults(func=cmd_validate)

    generate_file_parser = subparsers.add_parser("generate-file")
    generate_file_parser.add_argument("input")
    generate_file_parser.add_argument("--output", "-o", required=True)
    generate_file_parser.set_defaults(func=cmd_generate_file)

    prompt_parser = subparsers.add_parser("generate-prompt")
    prompt_parser.add_argument("requirement")
    prompt_parser.add_argument("--approach", choices=["dsl"], default="dsl")
    prompt_parser.add_argument("--provider", default="openrouter")
    prompt_parser.add_argument("--model", default=None)
    prompt_parser.add_argument("--output", "-o", default="blueprint.yaml")
    prompt_parser.set_defaults(func=cmd_generate_prompt)

    experiments_parser = subparsers.add_parser("experiments")
    experiment_subparsers = experiments_parser.add_subparsers(dest="experiment_command", required=True)
    run_parser = experiment_subparsers.add_parser("run")
    run_parser.add_argument("--approach", default="all")
    run_parser.add_argument("--provider", default="openrouter")
    run_parser.add_argument("--model", default=None)
    run_parser.add_argument("--case", dest="case_id", default=None)
    run_parser.add_argument("--limit", type=int, default=None)
    run_parser.add_argument("--repetitions", type=int, default=1)
    run_parser.add_argument("--judge", action="store_true")
    run_parser.set_defaults(
        func=lambda args: run_experiments(
            approach=args.approach,
            provider=args.provider,
            case_id=args.case_id,
            limit=args.limit,
            repetitions=args.repetitions,
            judge_enabled=args.judge,
        )
    )
    export_parser = experiment_subparsers.add_parser("export")
    export_parser.set_defaults(func=lambda _args: __import__("apps.experiments.export_analytics"))
    return parser


def main() -> None:
    """Main CLI entry point."""
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
