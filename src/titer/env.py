from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@lru_cache()
def load_project_env(dotenv_path: Optional[Path] = None) -> Optional[Path]:
    """Load environment variables from a .env file located in the project tree."""
    path = dotenv_path or _find_dotenv()
    if not path:
        return None
    loaded = load_dotenv(path)
    return path if loaded else None


def _find_dotenv() -> Optional[Path]:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".env"
        if candidate.exists():
            return candidate
    return None
