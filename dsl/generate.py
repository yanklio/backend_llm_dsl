import argparse
import sys
from pathlib import Path

import yaml
from core.modules.module import generate_module
from core.modules.relation import handle_relations
from core.root import generate_root_module
from jinja2 import Environment, FileSystemLoader
from utils.type import to_ts_type

# Add parent directory to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared.logs.logger import logger


def main(blueprint_file, nest_project_path=None):
    with open(blueprint_file, "r") as f:
        data = yaml.safe_load(f)

    script_dir = Path(__file__).parent
    template_dir = script_dir / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))

    env.filters["to_ts_type"] = to_ts_type

    base_output_dir = Path(nest_project_path) if nest_project_path else Path("nest_project")

    if not base_output_dir.exists():
        base_output_dir.mkdir(parents=True, exist_ok=True)

    root_config = data.get("root", {})
    modules_data = data.get("modules", [])

    if not modules_data:
        logger.warn("No modules defined in blueprint!")
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

    generate_root_module(root_config, modules_data, env, base_output_dir)

    src_dir = base_output_dir / "src"
    for module_data in modules_data:
        generate_module(module_data, env, src_dir)

    logger.success(f"✓ Generation Complete! ({len(modules_data)} modules)")


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
    parser.add_argument(
        "--nest-project",
        "-p",
        type=str,
        help="Path to existing NestJS project directory (default: nest_project)",
    )

    args = parser.parse_args()

    main(args.blueprint_file, args.nest_project)
