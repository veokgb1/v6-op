#!/usr/bin/env python3
"""
data_prefetch.py — V6OP K 线缓存预热（协调者/工作者并行）

协调者模式:
  将代码列表 round-robin 分成 N 块，并发启动 N 个子工作者进程。
  每个子进程独立持有一个 baostock 会话（进程隔离，无锁竞争）。
  汇总所有工作者报告，输出 prefetch_report.json。

工作者模式（PREFETCH_WORKER_ID 被设置时）:
  处理分配的代码块，顺序拉取，写出单工作者报告。

用法:
  python scripts/data_prefetch.py --codes data/ashare_codes.txt --limit 50 --days 365 --workers 8
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from time_utils import iso_cst

# ── 项目根 & 路径 ──────────────────────────────────────────────────────
_SCRIPTS_DIR = Path(__file__).parent.resolve()
_PROJECT_ROOT = _SCRIPTS_DIR.parent


def _ensure_scripts_on_path() -> None:
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))


# ── 代码文件读取 ───────────────────────────────────────────────────────
_CODE_PATTERN = re.compile(r"\b\d{6}\.(?:SZ|SH|BJ)\b", re.IGNORECASE)


def read_codes_from_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8-sig")
    codes: list[str] = []
    seen: set[str] = set()
    for code in _CODE_PATTERN.findall(text):
        key = code.strip().upper()
        if key and key not in seen:
            seen.add(key)
            codes.append(key)
    return codes


# ── 颜色日志 ──────────────────────────────────────────────────────────
_WORKER_ID = os.environ.get("PREFETCH_WORKER_ID", "").strip()
_TAG = f"Prefetch-W{_WORKER_ID}" if _WORKER_ID else "Prefetch"


def _configure_streams() -> None:
    """Windows UTF-8 编码修正 — 原地 reconfigure，不替换 sys.stdout/sys.stderr 对象。
    替换对象会在子进程退出时触发 'I/O operation on closed file' / 'lost sys.stderr'。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"


def _log(level: str, msg: str) -> None:
    color = {"INFO": GREEN, "WARN": YELLOW, "ERROR": RED, "HEAD": CYAN}.get(level, RESET)
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}]{color}[{_TAG}][{level}]{RESET} {msg}", flush=True)


# ── 工作者核心循环 ────────────────────────────────────────────────────

def _fetch_loop(codes: list[str], days: int, batch: int = 50) -> dict:
    _ensure_scripts_on_path()
    # 强制 FAST_FULL_SCAN，清除 READ_CACHE_ONLY
    os.environ["FAST_FULL_SCAN"] = "true"
    os.environ.pop("READ_CACHE_ONLY", None)

    from ohlcv_provider import fetch_ohlcv

    t0 = time.time()
    cache_hit = 0
    fetched_ok = 0
    stale_used = 0
    failed = 0
    bj_skipped = 0
    failed_codes: list[dict] = []
    stale_codes: list[str] = []
    bar_maxes: list[str] = []

    for i, code in enumerate(codes, 1):
        try:
            df = fetch_ohlcv(code, days=days, verbose=False)
            if df is None:
                if "." in code and code.split(".")[-1].upper() == "BJ":
                    bj_skipped += 1
                else:
                    failed += 1
                    failed_codes.append({"code": code})
            else:
                src = df.attrs.get("source", "")
                if src == "cache":
                    cache_hit += 1
                elif src == "stale_cache":
                    stale_used += 1
                    stale_codes.append(code)
                else:
                    fetched_ok += 1
                try:
                    bar_maxes.append(str(df.index[-1])[:10])
                except Exception:
                    pass
        except Exception as exc:
            failed += 1
            failed_codes.append({"code": code, "error": str(exc)})
            _log("WARN", f"  {code} 异常: {exc}")

        if i % batch == 0 or i == len(codes):
            elapsed = time.time() - t0
            rate = i / elapsed if elapsed > 0 else 0
            _log("INFO",
                 f"进度 {i}/{len(codes)}  "
                 f"命中={cache_hit} 新拉={fetched_ok} stale={stale_used} 失败={failed} BJ={bj_skipped}  "
                 f"{rate:.1f}只/s  {elapsed:.0f}s")

    return {
        "cache_hit": cache_hit,
        "fetched_ok": fetched_ok,
        "stale_used": stale_used,
        "failed": failed,
        "bj_skipped": bj_skipped,
        "failed_codes": failed_codes,
        "stale_codes": stale_codes,
        "data_time_max": max(bar_maxes) if bar_maxes else None,
        "duration_seconds": round(time.time() - t0, 1),
    }


