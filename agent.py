import time, duckdb, anthropic

USE_AI = True   # Step 3: leave False. Step 4: change to True.

db = duckdb.connect()
# A "view" is a saved query. Every time we use 'sales', it re-reads the CSV, so we always see fresh data.
db.execute("CREATE VIEW sales AS SELECT * FROM read_csv_auto('sales.csv', ignore_errors=true)")

# ---------- The detector: plain math, no AI ----------
def check_latest_minute():
    df = db.execute("""
        SELECT date_trunc('minute', ts) AS minute, SUM(amount) AS revenue
        FROM sales GROUP BY 1 ORDER BY 1
    """).df()
    finished = df.iloc[:-1]                  # drop the current minute, since it's still filling up
    history = finished.revenue.iloc[-31:-1]  # the 30 minutes before the latest finished one
    latest = finished.iloc[-1]
    z = (latest.revenue - history.mean()) / history.std()
    return latest.minute, latest.revenue, history.mean(), z

# ---------- The agent: Claude investigates with SQL ----------
SYSTEM = """You are a data analyst investigating alerts on live sales data.
Table 'sales' has columns: ts (timestamp), product, region, amount (dollars).
Use run_sql to investigate. Compare the alert minute with normal behaviour,
break it down by product and region, then reply with a 3-sentence plain-English summary."""

TOOLS = [{
    "name": "run_sql",
    "description": "Run a read-only DuckDB SQL query on the 'sales' table. Returns up to 50 rows.",
    "input_schema": {"type": "object",
                     "properties": {"query": {"type": "string"}},
                     "required": ["query"]},
}]

def run_sql(query):
    if not query.strip().lower().startswith(("select", "with", "describe")):
        return "Only read-only queries are allowed."
    try:
        return db.execute(query).df().head(50).to_string()
    except Exception as e:
        return f"Error: {e}"   # Claude sees the error and can fix its own query

def investigate(alert):
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": f"Alert: {alert} Find out why."}]
    for _ in range(8):   # safety cap on the number of steps
        resp = client.messages.create(model="claude-haiku-5-5", max_tokens=1500,
                                      system=SYSTEM, tools=TOOLS, messages=messages)
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":   # Claude is done investigating
            return "".join(b.text for b in resp.content if b.type == "text")
        results = []
        for b in resp.content:
            if b.type == "tool_use":
                print("   ↳ query:", " ".join(b.input["query"].split())[:110])
                results.append({"type": "tool_result", "tool_use_id": b.id,
                                "content": run_sql(b.input["query"])})
        messages.append({"role": "user", "content": results})
    return "Investigation hit the step limit."

# ---------- The main loop ----------
print("Watching sales.csv... (Ctrl+C to stop)")
last_seen = None
while True:
    try:
        minute, revenue, normal, z = check_latest_minute()
    except Exception:
        time.sleep(5)   # the file was mid-write; try again shortly
        continue
    if minute != last_seen:   # only report once per finished minute
        last_seen = minute
        print(f"{minute:%H:%M}  revenue ${revenue:,.0f}   (normal ≈ ${normal:,.0f}, z = {z:+.1f})")
        if abs(z) > 3:
            alert = f"Revenue for {minute:%H:%M} was ${revenue:,.0f} vs a normal ${normal:,.0f}."
            print("🚨", alert)
            if USE_AI:
                print("🔎 Investigating...")
                print("\n" + investigate(alert) + "\n")
    time.sleep(10)