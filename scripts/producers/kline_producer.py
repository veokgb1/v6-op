#!/usr/bin/env python3
"""
kline_producer.py — V6OP K线形态 Producer

15 种形态纯 pandas 实现，只读本地缓存，输出 V6 Mask JSON。

用法:
  python scripts/producers/kline_producer.py \
    --codes data/ashare_codes.txt \
    --limit 50 \
    --cache-dir var/cache/kline_daily \
    --out output/current/kline_mask.json
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
import traceback
from datetime import datetime
from pathlib import Path

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
    print(f"[{ts}]{color}[KlineProducer][{level}]{RESET} {msg}", flush=True)


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
#  形态检测（向量化）
# ════════════════════════════════════════════════════════════════════

def _body(o: pd.Series, c: pd.Series) -> pd.Series:
    return (c - o).abs()

def _upper_shadow(o: pd.Series, c: pd.Series, h: pd.Series) -> pd.Series:
    return h - pd.concat([o, c], axis=1).max(axis=1)

def _lower_shadow(o: pd.Series, c: pd.Series, l: pd.Series) -> pd.Series:
    return pd.concat([o, c], axis=1).min(axis=1) - l


def detect_hammer(o, h, l, c, sr) -> pd.Series:
    bd = _body(o, c); ls = _lower_shadow(o, c, l); us = _upper_shadow(o, c, h)
    return ((ls >= sr * bd) & (us < bd) & (bd > 0)).astype(int)

def detect_inverted_hammer(o, h, l, c, sr) -> pd.Series:
    bd = _body(o, c); us = _upper_shadow(o, c, h); ls = _lower_shadow(o, c, l)
    return ((us >= sr * bd) & (ls < bd) & (bd > 0)).astype(int)

def detect_shooting_star(o, h, l, c, sr) -> pd.Series:
    bd = _body(o, c); us = _upper_shadow(o, c, h); ls = _lower_shadow(o, c, l)
    uptrend = c.shift(1) > c.shift(2)
    return -((us >= sr * bd) & (ls < bd) & (bd > 0) & uptrend).astype(int)

def detect_engulfing(o, h, l, c) -> pd.Series:
    o1, c1 = o.shift(1), c.shift(1)
    bull = (c1 < o1) & (c > o) & (c >= o1) & (o <= c1)
    bear = (c1 > o1) & (c < o) & (c <= o1) & (o >= c1)
    s = pd.Series(0, index=o.index)
    s[bull] = 1; s[bear] = -1
    return s

def detect_harami(o, h, l, c) -> pd.Series:
    bd = _body(o, c); o1, c1 = o.shift(1), c.shift(1); bd1 = _body(o1, c1)
    top1 = pd.concat([o1, c1], axis=1).max(axis=1)
    bot1 = pd.concat([o1, c1], axis=1).min(axis=1)
    top  = pd.concat([o, c],  axis=1).max(axis=1)
    bot  = pd.concat([o, c],  axis=1).min(axis=1)
    contained = (top <= top1) & (bot >= bot1)
    bull = (c1 < o1) & (bd1 > bd) & contained
    bear = (c1 > o1) & (bd1 > bd) & contained
    s = pd.Series(0, index=o.index)
    s[bull] = 1; s[bear] = -1
    return s

def detect_piercing_line(o, h, l, c) -> pd.Series:
    o1, c1, l1 = o.shift(1), c.shift(1), l.shift(1)
    mid1 = (o1 + c1) / 2
    return ((c1 < o1) & (c > o) & (o < l1) & (c > mid1)).astype(int)

def detect_dark_cloud(o, h, l, c) -> pd.Series:
    o1, c1, h1 = o.shift(1), c.shift(1), h.shift(1)
    mid1 = (o1 + c1) / 2
    return -((c1 > o1) & (c < o) & (o > h1) & (c < mid1)).astype(int)

def detect_morning_star(o, h, l, c) -> pd.Series:
    o1, c1 = o.shift(2), c.shift(2)
    o2, c2 = o.shift(1), c.shift(1)
    rng2 = (h.shift(1) - l.shift(1)).replace(0, np.nan)
    bd2  = _body(o2, c2)
    cond = ((c1 < o1) & (bd2 / rng2 < 0.3) & (h.shift(1) < l.shift(2))
            & (c > o) & (c > (o1 + c1) / 2))
    return cond.fillna(False).astype(int)

def detect_evening_star(o, h, l, c) -> pd.Series:
    o1, c1 = o.shift(2), c.shift(2)
    o2, c2 = o.shift(1), c.shift(1)
    rng2 = (h.shift(1) - l.shift(1)).replace(0, np.nan)
    bd2  = _body(o2, c2)
    cond = ((c1 > o1) & (bd2 / rng2 < 0.3) & (l.shift(1) > h.shift(2))
            & (c < o) & (c < (o1 + c1) / 2))
    return -(cond.fillna(False).astype(int))

def detect_three_white_soldiers(o, h, l, c) -> pd.Series:
    o1, c1 = o.shift(2), c.shift(2)
    o2, c2 = o.shift(1), c.shift(1)
    cond = ((c1 > o1) & (c2 > o2) & (c > o) & (c2 > c1) & (c > c2)
            & (o2 >= o1) & (o2 <= c1) & (o >= o2) & (o <= c2))
    return cond.fillna(False).astype(int)

def detect_three_black_crows(o, h, l, c) -> pd.Series:
    o1, c1 = o.shift(2), c.shift(2)
    o2, c2 = o.shift(1), c.shift(1)
    cond = ((c1 < o1) & (c2 < o2) & (c < o) & (c2 < c1) & (c < c2)
            & (o2 <= o1) & (o2 >= c1) & (o <= o2) & (o >= c2))
    return -(cond.fillna(False).astype(int))


# ── 单股分析 ──────────────────────────────────────────────────────────

def _analyze_one(code: str, df: pd.DataFrame,
                 signal_bars: int, body_pct: float,
                 shadow_ratio: float, pass_neutral: bool) -> dict:
    result: dict = {
        "code":             code,
        "passed":           False,
        "total_score":      0,
        "bull_patterns":    [],
        "bear_patterns":    [],
        "last_signal_date": None,
        "error":            None,
        "adjust":           "hfq",
    }
    try:
        o, h, l, c = df["open"], df["high"], df["low"], df["close"]
        scores = pd.DataFrame(index=df.index)
        scores["hammer"]        = detect_hammer(o, h, l, c, shadow_ratio)
        scores["inv_hammer"]    = detect_inverted_hammer(o, h, l, c, shadow_ratio)
        scores["shooting_star"] = detect_shooting_star(o, h, l, c, shadow_ratio)
        scores["engulfing"]     = detect_engulfing(o, h, l, c)
        scores["harami"]        = detect_harami(o, h, l, c)
        scores["piercing"]      = detect_piercing_line(o, h, l, c)
        scores["dark_cloud"]    = detect_dark_cloud(o, h, l, c)
        scores["morning_star"]  = detect_morning_star(o, h, l, c)
        scores["evening_star"]  = detect_evening_star(o, h, l, c)
        scores["three_white"]   = detect_three_white_soldiers(o, h, l, c)
        scores["three_black"]   = detect_three_black_crows(o, h, l, c)

        total        = scores.sum(axis=1)
        window_total = int(total.iloc[-signal_bars:].sum())
        w_scores     = scores.iloc[-signal_bars:]
        w_total_s    = total.iloc[-signal_bars:]

        nonzero = w_total_s[w_total_s != 0]
        last_date = None
        if not nonzero.empty:
            last_idx  = nonzero.index[-1]
            last_date = last_idx.strftime("%Y-%m-%d") if hasattr(last_idx, "strftime") else str(last_idx)

        bull_pats, bear_pats = [], []
        for pat, col in [("锤子线","hammer"), ("倒锤子线","inv_hammer"),
                         ("吞没(多)","engulfing"), ("孕线(多)","harami"),
                         ("刺穿线","piercing"), ("晨星","morning_star"),
                         ("三白兵","three_white")]:
            if w_scores[col].gt(0).any():
                bull_pats.append(pat)
        for pat, col in [("射击之星","shooting_star"), ("乌云盖顶","dark_cloud"),
                         ("吞没(空)","engulfing"), ("孕线(空)","harami"),
                         ("暮星","evening_star"), ("三乌鸦","three_black")]:
            if w_scores[col].lt(0).any():
                bear_pats.append(pat)

        threshold = 0 if pass_neutral else 1
        result["passed"]           = bool(window_total >= threshold)
        result["total_score"]      = window_total
        result["bull_patterns"]    = bull_pats
        result["bear_patterns"]    = bear_pats
        result["last_signal_date"] = last_date

    except Exception as exc:
        result["error"] = str(exc)
        _log("WARN", f"  {code} 异常: {exc}")

    return result


def _make_mask_id(codes: list[str], params: dict) -> str:
    key = json.dumps(sorted(codes) + [params], sort_keys=True, ensure_ascii=False)
    return "kline_" + hashlib.sha1(key.encode()).hexdigest()[:12]


# ── 主逻辑 ────────────────────────────────────────────────────────────

def run(
    codes: list[str],
    cache_dir: Path,
    signal_bars: int = 5,
    body_pct: float = 0.1,
    shadow_ratio: float = 2.0,
    pass_neutral: bool = False,
    days: int = 365,
    out: Path | None = None,
) -> dict:
    os.environ["READ_CACHE_ONLY"] = "true"
    os.environ.pop("FAST_FULL_SCAN", None)

    from ohlcv_provider import fetch_ohlcv

    t0 = time.time()
    params = {"signal_bars": signal_bars, "body_pct": body_pct,
              "shadow_ratio": shadow_ratio, "pass_neutral": pass_neutral, "days": days}

    hit_codes:  list[str] = []
    miss_codes: list[str] = []
    evidence:   dict      = {}

    _log("HEAD",
         f"{'='*55}\nKlineProducer  bars={signal_bars}  shadow={shadow_ratio}  body={body_pct}\n{'='*55}")

    for i, code in enumerate(codes, 1):
        df = fetch_ohlcv(code, days=days, verbose=False)
        if df is None:
            miss_codes.append(code)
            evidence[code] = {"status": "cache_miss", "adjust": "hfq"}
            continue

        res = _analyze_one(code, df, signal_bars, body_pct, shadow_ratio, pass_neutral)

        if res.get("error"):
            miss_codes.append(code)
            evidence[code] = {"status": "error", "error": res["error"], "adjust": "hfq"}
            continue

        if res["passed"]:
            hit_codes.append(code)
            evidence[code] = {
                "status":           "hit",
                "total_score":      res["total_score"],
                "bull_patterns":    res["bull_patterns"],
                "bear_patterns":    res["bear_patterns"],
                "last_signal_date": res["last_signal_date"],
                "adjust":           "hfq",
            }
        else:
            miss_codes.append(code)
            evidence[code] = {
                "status":      "no_bullish",
                "total_score": res["total_score"],
                "adjust":      "hfq",
            }

        if i % 10 == 0 or i == len(codes):
            _log("INFO", f"进度 {i}/{len(codes)}  hit={len(hit_codes)}")

    elapsed = time.time() - t0
    mask_id = _make_mask_id(codes, params)

    result = {
        "mask_id":       mask_id,
        "producer":      "KlineProducer",
        "skill_id":      "kline",
        "skill_name":    "K线形态",
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
         f"\n{'='*55}\nKline完成  {len(codes)} 只 → hit={len(hit_codes)} miss={len(miss_codes)}  "
         f"{elapsed:.1f}s\n{'='*55}")

    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        _log("INFO", f"kline_mask.json → {out}")

    return result


def main() -> None:
    import io as _io
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="V6OP K线形态 Producer")
    parser.add_argument("--codes",        required=True)
    parser.add_argument("--limit",        type=int, default=0)
    parser.add_argument("--cache-dir",    default="var/cache/kline_daily")
    parser.add_argument("--out",          default="output/current/kline_mask.json")
    parser.add_argument("--signal-bars",  type=int,   default=5)
    parser.add_argument("--body-pct",     type=float, default=0.1)
    parser.add_argument("--shadow-ratio", type=float, default=2.0)
    parser.add_argument("--days",         type=int,   default=365)
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
        body_pct=args.body_pct, shadow_ratio=args.shadow_ratio, days=args.days, out=out)


if __name__ == "__main__":
    main()
