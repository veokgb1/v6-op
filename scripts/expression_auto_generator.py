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
    *,
    pre_exclude_codes: list[str] | None = None,
) -> dict[str, Any]:
    """
    根据 Producer 结果列表和策略图自动生成 MaskExpression 规格。

    Args:
        producer_results   : 每个 Producer 的 run() 输出 dict 列表
        graph              : strategy_graph_builder.build() 的输出
        pre_exclude_codes  : sequential/simple_hybrid 路径已算好的正向命中列表

    Returns dict with:
      steps              : list[dict]  并行交集路径可执行表达式步骤（mask: refs）
      path_type          : str
      path_description   : str        路径人类可读描述
      sequential_chain   : list[dict] sequential/simple_hybrid 路径步骤文档
      executable         : bool       steps 是否可直接由 expression_runner 执行
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

    negative_skill_ids_list = [r.get("skill_id", "") for r in negative_results]
    negative_mask_ids_list  = [r.get("mask_id", "")  for r in negative_results]

    if not positive_results:
        warnings.append("没有正向技能结果，无法生成合并表达式。")
        return {
            "steps": [],
            "path_type": path_type,
            "path_description": "无正向技能",
            "sequential_chain": [],
            "executable": False,
            "primary_expression_id": None,
            "positive_mask_ids": [],
            "negative_mask_ids": negative_mask_ids_list,
            "metadata": metadata,
            "warnings": warnings,
            "generated_at": datetime.now().isoformat(),
        }

    positive_skill_ids = [r.get("skill_id", "") for r in positive_results]
    positive_mask_ids  = [r.get("mask_id", "")  for r in positive_results]

    # ── G8: 根据 path_type 生成路径准确的规格 ─────────────────────────

    if path_type in ("sequential", "simple_hybrid"):
        # sequential / simple_hybrid 的 Producer 仍按动态 scope 执行；
        # expression steps 负责对这些动态生成的 mask 做最终路径合并，
        # 让报告表达式与真实执行结果走同一套步骤。
        sequential_chain: list[dict[str, Any]] = []
        for i, result in enumerate(positive_results):
            sid   = result.get("skill_id", "")
            sname = result.get("skill_name", sid)
            input_n  = result.get("hit_count", 0) + result.get("miss_count", 0)
            output_n = result.get("hit_count", 0)
            skipped  = result.get("status") == "skipped"
            if path_type == "simple_hybrid":
                phase = "parallel" if i < 2 else "sequential"
            else:
                phase = "sequential"
            sequential_chain.append({
                "step": i + 1,
                "skill_id": sid,
                "skill_name": sname,
                "phase": phase,
                "input_count": input_n if not skipped else 0,
                "output_count": output_n,
                "skipped": skipped,
                "notes": result.get("notes", ""),
            })

        # EXCLUDE 文档
        if negative_results:
            pre_n = len(pre_exclude_codes) if pre_exclude_codes is not None else "?"
            sequential_chain.append({
                "step": len(positive_results) + 1,
                "skill_id": "exclude",
                "skill_name": "排雷过滤",
                "phase": "exclude",
                "input_count": pre_n,
                "output_count": "—",
                "skipped": False,
                "notes": f"排除负向命中技能: {', '.join(negative_skill_ids_list)}",
            })

        steps: list[dict[str, Any]] = []
        primary_id: str | None = None
        if path_type == "sequential":
            seq_expr_id = _expr_id("seq", positive_skill_ids)
            steps.append({
                "expression_id": seq_expr_id,
                "expression_name_cn": "顺序漏斗最终正向结果",
                "op": "SEQUENCE",
                "inputs": [f"mask:{mid}" for mid in positive_mask_ids],
                "params": {},
                "output_mask_alias": "sequential_positive",
                "metadata": {
                    "path_type": path_type,
                    "skill_ids": positive_skill_ids,
                    "dynamic_scope": True,
                },
            })
            primary_id = seq_expr_id
        else:
            first_two_ids = positive_mask_ids[:2]
            rest_ids = positive_mask_ids[2:]
            if len(first_two_ids) >= 2:
                hybrid_base_id = _expr_id("hybrid_base", positive_skill_ids[:2])
                steps.append({
                    "expression_id": hybrid_base_id,
                    "expression_name_cn": "简单混合前段并行交集",
                    "op": "AND",
                    "inputs": [f"mask:{mid}" for mid in first_two_ids],
                    "params": {},
                    "output_mask_alias": "hybrid_parallel_base",
                    "metadata": {
                        "path_type": path_type,
                        "skill_ids": positive_skill_ids[:2],
                        "dynamic_scope": False,
                    },
                })
                if rest_ids:
                    hybrid_seq_id = _expr_id("hybrid_seq", positive_skill_ids)
                    steps.append({
                        "expression_id": hybrid_seq_id,
                        "expression_name_cn": "简单混合后段顺序结果",
                        "op": "SEQUENCE",
                        "inputs": [f"mask:{hybrid_base_id}_result"]
                        + [f"mask:{mid}" for mid in rest_ids],
                        "params": {},
                        "output_mask_alias": "hybrid_positive",
                        "metadata": {
                            "path_type": path_type,
                            "skill_ids": positive_skill_ids,
                            "dynamic_scope": True,
                        },
                    })
                    primary_id = hybrid_seq_id
                else:
                    primary_id = hybrid_base_id
            else:
                only_id = _expr_id("hybrid_seq", positive_skill_ids)
                steps.append({
                    "expression_id": only_id,
                    "expression_name_cn": "简单混合单正向结果",
                    "op": "SEQUENCE",
                    "inputs": [f"mask:{mid}" for mid in positive_mask_ids],
                    "params": {},
                    "output_mask_alias": "hybrid_positive",
                    "metadata": {
                        "path_type": path_type,
                        "skill_ids": positive_skill_ids,
                        "dynamic_scope": True,
                    },
                })
                primary_id = only_id

        if negative_results and primary_id:
            exclude_expr_id = _expr_id("final", positive_skill_ids + negative_skill_ids_list)
            steps.append({
                "expression_id": exclude_expr_id,
                "expression_name_cn": "路径正向结果排除负向过滤",
                "op": "EXCLUDE",
                "inputs": [f"mask:{primary_id}_result"]
                + [f"mask:{mid}" for mid in negative_mask_ids_list],
                "params": {},
                "output_mask_alias": "final_result",
                "metadata": {
                    "excludes_skills": negative_skill_ids_list,
                    "base_expression": primary_id,
                },
            })
            primary_id = exclude_expr_id

        path_cn_map = {
            "sequential": "顺序漏斗（逐层缩小，最终由 SEQUENCE 表达式收口）",
            "simple_hybrid": "简单混合（前2并行 AND → 后续顺序，最终由表达式收口）",
        }
        path_desc = path_cn_map.get(path_type, path_type)

        return {
            "steps": steps,
            "path_type": path_type,
            "path_description": path_desc,
            "sequential_chain": sequential_chain,
            "executable": bool(steps),
            "primary_expression_id": primary_id,
            "positive_mask_ids": positive_mask_ids,
            "negative_mask_ids": negative_mask_ids_list,
            "metadata": metadata,
            "warnings": warnings,
            "generated_at": datetime.now().isoformat(),
        }

    # ── parallel_and: 生成可执行的 AND + EXCLUDE 表达式步骤 ──────────

    merge_node = graph.get("merge_node", {})
    merge_op = merge_node.get("op", "AND")
    merge_params = merge_node.get("params", {})
    merge_expr_id = _expr_id("pos", positive_skill_ids)

    # Step 1: 正向技能合并（AND）
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
        exclude_expr_id = _expr_id("final", positive_skill_ids + negative_skill_ids_list)
        exclude_step: dict[str, Any] = {
            "expression_id": exclude_expr_id,
            "expression_name_cn": "正向命中排除负向过滤（排雷）",
            "op": "EXCLUDE",
            "inputs": [f"mask:{merge_expr_id}_result"]
            + [f"mask:{mid}" for mid in negative_mask_ids_list],
            "params": {},
            "output_mask_alias": "final_result",
            "metadata": {
                "excludes_skills": negative_skill_ids_list,
                "base_expression": merge_expr_id,
            },
        }
        steps.append(exclude_step)
        primary_id = exclude_expr_id

    return {
        "steps": steps,
        "path_type": path_type,
        "path_description": "并行交集（所有正向技能同时对全量运行，取交集）",
        "sequential_chain": [],
        "executable": True,
        "primary_expression_id": primary_id,
        "positive_mask_ids": positive_mask_ids,
        "negative_mask_ids": negative_mask_ids_list,
        "metadata": metadata,
        "warnings": warnings,
        "generated_at": datetime.now().isoformat(),
    }
