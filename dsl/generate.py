import argparse
from pathlib import Path

import yaml
from core.modules.module import generate_module
from core.modules.relation import handle_relations
from core.root import generate_root_module
from jinja2 import Environment, FileSystemLoader
from utils.logger import Logger
from utils.type import to_ts_type


def main(blueprint_file):
    print("=" * 60)
    print("Starting Code Generation")
    print(f"Blueprint: {blueprint_file}")
    print("=" * 60 + "\n\n")

    with open(blueprint_file, "r") as f:
        data = yaml.safe_load(f)

    script_dir = Path(__file__).parent
    template_dir = script_dir / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))

    env.filters["to_ts_type"] = to_ts_type

    base_output_dir = Path("nest_project")

    root_config = data.get("root", {})
    modules_data = data.get("modules", [])


    if not modules_data:
        Logger.warn("No modules defined in blueprint!")
        return
    
    relations_map = handle_relations(modules_data, env, base_output_dir)

    for module_data in modules_data:
        module_name = module_data["name"]
        if "entity" in module_data and "relations" in module_data["entity"]:
            for relation in module_data["entity"]["relations"]:
                related_model = relation["model"]
                relation_key = (module_name, related_model)
                if relation_key in relations_map:
                    if "inverseField" in relations_map[relation_key]:
                        relation["inverseField"] = relations_map[relation_key]["inverseField"]

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
