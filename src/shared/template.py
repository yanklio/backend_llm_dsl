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
from src.shared.logger import logger

TEMPLATE_ERROR_CODES = {
    "not_found": "TEMPLATE002",
    "load": "TEMPLATE003",
    "render": "TEMPLATE004",
    "write": "TEMPLATE005",
}


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
        output_path: Path,
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
        template = self._load_template(template_name)
        output_code = self._render_template_content(template_name, template, data)
        self._write_rendered_output(template_name, output_path, output_code)

    def render_templates(
        self,
        templates: list[tuple[str, str]],
        data: dict[str, Any],
        output_dir: Path,
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
        output_dir.mkdir(parents=True, exist_ok=True)

        for template_name, output_filename in templates:
            output_path = output_dir / output_filename
            self.render_template(template_name, data, output_path)

    def _load_template(self, template_name: str) -> Template:
        """Load a Jinja template with structured error handling."""
        try:
            return self.env.get_template(template_name)
        except TemplateNotFound as exc:
            raise TemplateNotFoundException(
                f"Template not found: {template_name}",
                code=TEMPLATE_ERROR_CODES["not_found"],
                context={
                    "template_name": template_name,
                    "search_path": self._template_search_path(),
                },
            ) from exc
        except Exception as exc:
            raise self._render_error(
                f"Failed to load template {template_name}: {exc}",
                TEMPLATE_ERROR_CODES["load"],
                template_name=template_name,
                error=str(exc),
            ) from exc

    def _render_template_content(
        self,
        template_name: str,
        template: Template,
        data: dict[str, Any],
    ) -> str:
        """Render one template using the provided data."""
        try:
            return template.render(data)
        except Exception as exc:
            raise self._render_error(
                f"Failed to render template {template_name}: {exc}",
                TEMPLATE_ERROR_CODES["render"],
                template_name=template_name,
                data_keys=list(data.keys()),
                error=str(exc),
            ) from exc

    def _write_rendered_output(
        self,
        template_name: str,
        output_path: Path,
        output_code: str,
    ) -> None:
        """Write rendered output to disk and log success."""
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output_code)
            logger.success(f"Generated {output_path.name}")
        except Exception as exc:
            raise self._render_error(
                f"Failed to write rendered template to {output_path}: {exc}",
                TEMPLATE_ERROR_CODES["write"],
                template_name=template_name,
                output_path=str(output_path),
                error=str(exc),
            ) from exc

    def _template_search_path(self) -> str:
        """Return the configured template search path for diagnostics."""
        if hasattr(self.env.loader, "searchpath"):
            return str(self.env.loader.searchpath)
        return "unknown"

    def _render_error(self, message: str, code: str, **context: Any) -> TemplateRenderException:
        """Create a consistent template rendering exception."""
        return TemplateRenderException(message, code=code, context=context)


def render_single_template(
    env: Environment,
    template_name: str,
    data: dict[str, Any],
    output_path: Path,
) -> None:
    """Render a single template without instantiating `TemplateRenderer` manually."""
    renderer = TemplateRenderer(env)
    renderer.render_template(template_name, data, output_path)
