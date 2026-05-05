#!/usr/bin/env python3
"""
strategy_graph_builder.py — V6OP 策略图构建器

支持 charter 第一阶段三种固定路径：
  sequential    : 正向技能顺序过滤（AND 链），负向技能 EXCLUDE
  parallel_and  : 所有正向技能并行 AND，负向技能 EXCLUDE
  simple_hybrid : 前 2 个正向技能并线 AND，后续正向技能顺序过滤，负向技能 EXCLUDE

图节点类型：producer / merge / exclude

本轮不支持任意 DAG 编辑。
"""
from __future__ import annotations

from typing import Any

SUPPORTED_PATH_TYPES = ("sequential", "parallel_and", "simple_hybrid")


def build(
    selected_skills: list[str],
    skill_registry: dict[str, dict[str, Any]],
    path_type: str = "parallel_and",
) -> dict[str, Any]:
    """
    根据选择技能和路径类型构建策略图规格。

    Args:
        selected_skills : 选择的技能 ID 列表（有序）
        skill_registry  : {skill_id: skill_meta} 字典
        path_type       : "sequential" | "parallel_and" | "simple_hybrid"

    Returns:
        dict with: path_type, positive_nodes, negative_nodes,
                   merge_node, exclude_node, has_exclude
    """
    if path_type not in SUPPORTED_PATH_TYPES:
        raise ValueError(
            f"不支持的 path_type: {path_type!r}，"
            f"支持: {', '.join(SUPPORTED_PATH_TYPES)}"
        )

    positive_nodes: list[dict[str, Any]] = []
    negative_nodes: list[dict[str, Any]] = []

    for skill_id in selected_skills:
        meta = skill_registry.get(skill_id, {})
        hit_semantics = meta.get("hit_semantics", "positive")
        node: dict[str, Any] = {
            "node_id": skill_id,
            "skill_id": skill_id,
            "skill_name": meta.get("skill_name", skill_id),
            "type": "producer",
            "hit_semantics": hit_semantics,
            "data_requirement": meta.get("data_requirement", "none"),
            "notes": meta.get("notes", ""),
        }
        if hit_semantics == "negative":
            negative_nodes.append(node)
        else:
            positive_nodes.append(node)

    # 根据路径类型决定合并算子
    if path_type == "parallel_and":
        merge_op = "AND"
        merge_params: dict[str, Any] = {}
        merge_description = (
            f"所有 {len(positive_nodes)} 个正向技能并行 AND"
        )
    elif path_type == "sequential":
        merge_op = "AND"
        merge_params = {}
        merge_description = (
            f"{len(positive_nodes)} 个正向技能顺序过滤（AND 链）"
        )
    else:  # simple_hybrid
        # charter §8: 前2个并线AND → 后续顺序过滤（execution_engine 负责实际调度）
        parallel_count = min(2, len(positive_nodes))
        seq_count = max(0, len(positive_nodes) - parallel_count)
        merge_op = "AND"
        merge_params = {}
        if seq_count > 0:
            merge_description = (
                f"前{parallel_count}个正向技能并线AND，"
                f"后{seq_count}个顺序过滤"
            )
        else:
            merge_description = (
                f"{parallel_count}个正向技能并线AND（正向≤2，等价 parallel_and）"
            )

    merge_node: dict[str, Any] = {
        "node_id": "merge",
        "type": "merge",
        "op": merge_op,
        "params": merge_params,
        "inputs": [n["node_id"] for n in positive_nodes],
        "description": merge_description,
    }

    exclude_node: dict[str, Any] | None = None
    if negative_nodes:
        exclude_node = {
            "node_id": "exclude",
            "type": "exclude",
            "op": "EXCLUDE",
            "inputs": ["merge"] + [n["node_id"] for n in negative_nodes],
            "description": (
                f"从正向合并结果中排除 {len(negative_nodes)} 个"
                "负向技能命中（排雷）"
            ),
        }

    # 构建统一执行计划：按拓扑顺序排列的节点列表
    # 顺序：producer 节点（正向 → 负向）→ merge 节点 → exclude 节点（可选）
    execution_plan: list[dict[str, Any]] = []

    if path_type == "sequential":
        # 顺序：正向 producer 按输入顺序（漏斗链），负向 producer，merge，exclude
        for i, node in enumerate(positive_nodes):
            plan_node = {**node, "exec_order": i, "input_scope": "prev_hit" if i > 0 else "scope"}
            execution_plan.append(plan_node)
        base = len(positive_nodes)
        for j, node in enumerate(negative_nodes):
            execution_plan.append({**node, "exec_order": base + j, "input_scope": "scope"})
    elif path_type == "simple_hybrid":
        # 前2个正向并线，后续正向接前2的AND结果，负向对 scope 运行
        parallel_count = min(2, len(positive_nodes))
        for i, node in enumerate(positive_nodes[:parallel_count]):
            execution_plan.append({**node, "exec_order": i, "input_scope": "scope", "phase": "parallel"})
        for i, node in enumerate(positive_nodes[parallel_count:]):
            execution_plan.append({
                **node,
                "exec_order": parallel_count + i,
                "input_scope": "parallel_and_result",
                "phase": "sequential",
            })
        base = len(positive_nodes)
        for j, node in enumerate(negative_nodes):
            execution_plan.append({**node, "exec_order": base + j, "input_scope": "scope", "phase": "parallel"})
    else:  # parallel_and
        for i, node in enumerate(positive_nodes):
            execution_plan.append({**node, "exec_order": i, "input_scope": "scope"})
        base = len(positive_nodes)
        for j, node in enumerate(negative_nodes):
            execution_plan.append({**node, "exec_order": base + j, "input_scope": "scope"})

    # merge 和 exclude 节点加入 plan（不执行 producer，用于报告可检查性）
    execution_plan.append({**merge_node, "exec_order": len(execution_plan)})
    if exclude_node:
        execution_plan.append({**exclude_node, "exec_order": len(execution_plan)})

    return {
        "path_type": path_type,
        "positive_nodes": positive_nodes,
        "negative_nodes": negative_nodes,
        "merge_node": merge_node,
        "exclude_node": exclude_node,
        "has_exclude": exclude_node is not None,
        "total_skill_count": len(selected_skills),
        "positive_skill_count": len(positive_nodes),
        "negative_skill_count": len(negative_nodes),
        "execution_plan": execution_plan,
        "topological_order": [n["node_id"] for n in execution_plan],
    }