# ── 协调者: 分块 + 并行 ───────────────────────────────────────────────

def _run_coordinator(codes: list[str], days: int, workers: int,
                     report_dir: Path, cache_dir: Path,
                     prefetch_run_id: str | None = None) -> dict:
    n = min(workers, len(codes))
    chunks = [codes[i::n] for i in range(n)]

    if prefetch_run_id is None:
        prefetch_run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    # 每次运行使用独立子目录，避免混入旧 worker 报告
    worker_run_dir = report_dir / "prefetch_workers" / prefetch_run_id
    worker_run_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    procs: list[tuple[int, subprocess.Popen, list[str]]] = []
    worker_report_paths: list[tuple[int, Path, list[str]]] = []
    chunk_files: list[Path] = []

    for wid, chunk in enumerate(chunks):
        if not chunk:
            continue
        cf = worker_run_dir / f"chunk_{wid}.txt"
        wr = worker_run_dir / f"worker_{wid}_report.json"
        cf.write_text("\n".join(chunk) + "\n", encoding="utf-8")
        chunk_files.append(cf)
        worker_report_paths.append((wid, wr, chunk))

        _existing_pp = os.environ.get("PYTHONPATH", "")
        _new_pp = str(_SCRIPTS_DIR) + (os.pathsep + _existing_pp if _existing_pp else "")
        wenv = {
            **os.environ,
            "PREFETCH_WORKER_ID": str(wid),
            "PREFETCH_CHUNK_FILE": str(cf),
            "PREFETCH_REPORT": str(wr),
            "PREFETCH_DAYS": str(days),
            "PREFETCH_RUN_ID": prefetch_run_id,
            "FAST_FULL_SCAN": "true",
            "PYTHONPATH": _new_pp,
        }
        wenv.pop("READ_CACHE_ONLY", None)

        proc = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve())],
            env=wenv,
            cwd=str(_PROJECT_ROOT),
        )
        procs.append((wid, proc, chunk))
        _log("INFO", f"Worker-{wid} 启动 → {len(chunk)} 只")

    failed_wids: set[int] = set()
    for wid, proc, _chunk in procs:
        proc.wait()
        if proc.returncode != 0:
            _log("WARN", f"Worker-{wid} 退出码 {proc.returncode}")
            failed_wids.add(wid)

    # 汇总：只读取本轮成功 worker 的报告；失败 worker 的 codes 全部计入 failed
    totals: dict[str, int] = {"cache_hit": 0, "fetched_ok": 0, "stale_used": 0,
                               "failed": 0, "bj_skipped": 0}
    all_failed: list[dict] = []
    all_stale: list[str] = []
    all_data_time_maxes: list[str] = []

    for wid, wr, chunk in worker_report_paths:
        if wid in failed_wids:
            # Worker 失败：报告不可信，所有分配的 codes 计为失败
            totals["failed"] += len(chunk)
            all_failed.extend({"code": c, "error": "worker_failed"} for c in chunk)
            _log("WARN", f"Worker-{wid} 失败，{len(chunk)} 只代码计入失败")
        elif wr.exists():
            try:
                rpt = json.loads(wr.read_text(encoding="utf-8"))
                # 校验 run_id 一致性
                rpt_run_id = rpt.get("prefetch_run_id", "")
                if rpt_run_id and rpt_run_id != prefetch_run_id:
                    _log("WARN", f"Worker-{wid} 报告 run_id 不匹配，跳过")
                    totals["failed"] += len(chunk)
                    all_failed.extend({"code": c, "error": "run_id_mismatch"} for c in chunk)
                    continue
                for k in totals:
                    totals[k] += rpt.get(k, 0)
                all_failed.extend(rpt.get("failed_codes", []))
                all_stale.extend(rpt.get("stale_codes", []))
                # 汇总各 worker 的 data_time_max（取全局 max）
                dtm = rpt.get("data_time_max")
                if dtm:
                    all_data_time_maxes.append(str(dtm)[:10])
            except Exception as e:
                _log("WARN", f"无法读取 Worker-{wid} 报告: {e}")
                totals["failed"] += len(chunk)
                all_failed.extend({"code": c, "error": "report_unreadable"} for c in chunk)
        else:
            _log("WARN", f"Worker-{wid} 报告缺失: {wr.name}")
            totals["failed"] += len(chunk)
            all_failed.extend({"code": c, "error": "report_missing"} for c in chunk)

    # 清理临时块文件
    for cf in chunk_files:
        try:
            cf.unlink()
        except Exception:
            pass

    return {
        **totals,
        "failed_codes": all_failed,
        "stale_codes": all_stale,
        "data_time_max": max(all_data_time_maxes) if all_data_time_maxes else None,
        "duration_seconds": round(time.time() - t0, 1),
        "workers_total": len(procs),
        "workers_failed": len(failed_wids),
        "prefetch_run_id": prefetch_run_id,
    }


