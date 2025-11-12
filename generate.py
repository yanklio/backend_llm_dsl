import argparse
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

from helpers.module import generate_module
from helpers.root import generate_root_module
from helpers.types import to_ts_type


def main(blueprint_file):
    print("=" * 60)
    print("Starting Enhanced Code Generation")
    print(f"Blueprint: {blueprint_file}")
    print("=" * 60 + "\n\n")

    # Load the YAML data
    with open(blueprint_file, "r") as f:
        data = yaml.safe_load(f)

    # Setup Jinja2 environment
    env = Environment(loader=FileSystemLoader("./templates"))
    # Add custom filter
    env.filters["to_ts_type"] = to_ts_type

    # Base output directory
    base_output_dir = Path("nest_project")

    # Extract root and modules configuration
    root_config = data.get("root", {})
    modules_data = data.get("modules", [])

    if not modules_data:
        print("\n⚠ Warning: No modules defined in blueprint!")
        return

    # Generate root module files
    generate_root_module(root_config, modules_data, env, base_output_dir)

    # Generate each sub-module
    src_dir = base_output_dir / "src"
    for module_data in modules_data:
        generate_module(module_data, env, src_dir)

    print("\n" + "=" * 60)
    print("✓ Generation Complete!")
    print("=" * 60)

    # Print summary
    print("\nGenerated:")
    print(f"  - Root module: {root_config.get('name', 'App')}")
    print(f"  - Sub-modules: {len(modules_data)}")
    for module in modules_data:
        print(f"    • {module['name']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate Nest.JS code from an enhanced YAML blueprint with root + sub-modules."
    )
    parser.add_argument(
        "blueprint_file",
        type=str,
        nargs="?",
        default="blueprint.yaml",
        help="The path to the YAML blueprint file (default: blueprint.yaml)",
    )

    args = parser.parse_args()

    main(args.blueprint_file)
