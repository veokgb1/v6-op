import json, os, sys

run_dir = sys.argv[1]
path = os.path.join(run_dir, "analyzed_results.jsonl")
rows = []
if os.path.exists(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            rows.append(d)
            ft = d.get("failure_type","?")
            rc = d.get("result_count","?")
            st = d.get("analysis_status","?")
            el = d.get("elapsed_ms","?")
            qt = d.get("query_text","")[:45]
            qid = d.get("query_id","?")
            print(f"  {qid} | {st} | ft={ft} | rc={rc} | {el}ms | {qt}")

complete = os.path.exists(os.path.join(run_dir, "RUN_COMPLETE"))
counts = {}
for d in rows:
    s = d.get("analysis_status","?")
    counts[s] = counts.get(s, 0) + 1
print(f"  RUN_COMPLETE={complete}  counts={counts}")

# Print stock codes from successful results for A12 code pool
print("\n  [Stock codes in results]")
for d in rows:
    if d.get("result_count", 0) and d.get("result_count", 0) > 0:
        raw = d.get("raw_result", "")
        if isinstance(raw, list) and len(raw) > 0:
            codes = []
            for item in raw[:5]:
                if isinstance(item, dict):
                    code = item.get("股票代码") or item.get("code") or item.get("symbol","")
                    if code:
                        codes.append(str(code))
            if codes:
                print(f"    {d['query_id']}: {codes}")
