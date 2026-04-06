"""Tests for template rendering helper."""

from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

from src.shared.exceptions import (
    TemplateNotFoundException,
    TemplateRenderException,
)
from src.shared.template_helper import (
    TemplateRenderer,
    render_single_template,
)


class TestTemplateRenderer:
    """Tests for TemplateRenderer class."""

    def test_render_simple_template(self, jinja_env, temp_dir):
        """Test rendering a simple template."""
        renderer = TemplateRenderer(jinja_env)
        output_path = temp_dir / "output.txt"

        renderer.render_template(
            "simple.j2",
            {"name": "World"},
            output_path
        )

        assert output_path.exists()
        assert output_path.read_text() == "Hello World!"

    def test_render_complex_template(self, jinja_env, temp_dir):
        """Test rendering a template with loops."""
        renderer = TemplateRenderer(jinja_env)
        output_path = temp_dir / "complex.txt"

        renderer.render_template(
            "complex.j2",
            {"module": "User", "fields": ["id", "name", "email"]},
            output_path
        )

        assert output_path.exists()
        content = output_path.read_text()
        assert "Module: User" in content
        assert "idnameemail" in content

    def test_render_creates_parent_directories(self, jinja_env, temp_dir):
        """Test that render_template creates parent directories."""
        renderer = TemplateRenderer(jinja_env)
        output_path = temp_dir / "nested" / "dir" / "output.txt"

        renderer.render_template(
            "simple.j2",
            {"name": "Test"},
            output_path
        )

        assert output_path.exists()
        assert output_path.parent.exists()

    def test_template_not_found_raises_exception(self, jinja_env, temp_dir):
        """Test that missing template raises TemplateNotFoundException."""
        renderer = TemplateRenderer(jinja_env)
        output_path = temp_dir / "output.txt"

        with pytest.raises(TemplateNotFoundException) as exc_info:
            renderer.render_template(
                "nonexistent.j2",
                {"name": "Test"},
                output_path
            )

        assert "not found" in str(exc_info.value).lower()
        assert exc_info.value.code == "TEMPLATE002"
        assert "nonexistent.j2" in exc_info.value.context["template_name"]

    def test_invalid_template_data_raises_exception(self, sample_template_dir, temp_dir):
        """Test that invalid template data raises TemplateRenderException."""
        # Create a template that requires a variable
        (sample_template_dir / "requires_var.j2").write_text("Value: {{ required_var }}")

        # Use StrictUndefined to make undefined variables raise errors
        from jinja2 import StrictUndefined
        env = Environment(
            loader=FileSystemLoader(str(sample_template_dir)),
            undefined=StrictUndefined
        )
        renderer = TemplateRenderer(env)
        output_path = temp_dir / "output.txt"

        with pytest.raises(TemplateRenderException) as exc_info:
            renderer.render_template(
                "requires_var.j2",
                {},  # Missing required_var
                output_path
            )

        assert exc_info.value.code == "TEMPLATE004"

    def test_render_multiple_templates(self, jinja_env, temp_dir):
        """Test rendering multiple templates at once."""
        renderer = TemplateRenderer(jinja_env)
        output_dir = temp_dir / "output"

        templates = [
            ("simple.j2", "first.txt"),
            ("simple.j2", "second.txt"),
        ]

        renderer.render_templates(
            templates,
            {"name": "Test"},
            output_dir
        )

        assert (output_dir / "first.txt").exists()
        assert (output_dir / "second.txt").exists()
        assert (output_dir / "first.txt").read_text() == "Hello Test!"
        assert (output_dir / "second.txt").read_text() == "Hello Test!"

    def test_render_templates_creates_output_dir(self, jinja_env, temp_dir):
        """Test that render_templates creates the output directory."""
        renderer = TemplateRenderer(jinja_env)
        output_dir = temp_dir / "new_dir"

        templates = [("simple.j2", "output.txt")]

        renderer.render_templates(
            templates,
            {"name": "Test"},
            output_dir
        )

        assert output_dir.exists()
        assert (output_dir / "output.txt").exists()

    def test_render_templates_stops_on_error(self, jinja_env, temp_dir):
        """Test that render_templates stops when a template fails."""
        renderer = TemplateRenderer(jinja_env)
        output_dir = temp_dir / "output"

        templates = [
            ("simple.j2", "first.txt"),
            ("nonexistent.j2", "second.txt"),  # This will fail
            ("simple.j2", "third.txt"),
        ]

        with pytest.raises(TemplateNotFoundException):
            renderer.render_templates(
                templates,
                {"name": "Test"},
                output_dir
            )

        # First file should exist
        assert (output_dir / "first.txt").exists()
        # Third file should not exist (stopped on second)
        assert not (output_dir / "third.txt").exists()


class TestRenderSingleTemplate:
    """Tests for render_single_template convenience function."""

    def test_render_single_template_function(self, jinja_env, temp_dir):
        """Test the standalone render_single_template function."""
        output_path = temp_dir / "output.txt"

        render_single_template(
            jinja_env,
            "simple.j2",
            {"name": "Function"},
            output_path
        )

        assert output_path.exists()
        assert output_path.read_text() == "Hello Function!"

    def test_render_single_template_with_error(self, jinja_env, temp_dir):
        """Test that render_single_template propagates exceptions."""
        output_path = temp_dir / "output.txt"

        with pytest.raises(TemplateNotFoundException):
            render_single_template(
                jinja_env,
                "missing.j2",
                {"name": "Test"},
                output_path
            )
