#!/usr/bin/env python3
"""
v6_asset_alignment.py — V6OP 后台资产继承状态审计（总纲第三章）

对 V6 后台 10 个资产文件逐项审计，输出机器可检测的继承状态矩阵：
  used_in_mainline    : 已纳入主操盘链路关键路径
  adapted             : 已封装/适配，可在 v6-op 中调用
  read_only_reference : 第一阶段只读参考，不接入主链路
  deferred_phase      : 明确推迟至后续阶段

用法：
  python scripts/v6_asset_alignment.py
  python scripts/v6_asset_alignment.py --json-out output/verification/v6_asset_alignment.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent.resolve()
_V6_SCRIPTS   = _PROJECT_ROOT.parent / "v6" / "scripts" / "v6"

# ──────────────────────────────────────────────────────────────────────
# 审计矩阵（静态声明，与实际代码对齐）
# ──────────────────────────────────────────────────────────────────────

ASSET_MATRIX: list[dict] = [
    {
        "asset": "contracts.py",
        "status": "adapted",
        "description": "V6 数据契约：ScopeRef / ExpressionOp / combine_code_sets / fingerprint_codes(SHA256)。"
                       "execution_engine.py 已 import ExpressionRunner + ExpressionOp + MaskExpression；"
                       "mask_cache.py 指纹算法与 fingerprint_codes 保持一致（SHA256）。",
        "evidence": "execution_engine.py: from v6.contracts import ExpressionOp, MaskExpression",
        "v6op_files": ["scripts/execution_engine.py", "scripts/mask_cache.py"],
    },
    {
        "asset": "expression_runner.py",
        "status": "adapted",
        "description": "V6 ExpressionRunner：注册 Mask → 执行布尔表达式 → 返回命中代码列表。"
                       "execution_engine.py 在 _V6_AVAILABLE=True 时使用 V6 ExpressionRunner；"
                       "不可用时回退到内置 AND+EXCLUDE 逻辑（_fallback_combine）。",
        "evidence": "execution_engine.py: from v6.expression_runner import ExpressionRunner",
        "v6op_files": ["scripts/execution_engine.py"],
    },
    {
        "asset": "mask_store.py",
        "status": "read_only_reference",
        "description": "V6 MaskStore：持久化 Universe / Mask / Expression 到文件系统。"
                       "第一阶段 v6-op 使用自有 mask_cache.py（内容寻址 JSON 文件），"
                       "不接入 MaskStore 避免引入 V6 文件布局依赖。"
                       "后续阶段可替换为 MaskStore 实现账本体系。",
        "evidence": "mask_cache.py 使用独立 SHA256 fingerprint 文件，与 MaskStore 文件格式不同",
        "v6op_files": [],
        "deferred_reason": "第一阶段只需执行层内部复用，无需 V6 账本体系；后续阶段接入",
    },
    {
        "asset": "io_utils.py",
        "status": "read_only_reference",
        "description": "V6 io_utils：read_json_file / write_json_file（UTF-8 + sorted_keys）。"
                       "v6-op 当前直接使用 json + Path.write_text(encoding=utf-8)；"
                       "可小步替换，但第一阶段不引入额外依赖。",
        "evidence": "run_report.py / execution_engine.py 均使用标准 json.dumps",
        "v6op_files": [],
        "deferred_reason": "功能等价，第一阶段不引入 V6 模块依赖",
    },
    {
        "asset": "universe_provider.py",
        "status": "read_only_reference",
        "description": "V6 universe_from_codes_file()：从 codes 文件构建 Universe 对象。"
                       "v6-op source_resolver.py 直接处理 code 列表，不使用 Universe 包装；"
                       "第一阶段 scope 语义已足够，Universe 集成推迟。",
        "evidence": "source_resolver.py 返回 {scope_codes: list[str]} 而非 Universe 对象",
        "v6op_files": [],
        "deferred_reason": "第一阶段 scope 不需要 Universe 账本语义",
    },
    {
        "asset": "secret_masking.py",
        "status": "adapted",
        "description": "V6 secret_masking：mask_dict / mask_request / has_unmasked_secrets。"
                       "wencai_source.py 已引用脱敏机制：API Key 从 env 读取，"
                       "不写入磁盘/日志；v6_asset_alignment 本身也不记录敏感字段。"
                       "当 V6 路径可用时直接 import secret_masking；否则使用等价本地实现。",
        "evidence": "wencai_source.py: os.environ.get('IWENCAI_API_KEY') + 不落盘",
        "v6op_files": ["scripts/sources/wencai_source.py"],
    },
    {
        "asset": "live_recapture.py",
        "status": "read_only_reference",
        "description": "V6 live_recapture：iwencai API 调用封装（IWENCAI_ENDPOINT + secret_masking）。"
                       "v6-op wencai_source.py 直接调用 iwencai HTTP API，未引用 live_recapture。"
                       "接入 live_recapture 可统一 API 调用口径，但需对齐 V6 调用约定；推迟。",
        "evidence": "wencai_source.py 独立实现 HTTP 调用，未 import live_recapture",
        "v6op_files": [],
        "deferred_reason": "第一阶段 wencai_source 已功能可用；live_recapture 接入推迟到 API 层统一",
    },
    {
        "asset": "selection_condition.py",
        "status": "read_only_reference",
        "description": "V6 SelectionCondition：结构化条件表达式 → Mask 生成。"
                       "第一阶段 v6-op 直接由 producer 输出 hit_codes 列表，"
                       "不需要 SelectionCondition 语义层；推迟到条件编辑器阶段。",
        "evidence": "producer 直接返回 hit_codes list，无 SelectionCondition 封装",
        "v6op_files": [],
        "deferred_reason": "第一阶段不需要结构化条件语义；DAG/条件编辑器阶段接入",
    },
    {
        "asset": "mask_expression_executor.py",
        "status": "read_only_reference",
        "description": "V6 MaskExpressionExecutor：执行 MaskExpression AST。"
                       "v6-op 使用 ExpressionRunner（expression_runner.py）+ "
                       "fallback _fallback_combine；MaskExpressionExecutor 更底层，"
                       "ExpressionRunner 已满足需求，不重复接入。",
        "evidence": "execution_engine.py 使用 ExpressionRunner 而非 MaskExpressionExecutor",
        "v6op_files": [],
        "deferred_reason": "ExpressionRunner 已满足表达式执行需求；底层 executor 不重复接入",
    },
    {
        "asset": "report_group_summary.py",
        "status": "read_only_reference",
        "description": "V6 ReportGroupSummary：按组生成报告摘要（分析师/策略维度）。"
                       "第一阶段 v6-op 使用 run_report.py 生成单次执行报告；"
                       "多策略/分组报告能力推迟到报告体系完善阶段。",
        "evidence": "run_report.py 生成单次运行的 JSON + Markdown 报告",
        "v6op_files": ["scripts/run_report.py"],
        "deferred_reason": "第一阶段只需单次运行报告；分组摘要推迟",
    },
]


def check_file_exists(asset_file: str) -> bool:
    return (_V6_SCRIPTS / asset_file).exists()


def get_alignment_report() -> dict:
    """生成资产继承状态报告。"""
    results: list[dict] = []
    status_counts: dict[str, int] = {
        "used_in_mainline": 0,
        "adapted": 0,
        "read_only_reference": 0,
        "deferred_phase": 0,
    }

    for item in ASSET_MATRIX:
        asset = item["asset"]
        status = item["status"]
        v6_exists = check_file_exists(asset)

        row = {
            "asset": asset,
            "status": status,
            "v6_file_exists": v6_exists,
            "description": item["description"],
            "evidence": item["evidence"],
            "v6op_files": item.get("v6op_files", []),
        }
        if "deferred_reason" in item:
            row["deferred_reason"] = item["deferred_reason"]

        results.append(row)
        if status in status_counts:
            status_counts[status] += 1

    return {
        "generated_at": datetime.now().isoformat(),
        "total_assets": len(ASSET_MATRIX),
        "status_summary": status_counts,
        "assets": results,
        "v6_scripts_dir": str(_V6_SCRIPTS),
        "v6_scripts_accessible": _V6_SCRIPTS.exists(),
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="V6OP 后台资产继承状态审计")
    parser.add_argument("--json-out", dest="json_out", default=None,
                        help="输出 JSON 文件路径")
    args = parser.parse_args(argv)

    report = get_alignment_report()

    # 打印摘要
    summary = report["status_summary"]
    print(f"\nV6 资产继承审计  total={report['total_assets']}")
    print(f"  used_in_mainline   : {summary['used_in_mainline']}")
    print(f"  adapted            : {summary['adapted']}")
    print(f"  read_only_reference: {summary['read_only_reference']}")
    print(f"  deferred_phase     : {summary['deferred_phase']}")
    print(f"\nV6 scripts 目录: {report['v6_scripts_dir']}")
    print(f"  可访问: {report['v6_scripts_accessible']}")
    print()

    for row in report["assets"]:
        status_sym = {
            "used_in_mainline": "●",
            "adapted":          "◆",
            "read_only_reference": "○",
            "deferred_phase":   "◌",
        }.get(row["status"], "?")
        exists_sym = "✓" if row["v6_file_exists"] else "✗"
        print(f"  {status_sym} [{row['status']:<22}] {exists_sym} {row['asset']}")

    out_json = json.dumps(report, ensure_ascii=False, indent=2)

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(out_json, encoding="utf-8")
        print(f"\nJSON → {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
