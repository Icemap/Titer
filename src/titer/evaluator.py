from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from fnmatch import fnmatch
from typing import Any, Dict, Iterable, List, Mapping, Sequence
from urllib.parse import urlparse

from .engines.base import EngineResponse
from .engines.factory import EngineFactory


@dataclass
class EvaluationResult:
    timestamp: datetime
    prompts: List[str]
    engines: List[str]
    keywords: List[str]
    domain_wildcards: List[str]
    runs: int
    keyword_counts: Dict[str, float]
    domain_counts: Dict[str, float]
    raw_responses: List[Mapping[str, Any]]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "prompts": self.prompts,
            "engines": self.engines,
            "keywords": self.keywords,
            "domain_wildcards": self.domain_wildcards,
            "runs": self.runs,
            "keyword_counts": self.keyword_counts,
            "domain_counts": self.domain_counts,
            "raw_responses": self.raw_responses,
        }

    def as_row(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "prompts": json.dumps(self.prompts),
            "engines": json.dumps(self.engines),
            "keywords": json.dumps(self.keywords),
            "domain_wildcards": json.dumps(self.domain_wildcards),
            "runs": self.runs,
            "keyword_counts": json.dumps(self.keyword_counts),
            "domain_counts": json.dumps(self.domain_counts),
            "raw_responses": json.dumps(self.raw_responses),
        }


def run_evaluation(
    prompts: Sequence[str],
    engine_names: Sequence[str],
    keywords: Sequence[str],
    domain_wildcards: Sequence[str],
    runs: int = 1,
) -> EvaluationResult:
    if runs < 1:
        raise ValueError("Runs must be at least 1.")
    if not prompts:
        raise ValueError("At least one prompt is required.")
    if not engine_names:
        raise ValueError("At least one engine is required.")

    factory = EngineFactory()
    engines = [factory.create(name) for name in engine_names]

    keyword_totals: Counter[str] = Counter({kw: 0 for kw in keywords})
    domain_totals: Counter[str] = Counter({pattern: 0 for pattern in domain_wildcards})
    raw_records: List[Mapping[str, Any]] = []

    for run_index in range(runs):
        for engine in engines:
            for prompt in prompts:
                response = engine.run(prompt)
                keyword_totals.update(_count_keywords(response.content, keywords))
                domain_totals.update(_count_domains(response.cites, domain_wildcards))
                raw_records.append(
                    {
                        "run": run_index,
                        "prompt": prompt,
                        "engine": engine.name,
                        "content": response.content,
                        "cites": response.cites,
                        "raw": response.raw,
                    }
                )

    keyword_avgs = {kw: keyword_totals.get(kw, 0) / runs for kw in keywords}
    domain_avgs = {pattern: domain_totals.get(pattern, 0) / runs for pattern in domain_wildcards}

    return EvaluationResult(
        timestamp=datetime.now(timezone.utc),
        prompts=list(prompts),
        engines=list(engine_names),
        keywords=list(keywords),
        domain_wildcards=list(domain_wildcards),
        runs=runs,
        keyword_counts=keyword_avgs,
        domain_counts=domain_avgs,
        raw_responses=raw_records,
    )


def _count_keywords(content: str, keywords: Sequence[str]) -> Mapping[str, int]:
    counts: Dict[str, int] = {}
    for kw in keywords:
        pattern = re.escape(kw)
        matches = re.findall(pattern, content, flags=re.IGNORECASE)
        counts[kw] = len(matches)
    return counts


def _count_domains(cites: Iterable[str], domain_wildcards: Sequence[str]) -> Mapping[str, int]:
    counts: Dict[str, int] = {}
    for pattern in domain_wildcards:
        counts[pattern] = 0
    for cite in cites:
        domain = _extract_domain(cite)
        if not domain:
            continue
        for pattern in domain_wildcards:
            if fnmatch(domain, pattern.lower()):
                counts[pattern] += 1
    return counts


def _extract_domain(url: str) -> str | None:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = parsed.netloc.split(":")[0].lower()
    return host or None
