"""Pytest fixtures for unit tests.

Provides shared fixtures and test utilities used across all unit tests.
"""

import tempfile
from pathlib import Path
from typing import Generator

import pytest
from jinja2 import Environment, FileSystemLoader


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files.

    Yields:
        Path to temporary directory that is automatically cleaned up after test
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_file(temp_dir: Path) -> Path:
    """Create a temporary file path.

    Args:
        temp_dir: Fixture providing temporary directory

    Returns:
        Path to a temporary file (file is not created)
    """
    return temp_dir / "test_file.txt"


@pytest.fixture
def sample_template_dir(temp_dir: Path) -> Path:
    """Create a directory with sample templates for testing.

    Args:
        temp_dir: Fixture providing temporary directory

    Returns:
        Path to directory containing sample templates
    """
    template_dir = temp_dir / "templates"
    template_dir.mkdir()

    # Create a simple test template
    (template_dir / "simple.j2").write_text("Hello {{ name }}!")

    # Create a template with more complex structure
    (template_dir / "complex.j2").write_text(
        "Module: {{ module }}\nFields: {% for field in fields %}{{ field }}{% endfor %}"
    )

    return template_dir


@pytest.fixture
def jinja_env(sample_template_dir: Path) -> Environment:
    """Create a Jinja2 environment for testing.

    Args:
        sample_template_dir: Fixture providing template directory

    Returns:
        Configured Jinja2 Environment
    """
    return Environment(
        loader=FileSystemLoader(str(sample_template_dir)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True
    )


@pytest.fixture
def sample_module_data() -> dict:
    """Provide sample module data for testing.

    Returns:
        Dictionary with sample module configuration
    """
    return {
        "module": "User",
        "entity": {
            "fields": [
                {"name": "id", "type": "number"},
                {"name": "email", "type": "string"},
                {"name": "name", "type": "string"}
            ]
        },
        "authProtected": True,
        "relatedEntities": []
    }


@pytest.fixture(autouse=True)
def reset_config():
    """Reset global configuration before each test.

    This ensures tests don't interfere with each other through shared state.
    """
    from src.shared.config import reset_config
    reset_config()
    yield
    reset_config()