# ── 补拉 pass（参照 V5.10 prefetch_kline_cache._recovery_pass）─────────

def _recovery_pass(raw_failed: list[dict], days: int) -> dict:
    """
    对并行阶段失败的代码做一次顺序补拉。
    返回 {"recovered": [...], "still_failed": [...]}。
    若 baostock 不可达，所有代码仍失败，recovered=[]。
    """
    if not raw_failed:
        return {"recovered": [], "still_failed": []}

    _ensure_scripts_on_path()
    os.environ["FAST_FULL_SCAN"] = "true"
    os.environ.pop("READ_CACHE_ONLY", None)

    import random
    from ohlcv_provider import fetch_ohlcv

    _log("INFO", f"补拉 pass：对 {len(raw_failed)} 只瞬时失败代码单线程重试")
    recovered: list[dict] = []
    still_failed: list[dict] = []

    for i, item in enumerate(raw_failed):
        code = item["code"]
        if i > 0:
            time.sleep(random.uniform(0.3, 0.8))
        try:
            df = fetch_ohlcv(code, days=days, verbose=False)
            if df is not None:
                recovered.append({"code": code})
                _log("INFO", f"  补拉成功: {code}  ({len(df)} 行)")
            else:
                still_failed.append(item)
                _log("WARN", f"  补拉仍失败: {code}（返回 None）")
        except Exception as exc:
            still_failed.append({"code": code, "error": str(exc)})
            _log("WARN", f"  补拉异常: {code}: {exc}")

    _log("INFO", f"补拉 pass 完成：成功恢复 {len(recovered)} 只，仍失败 {len(still_failed)} 只")
    return {"recovered": recovered, "still_failed": still_failed}


def _apply_recovery(stats: dict, days: int) -> dict:
    """
    从 stats 取出 failed_codes，运行 _recovery_pass，将结果写回 stats。
    新增字段：failed_codes_raw / recovered_codes / recovered_count / failed_codes（最终）。
    """
    raw_failed = stats.pop("failed_codes", [])

    if raw_failed:
        rec = _recovery_pass(raw_failed, days)
        recovered = rec["recovered"]
        still_failed = rec["still_failed"]
        stats["failed"] = max(0, stats.get("failed", 0) - len(recovered))
        stats["fetched_ok"] = stats.get("fetched_ok", 0) + len(recovered)
    else:
        recovered = []
        still_failed = []

    stats["failed_codes_raw"] = raw_failed
    stats["recovered_codes"] = recovered
    stats["recovered_count"] = len(recovered)
    stats["failed_codes"] = still_failed
    return stats


# ── 主入口 ────────────────────────────────────────────────────────────

