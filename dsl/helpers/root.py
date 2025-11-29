from .logger import Logger


def generate_root_module(root_config, modules_data, env, output_dir):
    """Generate root module files (app.module.ts, main.ts, etc.)"""
    Logger.start("Generating root module files")

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
        Logger.success(f"Generated {app_module_path}")
    except Exception as e:
        Logger.error(f"Could not generate app.module.ts: {e}")

    # Generate main.ts
    try:
        template = env.get_template("root/main.ts.j2")
        output_code = template.render(template_data)
        main_path = src_dir / "main.ts"
        main_path.write_text(output_code)
        Logger.success(f"Generated {main_path}")
    except Exception as e:
        Logger.error(f"Could not generate main.ts: {e}")

    # Generate database config if database is specified
    if "database" in root_config:
        try:
            template = env.get_template("root/database.config.ts.j2")
            output_code = template.render(template_data)
            db_config_path = src_dir / "database.config.ts"
            db_config_path.write_text(output_code)
            Logger.success(f"Generated {db_config_path}")
        except Exception as e:
            Logger.error(f"Could not generate database.config.ts: {e}")

    # Generate app.controller.ts and app.service.ts
    try:
        template = env.get_template("root/app.controller.ts.j2")
        output_code = template.render(template_data)
        app_controller_path = src_dir / "app.controller.ts"
        app_controller_path.write_text(output_code)
        Logger.success(f"Generated {app_controller_path}")
    except Exception as e:
        Logger.error(f"Could not generate app.controller.ts: {e}")

    try:
        template = env.get_template("root/app.service.ts.j2")
        output_code = template.render(template_data)
        app_service_path = src_dir / "app.service.ts"
        app_service_path.write_text(output_code)
        Logger.success(f"Generated {app_service_path}")
    except Exception as e:
        Logger.error(f"Could not generate app.service.ts: {e}")

    Logger.end("Generated app.controller.ts and app.service.ts")
