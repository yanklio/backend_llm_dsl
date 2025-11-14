import argparse
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

from helpers.logger import Logger
from helpers.module import generate_module
from helpers.root import generate_root_module
from helpers.types import to_ts_type


def handle_relations(modules_data, env, base_output_dir):
    relations_map = {}
    for module_data in modules_data:
        module_name = module_data["name"]
        for relation in module_data.get("entity", {}).get("relations", []):
            try:
                related_model = relation["model"]
                relation_type = relation["type"]
                relation_field = relation["field"]
                relation_on_delete = relation.get("onDelete", "CASCADE")

                relations_map[(module_name, related_model)] = {
                    "model": related_model,
                    "type": relation_type,
                    "field": relation_field,
                    "onDelete": relation_on_delete,
                }

            except KeyError:
                Logger.error(f"Invalid relation format: {relation}")

    # Remove invalid relations where the related model doesn't exist as a module
    module_names = {module_data["name"] for module_data in modules_data}
    valid_relations = {}
    for (module_name, related_model), relation_data in relations_map.items():
        if related_model in module_names:
            valid_relations[(module_name, related_model)] = relation_data
        else:
            Logger.warn(
                f"Removing invalid relation: {module_name} -> {related_model} "
                f"(module '{related_model}' not found)"
            )

    # Second pass: add inverseField for bidirectional relations
    for (module_name, related_model), relation_data in valid_relations.items():
        # Check if there's a reverse relation
        reverse_key = (related_model, module_name)
        if reverse_key in valid_relations:
            reverse_relation = valid_relations[reverse_key]
            # Add inverseField pointing to the field in the related entity
            relation_data["inverseField"] = reverse_relation["field"]

    return valid_relations


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

    # Process relations and enrich them with inverseField mappings
    relations_map = handle_relations(modules_data, env, base_output_dir)

    if not modules_data:
        Logger.warn("No modules defined in blueprint!")
        return

    # Enrich module data with processed relations
    for module_data in modules_data:
        module_name = module_data["name"]
        # Find all relations for this module and add inverseField
        if "entity" in module_data and "relations" in module_data["entity"]:
            for relation in module_data["entity"]["relations"]:
                related_model = relation["model"]
                relation_key = (module_name, related_model)
                if relation_key in relations_map:
                    # Add inverseField from the processed relations
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
