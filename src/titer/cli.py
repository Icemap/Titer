from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List, Optional

import click

from .evaluator import EvaluationResult, run_evaluation
from .task_runner import (
    load_tasks_from_csv,
    load_tasks_from_sheet,
    run_tasks,
    write_results_to_csv,
    write_results_to_sheet,
)


@click.group()
def cli() -> None:
    """Run titer evaluations."""


@cli.command()
@click.option("--prompt", "prompts", multiple=True, required=True, help="Prompt to test. Repeat for multiple prompts.")
@click.option("--engine", "engines", multiple=True, required=True, help="Engine name in '<provider>/<model>' format.")
@click.option("--keyword", "keywords", multiple=True, help="Keyword to count in responses. Repeat for more.")
@click.option(
    "--domain",
    "domain_wildcards",
    multiple=True,
    help="Domain wildcard to match against citations (e.g., '*.example.com'). Repeat for more.",
)
@click.option("--runs", default=1, type=click.IntRange(min=1), show_default=True, help="Number of iterations to average.")
@click.option(
    "--output-csv",
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path),
    help="Optional path to append the result row as CSV.",
)
def run(
    prompts: List[str],
    engines: List[str],
    keywords: List[str],
    domain_wildcards: List[str],
    runs: int,
    output_csv: Optional[Path],
) -> None:
    """Execute a single evaluation."""
    result = run_evaluation(
        prompts=prompts,
        engine_names=engines,
        keywords=keywords,
        domain_wildcards=domain_wildcards,
        runs=runs,
    )
    if output_csv:
        _append_row(output_csv, result)
    click.echo(json.dumps(result.as_dict(), indent=2))


@cli.command(name="batch")
@click.option(
    "--task-file",
    required=False,
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path),
    help="CSV file with task parameters.",
)
@click.option(
    "--task-sheet",
    required=False,
    help="Google Sheet URL or ID containing task parameters.",
)
@click.option(
    "--task-sheet-worksheet",
    required=False,
    help="Worksheet name inside the task sheet (defaults to first).",
)
@click.option(
    "--output-file",
    required=False,
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path),
    help="CSV file to write aggregated results.",
)
@click.option(
    "--output-sheet",
    required=False,
    help="Google Sheet URL or ID to write aggregated results.",
)
@click.option(
    "--output-sheet-worksheet",
    required=False,
    help="Worksheet name for output sheet (defaults to first).",
)
@click.option(
    "--service-account",
    required=False,
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path),
    help="Path to service_account.json for Google Sheets.",
)
@click.option(
    "--share-output-sheet/--no-share-output-sheet",
    default=False,
    show_default=True,
    help="Whether to make the output sheet publicly readable.",
)
def batch(
    task_file: Path | None,
    task_sheet: str | None,
    task_sheet_worksheet: str | None,
    output_file: Path | None,
    output_sheet: str | None,
    output_sheet_worksheet: str | None,
    service_account: Path | None,
    share_output_sheet: bool,
) -> None:
    """Run evaluations for each row in a task CSV or Google Sheet."""
    if not task_file and not task_sheet:
        raise click.UsageError("One of --task-file or --task-sheet is required.")
    if task_file and task_sheet:
        raise click.UsageError("Provide only one of --task-file or --task-sheet.")
    if not output_file and not output_sheet:
        raise click.UsageError("One of --output-file or --output-sheet is required.")

    if task_sheet:
        tasks = load_tasks_from_sheet(task_sheet, worksheet=task_sheet_worksheet, service_account_path=service_account)
    else:
        tasks = load_tasks_from_csv(task_file)  # type: ignore[arg-type]

    results = run_tasks(tasks)
    rows = [result.as_row() for result in results]

    if output_file:
        write_results_to_csv(output_file, rows)
    sheet_url = None
    if output_sheet is not None:
        sheet_url = write_results_to_sheet(
            output_sheet,
            rows,
            worksheet=output_sheet_worksheet,
            service_account_path=service_account,
            share_public=share_output_sheet,
            place_first=True,
        )

    payload = [result.as_dict() for result in results]
    if sheet_url:
        payload.append({"output_sheet_url": sheet_url})
    click.echo(json.dumps(payload, indent=2))


def _append_row(path: Path, result: EvaluationResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = result.as_row()
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=row.keys())
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def main() -> None:
    cli(prog_name="titer")


if __name__ == "__main__":
    main()
