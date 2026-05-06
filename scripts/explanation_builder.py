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
