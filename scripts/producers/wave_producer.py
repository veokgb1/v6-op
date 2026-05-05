#!/usr/bin/env python3
"""
wave_producer.py — V6OP 波浪分析 Producer

Zigzag 摆动点 + Elliott Wave 5浪/ABC 结构，纯 pandas/numpy。
只读本地缓存，输出 V6 Mask JSON。

用法:
  python scripts/producers/wave_producer.py \
    --codes data/ashare_codes.txt \
    --limit 50 \
    --cache-dir var/cache/kline_daily \
    --out output/current/wave_mask.json
"""
from __future__ import annotations

ALGO_VERSION = "1.0.0"

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# ── 路径 ──────────────────────────────────────────────────────────────
_PRODUCERS_DIR = Path(__file__).parent.resolve()
_SCRIPTS_DIR   = _PRODUCERS_DIR.parent
_PROJECT_ROOT  = _SCRIPTS_DIR.parent

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# ── 颜色日志 ──────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
RESET  = "\033[0m"


def _log(level: str, msg: str) -> None:
    color = {"INFO": GREEN, "WARN": YELLOW, "ERROR": RED, "HEAD": CYAN}.get(level, RESET)
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}]{color}[WaveProducer][{level}]{RESET} {msg}", flush=True)


_CODE_PATTERN = re.compile(r"\b\d{6}\.(?:SZ|SH|BJ)\b", re.IGNORECASE)


