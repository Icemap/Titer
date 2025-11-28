from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List, Optional

import click

from .evaluator import EvaluationResult, run_evaluation
from .task_runner import run_task_file


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
    required=True,
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path),
    help="CSV file with task parameters.",
)
@click.option(
    "--output-file",
    required=True,
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path),
    help="CSV file to write aggregated results.",
)
def batch(task_file: Path, output_file: Path) -> None:
    """Run evaluations for each row in a task CSV."""
    results = run_task_file(task_file, output_file)
    payload = [result.as_dict() for result in results]
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
