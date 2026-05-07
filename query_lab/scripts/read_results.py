import json, sys, os

runs = [
    ("A6_time_window",       "run_20260507_154006"),
    ("A7_numeric_relative",  "run_20260507_154212"),
    ("A8_capital_flow",      "run_20260507_154454"),
    ("A9_technical_shape",   "run_20260507_154831"),
    ("A10_complex_boundary", "run_20260507_155054"),
]
base = r"F:\v.6\v6-op\query_lab\results\runs"

for label, run_id in runs:
    run_dir = os.path.join(base, run_id)
    complete = os.path.exists(os.path.join(run_dir, "RUN_COMPLETE"))
    print(f"=== {label} | {run_id} | RUN_COMPLETE={complete} ===")
    jsonl = os.path.join(run_dir, "analyzed_results.jsonl")
    counts = {}
    if os.path.exists(jsonl):
        with open(jsonl, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                status = d.get("analysis_status", "?")
                counts[status] = counts.get(status, 0) + 1
                qt = d.get("query_text", "")[:35]
                rc = d.get("result_count", "?")
                ft = d.get("failure_type", "?")
                rl = d.get("risk_level", "?")
                print(f"  {d['query_id']} | {status} | ft={ft} | rc={rc} | rl={rl} | {qt}")
    summary = " | ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    print(f"  SUMMARY: {summary}")
    print()
