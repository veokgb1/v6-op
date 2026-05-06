#!/usr/bin/env python3
"""
explanation_builder.py — V6OP 中文解释构建器

为最终命中生成每只股票的中文解释，包括：
- 命中哪些技能
- 每个技能的中文理由
- 是否用了后复权数据
- 是否受 SMC soft_filter / Wave 辅助放行影响
- 是否有数据缺失或旧K线风险

失败 / 未分析股票单列，不混进命中列表。
"""
from __future__ import annotations

from typing import Any


_SKILL_NAME_ZH: dict[str, str] = {
    "czsc": "缠论买点",
    "smc": "SMC聪明钱",
    "kline": "K线形态",
    "wave": "波浪分析",
    "landmine": "排雷过滤",
    "wencai": "问财选股",
}


def _czsc_reason(evidence: dict[str, Any]) -> str:
    buy_type = evidence.get("buy_type", "")
    last_date = evidence.get("last_signal_date", "")
    bi_count = evidence.get("bi_count", 0)
    parts: list[str] = []
    if buy_type:
        _type_cn = {"1st": "一买", "2nd": "二买", "3rd": "三买"}
        parts.append(f"检测到{_type_cn.get(buy_type, buy_type)}买点")
    else:
        parts.append("检测到缠论买点信号")
    if last_date:
        parts.append(f"最近信号日期 {last_date}")
    if bi_count:
        parts.append(f"当前笔数 {bi_count}")
    return "；".join(parts)


def _smc_reason(evidence: dict[str, Any], metadata: dict[str, Any]) -> str:
    sig = evidence.get("signal_type", "")
    date = evidence.get("last_signal_date", "")
    fvg = evidence.get("fvg_confirmed", False)
    mode = evidence.get("mode", "")

    parts: list[str] = []
    if sig:
        parts.append(f"{sig} 信号")
    if date:
        parts.append(f"最近信号日期 {date}")
    if fvg:
        parts.append("FVG 公允价值缺口确认")

    soft_filter_skills = metadata.get("soft_filter_skills", [])
    if "smc" in soft_filter_skills or mode == "soft_filter":
        parts.append("[soft_filter 模式：软过滤/透传，非 strict 正向命中]")

    return "；".join(parts) if parts else "SMC 聪明钱信号"


def _kline_reason(evidence: dict[str, Any]) -> str:
    score = evidence.get("total_score", 0)
    bull_pats = evidence.get("bull_patterns", [])
    bear_pats = evidence.get("bear_patterns", [])
    last_date = evidence.get("last_signal_date", "")
    parts: list[str] = []
    if bull_pats:
        parts.append(f"多头形态：{', '.join(str(p) for p in bull_pats[:3])}")
    if bear_pats:
        parts.append(f"空头形态：{', '.join(str(p) for p in bear_pats[:3])}")
    if not bull_pats and not bear_pats:
        parts.append("K线形态命中")
    if score:
        parts.append(f"形态净评分 {score:+d}")
    if last_date:
        parts.append(f"最近信号 {last_date}")
    return "；".join(parts) if parts else "K线形态命中"


def _wave_reason(evidence: dict[str, Any], metadata: dict[str, Any]) -> str:
    verdict = evidence.get("verdict", "")
    last_signal = evidence.get("last_signal", "")
    all_signals_count = evidence.get("all_signals_count", 0)

    auxiliary_signal_skills = metadata.get("weak_signal_skills", [])
    is_auxiliary = "wave" in auxiliary_signal_skills or verdict == "no_top"

    parts: list[str] = []
    if verdict == "abc_bottom":
        parts.append("检测到 ABC 底部形态（椭圆底）")
    elif verdict == "no_top":
        parts.append("未检测到5浪顶部，辅助放行")
    elif verdict:
        parts.append(f"波浪判断：{verdict}")
    if last_signal:
        parts.append(f"最近信号：{last_signal}")
    if all_signals_count:
        parts.append(f"信号总数 {all_signals_count}")
    if is_auxiliary:
        parts.append("（辅助放行，不应视为强买入结论）")

    return "；".join(parts) if parts else "波浪分析通过"


def _landmine_reason(evidence: dict[str, Any]) -> str:
    reasons = evidence.get("reasons", [])
    return "排雷命中（应剔除）：" + "；".join(reasons) if reasons else "排雷命中"


def _per_skill_reason(
    code: str,
    skill_id: str,
    producer_result: dict[str, Any],
    expr_metadata: dict[str, Any],
) -> str:
    evidence = producer_result.get("evidence", {}).get(code, {})
    if not evidence:
        return f"{_SKILL_NAME_ZH.get(skill_id, skill_id)} 命中（无详细证据）"

    if skill_id == "czsc":
        return _czsc_reason(evidence)
    elif skill_id == "smc":
        return _smc_reason(evidence, expr_metadata)
    elif skill_id == "kline":
        return _kline_reason(evidence)
    elif skill_id == "wave":
        return _wave_reason(evidence, expr_metadata)
    elif skill_id == "landmine":
        return _landmine_reason(evidence)
    else:
        return f"{_SKILL_NAME_ZH.get(skill_id, skill_id)} 命中"


