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
from datetime import date as _date
from pathlib import Path
from typing import Any

from time_utils import TIMEZONE_LABEL, format_cst, iso_cst, today_cst


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
    status = execution_result.get("status", "completed")
    error = execution_result.get("error")
    if status == "error" and error and error not in warnings:
        warnings.append(str(error))
    source_cfg = (execution_result.get("strategy") or {}).get("source", {})
    report_generated_at = format_cst()
    report_generated_at_iso = iso_cst()
    fetch_data_time_max = (
        fetch.get("data_time_max")
        or (fetch.get("prefetch_report") or {}).get("data_time_max")
        or execution_result.get("data_time_max")
    )

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
            ps["signal_note"] = "V5移植版，no_top→辅助放行"
        producer_summary.append(ps)

    data_coverage = {
        "scope_count": scope.get("scope_count", 0),
        "cached_count": len(fetch.get("cached_codes", [])),
        "missing_count": len(fetch.get("missing_codes", [])),
        "failed_count": len(fetch.get("failed_codes", [])),
        "stale_count": len(fetch.get("stale_codes", [])),
        "readiness": fetch.get("readiness", "unknown"),
        "failure_rate": fetch.get("failure_rate", 0.0),
        "data_time_max": fetch_data_time_max,
    }
    run_scope = (
        execution_result.get("run_scope")
        or scope.get("run_scope")
        or (execution_result.get("strategy") or {}).get("run_scope")
        or {}
    )
    run_scope_limit = int(run_scope.get("limit") or (execution_result.get("strategy") or {}).get("run_scope_limit") or 0)
    run_scope_label = run_scope.get("label") or (f"测试 {run_scope_limit}" if run_scope_limit > 0 else "全量")
    data_coverage.update({
        "source_original_count": run_scope.get("original_scope_count", scope.get("scope_count", 0)),
        "run_scope_limit": run_scope_limit,
        "run_scope_label": run_scope_label,
        "run_scope_applied": bool(run_scope.get("applied", False)),
        "run_scope_effective_count": run_scope.get("effective_scope_count", scope.get("scope_count", 0)),
    })

    source_type = scope.get("source_type")
    source_limit = source_cfg.get("limit")
    source_count = scope.get("scope_count", 0)
    unlimited = source_limit in (None, "", 0)
    # G3: 来源层语义 — 默认不限档位，旧 limit 仅作为兼容字段显示
    if unlimited:
        _limit_semantic = {
            "wencai": "不限档位，自动翻页直到没有新增股票",
            "all_a":  "全量读取本地 A 股名单，不截取",
            "manual": "手动输入，无上限限制",
        }.get(source_type or "", "不限")
    else:
        _limit_semantic = {
            "wencai": f"最多接收问财返回结果（limit={source_limit}），不保证一定返回这么多",
            "all_a":  f"本地A股名单最多截取 {source_limit} 只",
            "manual": "手动输入，无上限限制",
        }.get(source_type or "", f"limit={source_limit}")
    source_notes = {
        "manual": "手动输入股票代码；不是外部接口返回。",
        "all_a":  "读取本地 data/ashare_codes.txt，全量进入来源股票池。",
        "wencai": "调用问财接口取得股票池；默认不限档位，实际返回多少以问财接口为准。",
    }
    # G3 + G4-auth: source_info 诊断节
    source_info: dict[str, Any] = {
        "source_type": source_type,
        "status": scope.get("status"),
        "actual_count": source_count,
        "limit": source_limit,
        "limit_semantic": _limit_semantic,
        "run_scope": run_scope,
        "note": source_notes.get(source_type or "", "未知股票来源"),
    }
    if source_type == "wencai":
        source_info.update({
            "query_text":   scope.get("query_text", ""),
            "api_called":   scope.get("api_called", False),
            "elapsed_s":    scope.get("elapsed_s", 0.0),
            "count_note":   scope.get("count_note", ""),
            "auth_note":    scope.get("auth_note", (
                "pywencai 使用 session 认证（非 api_key 参数），"
                "IWENCAI_API_KEY 存在但未传入 pywencai.get()，"
                "实际认证依赖 pywencai 本地 session cookie。"
            )),
        })

    data_sources = {
        "stock_source": {
            "type": source_type,
            "actual_count": source_count,
            "original_count": run_scope.get("original_scope_count", source_count),
            "run_scope": run_scope,
            "limit": source_limit,
            "status": scope.get("status"),
            "note": source_notes.get(source_type or "", "未知股票来源"),
        },
        "kline": {
            "database": "var/cache/kline_daily",
            "analysis_mode": "Producer 阶段只读本地 K 线数据库",
            "prefetch_provider": (
                "baostock（本轮自动取数）"
                if execution_result.get("prefetch_triggered", False)
                else "本轮未访问外部行情源"
            ),
            "adjust": "hfq",
            "data_bar_time": fetch_data_time_max or "unknown",
            "source_publish_time": "unknown",
            "source_publish_note": "当前 baostock / 本地缓存链路未提供逐条发布时间戳。",
        },
    }

    actual_days_used: int = int(
        execution_result.get("actual_days_used")
        or (execution_result.get("strategy") or {}).get("params", {}).get("days", 365)
    )

    run_report: dict[str, Any] = {
        "run_id": execution_result.get("run_id", ""),
        "generated_at": report_generated_at,
        "generated_at_iso": report_generated_at_iso,
        "timezone": TIMEZONE_LABEL,
        "elapsed_seconds": execution_result.get("elapsed_seconds"),
        "status": status,
        "error": error,
        "actual_days_used": actual_days_used,
        "strategy": {
            "source": {
                "type": scope.get("source_type"),
                "scope_id": scope.get("scope_id"),
                "scope_count": scope.get("scope_count"),
                "status": scope.get("status"),
                "limit": source_cfg.get("limit"),
            },
            "selected_skills": execution_result.get("selected_skills", []),
            "path_type": execution_result.get("path_type", ""),
            "run_scope_limit": run_scope_limit,
            "run_scope": run_scope,
            "params": execution_result.get("params", {}),
        },
        "strategy_snapshot": execution_result.get("strategy", {}),
        "prefetch_report": fetch.get("prefetch_report", {}),
        "producer_summary": producer_summary,
        "expression": {
            "steps": expression.get("steps", []),
            "primary_expression_id": expression.get("primary_expression_id"),
            "executable": expression.get("executable", False),
            "path_description": expression.get("path_description", ""),
            "sequential_chain": expression.get("sequential_chain", []),
            "metadata": expr_metadata,
        },
        "final_hit_codes": final_hits,
        "final_hit_count": len(final_hits),
        "explanations": explanations.get("hits", []),
        "failed_codes": fetch.get("failed_codes", []),
        "stale_codes": fetch.get("stale_codes", []),
        "data_coverage": data_coverage,
        "data_sources": data_sources,
        "source_info": source_info,
        "run_scope": run_scope,
        "global_explanation": execution_result.get("global_explanation", {}),
        "data_provenance": execution_result.get("data_provenance", {}),
        "bridge_result": execution_result.get("bridge_result", {}),
        "data_time_max": fetch_data_time_max,
        "warnings": warnings,
        "prefetch_triggered": execution_result.get("prefetch_triggered", False),
        "mask_cache_hits":   execution_result.get("mask_cache_hits", 0),
        "mask_cache_misses": execution_result.get("mask_cache_misses", 0),
        "api_called": execution_result.get("api_called", False),
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
    data_time_max: str | None = (
        prefetch_rpt.get("data_time_max")
        or report.get("data_time_max")
        or dc.get("data_time_max")
    )

    # 计算数据新鲜度（stale_days = 距今自然日数）
    stale_days: int | None = None
    stale_note = ""
    if data_time_max:
        try:
            delta = (today_cst() - _date.fromisoformat(data_time_max[:10])).days
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
        "# A股全链路量化扫描报告 V6OP",
        "",
        "> V6OP 操盘报告",
        f"> 生成时间：{report['generated_at']}",
        f"> 时间口径：中国时间 {report.get('timezone', TIMEZONE_LABEL)}",
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
        f"- **运行耗时**：{report.get('elapsed_seconds', '—')} 秒",
    ]

    if soft_filter:
        lines.append(f"- ⚠ **soft_filter 技能**：{', '.join(soft_filter)}（调试模式，非正式正向结论）")
    if weak_signal:
        lines.append(f"- ⚠ **辅助放行技能**：{', '.join(weak_signal)}（no_top 只是未发现5浪顶部，不应视为强买入信号）")
    lines.append("")

    # 二、股票来源
    data_sources = report.get("data_sources", {})
    stock_source = data_sources.get("stock_source", {})
    kline_source = data_sources.get("kline", {})
    source_limit = source.get("limit")
    source_limit_text = "不限" if source_limit in (None, "", 0) else f"最多 {source_limit} 只"
    run_scope = report.get("run_scope", {})
    run_scope_limit = int(run_scope.get("limit") or 0)
    run_scope_text = run_scope.get("label") or (f"测试 {run_scope_limit}" if run_scope_limit > 0 else "全量")
    run_scope_origin = run_scope.get("original_scope_count", source.get("scope_count", "—"))
    lines.extend([
        "## 二、股票来源",
        "",
        f"- **来源类型**：{_source_type_cn.get(source['type'], source['type'])}",
        f"- **scope_id**：{source.get('scope_id', '—')}",
        f"- **实际来源数量**：{source.get('scope_count', '—')} 只",
        f"- **档位 / 上限**：{source_limit_text}",
        f"- **状态**：{source.get('status', '—')}",
        f"- **来源说明**：{stock_source.get('note', '—')}",
        "",
        "**行情/K线来源口径**：",
        f"- K线数据库：`{kline_source.get('database', 'var/cache/kline_daily')}`",
        f"- 本轮行情取数：{kline_source.get('prefetch_provider', '—')}",
        f"- 分析阶段：{kline_source.get('analysis_mode', 'Producer 阶段只读本地 K 线数据库')}",
        f"- 复权口径：{kline_source.get('adjust', 'hfq')}",
        f"- 数据最后K线日期（data_bar_time）：{data_time_max or 'unknown'}",
        f"- 数据源发布时间（source_publish_time）：unknown（{kline_source.get('source_publish_note', '行情源未提供发布时间戳')}）",
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
        lines.append("**触发了自动取数**：本轮访问 baostock，把缺少的日线写入本地 K 线数据库。")
        lines.append("")
        lines.extend([
            "| 指标 | 数值 |",
            "|---|---:|",
            f"| 来源总数 | {dc['scope_count']} |",
            f"| 本地已有K线 | {prefetch_hit} |",
            f"| 本次新取K线 | {prefetch_fetched} |",
            f"| 备用源补回 | {prefetch_recovered} |",
            f"| 取数失败 | {prefetch_failed} |",
            f"| 使用旧K线 | {prefetch_stale} |",
            f"| BJ（北交所）跳过 | {prefetch_bj} |",
            f"| K线数据最新日期 | {data_time_max or '—'} |",
            "| 数据源发布时间 | unknown（baostock 未提供逐条发布时间戳） |",
            f"| 数据延迟天数 | {stale_days if stale_days is not None else '—'} 自然日 |",
            "",
        ])
        if stale_note:
            lines.append(f"> {stale_note}")
            lines.append("")
    else:
        lines.append("**未触发本次预热 / 取数**：本轮不用重新拉行情，直接使用本地 K 线数据库；没有访问 baostock / akshare / yfinance。")
        lines.extend([
            "",
            "| 指标 | 数值 |",
            "|---|---:|",
            f"| 来源总数 | {dc['scope_count']} |",
            f"| 本地K线可用 | {dc['cached_count']} |",
            f"| 缺K线数据 | {dc['missing_count']} |",
            f"| K线数据最新日期 | {data_time_max or '—'} |",
            "| 数据源发布时间 | unknown |",
            f"| 数据延迟天数 | {stale_days if stale_days is not None else '—'} 自然日 |",
            f"| 就绪状态 | {dc['readiness']} |",
            "",
        ])
        if stale_note:
            lines.append(f"> {stale_note}")
            lines.append("")

    # 六、本地分析阶段
    _mc_hits   = report.get("mask_cache_hits", 0)
    _mc_misses = report.get("mask_cache_misses", 0)
    lines.extend([
        "## 六、本地分析阶段",
        "",
        "Producer 只读取 **本地K线数据**，不访问 baostock / akshare / yfinance。",
        "本地K线缺失时返回 miss，不触发网络请求。",
        "",
        "| 指标 | 数值 |",
        "|---|---:|",
        f"| 本地K线可分析 | {dc['cached_count']} 只 |",
        f"| 缺K线数据（miss） | {dc['missing_count']} 只 |",
        f"| 取数失败 | {dc['failed_count']} 只 |",
        f"| 旧K线数据 | {dc['stale_count']} 只 |",
        f"| 取数失败率 | {dc['failure_rate']:.1%} |",
        f"| 技能结果复用命中 | {_mc_hits} |",
        f"| 技能结果重新计算 | {_mc_misses} |",
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

    # 十、失败代码 / 旧K线 / 未分析代码
    lines.extend([
        "## 十、失败代码 / 旧K线 / 未分析代码",
        "",
    ])
    if failed:
        lines.append(f"**失败代码（{len(failed)} 只，数据拉取失败或解析错误）**：")
        lines.append(", ".join(failed[:50]) + ("..." if len(failed) > 50 else ""))
        lines.append("")
    else:
        lines.append("- 无失败代码。")
    if stale:
        lines.append(f"**旧K线数据（{len(stale)} 只，使用了本地旧K线）**：")
        lines.append(", ".join(stale[:50]) + ("..." if len(stale) > 50 else ""))
        lines.append("")
    else:
        lines.append("- 无旧K线数据。")
    if dc.get("missing_count", 0) > 0:
        lines.append(f"- **缺K线数据（{dc['missing_count']} 只）**：这些代码在本地分析阶段返回 miss，未被纳入命中计算。")
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
        "- 所有 Producer 只读本地K线数据，结果不包含本轮实时网络取数。",
    ])
    if soft_filter:
        lines.append(f"- SMC soft_filter 模式已标注（{', '.join(soft_filter)}），结果为软过滤/透传，非 strict 正向命中。")
    if weak_signal:
        lines.append(f"- 波浪辅助放行已标注（{', '.join(weak_signal)}），no_top 放行不应视为强买入信号。")
    lines.append("")

    # 十二、运行产物路径
    lines.extend([
        "## 十二、运行产物路径",
        "",
        "- **当前报告 JSON**：`output/current/run_report.json`",
        "- **当前报告 MD**：`output/current/run_report.md`",
        "- **人工可读报告格式**：Markdown（`.md`）；JSON 仅用于前端/程序读取。",
        f"- **本次归档目录**：`output/runs/{report.get('run_id', 'N/A')}/`",
        "",
        "---",
        "",
        f"*报告生成时间：{report['generated_at']}　　V6OP 操盘台*",
    ])

    return "\n".join(lines) + "\n"
