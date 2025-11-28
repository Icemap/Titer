from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from .evaluator import EvaluationResult, run_evaluation


def run_task_file(input_path: Path, output_path: Path) -> List[EvaluationResult]:
    tasks = _load_tasks(input_path)
    results: List[EvaluationResult] = []
    for task in tasks:
        result = run_evaluation(
            prompts=task["prompts"],
            engine_names=task["engines"],
            keywords=task["keywords"],
            domain_wildcards=task["domain_wildcards"],
            runs=task["runs"],
        )
        results.append(result)

    if results:
        _write_results(output_path, [result.as_row() for result in results])
    return results


def _load_tasks(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        tasks: List[Dict[str, Any]] = []
        for index, row in enumerate(reader):
            try:
                tasks.append(
                    {
                        "prompts": _parse_list(row.get("prompts")),
                        "engines": _parse_list(row.get("engines")),
                        "keywords": _parse_list(row.get("keywords")),
                        "domain_wildcards": _parse_list(row.get("domain_wildcards")),
                        "runs": int(row.get("runs", "1") or 1),
                    }
                )
            except Exception as exc:
                raise ValueError(f"Failed to load task row {index}: {exc}") from exc
    return tasks


def _write_results(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _parse_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except json.JSONDecodeError:
        pass
    return [part.strip() for part in text.split("|") if part.strip()]
