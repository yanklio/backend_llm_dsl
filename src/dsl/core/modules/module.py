"""Module generation logic for the DSL engine."""

from pathlib import Path
from typing import Any

from jinja2 import Environment

from src.shared.exceptions import TemplateException
from src.shared.logs.logger import logger
from src.shared.template_helper import TemplateRenderer


def handle_dto_file(template_data: dict[str, Any], dto_dir: Path, env: Environment) -> None:
    """Generate DTO files for the module.

    Args:
        template_data (dict[str, Any]): Data passed to the template.
        dto_dir (Path): Directory where DTOs should be saved.
        env (Environment): Jinja2 environment.
    """
    renderer = TemplateRenderer(env)
    module_lower = template_data["module"].lower()

    # Generate create DTO
    try:
        file_name = f"create-{module_lower}.dto.ts"
        renderer.render_template("dto/create-dto.ts.j2", template_data, dto_dir / file_name)
    except TemplateException as e:
        logger.error(f"Failed to generate create DTO: {e}")

    # Generate update DTO
    try:
        file_name = f"update-{module_lower}.dto.ts"
        renderer.render_template("dto/update-dto.ts.j2", template_data, dto_dir / file_name)
    except TemplateException as e:
        logger.error(f"Failed to generate update DTO: {e}")


def handle_entity_file(template_data: dict[str, Any], entities_dir: Path, env: Environment) -> None:
    """Generate entity files for the module.

    Args:
        template_data (dict[str, Any]): Data passed to the template.
        entities_dir (Path): Directory where entities should be saved.
        env (Environment): Jinja2 environment.
    """
    renderer = TemplateRenderer(env)
    file_name = f"{template_data['module'].lower()}.entity.ts"

    try:
        renderer.render_template("entity.ts.j2", template_data, entities_dir / file_name)
    except TemplateException as e:
        logger.error(f"Failed to generate entity file: {e}")


def generate_module(module_data: dict[str, Any], env: Environment, base_output_dir: Path) -> None:
    """Generate a single sub-module (entity module).

    Args:
        module_data (dict[str, Any]): Configuration for the module.
        env (Environment): Jinja2 environment.
        base_output_dir (Path): Base directory for output.
    """
    module_name = module_data["name"]
    logger.start(f"Generating {module_name} module...")

    module_dir = base_output_dir / module_name.lower()
    module_dir.mkdir(parents=True, exist_ok=True)

    dto_dir = module_dir / "dto"
    dto_dir.mkdir(parents=True, exist_ok=True)

    entities_dir = module_dir / "entities"
    entities_dir.mkdir(parents=True, exist_ok=True)

    files_to_generate = module_data.get("generate", [])

    template_data = {
        "module": module_name,
        "entity": module_data.get("entity", {}),
        "authProtected": module_data.get("authProtected", False),
        "relatedEntities": module_data.get("relatedEntities", []),
    }

    renderer = TemplateRenderer(env)

    for file_key in files_to_generate:
        template_name = f"{file_key}.ts.j2"

        if file_key == "dto":
            handle_dto_file(template_data, dto_dir, env)
            continue

        if file_key == "entity":
            handle_entity_file(template_data, entities_dir, env)
            continue

        try:
            file_name = f"{module_name.lower()}.{file_key}.ts"
            renderer.render_template(template_name, template_data, module_dir / file_name)
        except TemplateException as e:
            logger.error(f"Failed to generate {file_key}: {e}")

    logger.end(f"{module_name} module generated")
