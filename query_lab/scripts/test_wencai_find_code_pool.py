"""
test_wencai_find_code_pool.py — Test pywencai `find` parameter for code-pool requery.

Output: F:\v.6\v6-op\query_lab\results\code_pool_repair\
  find_test_results.jsonl
  find_test_report.md
"""
from __future__ import annotations
import json, os, time
from pathlib import Path

PROJECT = Path(r"F:\v.6\v6-op")
OUT_DIR = PROJECT / "query_lab" / "results" / "code_pool_repair"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CODES = ["000060", "603399", "600519", "000858", "600036", "601318", "000333", "600276", "000001", "600000"]

TESTS = [
    {"query": "今日成交额大于近5日平均成交额1.5倍",       "desc": "相对成交额1.5倍(find)"},
    {"query": "今日收盘价大于5日均线",                   "desc": "收盘>MA5(find)"},
    {"query": "近10日有涨停",                           "desc": "近10日涨停(find)"},
    {"query": "今日成交额大于近5日平均成交额1.5倍，今日收盘价大于5日均线", "desc": "相对成交额+MA5(find)"},
]

import pywencai

results = []

def run_test(query: str, find_codes: list[str] | None, desc: str) -> dict:
    t0 = time.time()
    kwargs = dict(query=query, query_type="stock", perpage=100, page=1)
    if find_codes is not None:
        kwargs["find"] = find_codes

    raw_error = ""
    raw_cols = []
    returned_codes: list[str] = []
    status = "ok"
    result_count = 0

    try:
        result = pywencai.get(**kwargs)
        elapsed_ms = round((time.time() - t0) * 1000, 1)

        if result is None:
            status = "empty_result"
        else:
            import pandas as pd
            if isinstance(result, pd.DataFrame):
                df = result
            elif isinstance(result, list):
                if not result:
                    status = "empty_result"
                    return _build(query, find_codes, desc, elapsed_ms, status, 0, [], [], raw_error)
                df = pd.DataFrame(result)
            elif isinstance(result, dict):
                # might be a dict of lists
                for v in result.values():
                    if isinstance(v, list) and v:
                        df = pd.DataFrame(v)
                        break
                else:
                    status = "empty_result"
                    return _build(query, find_codes, desc, elapsed_ms, status, 0, [], [], raw_error)
            else:
                status = "unknown_type"
                return _build(query, find_codes, desc, elapsed_ms, status, 0, [], [], str(type(result)))

            raw_cols = list(df.columns)[:15]

            # Extract codes
            code_col = None
            for c in df.columns:
                s = str(c)
                if "代码" in s or s.lower() in ("code", "symbol", "ticker"):
                    code_col = c
                    break

            if code_col:
                returned_codes = df[code_col].astype(str).str.zfill(6).tolist()

            result_count = len(df)
            if result_count == 0:
                status = "empty_result"

    except Exception as e:
        elapsed_ms = round((time.time() - t0) * 1000, 1)
        raw_error = str(e)[:300]
        status = "api_error"

    return _build(query, find_codes, desc, elapsed_ms, status, result_count, returned_codes, raw_cols, raw_error)


def _build(query, find_codes, desc, elapsed_ms, status, result_count, returned_codes, raw_cols, raw_error):
    in_pool = set(c.zfill(6) for c in (find_codes or []))
    out_of_pool = [c for c in returned_codes if c.zfill(6) not in in_pool]
    pool_overlap = [c for c in returned_codes if c.zfill(6) in in_pool]
    return {
        "desc": desc,
        "query": query,
        "find_codes": find_codes,
        "status": status,
        "result_count": result_count,
        "returned_codes": returned_codes[:20],
        "pool_overlap": pool_overlap,
        "out_of_pool_codes": out_of_pool[:5],
        "elapsed_ms": elapsed_ms,
        "raw_columns": raw_cols,
        "raw_error": raw_error,
    }


print("=" * 60)
print("pywencai find= parameter test")
print("=" * 60)

for t in TESTS:
    print(f"\n>>> {t['desc']}")
    print(f"    query: {t['query']}")
    print(f"    find={CODES[:4]}...")
    r = run_test(t["query"], CODES, t["desc"])
    results.append(r)
    print(f"    status={r['status']} rc={r['result_count']} elapsed={r['elapsed_ms']}ms")
    print(f"    returned: {r['returned_codes'][:5]}")
    print(f"    pool_overlap: {r['pool_overlap']}")
    print(f"    out_of_pool: {r['out_of_pool_codes'][:3]}")

# Save JSONL
jsonl_path = OUT_DIR / "find_test_results.jsonl"
with open(jsonl_path, "w", encoding="utf-8") as f:
    for r in results:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"\nSaved: {jsonl_path}")

# Determine verdict
all_empty = all(r["status"] == "empty_result" for r in results)
any_out_of_pool = any(r["out_of_pool_codes"] for r in results)
any_pool_hit = any(r["pool_overlap"] for r in results)

if all_empty:
    verdict = "FIND_NOT_SUPPORTED — pywencai find= returns empty for all queries"
elif any_out_of_pool:
    verdict = "FIND_IGNORES_POOL — returns stocks outside code pool, unusable"
elif any_pool_hit and not any_out_of_pool:
    verdict = "FIND_WORKS — respects code pool, returns only matching codes"
else:
    verdict = "INCONCLUSIVE — mixed results, manual review required"

print(f"\nVERDICT: {verdict}")

# Write report
report_path = OUT_DIR / "find_test_report.md"
lines = [
    "# pywencai find= 参数代码池复问测试报告",
    f"\n**测试时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
    f"**代码池**: {CODES}",
    f"\n## 最终结论\n\n**{verdict}**\n",
    "## 测试明细\n",
    "| desc | status | rc | elapsed | pool_overlap | out_of_pool |",
    "|------|--------|-----|---------|-------------|-------------|",
]
for r in results:
    lines.append(
        f"| {r['desc']} | {r['status']} | {r['result_count']} | {r['elapsed_ms']}ms"
        f" | {r['pool_overlap'][:3]} | {r['out_of_pool_codes'][:3]} |"
    )

lines += [
    "\n## 各条明细\n",
]
for r in results:
    lines.append(f"### {r['desc']}")
    lines.append(f"- query: `{r['query']}`")
    lines.append(f"- find_codes: `{r['find_codes']}`")
    lines.append(f"- status: `{r['status']}`")
    lines.append(f"- result_count: {r['result_count']}")
    lines.append(f"- elapsed_ms: {r['elapsed_ms']}")
    lines.append(f"- returned_codes: {r['returned_codes'][:10]}")
    lines.append(f"- pool_overlap: {r['pool_overlap']}")
    lines.append(f"- out_of_pool: {r['out_of_pool_codes']}")
    lines.append(f"- raw_columns: {r['raw_columns'][:8]}")
    lines.append(f"- raw_error: `{r['raw_error']}`")
    lines.append("")

report_path.write_text("\n".join(lines), encoding="utf-8")
print(f"Saved: {report_path}")
