#!/usr/bin/env python3
"""
fetch_planner.py — V6OP 数据预热规划器

输入：scope_codes, selected_skills, skill_registry
输出：prefetch_required, prefetch_plan, prefetch_report, readiness,
      failed_codes, stale_codes, failure_rate

规则：
- 合并 K 线类 Producer 的需求，只预热一次。
- 默认 lookback_days=365。
- 如果已有缓存且数据充分，可复用缓存。
- 读取 output/current/prefetch_report.json，将 failed/stale 传给后续结果层。
- 失败率 > 20% 时 readiness=aborted；否则 ready 或 partial。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).parent.resolve()
_PROJECT_ROOT = _SCRIPTS_DIR.parent

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def _get_kline_skills() -> frozenset[str]:
    """
    从 skill_registry 的 data_requirement 字段推导需要 K 线数据的技能集合。
    避免硬编码——新增技能后只需在 skill_registry.py 声明 data_requirement=kline_daily。
    """
    try:
        from skill_registry import SKILL_REGISTRY  # type: ignore
        return frozenset(
            s["skill_id"]
            for s in SKILL_REGISTRY
            if s.get("data_requirement") == "kline_daily"
        )
    except Exception:
        # fallback：若 skill_registry 不可用，使用已知集合（保证兼容性）
        return frozenset({"czsc", "smc", "kline", "wave", "landmine"})


def _cache_fname(code: str, days: int) -> str:
    """与 ohlcv_provider.cache_path() 完全相同的命名规则：000001.SZ → 000001_SZ_365d.pkl"""
    safe = code.replace(".", "_").replace("/", "_")
    return f"{safe}_{days}d.pkl"


def _load_prefetch_report(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def plan(
    scope_codes: list[str],
    selected_skills: list[str],
    *,
    cache_dir: Path | None = None,
    prefetch_report_path: Path | None = None,
    lookback_days: int = 365,
) -> dict:
    """
    分析所选技能的数据需求，检查缓存状态，决定是否需要预热。

    Returns dict with:
      prefetch_required  : bool
      prefetch_plan      : dict
      prefetch_report    : dict  (来自已存在的报告)
      readiness          : "ready" | "partial" | "aborted"
      cached_codes       : list[str]
      missing_codes      : list[str]
      failed_codes       : list[str]  (来自 prefetch_report)
      stale_codes        : list[str]  (来自 prefetch_report)
      available_codes    : list[str]
      failure_rate       : float
    """
    if cache_dir is None:
        cache_dir = _PROJECT_ROOT / "var" / "cache" / "kline_daily"
    if prefetch_report_path is None:
        prefetch_report_path = (
            _PROJECT_ROOT / "output" / "current" / "prefetch_report.json"
        )

    # 从 skill_registry.data_requirement 推导需要 K 线的技能（不硬编码集合）
    _kline_skill_set = _get_kline_skills()
    kline_skills = [s for s in selected_skills if s in _kline_skill_set]
    needs_kline = len(kline_skills) > 0

    # 读取已有 prefetch_report（包含历史失败/stale 信息）
    existing_report = _load_prefetch_report(prefetch_report_path)

    def _extract_codes(raw: list) -> list[str]:
        """支持 ['000001.SZ', ...] 和 [{'code': '000001.SZ'}, ...] 两种格式。"""
        result: list[str] = []
        for item in raw:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                code = item.get("code", "")
                if code:
                    result.append(code)
        return result

    # 只保留属于本次 scope 的历史失败/stale；跨 scope 的旧记录不污染当前 fetch_plan。
    _scope_set = set(scope_codes)
    failed_codes: list[str] = [
        c for c in _extract_codes(existing_report.get("failed_codes", []))
        if c in _scope_set
    ]
    stale_codes: list[str] = [
        c for c in _extract_codes(existing_report.get("stale_codes", []))
        if c in _scope_set
    ]

    # 语义区分：
    #   failed_codes — prefetch 真正失败，无可用数据，不得分析
    #   stale_codes  — 缓存存在但已过旧，仍可分析，但报告须标注"使用旧缓存"
    # 不变式：stale 不等同 failed，不影响 failure_rate 和 readiness 判断
    failed_codes_set = set(failed_codes)
    stale_codes_set = set(stale_codes)

    # 检查本地缓存覆盖
    # 不变式：同一只股票不能同时出现在 cached_codes 和 failed_codes。
    # 若 prefetch_report 已标记为 failed，即使本地有 .pkl 文件，也不计为 cached。
    # stale 股票有 .pkl 文件，应进入 cached_codes（可分析）。
    cached_codes: list[str] = []
    missing_codes: list[str] = []

    if needs_kline and cache_dir.exists():
        for code in scope_codes:
            cache_file = cache_dir / _cache_fname(code, lookback_days)
            if cache_file.exists() and code not in failed_codes_set:
                # 包含 stale 股票（有旧 .pkl）和正常 cached 股票
                cached_codes.append(code)
            elif code not in failed_codes_set and code not in stale_codes_set:
                # 真正缺失：既无缓存，也不是已知 failed/stale
                missing_codes.append(code)
            # failed_codes 中的股票：无论 .pkl 是否存在均不进入 cached_codes 或 missing_codes
    elif needs_kline:
        missing_codes = [
            c for c in scope_codes
            if c not in failed_codes_set and c not in stale_codes_set
        ]

    # 可用代码：可被 Producer 分析的代码（排除 failed 和 missing，stale 包含在内）
    missing_set = set(missing_codes)
    available_codes = [
        c for c in scope_codes
        if c not in failed_codes_set and c not in missing_set
    ]

    # 失败率：只统计真正失败的代码，stale 不计入
    total = len(scope_codes)
    failure_rate = len([c for c in scope_codes if c in failed_codes_set]) / total if total > 0 else 0.0

    # readiness 判断：只考虑真实失败率，stale 不触发 aborted
    if failure_rate > 0.20:
        readiness = "aborted"
    elif missing_codes:
        readiness = "partial"
    else:
        readiness = "ready"

    prefetch_required = bool(missing_codes) and needs_kline
    prefetch_plan: dict = {}
    if prefetch_required:
        prefetch_plan = {
            "codes_to_fetch": missing_codes,
            "count": len(missing_codes),
            "lookback_days": lookback_days,
            "cache_dir": str(cache_dir),
            "kline_skills_requiring_data": kline_skills,
            "command": (
                f".venv\\Scripts\\python.exe scripts\\data_prefetch.py "
                f"--days {lookback_days} --workers 8"
            ),
        }

    return {
        "prefetch_required": prefetch_required,
        "prefetch_plan": prefetch_plan,
        "prefetch_report": existing_report,
        "readiness": readiness,
        "cached_codes": cached_codes,
        "missing_codes": missing_codes,
        "failed_codes": failed_codes,
        "stale_codes": stale_codes,
        "available_codes": available_codes,
        "failure_rate": round(failure_rate, 4),
        "cache_dir": str(cache_dir),
        "lookback_days": lookback_days,
        "kline_skills": kline_skills,
        "generated_at": datetime.now().isoformat(),
    }
