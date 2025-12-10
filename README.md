# Titer

<div align="center">
  <img src="https://lab-static.pingcap.com/images/2025/11/28/100f9a0a9eb9c3b31a1d891e351bd964852ee9a7.jpg" alt="titer icon" width="200" />
</div>

Command line utility to test LLM responses for keyword frequency and citation domain matches. Engines are pluggable; OpenAI and Gemini implementations ship with web search enabled by default.

Why "Titer"? In chemistry, a titer quantifies concentration via titration. This project "titrates" LLM outputs by repeatedly measuring how often specific keywords or citation domains appear, providing a concentration-like readout across prompts and engines.

## Quickstart (uv)

```bash
uv venv
source .venv/bin/activate
uv sync
```

## CLI usage

Evaluate prompts once or multiple times and emit aggregated counts:

```bash
titer run \
  --prompt "What database should I use for AI apps?" \
  --engine "openai/gpt-4o" \
  --engine "gemini/gemini-2.0-flash" \
  --keyword "Postgres" --keyword "vector" \
  --domain "*.postgresql.org" --domain "*.wikipedia.org" \
  --runs 3 \
  --output-csv outputs/single-run.csv
```

Output is JSON printed to stdout plus an optional CSV row saved via `--output-csv`. Columns include:
- `timestamp`: ISO-8601 UTC timestamp
- `prompts`, `engines`, `keywords`, `domain_wildcards`: original inputs
- `runs`: number of iterations
- `keyword_counts`: JSON map of keyword -> average count across runs
- `domain_counts`: JSON map of domain wildcard -> average count across runs
- `raw_responses`: raw engine payloads for debugging

## Batch task runner

You can schedule repeated evaluations via a CSV task file and emit a CSV result file. Fields accept JSON arrays or `|`-separated strings.

Task CSV columns:
- `prompts`: list of prompts
- `engines`: list of `<provider>/<model>` names
- `keywords`: list of keywords
- `domain_wildcards`: list of wildcard domains (e.g., `*.example.com`)
- `runs`: integer iterations (default 1)

Example `example-task.csv` (uses `|`-separated lists to avoid CSV/JSON quoting issues):

```csv
prompts,engines,keywords,domain_wildcards,runs
"What database should I use for AI apps?","openai/gpt-4.1","database|vector","*.postgresql.org|*.wikipedia.org",2
```

If you prefer JSON arrays, remember to escape double quotes inside CSV cells, e.g.:

```csv
prompts,engines,keywords,domain_wildcards,runs
"[""What database should I use for AI apps?""]","[""openai/gpt-4.1""]","[""database"",""vector""]","[""*.postgresql.org"",""*.wikipedia.org""]",2
```

Run the task to a CSV file:

```bash
titer batch --task-file example-task.csv --output-file outputs/task.csv
```

### Batch via Google Sheets

You can read tasks from a Google Sheet and/or write results back to a Sheet. Use a service account JSON (place it at `service_account.json` or point `--service-account` to it). Example (reads from Sheet, writes results to a new worksheet in another Sheet):

```bash
titer batch \
  --task-sheet "https://docs.google.com/spreadsheets/d/<TASK_SHEET_ID>/edit" \
  --task-sheet-worksheet "Sheet1" \
  --output-sheet "https://docs.google.com/spreadsheets/d/<OUTPUT_SHEET_ID>/edit" \
  --output-sheet-worksheet "titer-results" \
  --share-output-sheet \
  --service-account service_account.json
```

Notes:
- You may mix CSV + Sheets (e.g., Sheet input + CSV output, or CSV input + Sheet output).
- `--share-output-sheet` makes the output sheet publicly readable (useful for sharing results).
- The Sheet columns match the CSV columns shown above.

Each input row produces one output row with the columns described above.

## Environment

- Place credentials in a project-level `.env` file. It is loaded automatically on import.
  - `OPENAI_API_KEY=...`
  - `GEMINI_API_KEY=...`
- Google Sheets: supply `service_account.json` (downloaded from Google Cloud) in the project root or pass `--service-account <path>`.

## Engine notes

- OpenAI: uses the Responses API with the `web_search` tool. Works with any model string, e.g., `openai/gpt-4o`, `openai/gpt-4.1`, `openai/o3-mini`.
- Gemini: uses `google-genai` with the Google Search tool. Works with model strings such as `gemini/gemini-2.0-flash`, `gemini/gemini-1.5-flash-8b`, `gemini/gemini-1.5-pro`.
  - Free plan Gemini keys can hit rate limits; the engine retries with exponential backoff and will surface a clear error if limits persist. Prefer smaller models (`gemini-2.0-flash`, `gemini-1.5-flash-8b`) for higher reliability.
- Additional engines can be added by implementing the `Engine` ABC (`titer/engines/base.py`) and registering them in the factory (`titer/engines/factory.py`).

## GitHub workflow

See `docs/github-workflow.md` for a ready-to-use weekly GitHub Actions workflow that reads tasks from Google Sheets and writes results back to Google Sheets using repository secrets.
