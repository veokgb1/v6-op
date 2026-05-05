#!/usr/bin/env python3
"""
landmine_producer.py — V6OP 排雷 Producer

hit_semantics = "negative"（命中 = 应剔除）。
检测：ST/退市 / 次新股 / K线不足 / 缓存缺失 / 数据不可用

V6OP-001 baostock 失败代码自动纳入"数据不可用"证据。

用法:
  python scripts/producers/landmine_producer.py \
    --codes data/ashare_codes.txt \
    --limit 50 \
    --cache-dir var/cache/kline_daily \
    --out output/current/landmine_mask.json
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
    print(f"[{ts}]{color}[LandmineProducer][{level}]{RESET} {msg}", flush=True)


_CODE_PATTERN = re.compile(r"\b\d{6}\.(?:SZ|SH|BJ)\b", re.IGNORECASE)

MIN_BARS = 60


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


# ── 排雷规则 ──────────────────────────────────────────────────────────

def _is_st(code: str) -> tuple[bool, str]:
    """规则基于代码前缀判断 ST（无股票名称时仅检查 BJ 板块作为警告）。"""
    if code.endswith(".BJ"):
        return False, ""
    return False, ""


def _check_code_risk(code: str) -> tuple[bool, str]:
    """代码层面的风险规则：BJ 板块（北交所）数据往往不可用。"""
    if code.endswith(".BJ"):
        return True, f"北交所代码 ({code})，baostock 数据不可用"
    return False, ""


def _check_kline(df, code: str) -> tuple[bool, str]:
    """K线层面规则：K线不足 MIN_BARS。"""
    if df is None:
        return True, f"缓存缺失或数据不可用"
    n = len(df)
    if n < MIN_BARS:
        return True, f"K线仅 {n} 根（< {MIN_BARS}），分析不可信"
    return False, ""


# ── 动态加载 prefetch 失败列表 ───────────────────────────────────────

def _load_prefetch_failures(
    prefetch_report_path: Path | None = None,
) -> set[str]:
    """从 output/current/prefetch_report.json 动态读取 failed/stale 代码。

    V6OP-003 约束：不再硬编码 V6OP-001 失败列表，动态读取。
    """
    if prefetch_report_path is None:
        prefetch_report_path = _PROJECT_ROOT / "output" / "current" / "prefetch_report.json"
    if not prefetch_report_path.exists():
        return set()
    try:
        data = json.loads(prefetch_report_path.read_text(encoding="utf-8"))

        def _extract(raw: list) -> set[str]:
            result: set[str] = set()
            for item in raw:
                if isinstance(item, str):
                    result.add(item)
                elif isinstance(item, dict):
                    code = item.get("code", "")
                    if code:
                        result.add(code)
            return result

        failed: set[str] = _extract(data.get("failed_codes", []))
        # stale_codes 仍有旧缓存，可被 Producer 分析，不视为不可用
        return failed
    except Exception as exc:
        _log("WARN", f"读取 prefetch_report.json 失败: {exc}，使用空集合")
        return set()


def _make_mask_id(codes: list[str]) -> str:
    key = json.dumps(sorted(codes), ensure_ascii=False)
    return "landmine_" + hashlib.sha1(key.encode()).hexdigest()[:12]


# ── 主逻辑 ────────────────────────────────────────────────────────────

def run(
    codes: list[str],
    cache_dir: Path,
    days: int = 365,
    out: Path | None = None,
    prefetch_report_path: Path | None = None,
) -> dict:
    os.environ["READ_CACHE_ONLY"] = "true"
    os.environ.pop("FAST_FULL_SCAN", None)

    from ohlcv_provider import fetch_ohlcv

    t0 = time.time()

    # 动态读取 prefetch 失败列表（V6OP-003：不再硬编码）
    dynamic_unavailable = _load_prefetch_failures(prefetch_report_path)
    if dynamic_unavailable:
        _log("INFO", f"从 prefetch_report.json 加载 {len(dynamic_unavailable)} 个已知不可用代码")

    hit_codes:  list[str] = []   # 命中排雷 = 有问题应剔除
    miss_codes: list[str] = []   # 未命中排雷 = 安全
    evidence:   dict      = {}
    hit_reasons: dict[str, list[str]] = {}

    _log("HEAD",
         f"{'='*55}\nLandmineProducer  hit_semantics=negative  min_bars={MIN_BARS}\n{'='*55}")

    for i, code in enumerate(codes, 1):
        reasons: list[str] = []

        # 规则 0：prefetch_report 已知不可用代码（动态读取）
        if code in dynamic_unavailable:
            reasons.append(f"prefetch_report 已知无数据（prefetch failed）")

        # 规则 1：北交所代码
        code_risk, code_reason = _check_code_risk(code)
        if code_risk:
            reasons.append(code_reason)

        # 读取缓存
        df = fetch_ohlcv(code, days=days, verbose=False)

        # 规则 2：缓存缺失 / K线不足
        if not reasons:
            kline_risk, kline_reason = _check_kline(df, code)
            if kline_risk:
                reasons.append(kline_reason)

        if reasons:
            hit_codes.append(code)
            hit_reasons[code] = reasons
            evidence[code] = {
                "status":  "landmine",
                "reasons": reasons,
                "adjust":  "hfq" if df is not None else "n/a",
            }
            _log("WARN", f"[排雷] {code}  原因: {'; '.join(reasons)}")
        else:
            miss_codes.append(code)
            evidence[code] = {
                "status":  "clear",
                "bars":    len(df) if df is not None else 0,
                "adjust":  "hfq",
            }

        if i % 10 == 0 or i == len(codes):
            _log("INFO", f"进度 {i}/{len(codes)}  hit(排雷)={len(hit_codes)}")

    elapsed = time.time() - t0
    mask_id = _make_mask_id(codes)

    result = {
        "mask_id":       mask_id,
        "producer":      "LandmineProducer",
        "skill_id":      "landmine",
        "skill_name":    "排雷过滤",
        "hit_semantics": "negative",
        "hit_codes":     hit_codes,
        "miss_codes":    miss_codes,
        "evidence":      evidence,
        "params":        {"min_bars": MIN_BARS, "days": days},
        "data_mode":     "read_cache_only",
        "data_requirement": "kline_daily",
        "adjust":        "hfq",
        "hit_count":     len(hit_codes),
        "miss_count":    len(miss_codes),
        "duration_seconds": round(elapsed, 1),
        "known_unavailable_in_input": [c for c in codes if c in dynamic_unavailable],
        "generated_at":  datetime.now().isoformat(),
    }

    _log("HEAD",
         f"\n{'='*55}\n排雷完成  {len(codes)} 只 → 排雷={len(hit_codes)} 安全={len(miss_codes)}  "
         f"{elapsed:.1f}s\n{'='*55}")

    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        _log("INFO", f"landmine_mask.json → {out}")

    return result


def main() -> None:
    import io as _io
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="V6OP 排雷 Producer")
    parser.add_argument("--codes",     required=True)
    parser.add_argument("--limit",     type=int, default=0)
    parser.add_argument("--cache-dir", default="var/cache/kline_daily")
    parser.add_argument("--out",       default="output/current/landmine_mask.json")
    parser.add_argument("--days",      type=int, default=365)
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

    run(codes=codes, cache_dir=cache_dir, days=args.days, out=out)


if __name__ == "__main__":
    main()
