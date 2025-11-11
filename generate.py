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
    return "any"


def main(blueprint_file):
    print(f"Starting code generation from: {blueprint_file}")

    # Load the YAML data
    with open(blueprint_file, "r") as f:
        data = yaml.safe_load(f)

    # Setup Jinja2 environment
    env = Environment(loader=FileSystemLoader("./templates"))
    # Add custom filter
    env.filters["to_ts_type"] = to_ts_type

    module_name = data["module"].lower()

    # Base output path for all generated Nest.JS code
    base_output_dir = Path(f"nest_project/src/{module_name}")
    base_output_dir.mkdir(parents=True, exist_ok=True)

    # Special path for DTOs
    dto_dir = base_output_dir / "dto"
    dto_dir.mkdir(parents=True, exist_ok=True)

    # Special path for entities
    entities_dir = base_output_dir / "entities"
    entities_dir.mkdir(parents=True, exist_ok=True)

    files_to_generate = data.get("generate", [])

    print(f"Generating module: {data['module']}")

    for file_key in files_to_generate:
        template_name = f"{file_key}.ts.j2"

        # Handle DTOs as a special case
        if file_key == "dto":
            # Generate create-dto
            template_name = "dto/create-dto.ts.j2"
            template = env.get_template(template_name)
            output_code = template.render(data)
            file_name = f"create-{module_name}.dto.ts"
            (dto_dir / file_name).write_text(output_code)
            print(f"  ✓ Generated {dto_dir / file_name}")

            # Generate update-dto
            template_name = "dto/update-dto.ts.j2"
            template = env.get_template(template_name)
            output_code = template.render(data)
            file_name = f"update-{module_name}.dto.ts"
            (dto_dir / file_name).write_text(output_code)
            print(f"  ✓ Generated {dto_dir / file_name}")
            continue  # Skip to next file

        # Handle entity as a special case
        if file_key == "entity":
            template = env.get_template(template_name)
            output_code = template.render(data)
            file_name = f"{module_name}.entity.ts"
            (entities_dir / file_name).write_text(output_code)
            print(f"  ✓ Generated {entities_dir / file_name}")
            continue  # Skip to next file

        # Standard file generation
        template = env.get_template(template_name)

        # Render the template with data from YAML
        output_code = template.render(data)

        # Save the file
        file_name = f"{module_name}.{file_key}.ts"
        (base_output_dir / file_name).write_text(output_code)
        print(f"  ✓ Generated {base_output_dir / file_name}")

    print("\nGeneration complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Nest.JS code from a YAML blueprint.")
    parser.add_argument("blueprint_file", type=str, help="The path to the YAML blueprint file.")

    args = parser.parse_args()

    main(args.blueprint_file)
