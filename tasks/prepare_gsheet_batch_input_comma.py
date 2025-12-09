from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import gspread

from titer.env import load_project_env


def populate_sheet(
    sheet_url: str,
    worksheet: str,
    service_account: Path,
    share_public: bool = False,
    include_gemini: bool = False,
) -> str:
    """Populate a Google Sheet worksheet with comma-separated batch tasks."""
    load_project_env()
    client = gspread.service_account(filename=str(service_account))
    sheet = client.open_by_url(sheet_url)
    try:
        ws = sheet.worksheet(worksheet)
    except Exception:
        ws = sheet.add_worksheet(title=worksheet, rows=200, cols=30)

    headers = ["prompt", "engines", "keywords", "domain_wildcards", "runs"]
    rows: List[List[str]] = [
        [
            "What database should I use for AI apps?",
            "openai/gpt-4o",
            "postgres,vector",
            "*.postgresql.org,*.wikipedia.org",
            "1",
        ],
    ]

    if include_gemini:
        rows.append(
            [
                "Summarize the benefits of vector databases in 3 bullets.",
                "gemini/gemini-2.0-flash",
                "vector database,performance",
                "*.milvus.io,*.wikipedia.org",
                "1",
            ]
        )

    ws.clear()
    ws.update([headers] + rows)

    if share_public:
        try:
            sheet.share(None, perm_type="anyone", role="reader")
        except Exception:
            pass  # If sharing fails, continue.

    return sheet.url


def main() -> None:
    parser = argparse.ArgumentParser(description="Populate Google Sheet with comma-separated Titer batch examples.")
    parser.add_argument("--sheet-url", required=True, help="Google Sheet URL to populate.")
    parser.add_argument(
        "--worksheet",
        default="titer-batch-input-comma",
        help="Worksheet name to create/overwrite.",
    )
    parser.add_argument(
        "--service-account",
        type=Path,
        default=Path("service_account.json"),
        help="Path to service_account.json for Google Sheets API.",
    )
    parser.add_argument(
        "--share",
        action="store_true",
        help="If set, share the sheet publicly (reader).",
    )
    parser.add_argument(
        "--include-gemini",
        action="store_true",
        help="Add a Gemini-only sample row (may hit free-tier quota).",
    )
    args = parser.parse_args()

    sheet_url = populate_sheet(
        sheet_url=args.sheet_url,
        worksheet=args.worksheet,
        service_account=args.service_account,
        share_public=args.share,
        include_gemini=args.include_gemini,
    )
    print(f"Populated worksheet '{args.worksheet}' in sheet: {sheet_url}")


if __name__ == "__main__":
    main()
