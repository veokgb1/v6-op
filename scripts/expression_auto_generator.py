#!/usr/bin/env python3
"""
expression_auto_generator.py — V6OP MaskExpression 自动生成器

根据 Producer hit_semantics 和策略图自动生成 MaskExpression 规格。

规则：
- positive 技能默认 AND / K_OF_N（取决于 path_type）
- negative 技能接入 EXCLUDE
- SMC soft_filter 结果如果被选中，expression metadata 中标注 mode=soft_filter
- Wave no_top 如果被选中，内部仍写入 weak_signal_skills，界面解释为“辅助放行”

不让用户手写表达式。
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any


def _expr_id(prefix: str, components: list[str]) -> str:
    key = prefix + "|" + ",".join(components)
    return f"expr_{prefix}_{hashlib.sha1(key.encode()).hexdigest()[:8]}"


def _path_cn(path_type: str, skill_ids: list[str]) -> str:
    names = " + ".join(skill_ids)
    if path_type == "parallel_and":
        return f"{names} 并行交集"
    elif path_type == "sequential":
        return f"{names} 顺序过滤"
    else:
        return f"{names} 混合命中"


def _detect_smc_soft_filter(result: dict[str, Any]) -> bool:
    """检查 SMC 结果是否使用了 soft_filter 模式。"""
    params = result.get("params", {})
    return result.get("skill_id") == "smc" and params.get("mode") == "soft_filter"


def _detect_wave_weak_signal(result: dict[str, Any]) -> bool:
    """检查 Wave 结果是否包含 no_top 辅助放行命中。"""
    if result.get("skill_id") != "wave":
        return False
    evidence = result.get("evidence", {})
    return any(
        isinstance(v, dict) and v.get("verdict") == "no_top"
        for v in evidence.values()
    )


def generate(
    producer_results: list[dict[str, Any]],
    graph: dict[str, Any],
) -> dict[str, Any]:
    """
    根据 Producer 结果列表和策略图自动生成 MaskExpression 规格。

    Args:
        producer_results : 每个 Producer 的 run() 输出 dict 列表
        graph            : strategy_graph_builder.build() 的输出

    Returns dict with:
      steps              : list[dict]  顺序执行的表达式步骤（使用 mask: refs）
      primary_expression_id : str
      metadata           : dict  含 soft_filter_skills, weak_signal_skills
      warnings           : list[str]
      generated_at       : str
    """
    metadata: dict[str, Any] = {}
    warnings: list[str] = []
    path_type = graph.get("path_type", "parallel_and")

    positive_results = [
        r for r in producer_results if r.get("hit_semantics") == "positive"
    ]
    negative_results = [
        r for r in producer_results if r.get("hit_semantics") == "negative"
    ]

    # 标注特殊模式
    for result in producer_results:
        if _detect_smc_soft_filter(result):
            metadata.setdefault("soft_filter_skills", []).append(
                result.get("skill_id", "smc")
            )
            warnings.append(
                "SMC 使用了 soft_filter 模式（全量透传），"
                "结果已标注；正式路径应使用 strict 模式。"
            )

        if _detect_wave_weak_signal(result):
            metadata.setdefault("weak_signal_skills", []).append(
                result.get("skill_id", "wave")
            )
            warnings.append(
                "WaveProducer 包含 no_top 辅助放行（无5浪顶→放行），"
                "已标注为辅助信号；不应视为强买入信号。"
            )

    if not positive_results:
        warnings.append("没有正向技能结果，无法生成合并表达式。")
        return {
            "steps": [],
            "primary_expression_id": None,
            "metadata": metadata,
            "warnings": warnings,
            "generated_at": datetime.now().isoformat(),
        }

    positive_skill_ids = [r.get("skill_id", "") for r in positive_results]
    positive_mask_ids = [r.get("mask_id", "") for r in positive_results]

    merge_node = graph.get("merge_node", {})
    merge_op = merge_node.get("op", "AND")
    merge_params = merge_node.get("params", {})
    merge_expr_id = _expr_id("pos", positive_skill_ids)

    # Step 1: 正向技能合并
    merge_step: dict[str, Any] = {
        "expression_id": merge_expr_id,
        "expression_name_cn": _path_cn(path_type, positive_skill_ids),
        "op": merge_op,
        "inputs": [f"mask:{mid}" for mid in positive_mask_ids],
        "params": merge_params,
        "output_mask_alias": "merge_result",
        "metadata": {
            "path_type": path_type,
            "skill_ids": positive_skill_ids,
            "soft_filter_skills": metadata.get("soft_filter_skills", []),
            "weak_signal_skills": metadata.get("weak_signal_skills", []),
        },
    }
    steps: list[dict[str, Any]] = [merge_step]
    primary_id = merge_expr_id

    # Step 2: 负向技能 EXCLUDE（排雷）
    if negative_results:
        negative_skill_ids = [r.get("skill_id", "") for r in negative_results]
        negative_mask_ids = [r.get("mask_id", "") for r in negative_results]
        exclude_expr_id = _expr_id(
            "final", positive_skill_ids + negative_skill_ids
        )

        exclude_step: dict[str, Any] = {
            "expression_id": exclude_expr_id,
            "expression_name_cn": "正向命中排除负向过滤（排雷）",
            "op": "EXCLUDE",
            # 第一个 input 是 merge_result（在 execution_engine 中注册为 mask）
            "inputs": [f"mask:{merge_expr_id}_result"]
            + [f"mask:{mid}" for mid in negative_mask_ids],
            "params": {},
            "output_mask_alias": "final_result",
            "metadata": {
                "excludes_skills": negative_skill_ids,
                "base_expression": merge_expr_id,
            },
        }
        steps.append(exclude_step)
        primary_id = exclude_expr_id

    return {
        "steps": steps,
        "primary_expression_id": primary_id,
        "positive_mask_ids": positive_mask_ids,
        "negative_mask_ids": [r.get("mask_id", "") for r in negative_results],
        "metadata": metadata,
        "warnings": warnings,
        "generated_at": datetime.now().isoformat(),
    }
