#!/usr/bin/env python3
"""
czsc_producer.py — V6OP 缠论买点 Producer

输入: 股票代码列表 + 本地缓存路径 + 参数
模式: READ_CACHE_ONLY（不触网，只读本地 pickle）
检测: CZSC 买点（一买/二买/三买）
输出: V6 Mask JSON

用法:
  python scripts/producers/czsc_producer.py \
    --codes data/ashare_codes.txt \
    --limit 50 \
    --cache-dir var/cache/kline_daily \
    --out output/current/czsc_mask.json
"""
from __future__ import annotations

ALGO_VERSION = "1.0.0"

import argparse
import hashlib
import io
import json
import os
import re
import sys
import time
import traceback
import warnings
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── 路径设置 ──────────────────────────────────────────────────────────
_PRODUCERS_DIR = Path(__file__).parent.resolve()
_SCRIPTS_DIR = _PRODUCERS_DIR.parent
_PROJECT_ROOT = _SCRIPTS_DIR.parent

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# ── V6 合约 (可选) ────────────────────────────────────────────────────
try:
    from v6_compat import v6_available, _V6_IMPORT_ERROR
    _HAS_V6 = v6_available()
except ImportError:
    _HAS_V6 = False
    _V6_IMPORT_ERROR = "v6_compat 未找到"

# ── CZSC 库 ───────────────────────────────────────────────────────────
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=r"Call to deprecated function.*cxt_third_bs.*",
)

_CZSC_AVAILABLE = False
_CZSC_IMPORT_ERROR: str | None = None

try:
    import czsc as _czsc_mod
    _czsc_ver = getattr(_czsc_mod, "__version__", "unknown")
    from czsc import CZSC, RawBar, Freq, ZS
    from czsc.signals.cxt import (
        cxt_first_buy_V221126,
        cxt_second_bs_V230320,
        cxt_third_bs_V230318,
        cxt_third_bs_V230319,
        cxt_three_bi_V230618,
        cxt_five_bi_V230619,
        cxt_bi_base_V230228,
    )
    _CZSC_AVAILABLE = True
except ImportError as e:
    _CZSC_IMPORT_ERROR = str(e)
except Exception as e:
    _CZSC_IMPORT_ERROR = f"czsc 初始化异常: {e}"

# ── 代码文件读取 ───────────────────────────────────────────────────────
_CODE_PATTERN = re.compile(r"\b\d{6}\.(?:SZ|SH|BJ)\b", re.IGNORECASE)


def _read_codes_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8-sig")
    seen: set[str] = set()
    codes: list[str] = []
    for code in _CODE_PATTERN.findall(text):
        key = code.strip().upper()
        if key and key not in seen:
            seen.add(key)
            codes.append(key)
    return codes


# ── 颜色日志 ──────────────────────────────────────────────────────────
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"


def _log(level: str, msg: str) -> None:
    color = {"INFO": GREEN, "WARN": YELLOW, "ERROR": RED, "HEAD": CYAN}.get(level, RESET)
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}]{color}[CZSC][{level}]{RESET} {msg}", flush=True)


# ── CZSC 分析核心 ─────────────────────────────────────────────────────

def _get_all_signals(c: "CZSC") -> dict:
    s: dict = {}
    s.update(cxt_first_buy_V221126(c, di=1))
    s.update(cxt_second_bs_V230320(c, di=1, ma_type="SMA", timeperiod=20))
    s.update(cxt_third_bs_V230318(c, di=1, ma_type="SMA", timeperiod=20))
    s.update(cxt_third_bs_V230319(c, di=1, ma_type="SMA", timeperiod=20))
    s.update(cxt_three_bi_V230618(c, di=1))
    s.update(cxt_five_bi_V230619(c, di=1))
    s.update(cxt_bi_base_V230228(c, di=1))
    return s


