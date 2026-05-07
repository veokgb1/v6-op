"""Inspect S9-007 and S9-008 raw data to see 领涨股简称 column values."""
from __future__ import annotations
import json
from pathlib import Path

RUN_ID = "run_20260507_193519"
RUNS_DIR = Path(r"F:\v.6\v6-op\query_lab\results\runs")

# Read query_results to get raw column data (result_analyzer may drop row detail)
qr_path = RUNS_DIR / RUN_ID / "query_results.jsonl"
rows_qr = [json.loads(l) for l in qr_path.read_text(encoding="utf-8").splitlines() if l.strip()]

for r in rows_qr:
    qid = r.get("query_id")
    if qid in ("S9-007", "S9-008"):
        print(f"\n{'='*60}")
        print(f"query_id: {qid}")
        print(f"query_text: {r.get('query_text')}")
        print(f"exec_status: {r.get('exec_status')}")
        print(f"result_count: {r.get('result_count')}")
        print(f"return_object_type: {r.get('return_object_type')}")
        print(f"raw_columns: {r.get('raw_columns','')}")
        print(f"extracted_sector_names: {r.get('extracted_sector_names','')}")
        print(f"extracted_index_codes: {r.get('extracted_index_codes','')}")
        print(f"extracted_stock_names: {r.get('extracted_stock_names','')}")
        print(f"extracted_reason_text: {r.get('extracted_reason_text','')}")

# Also re-run pywencai directly to see full data for S9-007
print("\n\n=== Direct pywencai query for S9-007 ===")
try:
    import pywencai
    result = pywencai.get(
        query="今日涨幅排名前5的板块及其领涨股",
        query_type="zhishu",
        perpage=5,
        page=1,
    )
    if result is None:
        print("Result: None")
    elif hasattr(result, "to_dict"):
        rows = result.to_dict(orient="records")
        print(f"Rows: {len(rows)}")
        if rows:
            print(f"Columns: {list(rows[0].keys())}")
            for row in rows[:3]:
                for k, v in row.items():
                    print(f"  {k}: {v}")
                print()
    elif isinstance(result, list) and result:
        print(f"Rows (list): {len(result)}")
        print(f"Columns: {list(result[0].keys())}")
        for row in result[:3]:
            for k, v in row.items():
                print(f"  {k}: {v}")
            print()
    else:
        print(f"Type: {type(result)}, Value: {result}")
except Exception as e:
    print(f"Error: {e}")
