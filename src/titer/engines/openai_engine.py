from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableSequence, Sequence
from urllib.parse import urlparse

from openai import OpenAI
from openai._exceptions import BadRequestError, OpenAIError

from .base import Engine, EngineResponse


class OpenAIEngine(Engine):
    """OpenAI engine implementation for GPT-4.1 with web search tool enabled."""

    def __init__(
        self,
        model: str = "gpt-4.1",
        client: OpenAI | None = None,
    ) -> None:
        self.model = model
        self.client = client or OpenAI()
        self.name = f"openai/{model}"

    def run(self, prompt: str) -> EngineResponse:
        try:
            response = self.client.responses.create(
                model=self.model,
                input=prompt,
                tools=[{"type": "web_search"}],
            )
        except OpenAIError as exc:
            if isinstance(exc, BadRequestError) and "web_search" in str(exc).lower():
                raise RuntimeError(
                    "OpenAI request failed: web_search is not enabled for this account or plan. "
                    "Enable the capability on your OpenAI plan to continue."
                ) from exc
            raise RuntimeError(f"OpenAI request failed: {exc}") from exc

        content = _extract_content(response)
        cites = _extract_citations(response)
        raw_payload = _serialize_response(response)
        return EngineResponse(content=content, cites=cites, raw=raw_payload)


def _extract_content(response: Any) -> str:
    if hasattr(response, "output_text") and getattr(response, "output_text"):
        return str(getattr(response, "output_text"))

    choices = getattr(response, "choices", None)
    if choices:
        message = getattr(choices[0], "message", None)
        if message and hasattr(message, "content"):
            return str(message.content)
        if message and hasattr(message, "text"):
            return str(message.text)

    if hasattr(response, "output") and response.output:
        first_output = response.output[0]
        content_items = getattr(first_output, "content", None)
        if content_items:
            chunks: MutableSequence[Any] = []
            for item in content_items:
                if hasattr(item, "type") and getattr(item, "type") == "output_text":
                    text_block = getattr(item, "text", None)
                    if text_block and hasattr(text_block, "value"):
                        chunks.append(str(text_block.value))
            if chunks:
                return "\n".join(chunks)

    return str(response)


def _extract_citations(response: Any) -> List[str]:
    cites: List[str] = []

    if hasattr(response, "output") and response.output:
        for output_item in response.output:
            content_items = getattr(output_item, "content", None)
            if not content_items:
                continue
            for item in content_items:
                annotations = getattr(item, "annotations", []) or []
                for annotation in annotations:
                    cite = _pull_citation(annotation)
                    if cite:
                        cites.append(cite)

    raw = _serialize_response(response)
    cites.extend(_find_urls_in_mapping(raw))
    return _dedupe(cites)


def _pull_citation(annotation: Any) -> str | None:
    citation = getattr(annotation, "citation", None)
    if citation and hasattr(citation, "uri") and citation.uri:
        return str(citation.uri)
    if isinstance(annotation, Mapping):
        cite = annotation.get("citation")
        if isinstance(cite, Mapping):
            uri = cite.get("uri")
            if uri:
                return str(uri)
    return None


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
