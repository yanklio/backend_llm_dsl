"""Template rendering helper for Jinja2 templates.

Provides reusable functions for rendering templates with consistent error handling,
eliminating code duplication throughout the codebase.
"""

from pathlib import Path
from typing import Any

from jinja2 import Environment, Template, TemplateNotFound

from src.shared.exceptions import (
    TemplateNotFoundException,
    TemplateRenderException,
)
from src.shared.logs.logger import logger


class TemplateRenderer:
    """Helper class for rendering Jinja2 templates with error handling.

    Provides methods for rendering single or multiple templates with automatic
    directory creation, error handling, and logging.

    Attributes:
        env: Jinja2 Environment instance
    """

    def __init__(self, env: Environment) -> None:
        """Initialize the template renderer.

        Args:
            env: Jinja2 Environment instance configured with template loader
        """
        self.env = env

    def render_template(
        self,
        template_name: str,
        data: dict[str, Any],
        output_path: Path
    ) -> None:
        """Render a single template to a file.

        Args:
            template_name: Name of the template file (e.g., "entity.ts.j2")
            data: Dictionary of data to pass to the template
            output_path: Path where the rendered output should be written

        Raises:
            TemplateNotFoundException: If the template file is not found
            TemplateRenderException: If template rendering fails
        """
        try:
            # Get the template
            template: Template = self.env.get_template(template_name)
        except TemplateNotFound as e:
            search_path = "unknown"
            if hasattr(self.env.loader, "searchpath"):
                search_path = str(self.env.loader.searchpath)
            raise TemplateNotFoundException(
                f"Template not found: {template_name}",
                code="TEMPLATE002",
                context={"template_name": template_name, "search_path": search_path},
            ) from e
        except Exception as e:
            raise TemplateRenderException(
                f"Failed to load template {template_name}: {e}",
                code="TEMPLATE003",
                context={"template_name": template_name, "error": str(e)}
            ) from e

        try:
            # Render the template
            output_code = template.render(data)
        except Exception as e:
            raise TemplateRenderException(
                f"Failed to render template {template_name}: {e}",
                code="TEMPLATE004",
                context={
                    "template_name": template_name,
                    "data_keys": list(data.keys()),
                    "error": str(e)
                }
            ) from e

        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the rendered content
            output_path.write_text(output_code)

            logger.success(f"Generated {output_path.name}")
        except Exception as e:
            raise TemplateRenderException(
                f"Failed to write rendered template to {output_path}: {e}",
                code="TEMPLATE005",
                context={
                    "template_name": template_name,
                    "output_path": str(output_path),
                    "error": str(e)
                }
            ) from e

    def render_templates(
        self,
        templates: list[tuple[str, str]],
        data: dict[str, Any],
        output_dir: Path
    ) -> None:
        """Render multiple templates to files.

        Args:
            templates: List of (template_name, output_filename) tuples
            data: Dictionary of data to pass to all templates
            output_dir: Directory where rendered files should be written

        Raises:
            TemplateException: If any template rendering fails

        Example:
            >>> renderer = TemplateRenderer(env)
            >>> templates = [
            ...     ("create-dto.ts.j2", "create-user.dto.ts"),
            ...     ("update-dto.ts.j2", "update-user.dto.ts")
            ... ]
            >>> renderer.render_templates(templates, data, Path("./dto"))
        """
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        for template_name, output_filename in templates:
            output_path = output_dir / output_filename
            self.render_template(template_name, data, output_path)


def render_single_template(
    env: Environment,
    template_name: str,
    data: dict[str, Any],
    output_path: Path
) -> None:
    """Convenience function to render a single template.

    This is a standalone function that creates a TemplateRenderer internally.
    Useful for one-off template rendering.

    Args:
        env: Jinja2 Environment instance
        template_name: Name of the template file
        data: Dictionary of data to pass to the template
        output_path: Path where the rendered output should be written

    Raises:
        TemplateNotFoundException: If the template file is not found
        TemplateRenderException: If template rendering fails

    Example:
        >>> from jinja2 import Environment, FileSystemLoader
        >>> env = Environment(loader=FileSystemLoader("templates"))
        >>> render_single_template(
        ...     env,
        ...     "entity.ts.j2",
        ...     {"module": "User", "fields": [...]},
        ...     Path("./entities/user.entity.ts")
        ... )
    """
    renderer = TemplateRenderer(env)
    renderer.render_template(template_name, data, output_path)
