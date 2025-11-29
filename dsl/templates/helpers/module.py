from .logger import Logger


def handle_dto_file(template_data, dto_dir, env):
    try:
        template = env.get_template("dto/create-dto.ts.j2")
        output_code = template.render(template_data)
        file_name = f"create-{template_data['module'].lower()}.dto.ts"
        (dto_dir / file_name).write_text(output_code)
        Logger.success(f"Generated {dto_dir / file_name}")
    except Exception as e:
        Logger.error(f"Failed to generate create DTO: {e}")

    # Generate update-dto
    try:
        template = env.get_template("dto/update-dto.ts.j2")
        output_code = template.render(template_data)
        file_name = f"update-{template_data['module'].lower()}.dto.ts"
        (dto_dir / file_name).write_text(output_code)
        Logger.success(f"Generated {dto_dir / file_name}")
    except Exception as e:
        Logger.error(f"Failed to generate update DTO: {e}")


def handle_entity_file(template_data, entities_dir, env):
    try:
        template = env.get_template("entity.ts.j2")
        output_code = template.render(template_data)
        file_name = f"{template_data['module'].lower()}.entity.ts"
        (entities_dir / file_name).write_text(output_code)
        Logger.success(f"Generated {entities_dir / file_name}")
    except Exception as e:
        Logger.error(f"Failed to generate entity file: {e}")


def generate_module(module_data, env, base_output_dir):
    """Generate a single sub-module (entity module)"""
    module_name = module_data["name"]
    Logger.start(f"Generating module: {module_name}")

    module_dir = base_output_dir / module_name.lower()
    module_dir.mkdir(parents=True, exist_ok=True)

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

        if file_key == "dto":
            handle_dto_file(template_data, dto_dir, env)
            continue

        if file_key == "entity":
            handle_entity_file(template_data, entities_dir, env)
            continue

        try:
            template = env.get_template(template_name)
            output_code = template.render(template_data)
            file_name = f"{module_name.lower()}.{file_key}.ts"
            (module_dir / file_name).write_text(output_code)
            Logger.success(f"Generated {module_dir / file_name}")
        except Exception as e:
            Logger.error(f"Failed to generate {file_key}: {e}")

    Logger.end(f"Generated module: {module_name}")
