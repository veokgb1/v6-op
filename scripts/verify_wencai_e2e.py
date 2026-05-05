#!/usr/bin/env python3
"""
verify_wencai_e2e.py — V6OP wencai 真实端到端验收辅助脚本

用法：
  python scripts/verify_wencai_e2e.py
  python scripts/verify_wencai_e2e.py --query "净利润增速大于20%" --limit 10

验收检查：
  1. IWENCAI_API_KEY 是否存在（不打印值）
  2. wencai source 是否返回 status=ok
  3. 若 ok，尝试 prefetch 至少 1 只并报告结果
  4. 若失败，明确归因（auth_failed / network_error / api_error / empty_result / key_missing / blocked）

本脚本不使用 fallback 冒充成功。失败必须明确归因。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).parent.resolve()
_PROJECT_ROOT = _SCRIPTS_DIR.parent

for _p in [str(_SCRIPTS_DIR), str(_SCRIPTS_DIR / "sources")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _section(title: str) -> None:
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")


def run_verify(query: str = "净利润增速大于20%", limit: int = 10) -> dict:
    results: dict = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "limit": limit,
    }

    # ── 1. API Key 检查 ────────────────────────────────────────────────
    _section("步骤 1：检查 IWENCAI_API_KEY")
    env_path = _PROJECT_ROOT / ".env"
    key_found = bool(os.environ.get("IWENCAI_API_KEY", "").strip())
    if not key_found and env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("IWENCAI_API_KEY=") and not line.startswith("#"):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    os.environ["IWENCAI_API_KEY"] = val
                    key_found = True
                break
    results["api_key_found"] = key_found
    print(f"  IWENCAI_API_KEY 存在: {key_found}  （值不显示）")
    if not key_found:
        print("  ⚠ key 未找到，wencai 查询将返回 key_missing / blocked")

    # ── 2. 问财来源查询 ───────────────────────────────────────────────
    _section("步骤 2：调用问财来源")
    from wencai_source import run as _wencai_run  # type: ignore
    scope = _wencai_run(query=query, limit=limit, out=None)

    status = scope.get("status", "error")
    codes = scope.get("scope_codes", [])
    results["wencai_status"] = status
    results["wencai_codes_count"] = len(codes)
    results["wencai_codes_sample"] = codes[:5]

    print(f"  status     = {status}")
    print(f"  返回代码数 = {len(codes)}")
    if codes:
        print(f"  代码样本   = {codes[:5]}")

    # 归因映射
    _fail_reasons = {
        "key_missing":    "API Key 不存在或未配置",
        "blocked":        "pywencai 库未安装（ImportError）",
        "auth_failed":    "API Key 无效（401 Unauthorized）",
        "empty_result":   "查询成功但返回 0 只股票",
        "network_error":  "网络连接失败（ConnectionError / TimeoutError）",
        "api_error":      "其他 API 错误",
        "error":          "未知错误",
    }
    if status != "ok":
        reason = _fail_reasons.get(status, f"未知状态: {status}")
        results["wencai_failure_reason"] = reason
        print(f"\n  [FAIL] wencai 未成功: {reason}")
        note = scope.get("note") or scope.get("error") or ""
        if note:
            print(f"    详情: {note}")
        results["wencai_e2e_closed"] = False
        _print_summary(results)
        return results

    print("  [OK] 问财返回 ok")

    # ── 3. prefetch 至少 1 只 ──────────────────────────────────────────
    _section("步骤 3：尝试预热（baostock）")
    sample_codes = codes[:min(5, len(codes))]
    print(f"  预热样本: {sample_codes}")

    from data_prefetch import run_prefetch  # type: ignore
    cache_dir = _PROJECT_ROOT / "var" / "cache" / "kline_daily"
    report_dir = _PROJECT_ROOT / "output" / "wencai_verify"

    try:
        prefetch_stats = run_prefetch(
            codes=sample_codes,
            days=365,
            workers=1,  # 验收脚本用单线程，不依赖子进程
            cache_dir=cache_dir,
            report_dir=report_dir,
        )
        results["prefetch_triggered"] = True
        results["prefetch_cache_hit"] = prefetch_stats.get("cache_hit", 0)
        results["prefetch_fetched_ok"] = prefetch_stats.get("fetched_ok", 0)
        results["prefetch_recovered_count"] = prefetch_stats.get("recovered_count", 0)
        results["prefetch_failed"] = prefetch_stats.get("failed", 0)
        results["prefetch_data_time_max"] = prefetch_stats.get("data_time_max")

        success_count = (prefetch_stats.get("cache_hit", 0)
                         + prefetch_stats.get("fetched_ok", 0)
                         + prefetch_stats.get("recovered_count", 0))
        print(f"  cache_hit={prefetch_stats.get('cache_hit',0)}  "
              f"fetched_ok={prefetch_stats.get('fetched_ok',0)}  "
              f"recovered={prefetch_stats.get('recovered_count',0)}  "
              f"failed={prefetch_stats.get('failed',0)}")
        print(f"  data_time_max={prefetch_stats.get('data_time_max')}")

        if success_count >= 1:
            print(f"\n  [OK] prefetch 成功至少 1 只（{success_count}）")
            results["wencai_e2e_closed"] = True
        else:
            print(f"\n  [FAIL] prefetch 全部失败（baostock 可能不可达）")
            results["wencai_e2e_closed"] = False
            results["prefetch_block_reason"] = "baostock 不可达（fetched_ok=0，可能是网络环境限制）"

    except Exception as exc:
        results["prefetch_triggered"] = False
        results["prefetch_exception"] = str(exc)
        results["wencai_e2e_closed"] = False
        print(f"\n  ✗ prefetch 异常: {exc}")

    _print_summary(results)
    return results


def _print_summary(results: dict) -> None:
    _section("验收摘要")
    closed = results.get("wencai_e2e_closed", False)
    print(f"  wencai status        = {results.get('wencai_status')}")
    print(f"  wencai 返回代码数    = {results.get('wencai_codes_count', 0)}")
    if results.get("prefetch_triggered"):
        print(f"  prefetch cache_hit   = {results.get('prefetch_cache_hit', 0)}")
        print(f"  prefetch fetched_ok  = {results.get('prefetch_fetched_ok', 0)}")
        print(f"  prefetch recovered   = {results.get('prefetch_recovered_count', 0)}")
        print(f"  prefetch failed      = {results.get('prefetch_failed', 0)}")
        print(f"  data_time_max        = {results.get('prefetch_data_time_max')}")
    elif "prefetch_block_reason" in results:
        print(f"  prefetch 阻塞原因    = {results['prefetch_block_reason']}")
    elif "prefetch_exception" in results:
        print(f"  prefetch 异常        = {results['prefetch_exception']}")
    elif "wencai_failure_reason" in results:
        print(f"  wencai 失败原因      = {results['wencai_failure_reason']}")
    print(f"\n  端到端闭合           = {'[OK] YES' if closed else '[FAIL] NO（见上方归因）'}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="V6OP wencai 真实端到端验收")
    parser.add_argument("--query", default="净利润增速大于20%", help="问财选股语句")
    parser.add_argument("--limit", type=int, default=10, help="最多返回 N 只")
    parser.add_argument("--json-out", help="将结果以 JSON 形式写入文件")
    args = parser.parse_args()

    results = run_verify(query=args.query, limit=args.limit)

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"结果已写入: {args.json_out}")


if __name__ == "__main__":
    main()
