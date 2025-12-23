# Titer: A Simple "Titration" Tool for LLM Responses

![titer.png 85%](https://lab-static.pingcap.com/images/2025/12/23/fa7e6fab2eb2c7b98d1b18fd9d85ef5910a06591.png)

Titer is a CLI utility that **measures what shows up in LLM answers** by counting:

- keyword frequency in the response text
- citation/source domain frequency (with wildcard support)

It doesn't judge correctness. Instead, it gives you a **repeatable, comparable signal** across models, prompts, and runs.

> The name comes from chemistry: titration measures concentration. Titer **titrates** LLM outputs by repeatedly measuring how often specific terms or domains appear.

## When it's useful

- **Model comparison**: see whether different models favor certain keywords or citation domains.
- **Stability checks**: run the same prompt multiple times and compare average counts.
- **Automated monitoring**: feed results into reports or dashboards for ongoing tracking.

Think of it as a **measurement tool**, not a full evaluation framework.

## How it works

Titer's pipeline is intentionally minimal and transparent:

1. **Read tasks** from CLI arguments, CSV, or Google Sheets.
2. **Call engines** by `provider/model` (OpenAI and Gemini are built in).
3. **Repeat runs** N times per prompt to reduce randomness.
4. **Extract signals**:
   - count keyword occurrences (case-insensitive)
   - extract URLs from responses, then match domain wildcards
5. **Write results** to JSON and optionally CSV / Google Sheets

## Key modules

- `titer/engines/`: engine adapters (OpenAI, Gemini)
- `titer/evaluator.py`: run loop + keyword/domain counting
- `titer/cli.py`: command-line interface
- `titer/task_runner.py`: CSV / Sheets batch runner

### Engine layer

Each engine implements a shared interface and returns a normalized response:

- `content`: the generated text
- `cites`: extracted URLs
- `raw`: original response payload

This keeps measurement logic consistent regardless of provider and makes it easy to add new engines later.

## Core measurement logic

### Keyword counts

Each keyword is matched with case-insensitive regex and counted. The final output averages counts across runs.

### Domain counts

Titer extracts URLs from the response payload, parses the host, and matches against wildcard patterns like:

- `*.pingcap.com`
- `*.tidb.io`

Matches are counted and averaged across runs.

## Usage examples

### Single run (CLI)

```bash
titer run \
  --prompt "What database should I use for AI apps?" \
  --engine "openai/gpt-4o" \
  --engine "gemini/gemini-2.0-flash" \
  --keyword "TiDB" --keyword "PingCAP" \
  --domain "*.pingcap.com" --domain "*.tidb.io" \
  --runs 3 \
  --output-csv outputs/single-run.csv
```

The output includes:

- `keyword_counts`: average counts per keyword
- `domain_counts`: average counts per domain wildcard
- `raw_responses`: full payloads for debugging

### Batch runs (CSV or Google Sheets)

For repeated jobs, you can load tasks from CSV or Sheets and write results back out. This is useful for weekly or monthly monitoring.

## What the output looks like

Each task produces a record with:

- timestamp
- prompts / engines / keywords / domain_wildcards
- runs
- keyword_counts (averages)
- domain_counts (averages)
- raw_responses (full payloads)

These can be fed into BI tools or post-processed with scripts.

## Limitations

- **Not fully reproducible**: online models and search tools change over time.
- **Coarse metrics**: frequency doesn't imply correctness or quality.
- **Interpretation required**: it's a measurement signal, not a conclusion.

## Summary

Titer is a lightweight, extensible tool for **observing LLM behavior through keyword and citation-domain frequency**. It's best used as a consistent measurement layer for comparisons, monitoring, or internal evaluation workflows.

If you need something that's simple, scriptable, and easy to extend, Titer is a good starting point.