def build(
    hit_codes: list[str],
    producer_results: list[dict[str, Any]],
    expr_metadata: dict[str, Any],
    *,
    failed_codes: list[str] | None = None,
    stale_codes: list[str] | None = None,
) -> dict[str, Any]:
    """
    为最终命中生成中文解释。

    Args:
        hit_codes        : 最终命中代码列表
        producer_results : 各 Producer 的 run() 输出
        expr_metadata    : expression_auto_generator 的 metadata
        failed_codes     : 已知失败代码（来自 fetch_planner）
        stale_codes      : 已知 stale 代码（来自 fetch_planner）

    Returns dict with:
        hits    : list[dict] - 每只命中股票的详细解释
        failed  : list[dict] - 失败股票列表
        stale_warnings : list[str] - stale 数据警告
    """
    failed_set = set(failed_codes or [])
    stale_set = set(stale_codes or [])

    # 按 skill_id 建立 producer 结果索引
    producer_by_skill: dict[str, dict[str, Any]] = {
        r.get("skill_id", ""): r for r in producer_results
    }

    # soft_filter / auxiliary signal 标注
    soft_filter_skills = set(expr_metadata.get("soft_filter_skills", []))
    weak_signal_skills = set(expr_metadata.get("weak_signal_skills", []))

    hits: list[dict[str, Any]] = []
    stale_warnings: list[str] = []

    for code in hit_codes:
        skill_hits: list[dict[str, Any]] = []
        uses_hfq = False
        has_soft_filter = False
        has_weak_signal = False
        data_quality_issues: list[str] = []

        for skill_id, prod_result in producer_by_skill.items():
            if prod_result.get("hit_semantics") == "negative":
                continue  # 负向技能不在命中解释中

            in_hit_codes = code in (prod_result.get("hit_codes") or [])
            if not in_hit_codes:
                continue

            evidence = prod_result.get("evidence", {}).get(code, {})
            adjust = evidence.get("adjust", "") or prod_result.get("adjust", "")
            if adjust == "hfq":
                uses_hfq = True

            if skill_id in soft_filter_skills:
                has_soft_filter = True
            if skill_id in weak_signal_skills:
                has_weak_signal = True

            reason = _per_skill_reason(code, skill_id, prod_result, expr_metadata)
            skill_hits.append({
                "skill_id": skill_id,
                "skill_name": _SKILL_NAME_ZH.get(skill_id, skill_id),
                "hit": True,
                "reason_cn": reason,
                "mode": (
                    "soft_filter" if skill_id in soft_filter_skills
                    else ("weak_signal" if skill_id in weak_signal_skills else "normal")
                ),
            })

        # 数据质量警告
        if code in stale_set:
            data_quality_issues.append("可能使用旧K线数据，结果仅供参考")
            stale_warnings.append(f"{code}: 使用旧K线数据")

        explanation_parts: list[str] = []
        if skill_hits:
            explanation_parts.append(
                f"命中 {len(skill_hits)} 个技能："
                + "、".join(s["skill_name"] for s in skill_hits)
            )
        if uses_hfq:
            explanation_parts.append("后复权(hfq)数据")
        if has_soft_filter:
            explanation_parts.append("⚠ SMC soft_filter 软过滤模式")
        if has_weak_signal:
            explanation_parts.append("⚠ 波浪辅助放行（no_top）")
        if data_quality_issues:
            explanation_parts.append("⚠ " + "；".join(data_quality_issues))

        hits.append({
            "code": code,
            "skill_hits": skill_hits,
            "hit_skill_count": len(skill_hits),
            "uses_hfq": uses_hfq,
            "has_soft_filter_mode": has_soft_filter,
            "has_weak_signal": has_weak_signal,
            "data_quality_issues": data_quality_issues,
            "explanation_cn": "；".join(explanation_parts) or "命中（无详细证据）",
        })

    # 失败代码单列
    failed: list[dict[str, Any]] = []
    for code in (failed_codes or []):
        failed.append({
            "code": code,
            "reason_cn": "数据预热失败，无法分析",
            "type": "fetch_failed",
        })

    return {
        "hits": hits,
        "hit_count": len(hits),
        "failed": failed,
        "failed_count": len(failed),
        "stale_warnings": stale_warnings,
        "soft_filter_mode_active": bool(soft_filter_skills),
        "weak_signal_active": bool(weak_signal_skills),
    }


