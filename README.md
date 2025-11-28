# Titer

<div align="center">
  <img src="https://lab-static.pingcap.com/images/2025/11/28/100f9a0a9eb9c3b31a1d891e351bd964852ee9a7.jpg" alt="titer icon" width="200" />
</div>

Command line utility to test LLM responses for keyword frequency and citation domain matches. Engines are pluggable; an OpenAI GPT-4.1 implementation ships with web search enabled by default.

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
  --engine "openai/gpt-4.1" \
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

Run the task:

```bash
titer batch --task-file example-task.csv --output-file outputs/task.csv
```

Each input row produces one output row with the columns described above.

## Environment

- Place credentials in a project-level `.env` file (e.g., `OPENAI_API_KEY=...`). It is loaded automatically on import.

## Engine notes

- OpenAI: uses `openai/gpt-4.1` with the Responses API and the `web_search` tool; it requires an account with web search access or calls will fail. Set `OPENAI_API_KEY` in the environment.
- Additional engines can be added by implementing the `Engine` ABC (`titer/engines/base.py`) and registering them in the factory (`titer/engines/factory.py`).
