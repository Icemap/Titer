from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Mapping, Sequence


@dataclass
class EngineResponse:
    """Normalized LLM response."""

    content: str
    cites: List[str]
    raw: Mapping[str, Any]


class Engine(ABC):
    """Abstract base class for LLM engines."""

    name: str

    @abstractmethod
    def run(self, prompt: str) -> EngineResponse:
        """Execute the prompt and return a normalized response."""
        raise NotImplementedError


def count_engines(engine_names: Sequence[str]) -> Mapping[str, int]:
    """Utility for validation in the CLI."""
    summary: dict[str, int] = {}
    for name in engine_names:
        summary[name] = summary.get(name, 0) + 1
    return summary