def _detect_buy_type(signals: dict) -> str:
    if not signals:
        return ""
    for k, v in signals.items():
        if "BUY1" in k and "一买" in str(v):
            return "一买"
    for k, v in signals.items():
        if "三笔" in k and "向上盘背" in str(v):
            return "一买(三笔盘背)"
    for k, v in signals.items():
        if "五笔" in k and "类一买" in str(v):
            return "一买(五笔类)"
    for k, v in signals.items():
        if ("second_bs" in k.lower() or "BS2" in k) and "二买" in str(v):
            return "二买"
    for v in signals.values():
        if "二买" in str(v):
            return "二买"
    for k, v in signals.items():
        if ("third_bs" in k.lower() or "BS3" in k) and "三买" in str(v):
            return "三买"
    for v in signals.values():
        if "三买" in str(v):
            return "三买"
    return ""


def _buy_type_matches(detected: str, filter_type: str) -> bool:
    if filter_type == "all":
        return bool(detected)
    if filter_type == "1":
        return detected.startswith("一买")
    if filter_type == "2":
        return detected == "二买"
    if filter_type == "3":
        return detected == "三买"
    return False


def _df_to_bars(df: "pd.DataFrame", symbol: str) -> list:
    bars = []
    for i, (dt, row) in enumerate(df.iterrows()):
        import pandas as pd
        if not isinstance(dt, datetime):
            dt = pd.Timestamp(dt).to_pydatetime()
        bars.append(RawBar(
            symbol=symbol,
            id=i,
            dt=dt,
            freq=Freq.D,
            open=float(row["open"]),
            close=float(row["close"]),
            high=float(row["high"]),
            low=float(row["low"]),
            vol=float(row.get("volume", row.get("vol", 0))),
            amount=float(row.get("amount", 0)),
        ))
    return bars


def _analyze_one(code: str, signal_bars: int, buy_type_filter: str) -> dict:
    """对单只股票执行缠论分析，返回结果字典。仅读缓存，不触网。"""
    from ohlcv_provider import fetch_ohlcv

    result: dict = {
        "code": code,
        "passed": False,
        "buy_type_found": "",
        "last_signal_date": None,
        "bi_count": 0,
        "bars_used": 0,
        "buy_events": [],
        "error": None,
    }

    df = fetch_ohlcv(code, days=365, verbose=False)
    if df is None or df.empty:
        result["error"] = "缓存未命中（READ_CACHE_ONLY 模式，无本地缓存）"
        return result

    result["bars_used"] = len(df)
    if len(df) < 50:
        result["error"] = f"K线不足（{len(df)} 根 < 50）"
        return result

    bars = _df_to_bars(df, code)
    c = CZSC(bars[:30])
    buy_events: list[dict] = []

    for bar in bars[30:]:
        c.update(bar)
        sigs = _get_all_signals(c)
        buy_type = _detect_buy_type(sigs)
        if buy_type and _buy_type_matches(buy_type, buy_type_filter):
            buy_events.append({
                "dt": bar.dt.strftime("%Y-%m-%d"),
                "bar_idx": bar.id,
                "buy_type": buy_type,
                "close": bar.close,
            })

    result["bi_count"] = len(c.bi_list)

    all_bar_ids = [b.id for b in bars]
    recent_start = all_bar_ids[-signal_bars] if len(all_bar_ids) >= signal_bars else 0
    recent_events = [e for e in buy_events if e["bar_idx"] >= recent_start]

    if recent_events:
        last = recent_events[-1]
        result["passed"] = True
        result["buy_type_found"] = last["buy_type"]
        result["last_signal_date"] = last["dt"]

    result["buy_events"] = buy_events[-5:]
    return result


# ── Mask JSON 构建 ────────────────────────────────────────────────────

def _make_mask_id(codes: list[str], params: dict) -> str:
    payload = json.dumps({"codes": sorted(codes), "params": params}, sort_keys=True)
    return "czsc_" + hashlib.sha256(payload.encode()).hexdigest()[:12]


