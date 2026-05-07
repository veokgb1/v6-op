"""Read sector run analyzed_results.jsonl and print summary."""
from __future__ import annotations
import json, sys
from collections import Counter
from pathlib import Path

RUNS_DIR = Path(r"F:\v.6\v6-op\query_lab\results\runs")

def read_run(run_id: str) -> None:
    path = RUNS_DIR / run_id / "analyzed_results.jsonl"
    if not path.exists():
        print(f"NOT FOUND: {path}")
        return
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"\n=== {run_id}  ({len(rows)} rows) ===")
    for d in rows:
        qid = d.get("query_id", "?")
        status = d.get("analysis_status", "?")
        rc = d.get("result_count", 0)
        backend = d.get("actual_query_backend", "?")
        rot = d.get("return_object_type", "")
        names = d.get("extracted_sector_names", "")[:60]
        route = d.get("next_pipeline_route", "")[:50]
        query = d.get("query_text", "")[:40]
        print(f"  {qid} | {status} | rc={rc} | {backend} | {rot}")
        print(f"    query: {query}")
        print(f"    names: {names}")
        print(f"    route: {route}")
    print()
    types = Counter(d.get("return_object_type", "") for d in rows)
    statuses = Counter(d.get("analysis_status", "") for d in rows)
    backends = Counter(d.get("actual_query_backend", "") for d in rows)
    print(f"  return_object_type: {dict(types)}")
    print(f"  analysis_status:    {dict(statuses)}")
    print(f"  actual_backend:     {dict(backends)}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        for run_id in sys.argv[1:]:
            read_run(run_id)
    else:
        # Find latest runs
        runs = sorted(RUNS_DIR.iterdir(), key=lambda p: p.stat().st_mtime)[-4:]
        for r in runs:
            read_run(r.name)
