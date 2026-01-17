import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.dsl.generate import main as dsl_generate_main
from src.llm.dsl_generate import natural_language_to_yaml, save_blueprint


def main():
    parser = argparse.ArgumentParser(
        description="Generate NestJS application from description"
    )

    parser.add_argument(
        "-b",
        "--blueprint",
        default="./blueprint.yaml",
        help="Path for blueprint YAML file (default: ./blueprint.yaml)",
    )

    parser.add_argument(
        "-p",
        "--project",
        default="./nest_project",
        help="Path for nest project directory (default: ./nest_project)",
    )

    parser.add_argument(
        "description",
        nargs="?",
        default="Create a NestJS application for a simple blog with users and posts",
        help="Description of the NestJS application to generate",
    )

    args = parser.parse_args()

    print("🤖 Generating blueprint with LLM...")
    result = natural_language_to_yaml(args.description)
    print(f"Stats: {result.duration_seconds}s via {result.provider}")

    save_blueprint(result.content, args.blueprint)
    print("✅ Blueprint generated!")
    print()

    print("🔧 Generating backend code...")
    try:
        dsl_generate_main(args.blueprint, args.project)
        print("✅ Backend code generated!")
    except Exception as e:
        print(f"❌ Failed to generate backend: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