def _read_codes(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8-sig")
    seen: set[str] = set()
    codes: list[str] = []
    for c in _CODE_PATTERN.findall(text):
        k = c.strip().upper()
        if k not in seen:
            seen.add(k)
            codes.append(k)
    return codes


# ════════════════════════════════════════════════════════════════════
#  Elliott Wave 引擎（从 V5 step8_wave_analysis.py 移植）
# ════════════════════════════════════════════════════════════════════

def _find_swings(high: pd.Series, low: pd.Series, window: int) -> List[Dict]:
    full_w = window * 2 + 1
    if len(high) < full_w:
        return []
    roll_max = high.rolling(full_w, center=True).max()
    roll_min = low.rolling(full_w, center=True).min()
    sh_mask  = high == roll_max
    sl_mask  = low  == roll_min

    raw = []
    for idx in high.index:
        is_h = bool(sh_mask.get(idx, False))
        is_l = bool(sl_mask.get(idx, False))
        if is_h and not is_l:
            raw.append({"index": idx, "price": float(high[idx]), "type": "H"})
        elif is_l and not is_h:
            raw.append({"index": idx, "price": float(low[idx]),  "type": "L"})

    if len(raw) < 2:
        return raw

    zigzag = [raw[0]]
    for pt in raw[1:]:
        if pt["type"] == zigzag[-1]["type"]:
            if pt["type"] == "H" and pt["price"] > zigzag[-1]["price"]:
                zigzag[-1] = pt
            elif pt["type"] == "L" and pt["price"] < zigzag[-1]["price"]:
                zigzag[-1] = pt
        else:
            zigzag.append(pt)
    return zigzag


def _check_fib(w1: float, w2: float, w3: float, w4: float, w5: float, tol: float) -> bool:
    if w1 == 0 or w3 == 0:
        return False
    if not (0.5 - tol <= w2 / w1 <= 0.618 + tol):
        return False
    if not (1.0 - tol <= w3 / w1 <= 2.618 + tol):
        return False
    if not (0.236 - tol <= w4 / w3 <= 0.5 + tol):
        return False
    return True


def _min_bars_ok(swings: List[Dict], start: int, count: int, min_bars: int) -> bool:
    for i in range(start, start + count - 1):
        a, b = swings[i]["index"], swings[i + 1]["index"]
        try:
            diff = abs((b - a).days)
        except Exception:
            diff = abs(float(b) - float(a))
        if diff < min_bars:
            return False
    return True


def _find_impulse(swings: List[Dict], tol: float, min_bars: int) -> List[Tuple]:
    results = []
    for i in range(len(swings) - 5):
        types = [s["type"] for s in swings[i:i+6]]

        if types == ["L", "H", "L", "H", "L", "H"]:
            x, p1, p2, p3, p4, p5 = swings[i:i+6]
            w1 = p1["price"] - x["price"]
            w2 = p1["price"] - p2["price"]
            w3 = p3["price"] - p2["price"]
            w4 = p3["price"] - p4["price"]
            w5 = p5["price"] - p4["price"]
            if w1 <= 0 or w3 <= 0 or w5 <= 0:            continue
            if p2["price"] <= x["price"]:                 continue
            if w3 < w1 and w3 < w5:                       continue
            if p4["price"] <= p1["price"]:                continue
            if not _min_bars_ok(swings, i, 6, min_bars):  continue
            if not _check_fib(w1, w2, w3, w4, w5, tol):  continue
            results.append((p5["index"], -1, "5浪上升完成"))

        elif types == ["H", "L", "H", "L", "H", "L"]:
            x, p1, p2, p3, p4, p5 = swings[i:i+6]
            w1 = x["price"]  - p1["price"]
            w2 = p2["price"] - p1["price"]
            w3 = p2["price"] - p3["price"]
            w4 = p4["price"] - p3["price"]
            w5 = p4["price"] - p5["price"]
            if w1 <= 0 or w3 <= 0 or w5 <= 0:            continue
            if p2["price"] >= x["price"]:                 continue
            if w3 < w1 and w3 < w5:                       continue
            if p4["price"] >= p1["price"]:                continue
            if not _min_bars_ok(swings, i, 6, min_bars):  continue
            if not _check_fib(w1, w2, w3, w4, w5, tol):  continue
            results.append((p5["index"], 1, "5浪下降完成"))

    return results


def _find_abc(swings: List[Dict], tol: float, min_bars: int) -> List[Tuple]:
    results = []
    for i in range(len(swings) - 3):
        types = [s["type"] for s in swings[i:i+4]]

        if types == ["H", "L", "H", "L"]:
            s0, pa, pb, pc = swings[i:i+4]
            wa = s0["price"] - pa["price"]
            wb = pb["price"] - pa["price"]
            wc = pb["price"] - pc["price"]
            if wa <= 0 or wb <= 0 or wc <= 0:                     continue
            if pb["price"] >= s0["price"]:                        continue
            if not (0.382 - tol <= wb / wa <= 0.618 + tol):       continue
            if not (0.618 - tol <= wc / wa <= 1.618 + tol):       continue
            if not _min_bars_ok(swings, i, 4, min_bars):          continue
            results.append((pc["index"], 1, "ABC下调完成"))

        elif types == ["L", "H", "L", "H"]:
            s0, pa, pb, pc = swings[i:i+4]
            wa = pa["price"] - s0["price"]
            wb = pa["price"] - pb["price"]
            wc = pc["price"] - pb["price"]
            if wa <= 0 or wb <= 0 or wc <= 0:                     continue
            if pb["price"] <= s0["price"]:                        continue
            if not (0.382 - tol <= wb / wa <= 0.618 + tol):       continue
            if not (0.618 - tol <= wc / wa <= 1.618 + tol):       continue
            if not _min_bars_ok(swings, i, 4, min_bars):          continue
            results.append((pc["index"], -1, "ABC上调完成"))

    return results


def _compute_wave_signals(df: pd.DataFrame, swing_window: int,
                          fib_tol: float, min_wave_bars: int) -> pd.DataFrame:
    result = pd.DataFrame({"signal": 0, "desc": ""}, index=df.index)
    swings = _find_swings(df["high"], df["low"], swing_window)
    if len(swings) < 4:
        return result

    all_events: List[Tuple] = []
    if len(swings) >= 6:
        all_events.extend(_find_impulse(swings, fib_tol, min_wave_bars))
    all_events.extend(_find_abc(swings, fib_tol, min_wave_bars))

    for idx, sig, desc in all_events:
        if idx in result.index:
            result.at[idx, "signal"] = sig
            result.at[idx, "desc"]   = desc
    return result


def _analyze_one(code: str, df: pd.DataFrame,
                 signal_bars: int, swing_window: int,
                 fib_tol: float, min_wave_bars: int = 5) -> dict:
    result: dict = {
        "code":              code,
        "passed":            False,
        "verdict":           "",
        "last_signal":       None,
        "all_signals_count": 0,
        "error":             None,
        "adjust":            "hfq",
    }
    try:
        wave_df = _compute_wave_signals(df, swing_window, fib_tol, min_wave_bars)
        recent  = wave_df.iloc[-signal_bars:]

        result["all_signals_count"] = int((wave_df["signal"] != 0).sum())

        nonzero  = recent[recent["signal"] != 0]
        last_sig = None
        if not nonzero.empty:
            row = nonzero.iloc[-1]
            last_sig = {
                "date":   row.name.strftime("%Y-%m-%d") if hasattr(row.name, "strftime") else str(row.name),
                "signal": int(row["signal"]),
                "desc":   str(row["desc"]),
            }
        result["last_signal"] = last_sig

        recent_neg = bool((recent["signal"] == -1).any())
        recent_pos = bool((recent["signal"] == 1).any())

        if recent_neg:
            result["passed"]  = False
            result["verdict"] = "blocked_5wave"
        elif recent_pos:
            result["passed"]  = True
            result["verdict"] = "abc_bottom"
        else:
            result["passed"]  = True
            result["verdict"] = "no_top"

    except Exception as exc:
        result["error"]  = str(exc)
        result["passed"] = False
        _log("WARN", f"  {code} 异常: {exc}")

    return result


def _make_mask_id(codes: list[str], params: dict) -> str:
    key = json.dumps(sorted(codes) + [params], sort_keys=True, ensure_ascii=False)
    return "wave_" + hashlib.sha1(key.encode()).hexdigest()[:12]


# ── 主逻辑 ────────────────────────────────────────────────────────────

def run(
    codes: list[str],
    cache_dir: Path,
    signal_bars: int = 20,
    swing_window: int = 10,
    fib_tolerance: float = 0.15,
    days: int = 365,
    out: Path | None = None,
) -> dict:
    os.environ["READ_CACHE_ONLY"] = "true"
    os.environ.pop("FAST_FULL_SCAN", None)

    from ohlcv_provider import fetch_ohlcv

    t0 = time.time()
    params = {"signal_bars": signal_bars, "swing_window": swing_window,
              "fib_tolerance": fib_tolerance, "days": days}

    hit_codes:  list[str] = []
    miss_codes: list[str] = []
    evidence:   dict      = {}

    _log("HEAD",
         f"{'='*55}\nWaveProducer  swing={swing_window}  fib_tol={fib_tolerance}  bars={signal_bars}\n{'='*55}")

    for i, code in enumerate(codes, 1):
        df = fetch_ohlcv(code, days=days, verbose=False)
        if df is None:
            miss_codes.append(code)
            evidence[code] = {"status": "cache_miss", "adjust": "hfq"}
            continue

        res = _analyze_one(code, df, signal_bars, swing_window, fib_tolerance)

        if res.get("error"):
            miss_codes.append(code)
            evidence[code] = {"status": "error", "error": res["error"], "adjust": "hfq"}
            continue

        if res["passed"]:
            hit_codes.append(code)
            evidence[code] = {
                "status":  "hit",
                "verdict": res["verdict"],
                "last_signal": res["last_signal"],
                "all_signals_count": res["all_signals_count"],
                "adjust":  "hfq",
            }
        else:
            miss_codes.append(code)
            evidence[code] = {
                "status":  "blocked_5wave",
                "last_signal": res["last_signal"],
                "adjust":  "hfq",
            }

        if i % 10 == 0 or i == len(codes):
            _log("INFO", f"进度 {i}/{len(codes)}  hit={len(hit_codes)}")

    elapsed = time.time() - t0
    mask_id = _make_mask_id(codes, params)

    result = {
        "mask_id":       mask_id,
        "producer":      "WaveProducer",
        "skill_id":      "wave",
        "skill_name":    "波浪分析",
        "hit_semantics": "positive",
        "hit_codes":     hit_codes,
        "miss_codes":    miss_codes,
        "evidence":      evidence,
        "params":        params,
        "data_mode":     "read_cache_only",
        "data_requirement": "kline_daily",
        "adjust":        "hfq",
        "hit_count":     len(hit_codes),
        "miss_count":    len(miss_codes),
        "duration_seconds": round(elapsed, 1),
        "generated_at":  datetime.now().isoformat(),
    }

    _log("HEAD",
         f"\n{'='*55}\nWave完成  {len(codes)} 只 → hit={len(hit_codes)} miss={len(miss_codes)}  "
         f"{elapsed:.1f}s\n{'='*55}")

    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        _log("INFO", f"wave_mask.json → {out}")

    return result


def main() -> None:
    import io as _io
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="V6OP 波浪分析 Producer")
    parser.add_argument("--codes",         required=True)
    parser.add_argument("--limit",         type=int,   default=0)
    parser.add_argument("--cache-dir",     default="var/cache/kline_daily")
    parser.add_argument("--out",           default="output/current/wave_mask.json")
    parser.add_argument("--signal-bars",   type=int,   default=20)
    parser.add_argument("--swing-window",  type=int,   default=10)
    parser.add_argument("--fib-tolerance", type=float, default=0.15)
    parser.add_argument("--days",          type=int,   default=365)
    args = parser.parse_args()

    codes_path = Path(args.codes)
    if not codes_path.is_absolute():
        codes_path = _PROJECT_ROOT / codes_path
    codes = _read_codes(codes_path)
    if args.limit > 0:
        codes = codes[:args.limit]

    cache_dir = Path(args.cache_dir)
    if not cache_dir.is_absolute():
        cache_dir = _PROJECT_ROOT / cache_dir
    os.environ["KLINE_CACHE_DIR"] = str(cache_dir)

    out = Path(args.out)
    if not out.is_absolute():
        out = _PROJECT_ROOT / out

    run(codes=codes, cache_dir=cache_dir, signal_bars=args.signal_bars,
        swing_window=args.swing_window, fib_tolerance=args.fib_tolerance,
        days=args.days, out=out)


if __name__ == "__main__":
    main()
