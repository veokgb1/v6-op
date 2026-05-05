#!/usr/bin/env python3
"""
verify_prefetch_300.py — V6OP 大样本预热验收脚本（总纲对象接力表）

目标：验证 300 只股票能在 timeout 秒内完成预热（含缓存命中），
并输出 cache_hit/fetched_ok/failed/data_time_max 等统计。

超时行为：
- 内部 timeout：在 timeout_seconds 内未完成 → 终止 worker 子进程，写 partial JSON
- partial JSON status="timeout"，含 workers_cleaned=True
- exit code: 0=pass/dry_run, 1=fail/error/timeout, 2=env_error

用法：
  python scripts/verify_prefetch_300.py --limit 20 --workers 2 --json-out output/verification/smoke.json
  python scripts/verify_prefetch_300.py --limit 300 --workers 8 --timeout 240 --json-out output/verification/v6op024_prefetch_300.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).parent.resolve()
_PROJECT_ROOT = _SCRIPTS_DIR.parent

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
RESET  = "\033[0m"


def _log(level: str, msg: str) -> None:
    color = {"INFO": GREEN, "WARN": YELLOW, "ERROR": RED, "HEAD": CYAN}.get(level, RESET)
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}]{color}[Verify300][{level}]{RESET} {msg}", flush=True)


def _get_ashare_codes(limit: int) -> tuple[list[str], str | None]:
    """
    获取用于验收的 A 股代码列表。
    优先读取本地 data/ashare_codes.txt，
    fallback 到扫描缓存目录中的 .pkl 文件名推断。
    返回 (codes, error_reason)；无法获取时 codes=[], error_reason 说明原因。
    """
    ashare_txt = _PROJECT_ROOT / "data" / "ashare_codes.txt"
    if ashare_txt.exists():
        try:
            from data_prefetch import read_codes_from_file
            all_codes = read_codes_from_file(ashare_txt)
            if all_codes:
                return all_codes[:limit], None
        except Exception:
            pass

    cache_dir = _PROJECT_ROOT / "var" / "cache" / "kline_daily"
    if cache_dir.exists():
        pkl_codes = []
        for p in cache_dir.glob("*.pkl"):
            stem = p.stem  # e.g. 000001_SZ_365d
            parts = stem.rsplit("_", 1)
            if len(parts) == 2 and parts[1].endswith("d"):
                code_part = parts[0]  # 000001_SZ
                code = code_part.replace("_", ".", 1)  # 000001.SZ
                if "." in code:
                    pkl_codes.append(code)
        if pkl_codes:
            import random
            random.shuffle(pkl_codes)
            return pkl_codes[:limit], None

    return [], "无法获取 A 股代码列表：data/ashare_codes.txt 不存在且 var/cache/kline_daily/ 无缓存文件"


def _kill_prefetch_workers() -> int:
    """
    清理当前进程的所有子进程（data_prefetch worker）。
    返回已终止的进程数。
    使用 psutil（已在 .venv 中安装）。
    """
    killed = 0
    try:
        import psutil
        current = psutil.Process(os.getpid())
        children = current.children(recursive=True)
        for child in children:
            try:
                child.kill()
                killed += 1
                _log("WARN", f"  清理 worker PID={child.pid}")
            except Exception:
                pass
    except ImportError:
        _log("WARN", "  psutil 未安装，无法自动清理 worker 子进程")
    except Exception as exc:
        _log("WARN", f"  worker 清理异常: {exc}")
    return killed


def run_verification(
    limit: int = 300,
    workers: int = 8,
    days: int = 365,
    timeout_seconds: int = 240,
) -> dict:
    """
    执行预热验收并返回统计结果。
    支持内部超时：timeout_seconds 内未完成则终止 worker 并返回 partial JSON。
    """
    t_start = time.time()
    _log("HEAD", f"{'='*55}\n大样本预热验收  limit={limit}  workers={workers}  "
                 f"timeout={timeout_seconds}s\n{'='*55}")

    codes, err = _get_ashare_codes(limit)
    if err or not codes:
        reason = err or "代码列表为空"
        _log("ERROR", f"无法获取代码列表：{reason}")
        return {
            "status": "env_error",
            "env_error": reason,
            "limit": limit,
            "workers": workers,
            "verified_at": datetime.now().isoformat(),
        }

    actual_limit = min(limit, len(codes))
    codes = codes[:actual_limit]
    _log("INFO", f"实际代码数: {len(codes)}（请求 {limit}）")

    try:
        import ohlcv_provider  # type: ignore  # noqa: F401
    except ImportError as exc:
        reason = f"ohlcv_provider 模块不可导入: {exc}"
        _log("ERROR", reason)
        return {
            "status": "env_error",
            "env_error": reason,
            "limit": limit,
            "workers": workers,
            "verified_at": datetime.now().isoformat(),
        }

    cache_dir = _PROJECT_ROOT / "var" / "cache" / "kline_daily"
    report_dir = _PROJECT_ROOT / "output" / "verification"
    report_dir.mkdir(parents=True, exist_ok=True)

    import data_prefetch as _dp  # type: ignore
    _log("INFO", f"启动 data_prefetch.run_prefetch  {len(codes)} 只  workers={workers}  days={days}")

    # ── 在子线程中运行 run_prefetch，主线程监控超时 ────────────────
    _result: dict = {}
    _error: dict = {}
    _done = threading.Event()

    def _prefetch_thread():
        try:
            stats = _dp.run_prefetch(
                codes=codes,
                days=days,
                workers=workers,
                cache_dir=cache_dir,
                report_dir=report_dir,
            )
            _result["stats"] = stats
        except Exception as exc:
            _error["exc"] = exc
        finally:
            _done.set()

    t = threading.Thread(target=_prefetch_thread, daemon=True)
    t.start()

    finished = _done.wait(timeout=timeout_seconds)
    elapsed = round(time.time() - t_start, 2)

    if not finished:
        # ── 超时：清理 worker 子进程，返回 partial JSON ──────────────
        _log("WARN", f"⏱ 预热超时（{timeout_seconds}s），开始清理 worker…")
        killed = _kill_prefetch_workers()
        _log("WARN", f"  已终止 {killed} 个 worker 进程")
        return {
            "status": "timeout",
            "partial": True,
            "workers_cleaned": True,
            "workers_killed": killed,
            "limit": limit,
            "actual_code_count": actual_limit,
            "workers": workers,
            "days": days,
            "elapsed_seconds": elapsed,
            "timeout_seconds": timeout_seconds,
            "verified_at": datetime.now().isoformat(),
            "verdict_notes": [
                f"运行超过 {timeout_seconds}s 被终止，输出为 partial 结果"
            ],
        }

    if _error:
        exc = _error["exc"]
        reason = f"run_prefetch 执行异常: {exc}"
        _log("ERROR", reason)
        return {
            "status": "error",
            "error": reason,
            "limit": limit,
            "workers": workers,
            "elapsed_seconds": elapsed,
            "verified_at": datetime.now().isoformat(),
        }

    stats = _result["stats"]

    cache_hit      = stats.get("cache_hit", 0)
    fetched_ok     = stats.get("fetched_ok", 0)
    recovered      = stats.get("recovered_count", 0)
    failed         = stats.get("failed", 0)
    data_time_max  = stats.get("data_time_max", None)
    # recovered is already folded into fetched_ok by data_prefetch._apply_recovery;
    # adding it again would double-count. recovered_count is kept as an informational field only.
    total          = cache_hit + fetched_ok + failed
    failure_rate   = failed / max(total, 1)

    _log("INFO",
         f"命中缓存={cache_hit}  新拉={fetched_ok}  "
         f"补拉恢复={recovered}  失败={failed}  "
         f"data_time_max={data_time_max}  "
         f"耗时={elapsed}s")

    passed = True
    verdict_notes = []

    if failure_rate > 0.5:
        passed = False
        verdict_notes.append(f"失败率 {failure_rate:.1%} > 50%，验收不通过")

    if actual_limit < limit * 0.8:
        passed = False
        verdict_notes.append(
            f"实际获取代码数 {actual_limit} < 请求数 {limit} 的 80%，代码源不足"
        )

    if passed and not verdict_notes:
        verdict_notes.append("验收通过")

    verdict = "pass" if passed else "fail"
    _log("HEAD" if passed else "WARN",
         f"验收结论: {verdict.upper()}  {'; '.join(verdict_notes)}")

    return {
        "status": verdict,
        "verdict_notes": verdict_notes,
        "limit": limit,
        "actual_code_count": actual_limit,
        "workers": workers,
        "days": days,
        "cache_hit": cache_hit,
        "fetched_ok": fetched_ok,
        "recovered_count": recovered,
        "failed": failed,
        "failure_rate": round(failure_rate, 4),
        "data_time_max": data_time_max,
        "elapsed_seconds": elapsed,
        "timeout_seconds": timeout_seconds,
        "verified_at": datetime.now().isoformat(),
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="V6OP 大样本预热验收（总纲对象接力表）"
    )
    parser.add_argument("--limit",    type=int, default=300, help="验收代码只数（默认 300）")
    parser.add_argument("--workers",  type=int, default=8,   help="并发工作者数（默认 8）")
    parser.add_argument("--days",     type=int, default=365, help="回看天数（默认 365）")
    parser.add_argument("--timeout",  type=int, default=240, help="超时秒数（默认 240）")
    parser.add_argument("--json-out", dest="json_out", default=None,
                        help="JSON 输出路径")
    parser.add_argument("--dry-run",  action="store_true",
                        help="仅打印脚本结构，不实际运行预热（用于 CI 结构验证）")
    args = parser.parse_args(argv)

    if args.dry_run:
        print("[DRY-RUN] verify_prefetch_300.py 结构验证通过", flush=True)
        result = {
            "status": "dry_run",
            "limit": args.limit,
            "workers": args.workers,
            "days": args.days,
            "timeout_seconds": args.timeout,
            "verified_at": datetime.now().isoformat(),
        }
    else:
        result = run_verification(
            limit=args.limit,
            workers=args.workers,
            days=args.days,
            timeout_seconds=args.timeout,
        )

    out_path = Path(args.json_out) if args.json_out else (
        _PROJECT_ROOT / "output" / "verification" / "verify_prefetch_result.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    _log("INFO", f"JSON 结果已写入: {out_path}")

    status = result.get("status", "error")
    if status in ("pass", "dry_run"):
        return 0
    if status == "env_error":
        _log("WARN", f"环境限制（非代码错误）：{result.get('env_error', '')}")
        return 2
    # timeout / fail / error → exit 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
