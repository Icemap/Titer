from __future__ import annotations

import time
from typing import Any, List, Mapping, MutableSequence, Sequence
from urllib.parse import urlparse

from google import genai
from google.genai import types

from .base import Engine, EngineResponse


class GeminiEngine(Engine):
    """Gemini engine implementation with Google Search tool enabled."""

    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        client: genai.Client | None = None,
        max_retries: int = 3,
        backoff_seconds: float = 2.0,
    ) -> None:
        self.model = model
        self.client = client or genai.Client()
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.name = f"gemini/{model}"

    def run(self, prompt: str) -> EngineResponse:
        # Retry for rate limits / transient errors because free plan is bursty.
        last_err: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                tool = types.Tool(google_search=types.GoogleSearch())
                config = types.GenerateContentConfig(tools=[tool])
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )
                content = _extract_content(response)
                cites = _extract_citations(response)
                raw_payload = _serialize_response(response)
                return EngineResponse(content=content, cites=cites, raw=raw_payload)
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                if attempt + 1 >= self.max_retries or not _is_retryable(exc):
                    raise RuntimeError(f"Gemini request failed: {exc}") from exc
                sleep_for = self.backoff_seconds * (2**attempt)
                time.sleep(sleep_for)
        raise RuntimeError(f"Gemini request failed: {last_err}")  # defensive


def _is_retryable(exc: Exception) -> bool:
    text = str(exc).lower()
    retry_tokens = ("rate", "quota", "429", "resource exhausted", "exceeded")
    return any(token in text for token in retry_tokens)


def _extract_content(response: Any) -> str:
    if hasattr(response, "text") and getattr(response, "text"):
        return str(getattr(response, "text"))

    if hasattr(response, "candidates") and response.candidates:
        candidate = response.candidates[0]
        parts = getattr(candidate, "content", None)
        if parts and hasattr(parts, "parts"):
            chunks: MutableSequence[str] = []
            for part in parts.parts:
                text = getattr(part, "text", None)
                if text:
                    chunks.append(str(text))
            if chunks:
                return "\n".join(chunks)
    return str(response)


def _extract_citations(response: Any) -> List[str]:
    cites: List[str] = []

    # Try explicit citation objects if present.
    if hasattr(response, "candidates"):
        for candidate in response.candidates:
            grounded = getattr(candidate, "grounding_metadata", None)
            if grounded and hasattr(grounded, "supporting_contents"):
                for item in grounded.supporting_contents or []:
                    if hasattr(item, "uri") and item.uri:
                        cites.append(str(item.uri))

    # Fallback: search entire payload for URLs.
    raw = _serialize_response(response)
    cites.extend(_find_urls_in_mapping(raw))
    return _dedupe(cites)


def _find_urls_in_mapping(raw: Mapping[str, Any]) -> List[str]:
    urls: List[str] = []

    def _walk(value: Any) -> None:
        if isinstance(value, str):
            parsed = urlparse(value)
            if parsed.scheme and parsed.netloc:
                urls.append(value)
        elif isinstance(value, Mapping):
            for nested in value.values():
                _walk(nested)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for item in value:
                _walk(item)

    _walk(raw)
    return urls


def _dedupe(items: Sequence[str]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _serialize_response(response: Any) -> Mapping[str, Any]:
    if hasattr(response, "model_dump"):
        dumped = response.model_dump()
        if isinstance(dumped, Mapping):
            return dumped
    if hasattr(response, "model_dump_json"):
        import json

        try:
            data = json.loads(response.model_dump_json())
            if isinstance(data, Mapping):
                return data
        except Exception:
            pass
    if isinstance(response, Mapping):
        return response
    return {"repr": repr(response)}
