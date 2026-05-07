"""
inspect_astock_return_contract.py
直接查询 pywencai，捕获完整 raw_columns 和所有字段值。
目的：确认 问财选A股 除股票代码外还返回哪些字段。
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / "query_lab" / "results" / "return_contract"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

QUERIES = [
    ("AR-001", "今日涨幅大于3%"),
    ("AR-002", "今日成交额大于5亿"),
    ("AR-003", "今日换手率大于5%"),
    ("AR-004", "今日量比大于1.5"),
    ("AR-005", "今日主力净流入大于1亿"),
    ("AR-006", "流通市值在80亿到300亿之间"),
    ("AR-007", "半导体板块，今日涨幅大于3%"),
    ("AR-008", "今日涨幅大于3%，今日成交额大于5亿，今日主力净流入为正"),
]

SLEEP_SEC = 3.0
PERPAGE = 100

# Column classification patterns
_QUOTE_KEYWORDS = ("涨跌幅", "涨幅", "跌幅", "收盘", "最新价", "现价", "开盘", "最高", "最低", "均价")
_FACTOR_KEYWORDS = ("成交额", "成交量", "换手率", "量比", "主力净流入", "主力资金", "资金流向",
                    "流通市值", "总市值", "市值", "市盈率", "市净率", "换手")
_NAME_KEYWORDS = ("股票简称", "简称", "股票名称", "名称", "证券简称", "证券名称")
_CODE_KEYWORDS = ("股票代码", "证券代码", "代码", "symbol", "code")
_SECTOR_KEYWORDS = ("所属行业", "所属板块", "行业", "板块", "概念", "industry", "sector")

_CODE_RE = re.compile(r"^\d{6}(\.(?:SH|SZ|BJ))?$", re.IGNORECASE)


def _classify_col(col: str) -> str:
    c = str(col)
    if any(k in c for k in _CODE_KEYWORDS):
        return "code"
    if any(k in c for k in _NAME_KEYWORDS):
        return "name"
    if any(k in c for k in _QUOTE_KEYWORDS):
        return "quote"
    if any(k in c for k in _FACTOR_KEYWORDS):
        return "factor"
    if any(k in c for k in _SECTOR_KEYWORDS):
        return "sector"
    return "other"


def _extract_stock_info(rows: list[dict]) -> dict:
    codes, names = [], []
    quote_cols, factor_cols, sector_cols, other_cols = [], [], [], []
    seen_codes: set[str] = set()
    seen_names: set[str] = set()

    if not rows:
        return {
            "codes": [], "names": [], "quote_cols": [],
            "factor_cols": [], "sector_cols": [], "other_cols": [],
        }

    all_cols = list(rows[0].keys())
    for col in all_cols:
        cat = _classify_col(col)
        if cat == "quote":
            quote_cols.append(col)
        elif cat == "factor":
            factor_cols.append(col)
        elif cat == "sector":
            sector_cols.append(col)
        elif cat not in ("code", "name"):
            other_cols.append(col)

    for row in rows:
        # Extract code
        for f in ["股票代码", "证券代码", "代码", "symbol", "code"]:
            if f in row:
                val = str(row[f]).strip()
                clean = re.sub(r"\.(SH|SZ|BJ)$", "", val, flags=re.IGNORECASE)
                if re.match(r"^\d{6}$", clean) and val not in seen_codes:
                    seen_codes.add(val)
                    codes.append(val)
                    break
        # Extract name
        for f in ["股票简称", "证券简称", "股票名称", "证券名称", "简称", "名称"]:
            if f in row:
                val = str(row[f]).strip()
                if val and val not in ("nan", "None", "") and val not in seen_names:
                    seen_names.add(val)
                    names.append(val)
                    break

    return {
        "codes": codes,
        "names": names,
        "quote_cols": quote_cols,
        "factor_cols": factor_cols,
        "sector_cols": sector_cols,
        "other_cols": other_cols,
    }


def _sample_values(rows: list[dict], cols: list[str], n: int = 2) -> dict[str, list]:
    """Sample first n non-null values for each column."""
    out = {}
    for col in cols:
        vals = []
        for row in rows:
            v = row.get(col)
            if v is not None and str(v).strip() not in ("", "nan", "None"):
                vals.append(str(v).strip())
            if len(vals) >= n:
                break
        out[col] = vals
    return out


def run_one(qid: str, query_text: str) -> dict:
    print(f"\n{'='*60}")
    print(f"[{qid}] {query_text}")
    try:
        import pywencai
    except ImportError:
        print("  pywencai not installed")
        return {"query_id": qid, "query_text": query_text, "status": "blocked"}

    t0 = time.time()
    try:
        result = pywencai.get(
            query=query_text,
            query_type="stock",
            perpage=PERPAGE,
            page=1,
        )
    except Exception as exc:
        elapsed = round((time.time() - t0) * 1000, 1)
        print(f"  ERROR: {exc}")
        return {
            "query_id": qid, "query_text": query_text,
            "status": "api_error", "raw_error": str(exc)[:200],
            "elapsed_ms": elapsed,
        }

    elapsed = round((time.time() - t0) * 1000, 1)

    rows: list[dict] = []
    if result is None:
        pass
    elif isinstance(result, list):
        rows = result
    elif hasattr(result, "to_dict"):
        rows = result.to_dict(orient="records")
    elif isinstance(result, dict):
        for v in result.values():
            if isinstance(v, list):
                rows = v
                break

    if not rows:
        print(f"  status=empty_result  elapsed={elapsed}ms")
        return {
            "query_id": qid, "query_text": query_text,
            "status": "empty_result", "result_count": 0,
            "raw_columns": "", "elapsed_ms": elapsed,
        }

    raw_cols = list(rows[0].keys())
    info = _extract_stock_info(rows)
    sample_vals = _sample_values(rows, raw_cols[:30], n=2)

    # Classify return type
    has_codes = bool(info["codes"])
    has_names = bool(info["names"])
    has_quote = bool(info["quote_cols"])
    has_factor = bool(info["factor_cols"])

    if has_codes and has_names and (has_quote or has_factor):
        return_type = "stock_with_quote" if has_quote else "stock_with_factor"
    elif has_codes and has_names:
        return_type = "stock_code_name"
    elif has_codes:
        return_type = "stock_code_only"
    elif rows:
        return_type = "mixed_unknown"
    else:
        return_type = "empty_or_error"

    rec = {
        "query_id": qid,
        "query_text": query_text,
        "status": "ok",
        "return_object_type": return_type,
        "result_count": len(rows),
        "elapsed_ms": elapsed,
        "raw_columns": "|".join(str(c) for c in raw_cols),
        "extracted_stock_codes": "|".join(info["codes"][:5]),
        "extracted_stock_names": "|".join(info["names"][:5]),
        "quote_cols": "|".join(info["quote_cols"]),
        "factor_cols": "|".join(info["factor_cols"]),
        "sector_cols": "|".join(info["sector_cols"]),
        "other_cols": "|".join(info["other_cols"]),
        "sample_values": sample_vals,
    }

    print(f"  status=ok  rc={len(rows)}  elapsed={elapsed}ms")
    print(f"  return_type: {return_type}")
    print(f"  raw_columns ({len(raw_cols)}): {' | '.join(str(c) for c in raw_cols[:8])}...")
    if info["codes"]:
        print(f"  codes: {info['codes'][:3]}")
    if info["names"]:
        print(f"  names: {info['names'][:3]}")
    if info["quote_cols"]:
        print(f"  quote_cols: {info['quote_cols'][:5]}")
    if info["factor_cols"]:
        print(f"  factor_cols: {info['factor_cols'][:5]}")
    if info["sector_cols"]:
        print(f"  sector_cols: {info['sector_cols']}")

    return rec


def main():
    # Load env
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k not in os.environ:
                os.environ[k] = v

    api_key = os.environ.get("IWENCAI_API_KEY", "")
    if not api_key:
        print("[ERROR] IWENCAI_API_KEY not set")
        sys.exit(1)

    print(f"[inspect_astock_return_contract] queries={len(QUERIES)}  perpage={PERPAGE}")
    print(f"Results dir: {RESULTS_DIR}")

    all_results = []
    for i, (qid, qt) in enumerate(QUERIES):
        rec = run_one(qid, qt)
        all_results.append(rec)
        if i < len(QUERIES) - 1:
            time.sleep(SLEEP_SEC)

    # Save JSONL
    out_path = RESULTS_DIR / "ar_results.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for r in all_results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n[DONE] Results → {out_path}")

    # Print summary
    print("\n=== SUMMARY ===")
    for r in all_results:
        rt = r.get("return_object_type", r.get("status", "?"))
        rc = r.get("result_count", 0)
        elapsed = r.get("elapsed_ms", 0)
        print(f"  {r['query_id']:8s}  rc={rc:4d}  {rt:25s}  {elapsed:.0f}ms")

    # Print column aggregation
    print("\n=== COLUMN SURVEY ===")
    all_raw_cols: set[str] = set()
    all_quote_cols: set[str] = set()
    all_factor_cols: set[str] = set()
    all_sector_cols: set[str] = set()
    for r in all_results:
        if r.get("raw_columns"):
            all_raw_cols.update(r["raw_columns"].split("|"))
        if r.get("quote_cols"):
            all_quote_cols.update(r["quote_cols"].split("|"))
        if r.get("factor_cols"):
            all_factor_cols.update(r["factor_cols"].split("|"))
        if r.get("sector_cols"):
            all_sector_cols.update(r["sector_cols"].split("|"))

    print(f"All raw columns seen: {sorted(all_raw_cols)}")
    print(f"Quote cols: {sorted(all_quote_cols)}")
    print(f"Factor cols: {sorted(all_factor_cols)}")
    print(f"Sector cols: {sorted(all_sector_cols)}")

    print(f"\n[RUN_COMPLETE] results_path={out_path}")


if __name__ == "__main__":
    main()
