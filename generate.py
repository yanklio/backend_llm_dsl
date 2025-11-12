import argparse
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader


# --- Helper to convert types ---
def to_ts_type(py_type):
    """Converts a simple Python type to a TypeScript type."""
    if py_type == "string":
        return "string"
    if py_type == "number":
        return "number"
    if py_type == "boolean":
        return "boolean"
    if py_type == "enum":
        return "string"
    return "any"


def generate_root_module(root_config, modules_data, env, output_dir):
    """Generate root module files (app.module.ts, main.ts, etc.)"""
    print("\n=== Generating Root Module ===")

    root_name = root_config.get("name", "App")
    src_dir = output_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    # Prepare data for root templates
    template_data = {
        "root": root_config,
        "modules": modules_data,
        "module_names": [m["name"] for m in modules_data],
    }

    # Generate app.module.ts
    try:
        template = env.get_template("root/app.module.ts.j2")
        output_code = template.render(template_data)
        app_module_path = src_dir / "app.module.ts"
        app_module_path.write_text(output_code)
        print(f"  ✓ Generated {app_module_path}")
    except Exception as e:
        print(f"  ⚠ Could not generate app.module.ts: {e}")

    # Generate main.ts
    try:
        template = env.get_template("root/main.ts.j2")
        output_code = template.render(template_data)
        main_path = src_dir / "main.ts"
        main_path.write_text(output_code)
        print(f"  ✓ Generated {main_path}")
    except Exception as e:
        print(f"  ⚠ Could not generate main.ts: {e}")

    # Generate database config if database is specified
    if "database" in root_config:
        try:
            template = env.get_template("root/database.config.ts.j2")
            output_code = template.render(template_data)
            db_config_path = src_dir / "database.config.ts"
            db_config_path.write_text(output_code)
            print(f"  ✓ Generated {db_config_path}")
        except Exception as e:
            print(f"  ⚠ Could not generate database.config.ts: {e}")

    # Generate app.controller.ts and app.service.ts
    try:
        template = env.get_template("root/app.controller.ts.j2")
        output_code = template.render(template_data)
        app_controller_path = src_dir / "app.controller.ts"
        app_controller_path.write_text(output_code)
        print(f"  ✓ Generated {app_controller_path}")
    except Exception as e:
        print(f"  ⚠ Could not generate app.controller.ts: {e}")

    try:
        template = env.get_template("root/app.service.ts.j2")
        output_code = template.render(template_data)
        app_service_path = src_dir / "app.service.ts"
        app_service_path.write_text(output_code)
        print(f"  ✓ Generated {app_service_path}")
    except Exception as e:
        print(f"  ⚠ Could not generate app.service.ts: {e}")


def generate_module(module_data, env, base_output_dir):
    """Generate a single sub-module (entity module)"""
    module_name = module_data["name"]
    print(f"\n=== Generating Module: {module_name} ===")

    # Create module directory
    module_dir = base_output_dir / module_name.lower()
    module_dir.mkdir(parents=True, exist_ok=True)

    # Special paths for DTOs and entities
    dto_dir = module_dir / "dto"
    dto_dir.mkdir(parents=True, exist_ok=True)

    entities_dir = module_dir / "entities"
    entities_dir.mkdir(parents=True, exist_ok=True)

    files_to_generate = module_data.get("generate", [])

    # Prepare template data with module-specific info
    template_data = {
        "module": module_name,
        "entity": module_data.get("entity", {}),
        "authProtected": module_data.get("authProtected", False),
    }

    for file_key in files_to_generate:
        template_name = f"{file_key}.ts.j2"

        # Handle DTOs as a special case
        if file_key == "dto":
            # Generate create-dto
            try:
                template = env.get_template("dto/create-dto.ts.j2")
                output_code = template.render(template_data)
                file_name = f"create-{module_name.lower()}.dto.ts"
                (dto_dir / file_name).write_text(output_code)
                print(f"  ✓ Generated {dto_dir / file_name}")
            except Exception as e:
                print(f"  ✗ Failed to generate create DTO: {e}")

            # Generate update-dto
            try:
                template = env.get_template("dto/update-dto.ts.j2")
                output_code = template.render(template_data)
                file_name = f"update-{module_name.lower()}.dto.ts"
                (dto_dir / file_name).write_text(output_code)
                print(f"  ✓ Generated {dto_dir / file_name}")
            except Exception as e:
                print(f"  ✗ Failed to generate update DTO: {e}")
            continue

        # Handle entity as a special case
        if file_key == "entity":
            try:
                template = env.get_template(template_name)
                output_code = template.render(template_data)
                file_name = f"{module_name.lower()}.entity.ts"
                (entities_dir / file_name).write_text(output_code)
                print(f"  ✓ Generated {entities_dir / file_name}")
            except Exception as e:
                print(f"  ✗ Failed to generate entity: {e}")
            continue

        # Standard file generation (controller, service, module)
        try:
            template = env.get_template(template_name)
            output_code = template.render(template_data)
            file_name = f"{module_name.lower()}.{file_key}.ts"
            (module_dir / file_name).write_text(output_code)
            print(f"  ✓ Generated {module_dir / file_name}")
        except Exception as e:
            print(f"  ✗ Failed to generate {file_key}: {e}")


def main(blueprint_file):
    print("=" * 60)
    print("Starting Enhanced Code Generation")
    print(f"Blueprint: {blueprint_file}")
    print("=" * 60)

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
