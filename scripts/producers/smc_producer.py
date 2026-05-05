#!/usr/bin/env python3
"""
smc_producer.py — V6OP SMC 聪明钱 Producer

只读本地缓存，检测 BOS / ChoCH / FVG，输出 V6 Mask JSON。
依赖: smartmoneyconcepts

用法:
  python scripts/producers/smc_producer.py \
    --codes data/ashare_codes.txt \
    --limit 50 \
    --cache-dir var/cache/kline_daily \
    --out output/current/smc_mask.json
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
from typing import Optional

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
    print(f"[{ts}]{color}[SMCProducer][{level}]{RESET} {msg}", flush=True)


# ── SMC 库检查 ────────────────────────────────────────────────────────
# smartmoneyconcepts.__init__ 在导入时向 stdout 打印 ⭐ (U+2B50)。
# 在 Windows GBK 终端下此操作触发 UnicodeEncodeError，导致整个模块加载失败。
# 修复：用 redirect_stdout 捕获导入时的所有输出，对所有异常做 safe fallback。
import contextlib as _contextlib
import io as _io

_SMC_AVAILABLE = False
_SMC_IMPORT_ERROR: str | None = None
_smc = None  # type: ignore

try:
    with _contextlib.redirect_stdout(_io.StringIO()):
        from smartmoneyconcepts import smc as _smc  # type: ignore
    _SMC_AVAILABLE = True
except (ImportError, UnicodeEncodeError, Exception) as _e:
    _SMC_IMPORT_ERROR = str(_e)


# ── 代码文件读取 ──────────────────────────────────────────────────────
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


# ── SMC 核心分析 ──────────────────────────────────────────────────────

def _compute_smc(df, swing_length: int, close_break: bool) -> dict | None:
    import numpy as np
    import pandas as pd

    min_bars = swing_length * 2
    if len(df) < min_bars:
        return None

    ohlc = df[["open", "high", "low", "close", "volume"]].copy()
    # baostock 返回的列可能为字符串类型，强制转数值；转失败的行丢弃
    for _col in ["open", "high", "low", "close", "volume"]:
        ohlc[_col] = pd.to_numeric(ohlc[_col], errors="coerce")
    ohlc = ohlc.dropna(subset=["open", "high", "low", "close"])
    if len(ohlc) < min_bars:
        return None

    swing_hl  = _smc.swing_highs_lows(ohlc, swing_length=swing_length)
    bos_choch = _smc.bos_choch(ohlc, swing_highs_lows=swing_hl, close_break=close_break)
    fvg_df    = _smc.fvg(ohlc)

    bos_val   = bos_choch["BOS"].fillna(0).astype(int)
    choch_val = bos_choch["CHOCH"].fillna(0).astype(int)
    fvg_val   = fvg_df["FVG"].fillna(0).astype(int)

    # smartmoneyconcepts 可能将结果的 index 重置为 RangeIndex；
    # 若长度吻合则恢复 ohlc 的 DatetimeIndex，确保 last_signal_date 是日期字符串而非整数。
    if len(bos_val) == len(ohlc) and not isinstance(bos_val.index, pd.DatetimeIndex):
        bos_val.index   = ohlc.index
        choch_val.index = ohlc.index
        fvg_val.index   = ohlc.index

    structure = choch_val.where(choch_val != 0, bos_val)
    buy  = (structure == 1)  & (fvg_val >= 0)
    sell = (structure == -1) & (fvg_val <= 0)
    signal = buy.astype(int) - sell.astype(int)

    return {
        "signal_series": signal,
        "choch_series":  choch_val,
        "bos_series":    bos_val,
        "fvg_series":    fvg_val,
    }


def _analyze_one(code: str, df, signal_bars: int,
                 swing_length: int, close_break: bool) -> dict:
    result: dict = {
        "code":             code,
        "has_recent_buy":   False,
        "last_signal_date": None,
        "signal_type":      "",
        "fvg_confirmed":    False,
        "buy_count":        0,
        "error":            None,
        "adjust":           "hfq",
    }

    try:
        res = _compute_smc(df, swing_length, close_break)
        if res is None:
            result["error"] = f"K线不足 {swing_length * 2} 根"
            return result

        signal = res["signal_series"]
        choch  = res["choch_series"]
        fvg    = res["fvg_series"]

        result["buy_count"] = int((signal == 1).sum())

        recent_signal = signal.iloc[-signal_bars:]
        recent_buy    = recent_signal[recent_signal == 1]

        if recent_buy.empty:
            return result

        last_idx  = recent_buy.index[-1]
        last_date = last_idx.strftime("%Y-%m-%d") if hasattr(last_idx, "strftime") else str(last_idx)

        is_choch = int(choch.reindex([last_idx], fill_value=0).iloc[0]) != 0
        has_fvg  = int(fvg.reindex([last_idx],  fill_value=0).iloc[0]) != 0

        result["has_recent_buy"]   = True
        result["last_signal_date"] = last_date
        result["signal_type"]      = "ChoCH" if is_choch else "BOS"
        result["fvg_confirmed"]    = has_fvg

    except Exception as exc:
        result["error"] = str(exc)
        _log("WARN", f"  {code} 异常: {exc}")

    return result


# ── mask_id ───────────────────────────────────────────────────────────

def _make_mask_id(codes: list[str], params: dict) -> str:
    key = json.dumps(sorted(codes) + [params], sort_keys=True, ensure_ascii=False)
    return "smc_" + hashlib.sha1(key.encode()).hexdigest()[:12]


# ── 主逻辑 ────────────────────────────────────────────────────────────

def run(
    codes: list[str],
    cache_dir: Path,
    signal_bars: int = 15,
    swing_length: int = 10,
    close_break: bool = True,
    mode: str = "soft_filter",
    days: int = 365,
    out: Path | None = None,
) -> dict:
    os.environ["READ_CACHE_ONLY"] = "true"
    os.environ.pop("FAST_FULL_SCAN", None)

    from ohlcv_provider import fetch_ohlcv

    if not _SMC_AVAILABLE:
        _log("ERROR", f"smartmoneyconcepts 不可用: {_SMC_IMPORT_ERROR}")
        result = {
            "mask_id":       "smc_blocked",
            "producer":      "SMCProducer",
            "skill_id":      "smc",
            "skill_name":    "SMC聪明钱",
            "hit_semantics": "positive",
            "hit_codes":     [],
            "miss_codes":    codes,
            "evidence":      {},
            "params":        {"signal_bars": signal_bars, "swing_length": swing_length,
                              "mode": mode, "days": days},
            "data_mode":     "read_cache_only",
            "data_requirement": "kline_daily",
            "adjust":        "hfq",
            "status":        "blocked",
            "error":         f"smartmoneyconcepts 不可用: {_SMC_IMPORT_ERROR}",
            "generated_at":  datetime.now().isoformat(),
        }
        if out:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    t0 = time.time()
    params = {"signal_bars": signal_bars, "swing_length": swing_length,
              "close_break": close_break, "mode": mode, "days": days}

    hit_codes:  list[str] = []
    miss_codes: list[str] = []
    evidence:   dict      = {}

    _log("HEAD",
         f"{'='*55}\nSMCProducer  mode={mode}  swing={swing_length}  bars={signal_bars}\n{'='*55}")

    for i, code in enumerate(codes, 1):
        df = fetch_ohlcv(code, days=days, verbose=False)
        if df is None:
            miss_codes.append(code)
            evidence[code] = {"status": "cache_miss", "adjust": "hfq"}
            continue

        res = _analyze_one(code, df, signal_bars, swing_length, close_break)

        if res.get("error"):
            miss_codes.append(code)
            evidence[code] = {"status": "error", "error": res["error"], "adjust": "hfq"}
            continue

        if mode == "bypass":
            hit_codes.append(code)
            evidence[code] = {"status": "bypass", "adjust": "hfq"}
        elif mode == "soft_filter":
            hit_codes.append(code)
            evidence[code] = {
                "status":      "hit" if res["has_recent_buy"] else "pass_soft",
                "has_signal":  res["has_recent_buy"],
                "signal_type": res["signal_type"],
                "last_signal_date": res["last_signal_date"],
                "fvg_confirmed":    res["fvg_confirmed"],
                "adjust":      "hfq",
            }
        else:
            if res["has_recent_buy"]:
                hit_codes.append(code)
                evidence[code] = {
                    "status":      "hit",
                    "signal_type": res["signal_type"],
                    "last_signal_date": res["last_signal_date"],
                    "fvg_confirmed":    res["fvg_confirmed"],
                    "buy_count":        res["buy_count"],
                    "adjust":      "hfq",
                }
            else:
                miss_codes.append(code)
                evidence[code] = {"status": "no_recent_signal", "adjust": "hfq"}

        if i % 10 == 0 or i == len(codes):
            _log("INFO", f"进度 {i}/{len(codes)}  hit={len(hit_codes)}")

    elapsed = time.time() - t0
    mask_id = _make_mask_id(codes, params)

    result = {
        "mask_id":       mask_id,
        "producer":      "SMCProducer",
        "skill_id":      "smc",
        "skill_name":    "SMC聪明钱",
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
        "smc_version":   "smartmoneyconcepts-0.0.27",
        "generated_at":  datetime.now().isoformat(),
    }

    _log("HEAD",
         f"\n{'='*55}\nSMC完成  {len(codes)} 只 → hit={len(hit_codes)} miss={len(miss_codes)}  "
         f"{elapsed:.1f}s\n{'='*55}")

    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        _log("INFO", f"smc_mask.json → {out}")

    return result


def main() -> None:
    import io as _io
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="V6OP SMC Producer")
    parser.add_argument("--codes",        required=True)
    parser.add_argument("--limit",        type=int, default=0)
    parser.add_argument("--cache-dir",    default="var/cache/kline_daily")
    parser.add_argument("--out",          default="output/current/smc_mask.json")
    parser.add_argument("--signal-bars",  type=int, default=15)
    parser.add_argument("--swing-length", type=int, default=10)
    parser.add_argument("--mode",         default="soft_filter")
    parser.add_argument("--days",         type=int, default=365)
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
        swing_length=args.swing_length, mode=args.mode, days=args.days, out=out)


if __name__ == "__main__":
    main()
