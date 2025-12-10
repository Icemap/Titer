# GitHub Workflow: Weekly Titer Batch Run

This workflow runs `titer batch` weekly, using Google Sheets for input and output. Each run writes results to a new output worksheet named with the UTC date and moves that tab to the front.

## Secrets to configure

Add these repository secrets:

- `OPENAI_API_KEY` – OpenAI key.
- `GEMINI_API_KEY` – Gemini key (optional; keep tasks OpenAI-only if free-tier quota is tight).
- `GCP_SERVICE_ACCOUNT_JSON_B64` – Base64-encoded contents of `service_account.json`.
- `TITER_TASK_SHEET_URL` – Google Sheet URL (or ID) for batch input.
- `TITER_TASK_SHEET_WORKSHEET` – Worksheet name for input (e.g., `titer-batch-input-comma`).
- `TITER_OUTPUT_SHEET_URL` – Google Sheet URL (or ID) for batch output.
- `PYTHON_VERSION` – Optional Python version override (defaults to `3.12`).

## Workflow file

Save as `.github/workflows/weekly-titer-batch.yml`:

```yaml
name: Weekly Titer Batch

on:
  schedule:
    - cron: "0 2 * * MON" # Every Monday at 02:00 UTC
  workflow_dispatch: {}    # Manual trigger for testing

jobs:
  run-batch:
    runs-on: ubuntu-latest
    env:
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
      TITER_TASK_SHEET_URL: ${{ secrets.TITER_TASK_SHEET_URL }}
      TITER_TASK_SHEET_WORKSHEET: ${{ secrets.TITER_TASK_SHEET_WORKSHEET }}
      TITER_OUTPUT_SHEET_URL: ${{ secrets.TITER_OUTPUT_SHEET_URL }}
    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ secrets.PYTHON_VERSION || '3.12' }}

      - name: Install uv
        run: |
          pip install uv

      - name: Restore dependencies
        run: |
          uv sync --frozen

      - name: Write service account file
        env:
          GCP_SERVICE_ACCOUNT_JSON_B64: ${{ secrets.GCP_SERVICE_ACCOUNT_JSON_B64 }}
        run: |
          if [ -z "$GCP_SERVICE_ACCOUNT_JSON_B64" ]; then
            echo "Missing GCP_SERVICE_ACCOUNT_JSON_B64 secret" >&2
            exit 1
          fi
          echo "$GCP_SERVICE_ACCOUNT_JSON_B64" | base64 -d > service_account.json

      - name: Set output worksheet name (UTC date)
        run: |
          echo "TITER_OUTPUT_SHEET_WORKSHEET=$(date -u +%Y-%m-%d)" >> "$GITHUB_ENV"

      - name: Run weekly batch
        run: |
          source .venv/bin/activate
          titer batch \
            --task-sheet "$TITER_TASK_SHEET_URL" \
            --task-sheet-worksheet "$TITER_TASK_SHEET_WORKSHEET" \
            --output-sheet "$TITER_OUTPUT_SHEET_URL" \
            --output-sheet-worksheet "$TITER_OUTPUT_SHEET_WORKSHEET" \
            --service-account service_account.json \
            --share-output-sheet
```

## Notes
- Each run writes to a date-named worksheet (UTC) and moves that tab to the front of the sheet.
- Keep the input sheet rows OpenAI-only if your Gemini free-tier quota is tight.
- The workflow uses `uv sync --frozen` to install dependencies from `uv.lock`.
- Output sheet is made publicly readable via `--share-output-sheet`; remove that flag if you prefer private sharing and grant the service account access manually.
