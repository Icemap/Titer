from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence
import gspread

from .env import load_project_env
from .evaluator import EvaluationResult, run_evaluation


def run_tasks(tasks: Sequence[Dict[str, Any]]) -> List[EvaluationResult]:
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
    return results


def run_task_file(input_path: Path, output_path: Path) -> List[EvaluationResult]:
    tasks = load_tasks_from_csv(input_path)
    results = run_tasks(tasks)
    if results:
        write_results_to_csv(output_path, [result.as_row() for result in results])
    return results


def load_tasks_from_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    return _parse_task_rows(rows)


def load_tasks_from_sheet(
    sheet_ref: str,
    worksheet: str | None = None,
    service_account_path: Path | None = None,
) -> List[Dict[str, Any]]:
    client = _get_gspread_client(service_account_path)
    sheet = _open_sheet(client, sheet_ref)
    ws = sheet.worksheet(worksheet) if worksheet else sheet.sheet1
    records = ws.get_all_records(default_blank="")
    return _parse_task_rows(records)


def write_results_to_csv(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_results_to_sheet(
    sheet_ref: str | None,
    rows: Sequence[Dict[str, Any]],
    worksheet: str | None = None,
    service_account_path: Path | None = None,
    create_if_missing: bool = True,
    share_public: bool = False,
    place_first: bool = False,
) -> str:
    if not rows:
        raise ValueError("No rows to write to Google Sheets.")

    client = _get_gspread_client(service_account_path)
    if sheet_ref:
        sheet = _open_sheet(client, sheet_ref, create_if_missing=create_if_missing)
    else:
        title = f"Titer Results {datetime.utcnow().isoformat()}"
        sheet = client.create(title=title)
    if share_public:
        try:
            sheet.share(None, perm_type="anyone", role="reader")
        except Exception:
            pass  # If sharing fails, still proceed.

    ws = _get_or_create_worksheet(sheet, worksheet)
    if place_first:
        _move_worksheet_to_front(sheet, ws)
    fieldnames = list(rows[0].keys())
    data_rows = _prepare_sheet_rows(rows, fieldnames)
    data = [fieldnames] + data_rows
    ws.clear()
    ws.update(values=data)
    return sheet.url


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
    # Support '|' or ',' separated lists for user-friendly sheets.
    delimiter = "|" if "|" in text else ","
    return [part.strip() for part in text.split(delimiter) if part.strip()]


def _parse_prompt(value: Any) -> List[str]:
    """Parse a single prompt value; do NOT split on commas/pipes to keep prompt text intact."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    text = str(value)
    if not text.strip():
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except json.JSONDecodeError:
        pass
    return [text]


def _parse_task_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    tasks: List[Dict[str, Any]] = []
    for index, row in enumerate(rows):
        try:
            prompts = _parse_prompt(row.get("prompt"))
            if not prompts:
                # Backwards compatibility: fall back to "prompts" column.
                prompts = _parse_prompt(row.get("prompts"))
            tasks.append(
                {
                    "prompts": prompts,
                    "engines": _parse_list(row.get("engines")),
                    "keywords": _parse_list(row.get("keywords")),
                    "domain_wildcards": _parse_list(row.get("domain_wildcards")),
                    "runs": int(row.get("runs", "1") or 1),
                }
            )
        except Exception as exc:
            raise ValueError(f"Failed to load task row {index}: {exc}") from exc
    return tasks


def _get_gspread_client(service_account_path: Path | None = None) -> gspread.Client:
    # Ensure .env is loaded for other creds that might be needed.
    load_project_env()
    path = service_account_path or Path("service_account.json")
    if not path.exists():
        raise FileNotFoundError(
            f"service account file not found at {path}. Provide the path or place it in the project root."
        )
    return gspread.service_account(filename=str(path))


def _open_sheet(client: gspread.Client, sheet_ref: str, create_if_missing: bool = False) -> gspread.Spreadsheet:
    try:
        if "http" in sheet_ref:
            return client.open_by_url(sheet_ref)
        return client.open_by_key(sheet_ref)
    except Exception as exc:
        if not create_if_missing:
            raise
        sheet = client.create(sheet_ref or "Titer Results")
        return sheet


def _get_or_create_worksheet(sheet: gspread.Spreadsheet, name: str | None) -> gspread.Worksheet:
    if not name:
        return sheet.sheet1
    try:
        return sheet.worksheet(name)
    except Exception:
        return sheet.add_worksheet(title=name, rows=1000, cols=26)


def _move_worksheet_to_front(sheet: gspread.Spreadsheet, ws: gspread.Worksheet) -> None:
    """Place the worksheet as the first tab."""
    try:
        others = [w for w in sheet.worksheets() if w.id != ws.id]
        sheet.reorder_worksheets([ws] + others)
    except Exception:
        pass


def _prepare_sheet_rows(rows: Sequence[Dict[str, Any]], fieldnames: Sequence[str], max_len: int = 45000) -> List[List[str]]:
    """Ensure no cell exceeds Sheets limits by truncating long content."""
    prepared: List[List[str]] = []
    for row in rows:
        prepared_row: List[str] = []
        for field in fieldnames:
            value = row.get(field, "")
            text = "" if value is None else str(value)
            if len(text) > max_len:
                text = text[: max_len - 3] + "..."
            prepared_row.append(text)
        prepared.append(prepared_row)
    return prepared
