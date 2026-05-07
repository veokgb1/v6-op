"""Dump all sector run results with correct UTF-8 encoding."""
from __future__ import annotations
import json
from pathlib import Path
from collections import Counter

RUNS = [
    ("S1_basic",          "run_20260507_184927"),
    ("S2_synonym",        "run_20260507_185040"),
    ("S3_combo",          "run_20260507_185133"),
    ("S4_risky",          "run_20260507_185212"),
    ("S5_emotion_style",  "run_20260507_185404"),
    ("S6_two_step",       "run_20260507_185451"),
    ("S7_low_reversal",   "run_20260507_185554"),
    ("S8_return_contract","run_20260507_185649"),
]

RUNS_DIR = Path(r"F:\v.6\v6-op\query_lab\results\runs")

for group, run_id in RUNS:
    path = RUNS_DIR / run_id / "analyzed_results.jsonl"
    if not path.exists():
        print(f"MISSING: {path}")
        continue
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    types = Counter(r.get("return_object_type","") for r in rows)
    statuses = Counter(r.get("analysis_status","") for r in rows)
    print(f"\n{'='*60}")
    print(f"GROUP: {group}  run: {run_id}  rows: {len(rows)}")
    print(f"  status_counts: {dict(statuses)}")
    print(f"  type_counts:   {dict(types)}")
    for r in rows:
        qid = r.get("query_id","?")
        status = r.get("analysis_status","?")
        rc = r.get("result_count",0)
        backend = r.get("actual_query_backend","?")
        rot = r.get("return_object_type","")
        query = r.get("query_text","")
        names = r.get("extracted_sector_names","")
        names_sample = "|".join(names.split("|")[:4]) if names else ""
        print(f"  {qid} | {status} | rc={rc} | {backend} | {rot}")
        print(f"    q: {query}")
        if names_sample:
            print(f"    names: {names_sample}")