def _worker_main() -> None:
    _configure_streams()

    chunk_file = Path(os.environ.get("PREFETCH_CHUNK_FILE", ""))
    report_path = Path(os.environ.get("PREFETCH_REPORT", ""))
    days = int(os.environ.get("PREFETCH_DAYS", "365"))

    if not chunk_file.exists():
        sys.exit(0)

    codes_text = chunk_file.read_text(encoding="utf-8")
    codes = [c.strip().upper() for c in codes_text.splitlines() if c.strip()]
    if not codes:
        sys.exit(0)

    wid_int = int(_WORKER_ID) if _WORKER_ID.isdigit() else 0
    if wid_int > 0:
        import random
        jitter = wid_int * 0.35 + random.uniform(0, 0.5)
        time.sleep(jitter)

    stats = _fetch_loop(codes, days=days)
    prefetch_run_id = os.environ.get("PREFETCH_RUN_ID", "")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps({
            "worker_id": _WORKER_ID,
            "prefetch_run_id": prefetch_run_id,
            "total_codes": len(codes),
            "kline_days": days,
            "run_at": iso_cst(),
            **stats,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def run_prefetch(
    codes: list[str],
    days: int = 365,
    workers: int = 8,
    cache_dir: Path | None = None,
    report_dir: Path | None = None,
) -> dict:
    """
    Python 可直接调用的预热入口（供 execution_engine 在 /api/run 链路中调用）。

    协调者模式（workers>1 且 codes>2）：启动子进程并行拉取。
    单线程模式：直接在当前进程拉取（适用于小股票池或测试）。

    Returns dict:
      cache_hit, fetched_ok, stale_used, failed, bj_skipped,
      failed_codes, stale_codes, duration_seconds
    """
    if cache_dir is None:
        cache_dir = _PROJECT_ROOT / "var" / "cache" / "kline_daily"
    if report_dir is None:
        report_dir = _PROJECT_ROOT / "output" / "current"

    if not codes:
        return {
            "cache_hit": 0, "fetched_ok": 0, "stale_used": 0,
            "failed": 0, "bj_skipped": 0,
            "failed_codes": [], "failed_codes_raw": [], "recovered_codes": [],
            "recovered_count": 0, "stale_codes": [],
            "data_time_max": None, "duration_seconds": 0,
        }

    os.environ["KLINE_CACHE_DIR"] = str(cache_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    prefetch_run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    if workers <= 1 or len(codes) <= 2:
        _ensure_scripts_on_path()
        os.environ["FAST_FULL_SCAN"] = "true"
        os.environ.pop("READ_CACHE_ONLY", None)
        stats = _fetch_loop(codes, days=days)
    else:
        raw = _run_coordinator(
            codes=codes, days=days, workers=workers,
            report_dir=report_dir, cache_dir=cache_dir,
            prefetch_run_id=prefetch_run_id,
        )
        raw.pop("workers_total", None)
        raw.pop("workers_failed", None)
        stats = raw

    # 并行或串行阶段结束后：单线程补拉 pass（对瞬时失败代码重试）
    stats = _apply_recovery(stats, days)

    # 写 prefetch_report.json（供 fetch_planner 重新读取）
    report: dict = {
        "step": "prefetch_kline_cache",
        "prefetch_run_id": prefetch_run_id,
        "total_codes": len(codes),
        "kline_days": days,
        "workers": workers,
        "cache_hit":        stats.get("cache_hit",        0),
        "fetched_ok":       stats.get("fetched_ok",       0),
        "stale_used":       stats.get("stale_used",       0),
        "failed":           stats.get("failed",           0),
        "bj_skipped":       stats.get("bj_skipped",       0),
        "failed_codes_raw": stats.get("failed_codes_raw", []),
        "recovered_codes":  stats.get("recovered_codes",  []),
        "recovered_count":  stats.get("recovered_count",  0),
        "failed_codes":     stats.get("failed_codes",     []),
        "stale_codes":      stats.get("stale_codes",      []),
        "data_time_max":    stats.get("data_time_max"),
        "duration_seconds": stats.get("duration_seconds", 0),
        "cache_dir": str(cache_dir),
        "run_at": iso_cst(),
    }
    (report_dir / "prefetch_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return stats


def main() -> None:
    _configure_streams()

    # 工作者模式
    if _WORKER_ID:
        _worker_main()
        return

    # 协调者模式
    parser = argparse.ArgumentParser(description="V6OP K线缓存预热")
    parser.add_argument("--codes", required=True, help="股票代码文件路径 (.txt 或 .md)")
    parser.add_argument("--limit", type=int, default=0, help="最多处理前 N 只 (0=全部)")
    parser.add_argument("--days", type=int, default=365, help="回看天数 (默认 365)")
    parser.add_argument("--workers", type=int, default=8, help="并行工作者数 (默认 8)")
    args = parser.parse_args()

    codes_path = Path(args.codes)
    if not codes_path.is_absolute():
        codes_path = _PROJECT_ROOT / codes_path
    if not codes_path.exists():
        print(f"[ERROR] 代码文件不存在: {codes_path}", flush=True)
        sys.exit(1)

    codes = read_codes_from_file(codes_path)
    if args.limit > 0:
        codes = codes[: args.limit]

    if not codes:
        print("[WARN] 代码列表为空，跳过预热", flush=True)
        sys.exit(0)

    cache_dir = _PROJECT_ROOT / "var" / "cache" / "kline_daily"
    report_dir = _PROJECT_ROOT / "output" / "current"
    report_path = report_dir / "prefetch_report.json"

    _log("HEAD",
         f"{'='*60}\n"
         f"V6OP K线缓存预热\n"
         f"  codes={len(codes)}  days={args.days}  workers={args.workers}\n"
         f"  cache_dir={cache_dir}\n"
         f"{'='*60}")

    if args.workers == 1 or len(codes) <= 1:
        _log("INFO", f"顺序模式（codes={len(codes)} ≤ workers=1）")
        _ensure_scripts_on_path()
        os.environ["FAST_FULL_SCAN"] = "true"
        os.environ.pop("READ_CACHE_ONLY", None)
        os.environ["KLINE_CACHE_DIR"] = str(cache_dir)
        stats = _fetch_loop(codes, days=args.days)
        workers_total = 1
        workers_failed = 0
    else:
        _log("INFO", f"{len(codes)} 只 → {args.workers} 进程并行拉取")
        os.environ["KLINE_CACHE_DIR"] = str(cache_dir)
        stats = _run_coordinator(codes, days=args.days, workers=args.workers,
                                 report_dir=report_dir, cache_dir=cache_dir)
        workers_total = stats.pop("workers_total", args.workers)
        workers_failed = stats.pop("workers_failed", 0)

    # 补拉 pass（对瞬时失败代码重试） — 与 run_prefetch() 路径对齐
    stats = _apply_recovery(stats, args.days)

    prefetch_run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    report = {
        "step": "prefetch_kline_cache",
        "prefetch_run_id": prefetch_run_id,
        "total_codes": len(codes),
        "kline_days": args.days,
        "workers": args.workers,
        "cache_hit":        stats.get("cache_hit",        0),
        "fetched_ok":       stats.get("fetched_ok",       0),
        "stale_used":       stats.get("stale_used",       0),
        "failed":           stats.get("failed",           0),
        "bj_skipped":       stats.get("bj_skipped",       0),
        "failed_codes_raw": stats.get("failed_codes_raw", []),
        "recovered_codes":  stats.get("recovered_codes",  []),
        "recovered_count":  stats.get("recovered_count",  0),
        "failed_codes":     stats.get("failed_codes",     []),
        "stale_codes":      stats.get("stale_codes",      []),
        "data_time_max":    stats.get("data_time_max"),
        "duration_seconds": stats.get("duration_seconds", 0),
        "cache_dir": str(cache_dir),
        "run_at": iso_cst(),
    }

    report_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _log("INFO", f"报告 → {report_path}")

    dur = stats.get("duration_seconds", 0)
    recovered = stats.get("recovered_count", 0)
    _log("HEAD",
         f"\n{'='*60}\n"
         f"预热完成  workers={workers_total} (失败={workers_failed})\n"
         f"  总计 {len(codes)} 只  命中缓存 {report['cache_hit']}  新拉成功 {report['fetched_ok']}\n"
         f"  补拉恢复 {recovered}  stale 降级 {report['stale_used']}  "
         f"最终失败 {report['failed']}  耗时 {dur}s\n"
         f"{'='*60}")

    if workers_failed > workers_total / 2:
        _log("ERROR", f"超过半数 Worker 失败 ({workers_failed}/{workers_total})")
        sys.exit(1)


if __name__ == "__main__":
    main()
