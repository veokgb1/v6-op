"""Print AR return contract results from JSONL."""
import json
from pathlib import Path

path = Path(r"F:\v.6\v6-op\query_lab\results\return_contract\ar_results.jsonl")
rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]

for r in rows:
    print()
    print(f"=== {r['query_id']} | {r['query_text']} ===")
    print(f"  status:        {r.get('status')}")
    print(f"  return_type:   {r.get('return_object_type', '?')}")
    print(f"  result_count:  {r.get('result_count', 0)}")
    print(f"  elapsed_ms:    {r.get('elapsed_ms', 0)}")
    raw = r.get("raw_columns", "")
    cols = raw.split("|") if raw else []
    print(f"  raw_columns ({len(cols)}): {raw}")
    print(f"  codes:         {r.get('extracted_stock_codes', '')}")
    print(f"  names:         {r.get('extracted_stock_names', '')}")
    print(f"  quote_cols:    {r.get('quote_cols', '')}")
    print(f"  factor_cols:   {r.get('factor_cols', '')}")
    print(f"  sector_cols:   {r.get('sector_cols', '')}")

# Aggregate all columns seen
print("\n=== ALL COLUMNS SEEN ACROSS ALL QUERIES ===")
all_cols = set()
for r in rows:
    raw = r.get("raw_columns", "")
    if raw:
        all_cols.update(raw.split("|"))
for c in sorted(all_cols):
    print(f"  {c}")

print("\n=== SAMPLE VALUES (first result AR-001) ===")
r0 = rows[0]
sv = r0.get("sample_values", {})
for col, vals in list(sv.items())[:15]:
    print(f"  {col}: {vals}")
