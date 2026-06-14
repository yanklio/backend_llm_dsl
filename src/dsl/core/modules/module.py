"""Module generation logic for the DSL engine."""

from pathlib import Path
from typing import Any

from jinja2 import Environment

from src.shared.exceptions import TemplateException
from src.shared.logger import logger
from src.shared.template import TemplateRenderer

DTO_TEMPLATES = [
    ("dto/create-dto.ts.j2", "create-{module}.dto.ts", "create DTO"),
    ("dto/update-dto.ts.j2", "update-{module}.dto.ts", "update DTO"),
]
SPECIAL_FILE_GENERATORS = {
    "dto": lambda template_data, module_dirs, env: handle_dto_file(
        template_data,
        module_dirs["dto"],
        env,
    ),
    "entity": lambda template_data, module_dirs, env: handle_entity_file(
        template_data,
        module_dirs["entities"],
        env,
    ),
}


def handle_dto_file(template_data: dict[str, Any], dto_dir: Path, env: Environment) -> None:
    """Generate DTO files for the module.

    Args:
        template_data (dict[str, Any]): Data passed to the template.
        dto_dir (Path): Directory where DTOs should be saved.
        env (Environment): Jinja2 environment.
    """
    renderer = TemplateRenderer(env)
    module_lower = template_data["module"].lower()

    for template_name, file_pattern, label in DTO_TEMPLATES:
        try:
            renderer.render_template(
                template_name,
                template_data,
                dto_dir / file_pattern.format(module=module_lower),
            )
        except TemplateException as e:
            logger.error(f"Failed to generate {label}: {e}")


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
    module_dirs = _create_module_directories(module_dir)

    files_to_generate = module_data.get("generate", [])
    template_data = {
        "module": module_name,
        "entity": module_data.get("entity", {}),
        "authProtected": module_data.get("authProtected", False),
        "relatedEntities": module_data.get("relatedEntities", []),
    }

    renderer = TemplateRenderer(env)

    for file_key in files_to_generate:
        if _generate_special_module_file(file_key, template_data, module_dirs, env):
            continue

        try:
            template_name = f"{file_key}.ts.j2"
            file_name = f"{module_name.lower()}.{file_key}.ts"
            renderer.render_template(template_name, template_data, module_dir / file_name)
        except TemplateException as e:
            logger.error(f"Failed to generate {file_key}: {e}")

    logger.end(f"{module_name} module generated")


def _create_module_directories(module_dir: Path) -> dict[str, Path]:
    """Create and return the standard directory layout for a module."""
    module_dir.mkdir(parents=True, exist_ok=True)
    module_dirs = {
        "module": module_dir,
        "dto": module_dir / "dto",
        "entities": module_dir / "entities",
    }
    for directory in module_dirs.values():
        directory.mkdir(parents=True, exist_ok=True)
    return module_dirs


def _generate_special_module_file(
    file_key: str,
    template_data: dict[str, Any],
    module_dirs: dict[str, Path],
    env: Environment,
) -> bool:
    """Generate files handled by dedicated helper functions."""
    generator = SPECIAL_FILE_GENERATORS.get(file_key)
    if generator is None:
        return False
    generator(template_data, module_dirs, env)
    return True
