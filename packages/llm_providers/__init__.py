"""LLM generation entry points and provider abstractions."""

import warnings

# LangChain currently emits this dependency warning on Python 3.14 during import.
# It is not actionable in experiment code and pollutes benchmark console/log output.
warnings.filterwarnings(
    "ignore",
    message=r"Core Pydantic V1 functionality isn't compatible with Python 3\.14 or greater\.",
    category=UserWarning,
)

from .core.client import LLMClient  # noqa: E402
from .providers import GenerationResult  # noqa: E402

__all__ = ["LLMClient", "GenerationResult"]
