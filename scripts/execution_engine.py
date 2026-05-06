#!/usr/bin/env python3
"""
execution_engine.py — V6OP 策略执行引擎

接受策略 JSON，完成：
  1. resolve source（来源解析）
  2. plan fetch（数据需求规划）
  3. prefetch if needed（按需预热）
  4. run selected producers（运行 Producer）
  5. build expression（自动生成表达式）
  6. run expression（执行表达式）
  7. build explanations（中文解释）
  8. write run report（输出报告）

用法:
  python scripts/execution_engine.py --demo manual
  python scripts/execution_engine.py --strategy path/to/strategy.json
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# ── 路径 ──────────────────────────────────────────────────────────────
_SCRIPTS_DIR = Path(__file__).parent.resolve()
_PROJECT_ROOT = _SCRIPTS_DIR.parent

# 输出根目录。默认 None 表示使用 _PROJECT_ROOT/output。
# 可由测试通过 monkeypatch 设为 tmp_path，防止写入真实 output/current 和 output/runs。
_OUTPUT_ROOT: Path | None = None

# Mask 缓存目录覆盖。默认 None 表示使用 _PROJECT_ROOT/output/mask_cache。
# 测试通过 monkeypatch 设为 tmp_path，防止 mock 结果污染真实缓存。
_MASK_CACHE_DIR: Path | None = None

for _p in [str(_SCRIPTS_DIR), str(_SCRIPTS_DIR / "producers"),
           str(_SCRIPTS_DIR / "sources")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from time_utils import iso_cst

# ── V6 ExpressionRunner ───────────────────────────────────────────────
_V6_SCRIPTS = _PROJECT_ROOT.parent / "v6" / "scripts"
if str(_V6_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_V6_SCRIPTS))

try:
    from v6.expression_runner import ExpressionRunner  # type: ignore
    from v6.contracts import ExpressionOp, MaskExpression  # type: ignore
    _V6_AVAILABLE = True
except ImportError:
    _V6_AVAILABLE = False

# ── 颜色日志 ──────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
RESET  = "\033[0m"

_LOG_EVENTS: list[dict[str, str]] = []

# 可选实时日志 sink。若设置为 callable(level, msg)，每次 _log() 时同步调用。
# v6op_server 在后台执行前设置此 sink，实现运行中事件实时推送到 /api/stream。
_log_sink = None

# ── 协作式中止标志 ────────────────────────────────────────────────────
# v6op_server 收到 POST /api/abort 后调用 request_abort()。
# execute() 在各步骤边界调用 _check_abort()，发现标志后抛出 AbortRequested。
# 不强杀线程/进程，确保资源正确释放。
_abort_requested: bool = False
_abort_lock = threading.Lock()


class AbortRequested(Exception):
    """用户请求中止执行时从步骤边界抛出，由 _run_execution_background 捕获。"""


def request_abort() -> None:
    global _abort_requested
    with _abort_lock:
        _abort_requested = True


def reset_abort() -> None:
    global _abort_requested
    with _abort_lock:
        _abort_requested = False


def is_abort_requested() -> bool:
    with _abort_lock:
        return _abort_requested


def _check_abort() -> None:
    """步骤边界中止检查：若已请求中止则抛出 AbortRequested。"""
    if is_abort_requested():
        raise AbortRequested("用户已请求中止执行")


def _log(level: str, msg: str) -> None:
    color = {"INFO": GREEN, "WARN": YELLOW, "ERROR": RED, "HEAD": CYAN}.get(level, RESET)
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}]{color}[ExecutionEngine][{level}]{RESET} {msg}"
    print(line, flush=True)
    _LOG_EVENTS.append({"ts": ts, "level": level, "msg": msg})
    if callable(_log_sink):
        try:
            _log_sink(level, msg)
        except Exception:
            pass


def get_log_events() -> list[dict[str, str]]:
    return list(_LOG_EVENTS)


def _log_code_waterfall(
    label: str,
    codes: list[str],
    *,
    limit: int = 5000,
) -> None:
    """Emit V5-style per-code waterfall logs with a guardrail for huge scopes."""
    total = len(codes)
    if total == 0:
        _log("INFO", f"  {label}: 空")
        return
    shown = codes[:limit]
    _log("INFO", f"  {label}: 开始列出 {len(shown)}/{total} 只")
    for idx, code in enumerate(shown, 1):
        _log("INFO", f"    {label} {idx:04d}/{total:04d}: {code}")
    if len(shown) < total:
        _log("INFO", f"    {label}: 还有 {total - len(shown)} 只未展开")


def _make_run_id() -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    salt = hashlib.sha1(ts.encode()).hexdigest()[:6]
    return f"run_{ts}_{salt}"


# ── 内部 Mask 注册与表达式执行 ────────────────────────────────────────

def _run_expression_steps(
    steps: list[dict[str, Any]],
    registry: dict[str, list[str]],
) -> tuple[list[str], list[str]]:
    """
    按顺序执行表达式步骤，将每步结果注册为新 mask。

    Args:
        steps    : expression_auto_generator 生成的步骤列表
        registry : {mask_id: [codes]}，已包含所有 producer mask

    Returns:
        (final_codes, step_summaries)
    """
    from v6.contracts import ExpressionOp, combine_code_sets  # type: ignore

    step_summaries: list[str] = []
    current_codes: list[str] = []

    for step in steps:
        op_str = step.get("op", "AND")
        inputs = step.get("inputs", [])
        params = step.get("params", {})
        expr_id = step.get("expression_id", "expr")

        # 解析 inputs：mask:<mask_id>
        code_sets: list[list[str]] = []
        for ref in inputs:
            if ref.startswith("mask:"):
                mask_id = ref[5:]
                if mask_id in registry:
                    code_sets.append(registry[mask_id])
                else:
                    _log("WARN", f"表达式引用 {ref!r} 不在注册表中，跳过")
                    code_sets.append([])
            else:
                _log("WARN", f"不支持的引用格式 {ref!r}，跳过")
                code_sets.append([])

        if not code_sets:
            current_codes = []
        else:
            try:
                op = ExpressionOp(op_str)
                k = params.get("k")
                top_n = params.get("top_n")
                current_codes = combine_code_sets(op, code_sets, k=k, top_n=top_n)
            except Exception as exc:
                _log("ERROR", f"表达式 {expr_id} 执行失败: {exc}")
                current_codes = []

        # 注册结果：供后续步骤引用
        result_alias = f"{expr_id}_result"
        registry[result_alias] = current_codes

        summary = (
            f"  {expr_id}: {op_str} "
            f"({len(code_sets)} 输入) → {len(current_codes)} 只命中"
        )
        step_summaries.append(summary)
        _log("INFO", summary.strip())

    return current_codes, step_summaries


def _fallback_combine(
    producer_results: list[dict[str, Any]],
    graph: dict[str, Any],
) -> list[str]:
    """V6 不可用时的内置表达式执行（仅支持 AND + EXCLUDE）。"""
    pos_results = [r for r in producer_results if r.get("hit_semantics") == "positive"]
    neg_results = [r for r in producer_results if r.get("hit_semantics") == "negative"]
    merge_op = graph.get("merge_node", {}).get("op", "AND")

    if not pos_results:
        return []

    pos_sets = [set(r.get("hit_codes", [])) for r in pos_results]
    if merge_op == "AND":
        merged = pos_sets[0]
        for s in pos_sets[1:]:
            merged = merged & s
        result = list(merged)
    elif merge_op == "K_OF_N":
        k = graph.get("merge_node", {}).get("params", {}).get("k", 1)
        from collections import Counter
        counts: Counter[str] = Counter()
        for s in pos_sets:
            for code in s:
                counts[code] += 1
        result = [c for c, cnt in counts.items() if cnt >= k]
    else:
        result = list(pos_sets[0])

    if neg_results:
        neg_set: set[str] = set()
        for r in neg_results:
            neg_set.update(r.get("hit_codes", []))
        result = [c for c in result if c not in neg_set]

    return result


# ── Producer 加载 ─────────────────────────────────────────────────────

def _load_producer_run(skill_id: str):
    """动态加载 Producer 的 run() 函数。"""
    module_map = {
        "czsc":     ("producers.czsc_producer",    "run"),
        "smc":      ("producers.smc_producer",     "run"),
        "kline":    ("producers.kline_producer",   "run"),
        "wave":     ("producers.wave_producer",    "run"),
        "landmine": ("producers.landmine_producer","run"),
    }
    if skill_id not in module_map:
        raise ImportError(f"不支持的 skill_id: {skill_id!r}")
    module_name, func_name = module_map[skill_id]
    import importlib
    mod = importlib.import_module(module_name)
    return getattr(mod, func_name)


# ── 主执行函数 ────────────────────────────────────────────────────────

def execute(strategy: dict[str, Any]) -> dict[str, Any]:
    """
    执行策略，返回执行结果 dict。

    strategy 格式：
      {
        "source": {"type": "manual", "codes": [...]} | {"type": "all_a"} | {"type": "wencai", "query": "..."},
        "skills": ["czsc", "kline", "landmine"],
        "path_type": "parallel_and",
        "params": {}
      }
    """
    t_start = time.time()
    _LOG_EVENTS.clear()
    reset_abort()   # 清除上次中止标志，确保新 run 干净启动
    run_id = _make_run_id()
    warnings: list[str] = []
    env_read = False

    _log("HEAD", f"{'='*55}\nV6OP 执行引擎  run_id={run_id}\n{'='*55}")

    # ── 导入本地模块 ──────────────────────────────────────────────────
    import source_resolver
    import fetch_planner
    import strategy_graph_builder
    import expression_auto_generator
    import explanation_builder
    import run_report as run_report_mod
    import mask_cache as _mask_cache
    from skill_registry import get_skill, SKILL_REGISTRY

    skill_registry_dict = {s["skill_id"]: s for s in SKILL_REGISTRY}

    # ── 1. 解析来源 ───────────────────────────────────────────────────
    _log("INFO", "步骤 1/8: 解析股票来源")
    source_cfg = strategy.get("source", {"type": "manual", "codes": []})
    source_type = source_cfg.get("type", "manual")

    if source_type == "wencai":
        env_read = True

    scope = source_resolver.resolve(
        source_type,
        manual_codes=source_cfg.get("codes"),
        wencai_query=source_cfg.get("query"),
        wencai_limit=source_cfg.get("limit", 300),
        ashare_limit=source_cfg.get("limit", 0),
        log_sink=_log,
    )
    api_called = _source_api_called(source_type, scope.get("status", ""))
    scope_codes = scope.get("scope_codes", [])
    _log("INFO", f"  scope: {scope['status']}  count={scope['scope_count']}")
    if scope_codes:
        _log_code_waterfall("来源股票", scope_codes, limit=5000)

    if scope.get("status") not in ("ok",):
        warnings.append(f"来源解析警告: {scope.get('error')}")
        if not scope_codes:
            _log("ERROR", "scope 为空，无法继续执行")
            return _error_result(
                run_id,
                "scope 为空",
                strategy,
                warnings,
                env_read,
                api_called,
                scope=scope,
                elapsed_seconds=round(time.time() - t_start, 2),
            )

    _check_abort()   # 步骤边界: 1→2

    # ── 2. 规划预热 ───────────────────────────────────────────────────
    _log("INFO", "步骤 2/8: 规划数据预热")
    selected_skills = strategy.get("skills", [])
    path_type = strategy.get("path_type", "parallel_and")
    params = strategy.get("params", {})

    cache_dir = _PROJECT_ROOT / "var" / "cache" / "kline_daily"
    fetch = fetch_planner.plan(
        scope_codes=scope_codes,
        selected_skills=selected_skills,
        cache_dir=cache_dir,
    )
    _log("INFO",
         f"  readiness={fetch['readiness']}  "
         f"cached={len(fetch['cached_codes'])}  "
         f"missing={len(fetch['missing_codes'])}  "
         f"failed={len(fetch['failed_codes'])}")

    if fetch["readiness"] == "aborted":
        _aborted_msg = (
            f"失败率 {fetch['failure_rate']:.1%} > 20%，readiness=aborted，"
            "中止 Producer 执行（总纲第九章）"
        )
        warnings.append(_aborted_msg)
        _log("ERROR", _aborted_msg)
        # 按总纲：失败率 >20% 时本批不得继续执行 Producer，返回 aborted 结果
        _out_root = _OUTPUT_ROOT or (_PROJECT_ROOT / "output")
        output_dir = _out_root / "current"
        output_dir.mkdir(parents=True, exist_ok=True)
        aborted_result: dict[str, Any] = {
            "run_id": run_id,
            "generated_at": iso_cst(),
            "elapsed_seconds": round(time.time() - t_start, 2),
            "status": "aborted",
            "aborted_reason": _aborted_msg,
            "strategy": strategy,
            "selected_skills": selected_skills,
            "path_type": path_type,
            "params": params,
            "scope": scope,
            "fetch_plan": fetch,
            "graph": {},
            "producer_results": [],
            "expression_spec": {},
            "final_hit_codes": [],
            "final_hit_count": 0,
            "explanations": {},
            "warnings": warnings,
            "env_read": env_read,
            "prefetch_triggered": False,
            "mask_cache_hits": 0,
            "mask_cache_misses": 0,
            "api_called": api_called,
            "v5_modified": False,
            "v6_modified": False,
        }
        _write_result_artifacts(aborted_result)
        return aborted_result

    _check_abort()   # 步骤边界: 2→3

    # ── 3. 真实预热（如有缺失缓存则自动调用 data_prefetch）─────────────
    _log("INFO", "步骤 3/8: 准备数据 — 检查缓存")
    _prefetch_triggered = False
    _prefetch_exception_missing: set[str] = set()
    if fetch["prefetch_required"]:
        missing = fetch["missing_codes"]
        _log("INFO", f"  缓存缺失 {len(missing)} 只，启动真实预热…")
        if len(missing) > 200:
            _log("WARN",
                 f"  ⚠ 预热范围较大（{len(missing)} 只），耗时可能超过 60 秒")

        import data_prefetch as _dp  # type: ignore
        # 用所有技能中最大的 days 参数作为预热天数
        prefetch_days = max(
            (params.get("skills", {}).get(s, {}).get("days", 365)
             for s in selected_skills),
            default=365,
        )
        report_dir = _PROJECT_ROOT / "output" / "current"

        try:
            _prefetch_triggered = True
            prefetch_stats = _dp.run_prefetch(
                codes=missing,
                days=prefetch_days,
                workers=8,
                cache_dir=cache_dir,
                report_dir=report_dir,
            )
            _log("INFO",
                 f"  预热完成  命中缓存={prefetch_stats.get('cache_hit', 0)}  "
                 f"新拉={prefetch_stats.get('fetched_ok', 0)}  "
                 f"恢复={prefetch_stats.get('recovered_count', 0)}  "
                 f"失败={prefetch_stats.get('failed', 0)}  "
                 f"耗时={prefetch_stats.get('duration_seconds', 0)}s")
            # 重新规划：读取刚写入的 prefetch_report
            fetch = fetch_planner.plan(
                scope_codes=scope_codes,
                selected_skills=selected_skills,
                cache_dir=cache_dir,
            )
            _log("INFO",
                 f"  重规划后 readiness={fetch['readiness']}  "
                 f"cached={len(fetch['cached_codes'])}  "
                 f"missing={len(fetch['missing_codes'])}")
        except Exception as _exc:
            _log("ERROR", f"  预热失败: {_exc}")
            warnings.append(f"预热失败: {_exc}")
            # 预热异常时，原本 missing 的代码没有数据，加入失败集合避免被 Producer 分析
            _prefetch_exception_missing = set(fetch.get("missing_codes", []))
    else:
        _log("INFO", "  缓存充足或无需 K 线，跳过预热")

    _check_abort()   # 步骤边界: 3→4

    # data_time_max 用于 mask_cache 指纹（总纲第十章）
    # 无论 prefetch 是否触发，都从本地 .pkl 缓存实际读取最大日期，
    # 避免缓存充足时 data_date="" 导致错误复用旧 Mask。
    _data_time_max: str = ""
    try:
        _data_time_max = _mask_cache.compute_scope_data_time_max(
            codes=scope_codes,
            cache_dir=cache_dir,
        )
    except Exception:
        pass
    if not _data_time_max and _prefetch_triggered:
        # 备选：从 prefetch_report 取（prefetch 触发后 report 有值）
        try:
            pr = fetch.get("prefetch_report") or {}
            _data_time_max = str(pr.get("data_time_max", ""))[:10]
        except Exception:
            pass
    _mc_dir = _MASK_CACHE_DIR if _MASK_CACHE_DIR is not None else (_PROJECT_ROOT / "output" / "mask_cache")

    # ── 4. 构建策略图 ──────────────────────────────────────────────────
    _log("INFO", "步骤 4/8: 构建策略图")
    graph = strategy_graph_builder.build(
        selected_skills=selected_skills,
        skill_registry=skill_registry_dict,
        path_type=path_type,
    )
    _log("INFO",
         f"  path_type={path_type}  "
         f"positive={graph['positive_skill_count']}  "
         f"negative={graph['negative_skill_count']}")

    _check_abort()   # 步骤边界: 4→5

    # ── 5. 运行 Producer（路径感知）──────────────────────────────────────
    _log("INFO", "步骤 5/8: 运行 Producer")
    producer_results: list[dict[str, Any]] = []
    os.environ["READ_CACHE_ONLY"] = "true"
    os.environ["KLINE_CACHE_DIR"] = str(cache_dir)

    # Producer 实际输入：排除 prefetch_report 中已知失败的代码。
    # _prefetch_exception_missing：预热抛异常时 missing_codes 无缓存，同样排除。
    # 不变式：不能既在 failed_codes 又被 Producer 当正常股票分析。
    _failed_set = set(fetch.get("failed_codes", [])) | _prefetch_exception_missing
    producer_scope = [c for c in scope_codes if c not in _failed_set]
    if len(producer_scope) < len(scope_codes):
        _log("INFO",
             f"  排除已知失败代码 {len(scope_codes) - len(producer_scope)} 只，"
             f"Producer 实际输入 {len(producer_scope)} 只")

    def _sp(skill_id: str, key: str, default: Any) -> Any:
        """读取技能参数：优先 params.skills.<skill_id>，其次 flat params，再用默认值。"""
        skill_scoped = params.get("skills", {}).get(skill_id, {})
        if key in skill_scoped:
            return skill_scoped[key]
        if key in params:
            return params[key]
        return default

    def _run_one(skill_id: str, codes: list[str]) -> dict[str, Any] | None:
        """运行单个技能 Producer，返回结果 dict，不支持时返回 None。"""
        skill_meta = get_skill(skill_id)
        if skill_meta is None:
            _log("WARN", f"  技能 {skill_id!r} 不在注册表中，跳过")
            warnings.append(f"技能 {skill_id!r} 不在注册表，已跳过")
            return None

        _log("INFO",
             f"  → 运行 {skill_meta['skill_name']} ({skill_id})  [{len(codes)} 只输入]")
        t_skill = time.time()

        try:
            run_fn = _load_producer_run(skill_id)

            if skill_id == "czsc":
                sp = {
                    "signal_bars": _sp("czsc", "signal_bars", 5),
                    "buy_type":    _sp("czsc", "buy_type",    "all"),
                    "days":        _sp("czsc", "days",        365),
                }
            elif skill_id == "smc":
                sp = {
                    "signal_bars":  _sp("smc", "signal_bars",  15),
                    "swing_length": _sp("smc", "swing_length", 10),
                    "close_break":  _sp("smc", "close_break",  True),
                    "mode":         _sp("smc", "mode",         _sp("smc", "smc_mode", "strict")),
                    "days":         _sp("smc", "days",         365),
                }
            elif skill_id == "kline":
                sp = {
                    "signal_bars":  _sp("kline", "signal_bars",  5),
                    "body_pct":     _sp("kline", "body_pct",     0.1),
                    "shadow_ratio": _sp("kline", "shadow_ratio", 2.0),
                    "pass_neutral": _sp("kline", "pass_neutral", False),
                    "days":         _sp("kline", "days",         365),
                }
            elif skill_id == "wave":
                sp = {
                    "signal_bars":   _sp("wave", "signal_bars",   20),
                    "swing_window":  _sp("wave", "swing_window",  10),
                    "fib_tolerance": _sp("wave", "fib_tolerance", 0.15),
                    "min_wave_bars": _sp("wave", "min_wave_bars", 5),
                    "days":          _sp("wave", "days",          365),
                }
            elif skill_id == "landmine":
                sp = {"days": _sp("landmine", "days", 365)}
            else:
                _log("WARN", f"  技能 {skill_id!r} 暂不支持动态调用，跳过")
                return None

            # ── 内容寻址 Mask 缓存（总纲第十章）────────────────────────────
            _fp = _mask_cache.compute_fingerprint(
                skill_id=skill_id,
                scope_codes=codes,
                params=sp,
                data_date=_data_time_max,
            )
            _cached = _mask_cache.cache_get(_fp, cache_dir=_mc_dir)
            if _cached is not None:
                _cached.setdefault("skill_id", skill_id)
                _cached.setdefault("skill_name", skill_meta.get("skill_name", skill_id))
                _cached.setdefault("hit_semantics", skill_meta.get("hit_semantics", "positive"))
                _cached["status"] = "ok"
                _cached["mask_cache_hit"] = True
                _log("INFO",
                     f"    {skill_id}: mask_cache_hit=true  "
                     f"hit={_cached.get('hit_count', 0)}  "
                     f"fp={_fp[:10]}…")
                _log_code_waterfall(
                    f"{skill_id} 命中明细",
                    _cached.get("hit_codes", []),
                    limit=500,
                )
                return _cached
            # ── cache miss: 执行 producer ─────────────────────────────────

            if skill_id == "landmine":
                result = run_fn(codes=codes, cache_dir=cache_dir, **sp)
                result["params_used"] = result.get("params", sp)
            else:
                result = run_fn(codes=codes, cache_dir=cache_dir, **sp)
                result["params_used"] = sp

            result["mask_cache_hit"] = False
            _mask_cache.cache_put(_fp, result, cache_dir=_mc_dir)

            result.setdefault("skill_id", skill_id)
            result.setdefault("skill_name", skill_meta.get("skill_name", skill_id))
            result.setdefault("hit_semantics", skill_meta.get("hit_semantics", "positive"))
            result["status"] = "ok"
            result["duration_seconds"] = round(time.time() - t_skill, 2)
            _log("INFO",
                 f"    {skill_id}: hit={result.get('hit_count', 0)}  "
                 f"miss={result.get('miss_count', 0)}  "
                 f"{result['duration_seconds']}s  fp={_fp[:10]}…")
            _log_code_waterfall(
                f"{skill_id} 命中明细",
                result.get("hit_codes", []),
                limit=500,
            )
            return result

        except Exception as exc:
            _log("ERROR", f"  {skill_id} 运行失败: {exc}")
            warnings.append(f"{skill_id} 运行失败: {exc}")
            skill_meta2 = get_skill(skill_id) or {}
            return {
                "skill_id": skill_id,
                "skill_name": skill_meta2.get("skill_name", skill_id),
                "hit_semantics": skill_meta2.get("hit_semantics", "positive"),
                "hit_codes": [],
                "miss_codes": list(codes),
                "evidence": {},
                "params": {},
                "mask_id": f"{skill_id}_error",
                "hit_count": 0,
                "miss_count": len(codes),
                "status": "error",
                "error": str(exc),
            }

    # 按语义分类（正向 / 负向）
    pos_skills = [
        s for s in selected_skills
        if skill_registry_dict.get(s, {}).get("hit_semantics", "positive") == "positive"
    ]
    neg_skills = [
        s for s in selected_skills
        if skill_registry_dict.get(s, {}).get("hit_semantics", "positive") == "negative"
    ]

    # pre_exclude_codes: sequential/hybrid 路径直接计算出的正向结果（再 EXCLUDE 负向）
    # None 表示使用 expression pipeline（parallel_and）
    pre_exclude_codes: list[str] | None = None

    if path_type == "sequential" and pos_skills:
        # ── 顺序漏斗：每个正向技能吃上一个的 hit_codes ──────────────────
        _log("INFO",
             f"  路径=sequential  链式过滤: {' → '.join(pos_skills)}"
             + (f"  排雷: {neg_skills}" if neg_skills else ""))
        current_scope = list(producer_scope)

        for skill_id in pos_skills:
            _check_abort()   # 每个技能前检查中止
            if not current_scope:
                _log("WARN", f"  上游已为空，跳过 {skill_id} 及后续正向技能")
                sk = skill_registry_dict.get(skill_id, {})
                producer_results.append({
                    "skill_id": skill_id,
                    "skill_name": sk.get("skill_name", skill_id),
                    "hit_semantics": "positive",
                    "hit_codes": [], "miss_codes": [],
                    "evidence": {}, "params": {},
                    "mask_id": f"{skill_id}_skipped",
                    "hit_count": 0, "miss_count": 0,
                    "status": "skipped",
                    "notes": "上游输入为空，已跳过",
                })
                continue

            result = _run_one(skill_id, current_scope)
            if result:
                producer_results.append(result)
                prev = len(current_scope)
                current_scope = result.get("hit_codes", [])
                _log("INFO", f"    漏斗: 输入 {prev} → 输出 {len(current_scope)}")

        pre_exclude_codes = current_scope

        # 负向技能对 producer_scope（不含已知失败）运行
        for skill_id in neg_skills:
            result = _run_one(skill_id, producer_scope)
            if result:
                producer_results.append(result)

    elif path_type == "simple_hybrid" and pos_skills:
        # ── 简单混合：前2个正向并线AND → 后续顺序过滤 → EXCLUDE负向 ────
        parallel_pos = pos_skills[:2]
        seq_pos = pos_skills[2:]
        label = (
            f"并线AND({'+'.join(parallel_pos)})"
            + (f" → 顺序({' → '.join(seq_pos)})" if seq_pos else "")
        )
        _log("INFO", f"  路径=simple_hybrid  {label}")

        # 阶段一：并线 AND（producer_scope）
        parallel_results: list[dict[str, Any]] = []
        for skill_id in parallel_pos:
            _check_abort()
            result = _run_one(skill_id, producer_scope)
            if result:
                parallel_results.append(result)
                producer_results.append(result)

        # 计算 AND 交集
        if parallel_results:
            sets = [set(r.get("hit_codes", [])) for r in parallel_results]
            intermediate = list(sets[0].intersection(*sets[1:])) if len(sets) > 1 else list(sets[0])
        else:
            intermediate = list(producer_scope)
        _log("INFO", f"  并线 AND 结果: {len(intermediate)} 只")

        # 阶段二：顺序过滤（中间结果）
        current_scope = intermediate
        for skill_id in seq_pos:
            _check_abort()
            if not current_scope:
                _log("WARN", f"  混合路径中间结果为空，跳过 {skill_id}")
                break
            result = _run_one(skill_id, current_scope)
            if result:
                producer_results.append(result)
                prev = len(current_scope)
                current_scope = result.get("hit_codes", [])
                _log("INFO", f"    顺序过滤: {prev} → {len(current_scope)}")

        pre_exclude_codes = current_scope

        # 负向技能对 producer_scope（不含已知失败）运行
        for skill_id in neg_skills:
            result = _run_one(skill_id, producer_scope)
            if result:
                producer_results.append(result)

    else:
        # ── parallel_and（默认）：所有技能对 producer_scope 并行运行 ──
        if path_type not in ("parallel_and",):
            _log("WARN", f"  未知路径 {path_type!r}，回退到 parallel_and")
        else:
            _log("INFO", "  路径=parallel_and  所有技能对全集并行运行")

        for skill_id in selected_skills:
            _check_abort()
            result = _run_one(skill_id, producer_scope)
            if result:
                producer_results.append(result)

    _check_abort()   # 步骤边界: 5→6

    # ── 6. 自动生成 MaskExpression ────────────────────────────────────
    _log("INFO", "步骤 6/8: 生成表达式规格（报告用）")
    expression_spec = expression_auto_generator.generate(
        producer_results=producer_results,
        graph=graph,
    )
    warnings.extend(expression_spec.get("warnings", []))
    for w in expression_spec.get("warnings", []):
        _log("WARN", f"  {w}")

    _log("INFO", "步骤 7/8: 执行表达式")
    final_hit_codes: list[str] = []

    if pre_exclude_codes is not None:
        # sequential / simple_hybrid: 正向结果已在 step 5 算好，只需 EXCLUDE 负向
        neg_hits: set[str] = set()
        for _r in producer_results:
            if _r.get("hit_semantics") == "negative":
                neg_hits.update(_r.get("hit_codes", []))
        final_hit_codes = [c for c in pre_exclude_codes if c not in neg_hits]
        _log("INFO",
             f"  {path_type}: 正向结果 {len(pre_exclude_codes)}  "
             f"排雷排除 {len(pre_exclude_codes) - len(final_hit_codes)}  "
             f"最终 {len(final_hit_codes)}")
    else:
        # parallel_and: expression runner (AND + EXCLUDE)
        mask_registry: dict[str, list[str]] = {}
        for prod in producer_results:
            mid = prod.get("mask_id", "")
            if mid:
                mask_registry[mid] = prod.get("hit_codes", [])

        steps = expression_spec.get("steps", [])

        if _V6_AVAILABLE and steps:
            final_hit_codes, step_summaries = _run_expression_steps(steps, mask_registry)
            for s in step_summaries:
                _log("INFO", s)
        elif steps:
            _log("WARN", "V6 不可用，使用内置 AND+EXCLUDE 逻辑")
            warnings.append("V6 ExpressionRunner 不可用，使用内置逻辑")
            final_hit_codes = _fallback_combine(producer_results, graph)
        else:
            _log("WARN", "无表达式步骤，回退到内置逻辑")
            final_hit_codes = _fallback_combine(producer_results, graph)

    _log("INFO", f"  最终命中: {len(final_hit_codes)} 只")

    # ── 8. 中文解释 & 报告 ────────────────────────────────────────────
    _log("INFO", "步骤 8/8: 生成中文解释与报告")
    explanations = explanation_builder.build(
        hit_codes=final_hit_codes,
        producer_results=producer_results,
        expr_metadata=expression_spec.get("metadata", {}),
        failed_codes=fetch.get("failed_codes", []),
        stale_codes=fetch.get("stale_codes", []),
    )

    elapsed = round(time.time() - t_start, 2)

    # prefetch_triggered=False 时历史 prefetch_report 不代表本次运行；
    # 清空避免把 scope 外旧失败代码写入当前 execution_result / run_report。
    fetch_for_result = {
        **fetch,
        "prefetch_report": fetch.get("prefetch_report") if _prefetch_triggered else None,
        "data_time_max": _data_time_max,
    }

    execution_result: dict[str, Any] = {
        "run_id": run_id,
        "generated_at": iso_cst(),
        "elapsed_seconds": elapsed,
        "status": "completed",
        "strategy": strategy,
        "selected_skills": selected_skills,
        "path_type": path_type,
        "params": params,
        "scope": scope,
        "fetch_plan": fetch_for_result,
        "data_time_max": _data_time_max,
        "graph": graph,
        "producer_results": producer_results,
        "expression_spec": expression_spec,
        "final_hit_codes": final_hit_codes,
        "final_hit_count": len(final_hit_codes),
        "explanations": explanations,
        "warnings": warnings,
        "env_read": env_read,
        "prefetch_triggered": _prefetch_triggered,
        "mask_cache_hits": sum(
            1 for r in producer_results if r.get("mask_cache_hit") is True
        ),
        "mask_cache_misses": sum(
            1 for r in producer_results if r.get("mask_cache_hit") is False
        ),
        "api_called": api_called,
        "v5_modified": False,
        "v6_modified": False,
    }

    # ── 写输出文件 ─────────────────────────────────────────────────────
    _out_root = _OUTPUT_ROOT or (_PROJECT_ROOT / "output")
    output_dir = _out_root / "current"
    output_dir.mkdir(parents=True, exist_ok=True)
    # 每次运行归档目录
    archive_dir = _out_root / "runs" / run_id
    archive_dir.mkdir(parents=True, exist_ok=True)

    exec_result_json = json.dumps(execution_result, ensure_ascii=False, indent=2)

    exec_result_path = output_dir / "execution_result.json"
    exec_result_path.write_text(exec_result_json, encoding="utf-8")
    (archive_dir / "execution_result.json").write_text(exec_result_json, encoding="utf-8")

    report_paths = run_report_mod.generate(execution_result, output_dir)
    run_report_mod.generate(execution_result, archive_dir)

    _log("HEAD",
         f"\n{'='*55}\n执行完成  run_id={run_id}  "
         f"elapsed={elapsed}s  "
         f"final_hits={len(final_hit_codes)}\n{'='*55}")
    _log("INFO", f"  execution_result.json → {exec_result_path}")
    _log("INFO", f"  run_report.json → {report_paths['report_json_path']}")
    _log("INFO", f"  run_report.md → {report_paths['report_md_path']}")
    _log("INFO", f"  归档目录 → {archive_dir}")

    return execution_result


def _error_result(
    run_id: str,
    error: str,
    strategy: dict[str, Any],
    warnings: list[str],
    env_read: bool,
    api_called: bool = False,
    *,
    scope: dict[str, Any] | None = None,
    elapsed_seconds: float | None = None,
) -> dict[str, Any]:
    error_result = {
        "run_id": run_id,
        "generated_at": iso_cst(),
        "elapsed_seconds": elapsed_seconds,
        "status": "error",
        "error": error,
        "strategy": strategy,
        "selected_skills": strategy.get("skills", []),
        "path_type": strategy.get("path_type", ""),
        "params": strategy.get("params", {}),
        "scope": scope or {},
        "fetch_plan": {
            "readiness": "aborted",
            "cached_codes": [],
            "missing_codes": [],
            "failed_codes": [],
            "stale_codes": [],
            "failure_rate": 0.0,
            "prefetch_report": None,
        },
        "graph": {},
        "producer_results": [],
        "expression_spec": {},
        "final_hit_codes": [],
        "final_hit_count": 0,
        "explanations": {},
        "warnings": warnings,
        "prefetch_triggered": False,
        "mask_cache_hits": 0,
        "mask_cache_misses": 0,
        "env_read": env_read,
        "api_called": api_called,
        "v5_modified": False,
        "v6_modified": False,
    }
    _write_result_artifacts(error_result)
    return error_result


def _write_result_artifacts(execution_result: dict[str, Any]) -> None:
    """Write execution_result and frontend run_report for terminal non-success runs."""
    import run_report as run_report_mod

    _out_root = _OUTPUT_ROOT or (_PROJECT_ROOT / "output")
    output_dir = _out_root / "current"
    archive_dir = _out_root / "runs" / execution_result["run_id"]
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)

    exec_result_json = json.dumps(execution_result, ensure_ascii=False, indent=2)
    exec_result_path = output_dir / "execution_result.json"
    exec_result_path.write_text(exec_result_json, encoding="utf-8")
    (archive_dir / "execution_result.json").write_text(exec_result_json, encoding="utf-8")

    report_paths = run_report_mod.generate(execution_result, output_dir)
    run_report_mod.generate(execution_result, archive_dir)

    _log("INFO", f"  execution_result.json → {exec_result_path}")
    _log("INFO", f"  run_report.json → {report_paths['report_json_path']}")
    _log("INFO", f"  run_report.md → {report_paths['report_md_path']}")
    _log("INFO", f"  归档目录 → {archive_dir}")


def _source_api_called(source_type: str, source_status: str) -> bool:
    """Whether source resolution attempted an external stock-source API."""
    if source_type != "wencai":
        return False
    return source_status not in {"key_missing", "blocked"}


# ── Demo 策略 ─────────────────────────────────────────────────────────

DEMO_STRATEGIES = {
    "manual": {
        "source": {
            "type": "manual",
            "codes": ["000001.SZ", "000002.SZ", "000063.SZ"],
        },
        "skills": ["czsc", "kline", "landmine"],
        "path_type": "parallel_and",
        "params": {},
    },
    "all_a_small": {
        "source": {
            "type": "all_a",
            "limit": 20,
        },
        "skills": ["kline", "landmine"],
        "path_type": "parallel_and",
        "params": {},
    },
}


def main() -> int:
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )

    parser = argparse.ArgumentParser(description="V6OP 策略执行引擎")
    parser.add_argument(
        "--demo", metavar="NAME",
        help="运行内置 demo 策略（可选: manual, all_a_small）",
    )
    parser.add_argument(
        "--strategy", metavar="FILE",
        help="从 JSON 文件加载策略",
    )
    args = parser.parse_args()

    if args.demo:
        name = args.demo
        if name not in DEMO_STRATEGIES:
            _log("ERROR", f"未知 demo: {name!r}，可用: {list(DEMO_STRATEGIES.keys())}")
            return 1
        strategy = DEMO_STRATEGIES[name]
        _log("INFO", f"使用 demo 策略: {name}")
    elif args.strategy:
        strategy_path = Path(args.strategy)
        if not strategy_path.exists():
            _log("ERROR", f"策略文件不存在: {strategy_path}")
            return 1
        strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    else:
        _log("INFO", "未指定策略，使用默认 demo manual")
        strategy = DEMO_STRATEGIES["manual"]

    result = execute(strategy)
    status = result.get("status", "unknown")
    hits = result.get("final_hit_count", 0)
    elapsed = result.get("elapsed_seconds", 0)

    print(json.dumps({
        "status": status,
        "run_id": result.get("run_id"),
        "final_hit_count": hits,
        "elapsed_seconds": elapsed,
        "warnings_count": len(result.get("warnings", [])),
    }, ensure_ascii=False, indent=2))

    return 0 if status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
