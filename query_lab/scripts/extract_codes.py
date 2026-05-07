"""Extract stock codes from query_results.jsonl for A12 code pool."""
import json, sys

run_dir = sys.argv[1]
path = run_dir + r"\query_results.jsonl"

print(f"Reading: {path}")
all_codes = []
with open(path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        qid = d.get("query_id", "?")
        rc = d.get("result_count", 0)
        if rc == 0:
            continue
        raw = d.get("raw_result", [])
        if not raw:
            continue
        # pywencai returns list of dicts
        found = []
        for item in raw[:10]:
            if isinstance(item, dict):
                # Try common code fields
                for field in ["股票代码", "code", "symbol", "ticker"]:
                    val = item.get(field)
                    if val:
                        found.append(str(val).zfill(6))
                        break
        print(f"  {qid} | rc={rc} | sample codes: {found[:5]}")
        all_codes.extend(found[:3])

# Dedupe preserving order
seen = set()
unique = []
for c in all_codes:
    if c not in seen:
        seen.add(c)
        unique.append(c)

print(f"\nUnique codes collected: {unique[:20]}")