def _build_mask_json(
    codes: list[str],
    results: list[dict],
    params: dict,
    cache_dir: str,
    data_mode: str,
    czsc_available: bool,
) -> dict:
    hit_codes = [r["code"] for r in results if r.get("passed")]
    miss_codes = [r["code"] for r in results if not r.get("passed")]
    evidence: dict = {}
    for r in results:
        if r.get("passed"):
            evidence[r["code"]] = {
                "buy_type": r.get("buy_type_found", ""),
                "last_signal_date": r.get("last_signal_date"),
                "bi_count": r.get("bi_count", 0),
                "bars_used": r.get("bars_used", 0),
                "buy_events": r.get("buy_events", []),
            }
        elif r.get("error"):
            evidence[r["code"]] = {"error": r["error"]}

    mask_id = _make_mask_id(codes, params)
    return {
        "mask_id": mask_id,
        "producer": "czsc_producer",
        "hit_semantics": "positive",
        "hit_codes": hit_codes,
        "miss_codes": miss_codes,
        "evidence": evidence,
        "params": params,
        "data_mode": data_mode,
        "cache_dir": cache_dir,
        "generated_at": datetime.now().isoformat(),
        "czsc_available": czsc_available,
        "czsc_version": getattr(_czsc_mod, "__version__", "unknown") if _CZSC_AVAILABLE else None,
        "czsc_import_error": _CZSC_IMPORT_ERROR if not _CZSC_AVAILABLE else None,
        "total_in": len(codes),
        "hit_count": len(hit_codes),
        "miss_count": len(miss_codes),
    }


# ── 可调用 run() ─────────────────────────────────────────────────────

