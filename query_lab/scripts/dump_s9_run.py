"""Dump S9 run results with full field detail."""
from __future__ import annotations
import json
from pathlib import Path

RUN_ID = "run_20260507_193519"
RUNS_DIR = Path(r"F:\v.6\v6-op\query_lab\results\runs")

path = RUNS_DIR / RUN_ID / "analyzed_results.jsonl"
rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]

print(f"=== S9 run: {RUN_ID}  rows: {len(rows)} ===\n")
for d in rows:
    print(f"{'─'*60}")
    print(f"  query_id:               {d.get('query_id')}")
    print(f"  analysis_status:        {d.get('analysis_status')}")
    print(f"  exec_status:            {d.get('exec_status')}")
    print(f"  result_count:           {d.get('result_count')}")
    print(f"  actual_backend:         {d.get('actual_query_backend')}")
    print(f"  return_object_type:     {d.get('return_object_type')}")
    print(f"  query_text:             {d.get('query_text')}")
    print(f"  raw_columns:            {d.get('raw_columns','')[:100]}")
    print(f"  extracted_sector_names: {d.get('extracted_sector_names','')[:80]}")
    print(f"  extracted_index_codes:  {d.get('extracted_index_codes','')[:60]}")
    print(f"  extracted_stock_codes:  {d.get('extracted_stock_codes','')}")
    print(f"  extracted_stock_names:  {d.get('extracted_stock_names','')}")
    print(f"  extracted_reason_text:  {d.get('extracted_reason_text','')}")
    print(f"  next_pipeline_route:    {d.get('next_pipeline_route','')[:70]}")
    print(f"  notes:                  {d.get('notes','')[:80]}")
    print()

from collections import Counter
types = Counter(d.get("return_object_type","") for d in rows)
statuses = Counter(d.get("analysis_status","") for d in rows)
backends = Counter(d.get("actual_query_backend","") for d in rows)
print(f"\n=== SUMMARY ===")
print(f"  return_object_type: {dict(types)}")
print(f"  analysis_status:    {dict(statuses)}")
print(f"  actual_backend:     {dict(backends)}")
