#!/usr/bin/env python3
"""
run_core_producers.py — V6OP 阶段 1 一键汇总

在已有缓存上运行本地 5 个 Producer（CZSC / SMC / Kline / Wave / Landmine）。
输出各 mask JSON + 汇总报告 core_producer_summary.json。

用法:
  python scripts/run_core_producers.py \
    --codes data/ashare_codes.txt \
    --limit 50 \
    --cache-dir var/cache/kline_daily
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ── 路径 ──────────────────────────────────────────────────────────────
_SCRIPTS_DIR  = Path(__file__).parent.resolve()
_PROJECT_ROOT = _SCRIPTS_DIR.parent

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
if str(_SCRIPTS_DIR / "producers") not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR / "producers"))

import re
_CODE_PATTERN = re.compile(r"\b\d{6}\.(?:SZ|SH|BJ)\b", re.IGNORECASE)

# ── 颜色日志 ──────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
RESET  = "\033[0m"


def _log(level: str, msg: str) -> None:
    color = {"INFO": GREEN, "WARN": YELLOW, "ERROR": RED, "HEAD": CYAN}.get(level, RESET)
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}]{color}[CoreProducers][{level}]{RESET} {msg}", flush=True)


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


# ── 各 Producer 执行 ──────────────────────────────────────────────────

def _run_czsc(codes: list[str], cache_dir: Path, out_dir: Path) -> dict:
    from producers.czsc_producer import run as czsc_run
    out = out_dir / "czsc_mask.json"
    try:
        result = czsc_run(codes=codes, cache_dir=cache_dir, out=out)
        return {
            "status":    "ok",
            "mask_path": str(out),
            "hit_count": result.get("hit_count", len(result.get("hit_codes", []))),
            "miss_count": result.get("miss_count", len(result.get("miss_codes", []))),
            "failed_count": 0,
            "data_mode": "read_cache_only",
            "adjust":    "hfq",
            "duration_s": result.get("duration_seconds", 0),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc), "mask_path": str(out)}


def _run_smc(codes: list[str], cache_dir: Path, out_dir: Path) -> dict:
    from producers.smc_producer import run as smc_run
    out = out_dir / "smc_mask.json"
    try:
        result = smc_run(codes=codes, cache_dir=cache_dir, out=out)
        status = result.get("status", "ok")
        return {
            "status":     status if status != "blocked" else "blocked",
            "mask_path":  str(out),
            "hit_count":  result.get("hit_count", 0),
            "miss_count": result.get("miss_count", 0),
            "failed_count": 0,
            "data_mode":  "read_cache_only",
            "adjust":     "hfq",
            "duration_s": result.get("duration_seconds", 0),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc), "mask_path": str(out)}


def _run_kline(codes: list[str], cache_dir: Path, out_dir: Path) -> dict:
    from producers.kline_producer import run as kline_run
    out = out_dir / "kline_mask.json"
    try:
        result = kline_run(codes=codes, cache_dir=cache_dir, out=out)
        return {
            "status":     "ok",
            "mask_path":  str(out),
            "hit_count":  result.get("hit_count", 0),
            "miss_count": result.get("miss_count", 0),
            "failed_count": 0,
            "data_mode":  "read_cache_only",
            "adjust":     "hfq",
            "duration_s": result.get("duration_seconds", 0),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc), "mask_path": str(out)}


def _run_wave(codes: list[str], cache_dir: Path, out_dir: Path) -> dict:
    from producers.wave_producer import run as wave_run
    out = out_dir / "wave_mask.json"
    try:
        result = wave_run(codes=codes, cache_dir=cache_dir, out=out)
        return {
            "status":     "ok",
            "mask_path":  str(out),
            "hit_count":  result.get("hit_count", 0),
            "miss_count": result.get("miss_count", 0),
            "failed_count": 0,
            "data_mode":  "read_cache_only",
            "adjust":     "hfq",
            "duration_s": result.get("duration_seconds", 0),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc), "mask_path": str(out)}


def _run_landmine(codes: list[str], cache_dir: Path, out_dir: Path) -> dict:
    from producers.landmine_producer import run as lm_run
    out = out_dir / "landmine_mask.json"
    try:
        result = lm_run(codes=codes, cache_dir=cache_dir, out=out)
        return {
            "status":          "ok",
            "mask_path":       str(out),
            "hit_count":       result.get("hit_count", 0),   # 排雷命中 = 应剔除
            "miss_count":      result.get("miss_count", 0),  # 安全
            "failed_count":    0,
            "hit_semantics":   "negative",
            "data_mode":       "read_cache_only",
            "adjust":          "hfq",
            "duration_s":      result.get("duration_seconds", 0),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc), "mask_path": str(out)}


# ── 主入口 ────────────────────────────────────────────────────────────

def main() -> None:
    import io as _io
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="V6OP 阶段 1 一键汇总")
    parser.add_argument("--codes",     required=True)
    parser.add_argument("--limit",     type=int, default=0)
    parser.add_argument("--cache-dir", default="var/cache/kline_daily")
    parser.add_argument("--out-dir",   default="output/current")
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

    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = _PROJECT_ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    _log("HEAD",
         f"{'='*60}\n"
         f"V6OP 阶段 1 一键汇总  codes={len(codes)}  cache={cache_dir}\n"
         f"{'='*60}")

    t0 = time.time()

    producers = [
        ("czsc",     "缠论买点",  _run_czsc),
        ("smc",      "SMC聪明钱", _run_smc),
        ("kline",    "K线形态",   _run_kline),
        ("wave",     "波浪分析",  _run_wave),
        ("landmine", "排雷过滤",  _run_landmine),
    ]

    results: dict[str, dict] = {}
    for skill_id, skill_name, runner in producers:
        _log("INFO", f"--- {skill_name} ---")
        r = runner(codes, cache_dir, out_dir)
        results[skill_id] = {"skill_name": skill_name, **r}
        status = r.get("status", "?")
        hit    = r.get("hit_count", "?")
        miss   = r.get("miss_count", "?")
        _log("INFO" if status == "ok" else "WARN",
             f"  {skill_name}: status={status}  hit={hit}  miss={miss}")

    total_elapsed = time.time() - t0

    summary = {
        "step":          "run_core_producers",
        "total_codes":   len(codes),
        "cache_dir":     str(cache_dir),
        "producers":     results,
        "total_duration_seconds": round(total_elapsed, 1),
        "env_loaded":    (Path(_PROJECT_ROOT / ".env")).exists(),
        "external_api_accessed": False,
        "generated_at":  datetime.now().isoformat(),
    }

    summary_path = out_dir / "core_producer_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    _log("HEAD",
         f"\n{'='*60}\n"
         f"汇总完成  {len(codes)} 只  耗时 {total_elapsed:.1f}s\n"
         + "\n".join(
             f"  {v['skill_name']}: {v.get('status','?')}  hit={v.get('hit_count','?')}"
             for v in results.values()
         )
         + f"\n报告 → {summary_path}\n{'='*60}")


if __name__ == "__main__":
    main()