def run(
    codes: list[str],
    cache_dir: "Path | None" = None,
    signal_bars: int = 5,
    buy_type: str = "all",
    days: int = 365,
    out: "Path | None" = None,
) -> dict:
    """以库函数方式调用 CZSC Producer，返回 mask JSON dict。"""
    import os
    from pathlib import Path as _Path

    if cache_dir is None:
        cache_dir = _PROJECT_ROOT / "var" / "cache" / "kline_daily"

    os.environ["READ_CACHE_ONLY"] = "true"
    os.environ["KLINE_CACHE_DIR"] = str(cache_dir)

    params = {"signal_bars": signal_bars, "buy_type": buy_type, "kline_days": days}

    if not _CZSC_AVAILABLE:
        mask_json = _build_mask_json(
            codes=codes, results=[], params=params,
            cache_dir=str(cache_dir), data_mode="czsc_unavailable",
            czsc_available=False,
        )
    else:
        results: list[dict] = []
        for code in codes:
            try:
                res = _analyze_one(code, signal_bars, buy_type)
            except Exception as exc:
                res = {"code": code, "passed": False, "error": str(exc)}
            results.append(res)

        mask_json = _build_mask_json(
            codes=codes, results=results, params=params,
            cache_dir=str(cache_dir), data_mode="read_cache_only",
            czsc_available=True,
        )

    if out is not None:
        _Path(out).parent.mkdir(parents=True, exist_ok=True)
        _Path(out).write_text(
            __import__("json").dumps(mask_json, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return mask_json


# ── 主入口 ────────────────────────────────────────────────────────────

def main() -> None:
    # Windows 控制台 UTF-8（只在直接运行时设置，不影响 import）
    import io as _io
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="V6OP 缠论买点 Producer")
    parser.add_argument("--codes", required=True, help="股票代码文件路径")
    parser.add_argument("--limit", type=int, default=0, help="最多处理前 N 只 (0=全部)")
    parser.add_argument("--cache-dir", default="var/cache/kline_daily", help="K线缓存目录")
    parser.add_argument("--out", default="output/current/czsc_mask.json", help="输出 Mask JSON 路径")
    parser.add_argument("--signal-bars", type=int, default=5, help="近 N 根 K 线内有信号才晋级")
    parser.add_argument("--buy-type", default="all", choices=["all", "1", "2", "3"],
                        help="买点类型过滤: all | 1 | 2 | 3")
    args = parser.parse_args()

    codes_path = Path(args.codes)
    if not codes_path.is_absolute():
        codes_path = _PROJECT_ROOT / codes_path
    if not codes_path.exists():
        print(f"[ERROR] 代码文件不存在: {codes_path}", flush=True)
        sys.exit(1)

    codes = _read_codes_file(codes_path)
    if args.limit > 0:
        codes = codes[: args.limit]

    cache_dir = Path(args.cache_dir)
    if not cache_dir.is_absolute():
        cache_dir = _PROJECT_ROOT / cache_dir

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = _PROJECT_ROOT / out_path

    params = {
        "signal_bars": args.signal_bars,
        "buy_type": args.buy_type,
        "kline_days": 365,
    }

    _log("HEAD",
         f"{'='*60}\n"
         f"V6OP 缠论买点 Producer\n"
         f"  codes={len(codes)}  signal_bars={args.signal_bars}  buy_type={args.buy_type}\n"
         f"  cache_dir={cache_dir}\n"
         f"  czsc 可用={_CZSC_AVAILABLE}"
         + (f"  版本={_czsc_mod.__version__}" if _CZSC_AVAILABLE else f"  错误={_CZSC_IMPORT_ERROR}")
         + f"\n{'='*60}")

    # 强制 READ_CACHE_ONLY
    os.environ["READ_CACHE_ONLY"] = "true"
    os.environ["KLINE_CACHE_DIR"] = str(cache_dir)

    # 如果 czsc 不可用，生成空 Mask 并报告阻断
    if not _CZSC_AVAILABLE:
        _log("ERROR", f"czsc 不可用，无法执行买点检测: {_CZSC_IMPORT_ERROR}")
        _log("WARN", "输出空 Mask JSON (data_mode=czsc_unavailable)")
        mask_json = _build_mask_json(
            codes=codes,
            results=[],
            params=params,
            cache_dir=str(cache_dir),
            data_mode="czsc_unavailable",
            czsc_available=False,
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(mask_json, ensure_ascii=False, indent=2), encoding="utf-8")
        _log("INFO", f"空 Mask → {out_path}")
        _log("ERROR",
             "阻断点: czsc 库未安装或不兼容当前 Python 版本\n"
             "  建议: pip install czsc==0.9.68\n"
             "  如与 Python 3.13 不兼容，请在报告中记录")
        sys.exit(2)

    # 执行分析
    hit_codes: list[str] = []
    miss_codes: list[str] = []
    results: list[dict] = []
    t0 = time.time()

    for i, code in enumerate(codes, 1):
        try:
            res = _analyze_one(code, args.signal_bars, args.buy_type)
        except Exception as exc:
            res = {
                "code": code,
                "passed": False,
                "buy_type_found": "",
                "last_signal_date": None,
                "bi_count": 0,
                "bars_used": 0,
                "buy_events": [],
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
        results.append(res)

        if res.get("passed"):
            hit_codes.append(code)
            _log("INFO",
                 f"[{i}/{len(codes)}] {GREEN}[晋级]{RESET} {code} "
                 f"买点={res['buy_type_found']} "
                 f"信号日={res['last_signal_date']} "
                 f"笔数={res['bi_count']}")
        elif res.get("error"):
            _log("WARN", f"[{i}/{len(codes)}] {code} ⚠ {res['error']}")
        else:
            _log("WARN",
                 f"[{i}/{len(codes)}] {code} 近{args.signal_bars}根K线无买点  "
                 f"笔数={res.get('bi_count', 0)}")

    mask_json = _build_mask_json(
        codes=codes,
        results=results,
        params=params,
        cache_dir=str(cache_dir),
        data_mode="read_cache_only",
        czsc_available=True,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(mask_json, ensure_ascii=False, indent=2), encoding="utf-8")

    elapsed = time.time() - t0
    _log("HEAD",
         f"\n{'='*60}\n"
         f"CZSC Producer 完成 ✓  {len(codes)} → 命中 {len(hit_codes)} 只\n"
         f"  miss={len([r for r in results if not r.get('passed')])}  "
         f"耗时={elapsed:.1f}s\n"
         f"  输出 → {out_path}\n"
         f"{'='*60}")


if __name__ == "__main__":
    main()
