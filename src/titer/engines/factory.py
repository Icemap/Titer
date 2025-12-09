from __future__ import annotations

from typing import Callable, Dict

from .base import Engine
from .openai_engine import OpenAIEngine
from .gemini_engine import GeminiEngine


class EngineFactory:
    """Factory to resolve engine names to instances."""

    def __init__(self) -> None:
        self._registry: Dict[str, Callable[[str], Engine]] = {
            "openai": self._build_openai,
            "gemini": self._build_gemini,
        }

    def create(self, engine_name: str) -> Engine:
        provider, model = self._split_engine_name(engine_name)
        builder = self._registry.get(provider)
        if not builder:
            raise ValueError(f"Unsupported provider '{provider}'.")
        return builder(model)

    def _split_engine_name(self, engine_name: str) -> tuple[str, str]:
        if "/" not in engine_name:
            raise ValueError("Engine name must follow '<provider>/<model>' format.")
        provider, model = engine_name.split("/", 1)
        if not provider or not model:
            raise ValueError("Engine name must include both provider and model.")
        return provider, model

    def _build_openai(self, model: str) -> Engine:
        return OpenAIEngine(model=model)

    def _build_gemini(self, model: str) -> Engine:
        return GeminiEngine(model=model)
