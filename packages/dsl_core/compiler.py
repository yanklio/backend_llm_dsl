"""Public compiler facade for textual DSL input."""

import argparse
from pathlib import Path
from typing import Any

import yaml

from .emitter import emit_blueprint
from .parser import parse
from .resolver import resolve


def compile_textual_dsl(source: str) -> dict[str, Any]:
    """Compile textual DSL source into an existing YAML blueprint dictionary."""
    program = parse(source)
    resolved = resolve(program)
    return emit_blueprint(resolved)


def compile_file(path: str | Path) -> dict[str, Any]:
    """Compile a textual DSL file into a blueprint dictionary."""
    source_path = Path(path)
    return compile_textual_dsl(source_path.read_text())


def main() -> None:
    """Compile textual DSL from the command line."""
    parser = argparse.ArgumentParser(description="Compile textual DSL to YAML blueprint")
    parser.add_argument("source", type=str, help="Path to a .dsl source file")
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Optional path where the YAML blueprint should be written",
    )
    args = parser.parse_args()

    blueprint = compile_file(args.source)
    yaml_text = yaml.safe_dump(blueprint, sort_keys=False)
    if args.output:
        Path(args.output).write_text(yaml_text)
    else:
        print(yaml_text)


if __name__ == "__main__":
    main()
