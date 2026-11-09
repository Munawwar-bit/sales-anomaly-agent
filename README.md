# Sales Anomaly Agent

A small AI agent that watches live sales data, detects unusual spikes,
and then **investigates the cause by itself** by writing and running SQL queries.

## How it works

1. **`generator.py`** simulates a shop: 2 hours of past sales, then a live feed.
   A few minutes in, it injects a hidden surge (Headphones in the North region).
2. **`agent.py`** works in two stages:
   - **Detector (plain math, no AI):** every 10 seconds it compares the latest
     minute's revenue with the previous 30 minutes using a z-score.
     If |z| > 3, it raises an alert.
   - **Investigator (Claude):** on an alert, Claude gets one tool, `run_sql`,
     and decides on its own which queries to run before writing a summary.

## Example run

```
20:34  revenue $1,801   (normal ≈ $2,211, z = -1.2)
20:35  revenue $14,990  (normal ≈ $2,194, z = +35.4)
🚨 Revenue for 20:35 was $14,990 vs a normal $2,194.
🔎 Investigating...
   ↳ query: SELECT ts, product, region, amount FROM sales WHERE ...
   ↳ query: SELECT strftime(ts, '%H:%M') AS minute, COUNT(*) AS n, ...
   ↳ query: SELECT product, region, COUNT(*) AS n, ...
   ↳ query: SELECT product, region, ... per-minute baseline ...
```

Without being told what to look for, the agent found that 138 of the
186 sales in that minute were Headphones in the North region
(normally one or two per minute), and noted it couldn't confirm the
business cause from the data alone.

## Design decisions

- **Cheap math first, AI only when needed.** The detector runs constantly for free;
  the model is only called when something is unusual.
- **Read-only tool.** `run_sql` rejects anything that isn't a SELECT/WITH/DESCRIBE query.
- **Errors go back to the model.** A failed query returns its error message,
  so Claude can fix its own SQL.
- **Step limit.** The investigation stops after 8 steps, so it can't loop forever.

## What I'd improve next

- Make queries date-aware (one query used `CAST(ts AS TIME)`, which would mix
  different days together in a longer dataset).
- Add a cooldown so a single long spike triggers one investigation, not several.
- Build a small evaluation set to measure how often the agent finds the right cause.

## Run it yourself

```
pip install -r requirements.txt
python generator.py          # terminal 1
```
```
# terminal 2 (PowerShell)
$env:ANTHROPIC_API_KEY="your-key"
python agent.py
```
The spike appears 3–5 minutes after the generator starts.
Set `USE_AI = False` in `agent.py` to run the detector without any API calls.

Built with Python, DuckDB, and the Claude API (`claude-haiku-5-5`).