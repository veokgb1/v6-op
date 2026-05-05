#!/usr/bin/env python3
"""
run_report.py — V6OP 报告生成器

生成前端可渲染 JSON 和中文 Markdown。

必须包含：source 摘要, selected_skills, path_type, params,
         prefetch_report, producer_summary, expression,
         final_hit_codes, explanations, failed_codes, stale_codes,
         data_coverage, warnings.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def generate(execution_result: dict[str, Any], output_dir: Path) -> dict[str, Path]:
    """
    生成 run_report.json 和 run_report.md。

    Args:
        execution_result : execution_engine 的输出字典
        output_dir       : 输出目录（output/current/）

    Returns:
        dict with: report_json_path, report_md_path
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── 整理 run_report 数据结构 ──────────────────────────────────────
    scope = execution_result.get("scope", {})
    fetch = execution_result.get("fetch_plan", {})
    producers = execution_result.get("producer_results", [])
    expression = execution_result.get("expression_spec", {})
    explanations = execution_result.get("explanations", {})
    final_hits = execution_result.get("final_hit_codes", [])
    expr_metadata = expression.get("metadata", {})

    warnings: list[str] = list(execution_result.get("warnings", []))
    warnings.extend(expression.get("warnings", []))
    warnings.extend(explanations.get("stale_warnings", []))

    producer_summary: list[dict[str, Any]] = []
    for prod in producers:
        ps: dict[str, Any] = {
            "skill_id": prod.get("skill_id"),
            "skill_name": prod.get("skill_name"),
            "hit_semantics": prod.get("hit_semantics"),
            "hit_count": prod.get("hit_count", 0),
            "miss_count": prod.get("miss_count", 0),
            "status": prod.get("status", "ok"),
            "data_mode": prod.get("data_mode"),
            "adjust": prod.get("adjust"),
            "duration_seconds": prod.get("duration_seconds"),
            "params_used": prod.get("params_used", prod.get("params", {})),
        }
        # 标注特殊模式
        params = ps["params_used"] or prod.get("params", {})
        if prod.get("skill_id") == "smc":
            ps["mode"] = params.get("mode", "strict")
            if ps["mode"] == "soft_filter":
                ps["mode_note"] = "soft_filter（调试模式，非正式路径）"
        if prod.get("skill_id") == "wave":
            ps["signal_note"] = "轻量版，no_top→放行 为弱信号"
        producer_summary.append(ps)

    data_coverage = {
        "scope_count": scope.get("scope_count", 0),
        "cached_count": len(fetch.get("cached_codes", [])),
        "missing_count": len(fetch.get("missing_codes", [])),
        "failed_count": len(fetch.get("failed_codes", [])),
        "stale_count": len(fetch.get("stale_codes", [])),
        "readiness": fetch.get("readiness", "unknown"),
        "failure_rate": fetch.get("failure_rate", 0.0),
    }

    run_report: dict[str, Any] = {
        "run_id": execution_result.get("run_id", ""),
        "generated_at": datetime.now().isoformat(),
        "strategy": {
            "source": {
                "type": scope.get("source_type"),
                "scope_id": scope.get("scope_id"),
                "scope_count": scope.get("scope_count"),
                "status": scope.get("status"),
            },
            "selected_skills": execution_result.get("selected_skills", []),
            "path_type": execution_result.get("path_type", ""),
            "params": execution_result.get("params", {}),
        },
        "prefetch_report": fetch.get("prefetch_report", {}),
        "producer_summary": producer_summary,
        "expression": {
            "steps": expression.get("steps", []),
            "primary_expression_id": expression.get("primary_expression_id"),
            "metadata": expr_metadata,
        },
        "final_hit_codes": final_hits,
        "final_hit_count": len(final_hits),
        "explanations": explanations.get("hits", []),
        "failed_codes": fetch.get("failed_codes", []),
        "stale_codes": fetch.get("stale_codes", []),
        "data_coverage": data_coverage,
        "warnings": warnings,
        "prefetch_triggered": execution_result.get("prefetch_triggered", False),
        "mask_cache_hits":   execution_result.get("mask_cache_hits", 0),
        "mask_cache_misses": execution_result.get("mask_cache_misses", 0),
        "api_called": False,
        "env_read": execution_result.get("env_read", False),
        "v5_modified": False,
        "v6_modified": False,
    }

    # ── 写 JSON ──────────────────────────────────────────────────────
    report_json_path = output_dir / "run_report.json"
    report_json_path.write_text(
        json.dumps(run_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # ── 写 Markdown ───────────────────────────────────────────────────
    report_md_path = output_dir / "run_report.md"
    report_md_path.write_text(
        _build_markdown(run_report),
        encoding="utf-8",
    )

    return {
        "report_json_path": report_json_path,
        "report_md_path": report_md_path,
    }


def _build_markdown(report: dict[str, Any]) -> str:
    strategy = report["strategy"]
    source = strategy["source"]
    dc = report["data_coverage"]
    hits = report["final_hit_codes"]
    explanations = report["explanations"]
    warnings = report["warnings"]
    producer_summary = report["producer_summary"]
    expr = report["expression"]
    expr_meta = expr.get("metadata", {})

    soft_filter = expr_meta.get("soft_filter_skills", [])
    weak_signal = expr_meta.get("weak_signal_skills", [])

    # prefetch_triggered 由 execution_engine 写入，表示本轮实际调用了 data_prefetch。
    # 不用 prefetch_report 内容判断（那是跨 run 的历史文件，不代表本次是否预热）。
    prefetch_triggered = report.get("prefetch_triggered", False)
    prefetch_rpt = report.get("prefetch_report", {}) if prefetch_triggered else {}
    prefetch_fetched = prefetch_rpt.get("fetched_ok", 0)
    prefetch_failed = prefetch_rpt.get("failed", 0)
    prefetch_stale = prefetch_rpt.get("stale_used", 0)
    prefetch_hit = prefetch_rpt.get("cache_hit", 0)
    prefetch_bj = prefetch_rpt.get("bj_skipped", 0)
    prefetch_recovered = prefetch_rpt.get("recovered_count", 0)
    data_time_max: str | None = prefetch_rpt.get("data_time_max")

    # 计算数据新鲜度（stale_days = 距今自然日数）
    stale_days: int | None = None
    stale_note = ""
    if data_time_max:
        try:
            from datetime import date as _date
            delta = (_date.today() - _date.fromisoformat(data_time_max[:10])).days
            stale_days = delta
            if delta >= 2:
                stale_note = f"⚠ 数据明显过旧（最新 {data_time_max[:10]}，距今 {delta} 自然日），请谨慎使用"
            elif delta >= 1:
                stale_note = f"⚠ 数据可能滞后（最新 {data_time_max[:10]}，距今 {delta} 自然日）"
        except Exception:
            pass

    failed = report.get("failed_codes", [])
    stale = report.get("stale_codes", [])

    _source_type_cn = {
        "manual": "手动代码",
        "all_a": "全 A 股扫描",
        "wencai": "问财选股",
    }
    _path_type_cn = {
        "sequential": "顺序漏斗（sequential）",
        "parallel_and": "并行取交集（parallel_and）",
        "simple_hybrid": "简单混合—前2并线+顺序过滤（simple_hybrid）",
    }
    _readiness_cn = {
        "ready": "就绪（ready）— 数据充足，结果可信",
        "partial": "部分就绪（partial）— 部分数据缺失，结果仅供参考",
        "aborted": "中止（aborted）— 数据严重不足，结果不可信",
        "unknown": "未知",
    }

    lines: list[str] = [
        "# V6OP 操盘报告",
        "",
        f"> 生成时间：{report['generated_at']}",
        f"> run_id：{report.get('run_id', 'N/A')}",
        "",
        "---",
        "",
        "## 一、本次策略摘要",
        "",
        f"- **来源类型**：{_source_type_cn.get(source['type'], source['type'])}",
        f"- **执行路径**：{_path_type_cn.get(strategy['path_type'], strategy['path_type'])}",
        f"- **技能组合**：{', '.join(strategy['selected_skills'])}",
        f"- **股票池规模**：{source.get('scope_count', '—')} 只",
        f"- **最终命中**：{len(hits)} 只",
        f"- **数据就绪状态**：{_readiness_cn.get(dc['readiness'], dc['readiness'])}",
    ]

    if soft_filter:
        lines.append(f"- ⚠ **soft_filter 技能**：{', '.join(soft_filter)}（调试模式，非正式正向结论）")
    if weak_signal:
        lines.append(f"- ⚠ **弱信号技能**：{', '.join(weak_signal)}（no_top 放行，不应视为强正向信号）")
    lines.append("")

    # 二、股票来源
    lines.extend([
        "## 二、股票来源",
        "",
        f"- **来源类型**：{_source_type_cn.get(source['type'], source['type'])}",
        f"- **scope_id**：{source.get('scope_id', '—')}",
        f"- **总数**：{source.get('scope_count', '—')} 只",
        f"- **状态**：{source.get('status', '—')}",
        "",
    ])

    # 三、路径类型与技能组合
    lines.extend([
        "## 三、路径类型与技能组合",
        "",
        f"**路径**：{_path_type_cn.get(strategy['path_type'], strategy['path_type'])}",
        "",
        "**技能列表**：",
    ])
    for ps in producer_summary:
        sem = "正向筛选" if ps["hit_semantics"] == "positive" else "负向排除"
        mode_note = ""
        if ps.get("mode_note"):
            mode_note = f"（{ps['mode_note']}）"
        elif ps.get("signal_note"):
            mode_note = f"（{ps['signal_note']}）"
        lines.append(f"- {ps['skill_name']}：{sem}{mode_note}，命中 {ps['hit_count']} 只 / 未中 {ps['miss_count']} 只")
    lines.append("")

    # 四、关键参数
    lines.extend([
        "## 四、关键参数",
        "",
        "| 技能 | 命中语义 | 命中数 | 未命中 | 实际参数 |",
        "|---|---|---:|---:|---|",
    ])
    for ps in producer_summary:
        params_used = json.dumps(ps.get("params_used", {}), ensure_ascii=False, sort_keys=True)
        lines.append(
            f"| {ps['skill_name']} | {ps['hit_semantics']} | "
            f"{ps['hit_count']} | {ps['miss_count']} | `{params_used}` |"
        )
    lines.append("")

    # 五、数据准备阶段
    lines.extend([
        "## 五、数据准备阶段",
        "",
    ])
    if prefetch_triggered:
        lines.append("**触发了自动预热**，访问了网络数据源（baostock / akshare / yfinance 之一）。")
        lines.append("")
        lines.extend([
            "| 指标 | 数值 |",
            "|---|---:|",
            f"| scope 总数 | {dc['scope_count']} |",
            f"| 命中本地缓存 | {prefetch_hit} |",
            f"| 新拉取成功 | {prefetch_fetched} |",
            f"| 补拉恢复 | {prefetch_recovered} |",
            f"| 拉取失败（最终） | {prefetch_failed} |",
            f"| Stale 降级使用 | {prefetch_stale} |",
            f"| BJ（北交所）跳过 | {prefetch_bj} |",
            f"| K线数据最新日期 | {data_time_max or '—'} |",
            f"| 数据延迟天数 | {stale_days if stale_days is not None else '—'} 自然日 |",
            "",
        ])
        if stale_note:
            lines.append(f"> {stale_note}")
            lines.append("")
    else:
        lines.append("**未触发本次预热**，使用已有缓存，未访问 baostock / akshare / yfinance。")
        lines.extend([
            "",
            "| 指标 | 数值 |",
            "|---|---:|",
            f"| scope 总数 | {dc['scope_count']} |",
            f"| 有缓存 | {dc['cached_count']} |",
            f"| 缓存缺失 | {dc['missing_count']} |",
            f"| 就绪状态 | {dc['readiness']} |",
            "",
        ])

    # 六、本地分析阶段
    _mc_hits   = report.get("mask_cache_hits", 0)
    _mc_misses = report.get("mask_cache_misses", 0)
    lines.extend([
        "## 六、本地分析阶段",
        "",
        "Producer 以 **READ_CACHE_ONLY** 模式运行，不访问 baostock / akshare / yfinance。",
        "缓存缺失时返回 miss，不触发网络请求。",
        "",
        "| 指标 | 数值 |",
        "|---|---:|",
        f"| 有缓存可分析 | {dc['cached_count']} 只 |",
        f"| 缺失缓存（miss） | {dc['missing_count']} 只 |",
        f"| 已知失败 | {dc['failed_count']} 只 |",
        f"| Stale 数据 | {dc['stale_count']} 只 |",
        f"| 失败率 | {dc['failure_rate']:.1%} |",
        f"| Mask缓存命中 | {_mc_hits} |",
        f"| Mask缓存未中 | {_mc_misses} |",
        "",
    ])

    # 七、命中股票列表
    lines.extend([
        f"## 七、命中股票列表（{len(hits)} 只）",
        "",
    ])
    if not hits:
        lines.append("本次无股票命中。")
    else:
        lines.append(f"共命中 **{len(hits)}** 只：")
        lines.append("")
        line_codes = ", ".join(hits[:100])
        if len(hits) > 100:
            line_codes += f"... （共 {len(hits)} 只，以下详细列出前 100 只）"
        lines.append(line_codes)
    lines.append("")

    # 八、单股中文证据
    lines.extend([
        "## 八、单股中文证据",
        "",
    ])
    if not explanations:
        lines.append("无命中股票，无证据输出。")
    else:
        for expl in explanations[:100]:
            code = expl.get("code", "")
            note = expl.get("explanation_cn", "—")
            skill_hits = expl.get("skill_hits", [])
            lines.append(f"### {code}")
            lines.append("")
            lines.append(f"**综合判断**：{note}")
            if skill_hits:
                lines.append("")
                lines.append("**技能证据**：")
                for sh in skill_hits:
                    sname = sh.get("skill_name", sh.get("skill_id", "?"))
                    reason = sh.get("reason_cn", "命中（无详细说明）")
                    lines.append(f"- {sname}：{reason}")
            dqi = expl.get("data_quality_issues", [])
            if dqi:
                lines.append("")
                lines.append("**数据质量备注**：")
                for q in dqi:
                    lines.append(f"- {q}")
            lines.append("")
        if len(explanations) > 100:
            lines.append(f"*（报告截断，仅显示前 100 只，共 {len(explanations)} 只）*")
            lines.append("")

    # 九、排除原因 / 负向技能命中
    neg_producers = [ps for ps in producer_summary if ps.get("hit_semantics") == "negative"]
    lines.extend([
        "## 九、排除原因 / 负向技能命中",
        "",
    ])
    if not neg_producers:
        lines.append("本次无负向技能（排除过滤器）。")
    else:
        for ps in neg_producers:
            lines.append(f"- **{ps['skill_name']}**：命中（排除）{ps['hit_count']} 只，未触发 {ps['miss_count']} 只")
    lines.append("")

    # 十、失败代码 / 旧缓存 / 未分析代码
    lines.extend([
        "## 十、失败代码 / 旧缓存 / 未分析代码",
        "",
    ])
    if failed:
        lines.append(f"**失败代码（{len(failed)} 只，数据拉取失败或解析错误）**：")
        lines.append(", ".join(failed[:50]) + ("..." if len(failed) > 50 else ""))
        lines.append("")
    else:
        lines.append("- 无失败代码。")
    if stale:
        lines.append(f"**Stale 数据（{len(stale)} 只，使用了旧缓存）**：")
        lines.append(", ".join(stale[:50]) + ("..." if len(stale) > 50 else ""))
        lines.append("")
    else:
        lines.append("- 无 Stale 数据。")
    if dc.get("missing_count", 0) > 0:
        lines.append(f"- **缓存缺失（{dc['missing_count']} 只）**：这些代码在本地分析阶段返回 miss，未被纳入命中计算。")
    lines.append("")

    # 十一、风险与边界声明
    lines.extend([
        "## 十一、风险与边界声明",
        "",
    ])
    if warnings:
        lines.append("**警告与标注**：")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")
    lines.extend([
        "**边界说明**：",
        "- 未修改 V5.10 / V6。",
        f"- 是否读取 .env：{'是' if report.get('env_read') else '否（未读取）'}",
        "- 未伪造 scope。",
        "- 所有 Producer 在 READ_CACHE_ONLY 模式下运行，结果基于本地缓存数据。",
    ])
    if soft_filter:
        lines.append(f"- SMC soft_filter 模式已标注（{', '.join(soft_filter)}），结果为软过滤/透传，非 strict 正向命中。")
    if weak_signal:
        lines.append(f"- 波浪弱信号已标注（{', '.join(weak_signal)}），no_top 放行不应视为强正向信号。")
    lines.append("")

    # 十二、运行产物路径
    lines.extend([
        "## 十二、运行产物路径",
        "",
        "- **当前报告 JSON**：`output/current/run_report.json`",
        "- **当前报告 MD**：`output/current/run_report.md`",
        f"- **本次归档目录**：`output/runs/{report.get('run_id', 'N/A')}/`",
        "",
        "---",
        "",
        f"*报告生成时间：{report['generated_at']}　　V6OP 操盘台*",
    ])

    return "\n".join(lines) + "\n"
