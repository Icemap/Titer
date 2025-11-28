from __future__ import annotations

from .env import load_project_env

__all__ = ["__version__", "load_project_env"]

__version__ = "0.1.0"

# Load .env if present to pick up credentials like OPENAI_API_KEY.
load_project_env()
