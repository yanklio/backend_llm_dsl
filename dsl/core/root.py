import sys
from pathlib import Path

# Add parent directory to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared.logs.logger import logger


def _prepare_template_data(root_config, modules_data):
    """Prepare template data for rendering"""
    return {
        "root": root_config,
        "modules": modules_data,
        "module_names": [m["name"] for m in modules_data],
    }


def _get_files_to_generate(root_config):
    """Get list of files to generate based on configuration"""
    files_to_generate = [
        ("root/app.module.ts.j2", "app.module.ts"),
        ("root/main.ts.j2", "main.ts"),
        ("root/app.controller.ts.j2", "app.controller.ts"),
        ("root/app.service.ts.j2", "app.service.ts"),
    ]

    if "database" in root_config:
        files_to_generate.append(("root/database.config.ts.j2", "database.config.ts"))

    return files_to_generate


def _generate_file(env, template_name, output_filename, template_data, src_dir):
    """Generate a single file from template"""
    try:
        template = env.get_template(template_name)
        output_code = template.render(template_data)
        output_path = src_dir / output_filename
        output_path.write_text(output_code)
        logger.success(f"Generated {output_path}")
    except Exception as e:
        logger.error(f"Could not generate {output_filename}: {e}")


def generate_root_module(root_config, modules_data, env, output_dir):
    """Generate root module files (app.module.ts, main.ts, etc.)"""
    src_dir = output_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    template_data = _prepare_template_data(root_config, modules_data)
    files_to_generate = _get_files_to_generate(root_config)

    for template_name, output_filename in files_to_generate:
        _generate_file(env, template_name, output_filename, template_data, src_dir)