def build_global_explanation(
    scope: dict[str, Any],
    fetch_plan: dict[str, Any],
    producer_results: list[dict[str, Any]],
    expression_spec: dict[str, Any],
    final_hit_codes: list[str],
    path_type: str,
    *,
    data_provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    G2: 构建五层全局解释契约。
    命中 0 时通过 why_zero 指出是哪一层导致清零。
    """
    final_count = len(final_hit_codes)

    # ── 来源层 ────────────────────────────────────────────────────────
    src_status = scope.get("status", "unknown")
    src_count = scope.get("scope_count", 0)
    src_type = scope.get("source_type", "unknown")
    source_layer: dict[str, Any] = {
        "source_type": src_type,
        "status": src_status,
        "actual_count": src_count,
        "api_called": scope.get("api_called", False),
        "query_text": scope.get("query_text", ""),
        "count_note": scope.get("count_note", ""),
        "ok": src_count > 0,
        "suggestion": (
            "来源返回 0 只股票，请检查查询条件、接口授权或切换来源" if src_count == 0 else ""
        ),
    }

    # ── 数据层 ────────────────────────────────────────────────────────
    cached = len(fetch_plan.get("cached_codes", []))
    missing = len(fetch_plan.get("missing_codes", []))
    failed = len(fetch_plan.get("failed_codes", []))
    stale = len(fetch_plan.get("stale_codes", []))
    readiness = fetch_plan.get("readiness", "unknown")
    dp = data_provenance or {}
    data_layer: dict[str, Any] = {
        "readiness": readiness,
        "cached": cached,
        "missing": missing,
        "failed": failed,
        "stale": stale,
        "fetched_new": dp.get("fetched_new", 0),
        "degraded": dp.get("degraded", 0),
        "oldest_data_date": dp.get("oldest_data_date", ""),
        "ok": failed == 0 and readiness != "aborted",
        "suggestion": (
            f"K线取数失败 {failed} 只，可能减少可分析股票数量" if failed > 0 else (
                "K线就绪率低，请检查网络或缓存目录" if readiness == "aborted" else ""
            )
        ),
    }

    # ── 技能层 ────────────────────────────────────────────────────────
    skill_stats: list[dict[str, Any]] = []
    first_zero_skill = ""
    for prod in producer_results:
        sid = prod.get("skill_id", "?")
        semantics = prod.get("hit_semantics", "positive")
        in_count = prod.get("total_in", prod.get("miss_count", 0) + prod.get("hit_count", 0))
        hit_count = prod.get("hit_count", 0)
        stat: dict[str, Any] = {
            "skill_id": sid,
            "hit_semantics": semantics,
            "input_count": in_count,
            "hit_count": hit_count,
            "miss_count": prod.get("miss_count", 0),
            "status": prod.get("status", "ok"),
        }
        if semantics == "positive" and hit_count == 0 and not first_zero_skill:
            first_zero_skill = sid
        skill_stats.append(stat)
    skill_layer: dict[str, Any] = {
        "skills": skill_stats,
        "first_zero_skill": first_zero_skill,
        "ok": final_count > 0 or not any(
            s["hit_semantics"] == "positive" and s["hit_count"] == 0
            for s in skill_stats
        ),
        "suggestion": (
            f"技能 {first_zero_skill} 命中 0，是技能层清零来源，可尝试放宽该技能参数"
            if first_zero_skill else ""
        ),
    }

    # ── 路径层 ────────────────────────────────────────────────────────
    steps = expression_spec.get("steps", [])
    path_zero_step = ""
    for step in steps:
        # 每步记录的中间结果数（若有）
        if step.get("output_count", -1) == 0 and not path_zero_step:
            path_zero_step = step.get("expression_id", "")
    path_layer: dict[str, Any] = {
        "path_type": path_type,
        "step_count": len(steps),
        "first_zero_step": path_zero_step,
        "ok": final_count > 0 or path_type not in ("sequential", "parallel_and", "simple_hybrid"),
        "suggestion": (
            f"路径步骤 {path_zero_step} 输出 0，顺序漏斗在此清零，可检查各步逻辑"
            if path_zero_step else (
                "并行 AND 交集为空，各技能命中集合没有共同股票，可改为 K_OF_N 模式"
                if path_type == "parallel_and" and final_count == 0 else ""
            )
        ),
    }

    # ── 报告层 ────────────────────────────────────────────────────────
    report_layer: dict[str, Any] = {
        "final_hit_count": final_count,
        "has_explanation": len(producer_results) > 0,
        "ok": True,
        "suggestion": "命中 0，请参考上层原因定位清零来源" if final_count == 0 else "",
    }

    # ── why_zero 归因 ────────────────────────────────────────────────
    why_zero: str = ""
    if final_count == 0:
        if src_count == 0:
            why_zero = f"source_layer: {src_type} 来源返回 0 只股票"
        elif failed > 0 and cached == 0:
            why_zero = f"data_layer: K线取数全部失败（{failed} 只），无可分析数据"
        elif first_zero_skill:
            why_zero = f"skill_layer: 技能 {first_zero_skill} 命中 0，最先清零"
        elif path_zero_step:
            why_zero = f"path_layer: 路径步骤 {path_zero_step} 输出 0"
        elif path_type == "parallel_and":
            why_zero = "path_layer: parallel_and 交集为空，各技能命中集合无共同股票"
        else:
            why_zero = "report_layer: 命中 0，原因不明，请检查所有层日志"

    return {
        "source_layer": source_layer,
        "data_layer": data_layer,
        "skill_layer": skill_layer,
        "path_layer": path_layer,
        "report_layer": report_layer,
        "why_zero": why_zero,
        "final_hit_count": final_count,
    }
