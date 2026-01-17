"""Module generation logic for the DSL engine."""

import sys
from pathlib import Path
from typing import Any, Dict

from jinja2 import Environment

# Add parent directory to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
from src.shared.logs.logger import logger


def handle_dto_file(
    template_data: Dict[str, Any], dto_dir: Path, env: Environment
) -> None:
    """Generate DTO files for the module.

    Args:
        template_data (Dict[str, Any]): Data passed to the template.
        dto_dir (Path): Directory where DTOs should be saved.
        env (Environment): Jinja2 environment.
    """
    try:
        template = env.get_template("dto/create-dto.ts.j2")
        output_code = template.render(template_data)
        file_name = f"create-{template_data['module'].lower()}.dto.ts"
        (dto_dir / file_name).write_text(output_code)
        logger.success(f"Generated {file_name}")
    except Exception as e:
        logger.error(f"Failed to generate create DTO: {e}")

    try:
        template = env.get_template("dto/update-dto.ts.j2")
        output_code = template.render(template_data)
        file_name = f"update-{template_data['module'].lower()}.dto.ts"
        (dto_dir / file_name).write_text(output_code)
        logger.success(f"Generated {file_name}")
    except Exception as e:
        logger.error(f"Failed to generate update DTO: {e}")


def handle_entity_file(
    template_data: Dict[str, Any], entities_dir: Path, env: Environment
) -> None:
    """Generate entity files for the module.

    Args:
        template_data (Dict[str, Any]): Data passed to the template.
        entities_dir (Path): Directory where entities should be saved.
        env (Environment): Jinja2 environment.
    """
    try:
        template = env.get_template("entity.ts.j2")
        output_code = template.render(template_data)
        file_name = f"{template_data['module'].lower()}.entity.ts"
        (entities_dir / file_name).write_text(output_code)
        logger.success(f"Generated {file_name}")
    except Exception as e:
        logger.error(f"Failed to generate entity file: {e}")


def generate_module(
    module_data: Dict[str, Any], env: Environment, base_output_dir: Path
) -> None:
    """Generate a single sub-module (entity module).

    Args:
        module_data (Dict[str, Any]): Configuration for the module.
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
            logger.success(f"Generated {file_name}")
        except Exception as e:
            logger.error(f"Failed to generate {file_key}: {e}")

    logger.end(f"{module_name} module generated")
