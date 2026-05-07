"""
report_writer.py — V2 报告写入器（累计版）

核心改动：
1. stable_dictionary / risk_dictionary / forbidden_dictionary 从所有历史 analyzed_results.jsonl 累计生成
2. 单次运行报告 run_summary.md 只反映本次
3. astock_ceiling_report.md 回答天花板分析问题
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


def _load_all_analyzed(query_lab_dir: Path) -> list[dict]:
    """扫描已完成 runs/*/analyzed_results.jsonl，累计返回。"""
    rows: list[dict] = []
    runs_dir = query_lab_dir / "results" / "runs"
    if not runs_dir.exists():
        return rows
    for run_dir in sorted(runs_dir.iterdir()):
        if not _is_completed_run(run_dir):
            continue
        f = run_dir / "analyzed_results.jsonl"
        if f.exists():
            with f.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        try:
                            rows.append(json.loads(line))
                        except Exception:
                            pass
    return rows


def _is_completed_run(run_dir: Path) -> bool:
    """只有带完成标记的 run 才能进入累计法典/字典。"""
    if (run_dir / "RUN_COMPLETE").exists():
        return True
    manifest = run_dir / "run_manifest.json"
    if not manifest.exists():
        return False
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except Exception:
        return False
    return data.get("completed") is True and data.get("status") == "completed"


class ReportWriter:
    def __init__(self, query_lab_dir: Path) -> None:
        self.query_lab_dir = query_lab_dir
        self.reports_dir = query_lab_dir / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    # ─── 单次 run 报告 ────────────────────────────────────────────────────────

    def write_run_summary(
        self,
        run_id: str,
        run_dir: Path,
        analyzed: list[Any],
        summary: dict,
        route: str,
        group: str | None,
    ) -> None:
        lines = [
            f"# QueryLab 运行报告 — {run_id}",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"**路由**: {route}  ",
            f"**分组**: {group or '全部'}  ",
            f"**总条数**: {summary['total']}  ",
            "",
            "## 状态统计",
            "",
            "| 状态 | 数量 |",
            "|------|------|",
            f"| stable / 稳定 | {summary['stable']} |",
            f"| unstable / 不稳定 | {summary['unstable']} |",
            f"| risky / 高风险 | {summary['risky']} |",
            f"| failed / 失败 | {summary['failed']} |",
            f"| forbidden / 禁用 | {summary['forbidden']} |",
            f"| invalid_query | {summary['invalid_query']} |",
            f"| pending | {summary['pending']} |",
            "",
        ]

        # 失败类型细分
        if summary.get("failure_types"):
            lines += ["## 失败类型分布", ""]
            for ft, cnt in summary["failure_types"].items():
                lines.append(f"- `{ft}`: {cnt} 条")
            lines.append("")

        astock = [a for a in analyzed if _get(a, "skill_type") == "astock"]
        if astock:
            lines += self._section_table("A股查询结果", astock)

        # 失败案例
        failed = [a for a in analyzed if _get(a, "analysis_status") in ("failed", "invalid_query")]
        if failed:
            lines += ["## 失败与非法案例", ""]
            for a in failed:
                ft = _get(a, "failure_type", "")
                fr = _get(a, "failure_reason_zh", "")
                lines.append(f"- **[{_get(a,'query_id')}]** `{_get(a,'query_text')[:60]}` "
                              f"→ `{_get(a,'exec_status')}` [{ft}] {fr}")
            lines.append("")

        out = run_dir / "run_summary.md"
        out.write_text("\n".join(lines), encoding="utf-8")
        print(f"[ReportWriter] run_summary → {out}")

    def write_astock_ceiling_report(
        self,
        run_id: str,
        run_dir: Path,
        analyzed: list[Any],
        summary: dict,
    ) -> None:
        """生成天花板报告（per run + 全局）"""
        all_analyzed = _load_all_analyzed(self.query_lab_dir)
        lines = self._build_ceiling_report(run_id, all_analyzed)

        # per run
        (run_dir / "astock_ceiling_report.md").write_text("\n".join(lines), encoding="utf-8")
        # 全局
        (self.reports_dir / "astock_ceiling_report.md").write_text("\n".join(lines), encoding="utf-8")
        print(f"[ReportWriter] astock_ceiling_report → 已更新")

    def _build_ceiling_report(self, run_id: str, all_analyzed: list[dict]) -> list[str]:
        astock_rows = [r for r in all_analyzed if r.get("skill_type") == "astock"]
        stable = [r for r in astock_rows if r.get("analysis_status") == "stable"]
        failed = [r for r in astock_rows if r.get("analysis_status") == "failed"]
        risky = [r for r in astock_rows if r.get("analysis_status") == "risky"]
        forbidden = [r for r in astock_rows if r.get("analysis_status") == "forbidden"]
        invalid = [r for r in astock_rows if r.get("analysis_status") == "invalid_query"]

        # 按条件数分析
        cond_stability: dict[int, list] = defaultdict(list)
        for r in astock_rows:
            cc = int(r.get("condition_count", 0) or 0)
            cond_stability[cc].append(r.get("analysis_status", ""))

        # 最短稳定路径
        shortest_stable = None
        for r in sorted(stable, key=lambda x: int(x.get("condition_count", 99) or 99)):
            shortest_stable = r
            break

        # 复杂度天花板分析
        ceiling_lines: list[str] = []
        for cc in sorted(cond_stability.keys()):
            statuses = cond_stability[cc]
            ok_count = statuses.count("stable")
            total_count = len(statuses)
            rate = round(ok_count / total_count, 2) if total_count > 0 else 0
            ceiling_lines.append(f"| {cc} | {total_count} | {ok_count} | {rate:.0%} |")

        # 最稳定字段（从 field_atoms 统计）
        field_success: dict[str, int] = defaultdict(int)
        field_total: dict[str, int] = defaultdict(int)
        for r in astock_rows:
            atoms = [a.strip() for a in (r.get("field_atoms") or "").split("|") if a.strip()]
            status = r.get("analysis_status", "")
            for atom in atoms:
                field_total[atom] += 1
                if status == "stable":
                    field_success[atom] += 1

        stable_fields = sorted(
            [(f, field_success[f], field_total[f]) for f in field_total],
            key=lambda x: (-x[1]/max(x[2],1), -x[1])
        )

        lines = [
            "# 问财选A股 天花板报告",
            "",
            f"**更新时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"**累计实测**: {len(astock_rows)} 条  ",
            f"**最新 run_id**: {run_id}  ",
            "",
            "## 1. 最短稳定问法",
            "",
        ]

        if shortest_stable:
            lines += [
                f"**推荐最短稳定表达**：`{shortest_stable.get('query_text','')}`",
                "",
                f"- 条件数：{shortest_stable.get('condition_count', 0)}",
                f"- 返回数量：{shortest_stable.get('result_count', 0)}",
                f"- 耗时：{shortest_stable.get('elapsed_ms', 0):.0f}ms",
                f"- 语义：{shortest_stable.get('normalized_intent','')}",
                "",
            ]
        else:
            lines += ["*尚无稳定结果，请继续实测。*", ""]

        lines += [
            "## 2. 推荐标准表达（稳定清单）",
            "",
            "| query_text | 条件数 | 返回数量 | 耗时ms | 组别 |",
            "|-----------|--------|---------|--------|------|",
        ]
        for r in sorted(stable, key=lambda x: int(x.get("condition_count",0) or 0)):
            qt = (r.get("query_text") or "")[:60].replace("|", "｜")
            lines.append(f"| {qt} | {r.get('condition_count',0)} | "
                         f"{r.get('result_count',0)} | {r.get('elapsed_ms',0):.0f} | {r.get('test_group','')} |")
        if not stable:
            lines.append("| *尚无稳定表达* | - | - | - | - |")
        lines.append("")

        lines += [
            "## 3. 复杂度天花板分析",
            "",
            "| 条件数 | 测试条数 | 稳定条数 | 稳定率 |",
            "|--------|---------|---------|--------|",
        ]
        lines += ceiling_lines if ceiling_lines else ["| - | - | - | - |"]
        lines.append("")

        # 找天花板拐点
        ceiling_cnt = None
        for cc in sorted(cond_stability.keys()):
            statuses = cond_stability[cc]
            ok_count = statuses.count("stable")
            total_count = len(statuses)
            rate = ok_count / total_count if total_count > 0 else 0
            if rate < 0.6 and total_count >= 2:
                ceiling_cnt = cc
                break

        if ceiling_cnt:
            lines.append(f"**天花板拐点**：从 **{ceiling_cnt} 条件** 开始稳定率明显下降。")
            lines.append(f"**建议最大条件数**：{ceiling_cnt - 1} 条。")
        else:
            lines.append("**天花板拐点**：当前测试数据不足，尚无明确结论。建议运行 A3_combo 完整阶梯测试。")
        lines.append("")

        lines += [
            "## 4. 最稳定字段",
            "",
            "| 字段 | 稳定次数 | 测试次数 | 稳定率 |",
            "|------|---------|---------|--------|",
        ]
        for fname, sc, tc in stable_fields[:15]:
            rate = sc / tc if tc > 0 else 0
            lines.append(f"| {fname} | {sc} | {tc} | {rate:.0%} |")
        if not stable_fields:
            lines.append("| *无数据* | - | - | - |")
        lines.append("")

        lines += [
            "## 5. 高风险字段",
            "",
        ]
        if risky:
            lines += [
                "| query_text | risk_tags | 组别 |",
                "|-----------|----------|------|",
            ]
            for r in risky:
                qt = (r.get("query_text") or "")[:60].replace("|", "｜")
                lines.append(f"| {qt} | {r.get('risk_tags','')} | {r.get('test_group','')} |")
        else:
            lines.append("*无已测高风险表达。*")
        lines.append("")

        lines += [
            "## 6. 禁止问（forbidden + invalid_query）",
            "",
        ]
        all_forbidden = forbidden + invalid
        if all_forbidden:
            lines += [
                "| query_text | 禁止原因 | 类别 |",
                "|-----------|---------|------|",
            ]
            for r in all_forbidden:
                qt = (r.get("query_text") or "")[:60].replace("|", "｜")
                reason = (r.get("failure_reason_zh") or r.get("notes") or "")[:60]
                lines.append(f"| {qt} | {reason} | {r.get('analysis_status','')} |")
        else:
            lines.append("*无已记录禁用表达。*")
        lines.append("")

        lines += [
            "## 7. 失败原因分布",
            "",
        ]
        failure_type_cnt: dict[str, int] = defaultdict(int)
        for r in failed:
            failure_type_cnt[r.get("failure_type", "unknown")] += 1
        if failure_type_cnt:
            for ft, cnt in sorted(failure_type_cnt.items(), key=lambda x: -x[1]):
                lines.append(f"- `{ft}`: {cnt} 条")
        else:
            lines.append("*无失败记录。*")
        lines.append("")

        lines += [
            "## 8. 用户自然语言改写建议",
            "",
            "| 用户说法 | 建议改写 | 状态 |",
            "|---------|---------|------|",
            "| 强势股 | 今日涨幅大于3%，今日成交额大于3亿 | 待验证 |",
            "| 小盘股 | 流通市值在30亿到150亿之间 | 待验证 |",
            "| 放量上涨 | 今日涨幅大于3%，今日量比大于1.5，今日成交额大于3亿 | 待验证 |",
            "| 资金关注 | 今日主力净流入为正，今日成交额大于3亿 | 待验证 |",
            "",
            "> 以上改写规则需实测后更新为 stable 方可进入 normalizer。",
            "",
        ]
        return lines

    # ─── 累计字典 ──────────────────────────────────────────────────────────────

    def write_stable_dictionary(self, _analyzed: list[Any] | None = None) -> None:
        """累计稳定字典：从所有历史 analyzed_results.jsonl 生成。"""
        all_rows = _load_all_analyzed(self.query_lab_dir)
        # 以 skill_type + query_text 去重，取最高 result_count
        seen: dict[str, dict] = {}
        for r in all_rows:
            if r.get("analysis_status") != "stable":
                continue
            key = f"{r.get('skill_type','')}__{r.get('query_text','')}"
            if key not in seen or r.get("result_count", 0) > seen[key].get("result_count", 0):
                seen[key] = r

        stable = sorted(seen.values(),
                        key=lambda x: (x.get("skill_type", ""), int(x.get("condition_count", 0) or 0)))

        lines = [
            "# 累计稳定表达字典",
            "",
            f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"共 {len(stable)} 条稳定表达（跨所有 run 去重）",
            "",
            "| query_id | skill_type | 条件数 | query_text | 返回数量 | 最新 run |",
            "|----------|-----------|--------|-----------|---------|---------|",
        ]
        for r in stable:
            qt = (r.get("query_text") or "")[:60].replace("|", "｜")
            lines.append(f"| {r.get('query_id','')} | {r.get('skill_type','')} | "
                         f"{r.get('condition_count',0)} | {qt} | "
                         f"{r.get('result_count',0)} | {r.get('run_id','')[:20]} |")
        lines.append("")

        out = self.reports_dir / "stable_dictionary.md"
        out.write_text("\n".join(lines), encoding="utf-8")
        print(f"[ReportWriter] stable_dictionary（累计）→ {out}  ({len(stable)} 条)")

    def write_risk_dictionary(self, _analyzed: list[Any] | None = None) -> None:
        """累计风险字典。"""
        all_rows = _load_all_analyzed(self.query_lab_dir)
        seen: dict[str, dict] = {}
        for r in all_rows:
            if r.get("analysis_status") not in ("risky", "failed"):
                continue
            key = f"{r.get('skill_type','')}__{r.get('query_text','')}__{r.get('analysis_status','')}"
            seen[key] = r

        risky = sorted(seen.values(), key=lambda x: x.get("analysis_status", ""))
        lines = [
            "# 累计风险表达字典",
            "",
            f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"共 {len(risky)} 条风险/失败表达",
            "",
            "| query_id | 状态 | 失败类型 | query_text | 失败原因 |",
            "|----------|------|---------|-----------|---------|",
        ]
        for r in risky:
            qt = (r.get("query_text") or "")[:50].replace("|", "｜")
            reason = (r.get("failure_reason_zh") or "")[:60].replace("|", "｜")
            lines.append(f"| {r.get('query_id','')} | {r.get('analysis_status','')} | "
                         f"{r.get('failure_type','')} | {qt} | {reason} |")
        lines.append("")

        out = self.reports_dir / "risk_dictionary.md"
        out.write_text("\n".join(lines), encoding="utf-8")
        print(f"[ReportWriter] risk_dictionary（累计）→ {out}  ({len(risky)} 条)")

    def write_forbidden_dictionary(self, _analyzed: list[Any] | None = None) -> None:
        """累计禁问字典。"""
        all_rows = _load_all_analyzed(self.query_lab_dir)
        seen: dict[str, dict] = {}
        for r in all_rows:
            if r.get("analysis_status") not in ("forbidden", "invalid_query"):
                continue
            key = f"{r.get('skill_type','')}__{r.get('query_text','')}"
            seen[key] = r

        forbidden = list(seen.values())
        lines = [
            "# 累计禁问字典",
            "",
            f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"共 {len(forbidden)} 条禁用/非法表达",
            "",
            "> 这些表达**不得**自动生成或进入 P1-P6。",
            "",
            "| query_id | 状态 | query_text | 禁止原因 | 类别 |",
            "|----------|------|-----------|---------|------|",
        ]
        for r in forbidden:
            qt = (r.get("query_text") or "")[:50].replace("|", "｜")
            reason = (r.get("failure_reason_zh") or r.get("notes") or "")[:60].replace("|", "｜")
            lines.append(f"| {r.get('query_id','')} | {r.get('analysis_status','')} | "
                         f"{qt} | {reason} | {r.get('category','')} |")
        lines.append("")

        out = self.reports_dir / "forbidden_dictionary.md"
        out.write_text("\n".join(lines), encoding="utf-8")
        print(f"[ReportWriter] forbidden_dictionary（累计）→ {out}  ({len(forbidden)} 条)")

    def write_normalizer_rules(self, _analyzed: list[Any] | None = None) -> None:
        all_rows = _load_all_analyzed(self.query_lab_dir)
        stable_texts = {r.get("query_text", "") for r in all_rows if r.get("analysis_status") == "stable"}

        seed_rules = [
            ("强势股",      "今日涨幅大于3%，今日成交额大于3亿",                        "待验证"),
            ("小盘股",      "流通市值在30亿到150亿之间",                              "待验证"),
            ("低位强势",    "流通市值在30亿到150亿之间，近20日涨幅小于20%，今日涨幅大于3%，今日成交额大于3亿", "待验证"),
            ("放量上涨",    "今日涨幅大于3%，今日量比大于1.5，今日成交额大于3亿",          "待验证"),
            ("资金关注",    "今日主力净流入为正，今日成交额大于3亿",                      "待验证"),
        ]

        lines = [
            "# 自然语言改写规则",
            "",
            f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "| 用户自然语言 | 建议改写 | 状态 |",
            "|------------|---------|------|",
        ]
        for natural, canonical, _ in seed_rules:
            status = "stable（已验证）" if canonical in stable_texts else "待验证"
            lines.append(f"| {natural} | {canonical} | {status} |")
        lines += ["", "> 只有 stable 状态的改写才能进入 normalizer 自动使用。", ""]

        out = self.reports_dir / "query_normalizer_rules.md"
        out.write_text("\n".join(lines), encoding="utf-8")
        print(f"[ReportWriter] query_normalizer_rules → {out}")

    def write_all_reports(
        self,
        run_id: str,
        run_dir: Path,
        analyzed: list[Any],
        summary: dict,
        route: str,
        group: str | None,
    ) -> None:
        self.write_run_summary(run_id, run_dir, analyzed, summary, route, group)
        # 只对 astock 生成天花板报告
        if route in ("astock", "all"):
            self.write_astock_ceiling_report(run_id, run_dir, analyzed, summary)
        # 累计字典（不传 analyzed，从历史文件读）
        self.write_stable_dictionary()
        self.write_risk_dictionary()
        self.write_forbidden_dictionary()
        self.write_normalizer_rules()

    # ─── 内部工具 ──────────────────────────────────────────────────────────────

    def _section_table(self, title: str, results: list[Any]) -> list[str]:
        lines = [
            f"## {title}",
            "",
            "| query_id | 状态 | 失败类型 | 结果数 | 耗时ms | query_text |",
            "|----------|------|---------|--------|--------|------------|",
        ]
        for a in results:
            qt = (_get(a, "query_text") or "")[:50].replace("|", "｜")
            lines.append(
                f"| {_get(a,'query_id')} | {_get(a,'analysis_status')} | "
                f"{_get(a,'failure_type','')} | {_get(a,'result_count')} | "
                f"{float(_get(a,'elapsed_ms',0)):.0f} | {qt} |"
            )
        lines.append("")
        return lines


def _get(obj: Any, key: str, default: Any = "") -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        return getattr(obj, key, default)
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default
