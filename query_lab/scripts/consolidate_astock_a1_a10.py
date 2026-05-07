"""Consolidate A1-A10 astock QueryLab results into clean review artifacts.

This script intentionally does not mutate historical run folders. It builds a
clean view from the accepted A1-A10 completed runs, so transient old failures do
not pollute the current astock canon candidate.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
QUERY_LAB = PROJECT_ROOT / "query_lab"
RUNS_DIR = QUERY_LAB / "results" / "runs"
REPORTS_DIR = QUERY_LAB / "reports"


ACCEPTED_RUNS = {
    "A1_basic": "run_20260507_150529",
    "A2_synonym": "run_20260507_150925",
    "A3_combo": "run_20260507_151853",
    "A4_risky": "run_20260507_152032",
    "A5_forbidden": "run_20260507_152351",
    "A6_time_window": "run_20260507_154006",
    "A7_numeric_relative": "run_20260507_154212",
    "A8_capital_flow": "run_20260507_154454",
    "A9_technical_shape": "run_20260507_154831",
    "A10_complex_boundary": "run_20260507_155054",
}


STATUS_RANK = {
    "stable": 5,
    "risky": 4,
    "forbidden": 3,
    "invalid_query": 3,
    "failed": 2,
    "unstable": 1,
    "pending": 0,
}

WEAK_TAGS = {
    "relative_comparison",
    "relative_condition",
    "vague_condition",
    "consecutive_condition",
    "non_standard_field",
    "candlestick",
    "jma_unverified",
    "natural_language",
    "vague_word",
    "sentiment_word",
    "prediction_word",
}


@dataclass
class GroupResult:
    group: str
    run_id: str
    complete: bool
    rows: list[dict]


def load_group(group: str, run_id: str) -> GroupResult:
    run_dir = RUNS_DIR / run_id
    complete = (run_dir / "RUN_COMPLETE").exists()
    rows: list[dict] = []
    analyzed = run_dir / "analyzed_results.jsonl"
    if analyzed.exists():
        for line in analyzed.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return GroupResult(group=group, run_id=run_id, complete=complete, rows=rows)


def status_bucket(row: dict) -> str:
    status = row.get("analysis_status", "")
    if status == "stable":
        risk_tags = {x.strip() for x in (row.get("risk_tags") or "").split("|") if x.strip()}
        if risk_tags & WEAK_TAGS:
            return "weak"
        return "strong"
    if status == "risky":
        return "weak"
    if status in ("forbidden", "invalid_query"):
        return "forbidden"
    if status == "failed":
        return "review"
    return "pending"


def choose_clean(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return clean unique rows and overridden obsolete rows.

    Key is query_text. A later/higher-ranked stable/risky result supersedes a
    transient failed result for the same query_text.
    """
    chosen: dict[str, dict] = {}
    overridden: list[dict] = []
    for row in rows:
        key = row.get("query_text", "").strip()
        if not key:
            key = f"__empty__:{row.get('query_id','')}"
        old = chosen.get(key)
        if old is None:
            chosen[key] = row
            continue
        new_rank = STATUS_RANK.get(row.get("analysis_status", ""), 0)
        old_rank = STATUS_RANK.get(old.get("analysis_status", ""), 0)
        # Prefer higher semantic rank, then newer group/run order naturally.
        if new_rank >= old_rank:
            overridden.append(old)
            chosen[key] = row
        else:
            overridden.append(row)
    return list(chosen.values()), overridden


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = [
        "query_id",
        "test_group",
        "bucket",
        "analysis_status",
        "recommended_usage",
        "risk_level",
        "condition_count",
        "query_text",
        "normalized_intent",
        "field_atoms",
        "risk_tags",
        "result_count",
        "elapsed_ms",
        "failure_type",
        "failure_reason_zh",
        "run_id",
        "notes",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            out = {field: row.get(field, "") for field in fields}
            out["bucket"] = status_bucket(row)
            writer.writerow(out)


def md_table(rows: list[dict], limit: int | None = None) -> list[str]:
    lines = [
        "| 分组 | query_id | 状态 | 用法 | 条件 | 返回 | Query | 标签/原因 |",
        "|---|---:|---|---|---:|---:|---|---|",
    ]
    seq = rows if limit is None else rows[:limit]
    for row in seq:
        reason = row.get("risk_tags") or row.get("failure_reason_zh") or row.get("notes", "")
        query = (row.get("query_text") or "").replace("|", "｜")
        lines.append(
            f"| {row.get('test_group','')} | {row.get('query_id','')} | "
            f"{row.get('analysis_status','')} | {status_bucket(row)} | "
            f"{row.get('condition_count',0)} | {row.get('result_count',0)} | "
            f"{query} | {reason.replace('|','｜')} |"
        )
    if not seq:
        lines.append("| - | - | - | - | - | - | - | - |")
    return lines


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    groups = [load_group(group, run_id) for group, run_id in ACCEPTED_RUNS.items()]
    all_rows = [row for group in groups for row in group.rows]
    clean_rows, overridden = choose_clean(all_rows)

    strong = [r for r in clean_rows if status_bucket(r) == "strong"]
    weak = [r for r in clean_rows if status_bucket(r) == "weak"]
    forbidden = [r for r in clean_rows if status_bucket(r) == "forbidden"]
    review = [r for r in clean_rows if status_bucket(r) == "review"]

    # Stable matrix seeds are strong rows only, grouped by broad topic.
    matrix_seed = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": "A1-A10 accepted completed QueryLab runs",
        "groups": ACCEPTED_RUNS,
        "strong_count": len(strong),
        "weak_count": len(weak),
        "forbidden_count": len(forbidden),
        "review_count": len(review),
        "strong_queries": [
            {
                "query_text": r.get("query_text", ""),
                "group": r.get("test_group", ""),
                "field_atoms": r.get("field_atoms", ""),
                "condition_count": r.get("condition_count", 0),
                "recommended_usage": r.get("recommended_usage", ""),
            }
            for r in strong
        ],
        "weak_queries": [
            {
                "query_text": r.get("query_text", ""),
                "group": r.get("test_group", ""),
                "risk_tags": r.get("risk_tags", ""),
                "recommended_usage": r.get("recommended_usage", ""),
            }
            for r in weak
        ],
        "forbidden_queries": [
            {
                "query_text": r.get("query_text", ""),
                "group": r.get("test_group", ""),
                "reason": r.get("failure_reason_zh", "") or r.get("risk_tags", ""),
            }
            for r in forbidden
        ],
    }

    (REPORTS_DIR / "astock_a1_a10_clean_dictionary.json").write_text(
        json.dumps(matrix_seed, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_csv(REPORTS_DIR / "astock_a1_a10_clean_dictionary.csv", clean_rows)

    status_counts = Counter(r.get("analysis_status", "") for r in clean_rows)
    group_counts = {
        group.group: Counter(r.get("analysis_status", "") for r in group.rows)
        for group in groups
    }
    field_stats: dict[str, Counter] = defaultdict(Counter)
    for row in clean_rows:
        atoms = [x.strip() for x in (row.get("field_atoms") or "").split("|") if x.strip()]
        if not atoms:
            atoms = ["未结构化"]
        for atom in atoms:
            field_stats[atom][row.get("analysis_status", "")] += 1

    lines: list[str] = [
        "# 问财选A股 A1-A10 整理验收报告",
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 1. 纳入范围",
        "",
        "只纳入以下已完成 run；未完成、中断、早期调试 run 全部排除。",
        "",
        "| 组别 | run_id | RUN_COMPLETE | 行数 | 状态统计 |",
        "|---|---|---:|---:|---|",
    ]

    for group in groups:
        counts = ", ".join(f"{k}={v}" for k, v in sorted(group_counts[group.group].items()))
        lines.append(
            f"| {group.group} | {group.run_id} | {group.complete} | "
            f"{len(group.rows)} | {counts} |"
        )

    lines += [
        "",
        "## 2. 清理规则",
        "",
        "- 同一句 Query 后续已 `stable` 或 `risky` 的，覆盖早期 `failed/empty_result/api_error`。",
        "- 接口返回 stable 但含 `relative_comparison / consecutive_condition / non_standard_field` 等风险标签的，整理时降为 `weak`。",
        "- 标准矩阵生成默认使用 `大于 / 小于 / 在...之间 / 为正`，同义词如 `超过/高于/以上` 只作为识别能力，不作为默认生成句式。",
        "- 只整理 A1-A10，本报告不新增 A11-A15。",
        "- `strong` 可进入标准矩阵；`weak` 只可人工选择或二次确认；`forbidden` 不得进入 P1-P6；`review` 留给第三阶段复测。",
        "",
        "## 3. 总体结论",
        "",
        f"- 原始纳入记录：{len(all_rows)} 条",
        f"- 去重清理后：{len(clean_rows)} 条",
        f"- 被覆盖旧记录：{len(overridden)} 条",
        f"- strong / 可进标准矩阵：{len(strong)} 条",
        f"- weak / 谨慎人工用：{len(weak)} 条",
        f"- forbidden / 禁用或非法：{len(forbidden)} 条",
        f"- review / 待第三阶段复测：{len(review)} 条",
        "",
        "清理后状态统计：",
        "",
        "| 状态 | 数量 |",
        "|---|---:|",
    ]
    for status, count in sorted(status_counts.items()):
        lines.append(f"| {status} | {count} |")

    lines += [
        "",
        "## 4. 可进入标准矩阵 strong",
        "",
        "这些是当前最适合做字段矩阵、P1-P6 收藏底座的表达。",
        "",
    ]
    lines += md_table(sorted(strong, key=lambda r: (r.get("test_group", ""), r.get("query_id", ""))))

    lines += [
        "",
        "## 5. weak / risky：可问，但不要默认生成",
        "",
        "这些表达能返回或部分返回，但含相对比较、模糊词、非标准技术字段或图形字段。建议作为人工高级选项，不自动进标准 P。",
        "",
    ]
    lines += md_table(sorted(weak, key=lambda r: (r.get("test_group", ""), r.get("query_id", ""))))

    lines += [
        "",
        "## 6. forbidden / invalid：不得进入 P1-P6",
        "",
    ]
    lines += md_table(sorted(forbidden, key=lambda r: (r.get("test_group", ""), r.get("query_id", ""))))

    lines += [
        "",
        "## 7. review：第三阶段优先复测",
        "",
    ]
    lines += md_table(sorted(review, key=lambda r: (r.get("test_group", ""), r.get("query_id", ""))))

    lines += [
        "",
        "## 8. 字段稳定性快照",
        "",
        "| 字段 | stable | risky | failed | forbidden | invalid_query |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for field, counts in sorted(
        field_stats.items(),
        key=lambda kv: (-(kv[1].get("stable", 0)), kv[0]),
    ):
        lines.append(
            f"| {field} | {counts.get('stable',0)} | {counts.get('risky',0)} | "
            f"{counts.get('failed',0)} | {counts.get('forbidden',0)} | "
            f"{counts.get('invalid_query',0)} |"
        )

    lines += [
        "",
        "## 9. 第三阶段建议",
        "",
        "- 先做 A11：给定股票池 / Bridge 二次验证。重点测“在这些代码中筛选/验证”。",
        "- 再做 A12：重型相对比较降载测试。比如先主题/板块/均线缩小股票池，再问平均成交额、量比、缩量。",
        "- 再做 A13：K线/形态字段专项。锤子线、阳包阴、平台突破、跌破/不跌破均线。",
        "- 再做 A14：涨停/回撤/缩量组合。比如十日内涨停、三日缩量、回撤 3%、未跌破 5 日均线。",
        "- 最后做 A15：矩阵生成验证。用法典字段+关系+数值自动拼标准 Query，再跑小批量验证。",
        "",
        "## 10. 产物",
        "",
        "- `query_lab/reports/astock_a1_a10_clean_dictionary.csv`：Excel 友好 UTF-8 BOM 表。",
        "- `query_lab/reports/astock_a1_a10_clean_dictionary.json`：后续页面/矩阵可读取的干净字典。",
        "- `query_lab/reports/ASTOCK_A1_A10_CONSOLIDATED_REPORT.md`：本整理报告。",
        "",
    ]

    (REPORTS_DIR / "ASTOCK_A1_A10_CONSOLIDATED_REPORT.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print("Wrote:")
    print(REPORTS_DIR / "ASTOCK_A1_A10_CONSOLIDATED_REPORT.md")
    print(REPORTS_DIR / "astock_a1_a10_clean_dictionary.csv")
    print(REPORTS_DIR / "astock_a1_a10_clean_dictionary.json")


if __name__ == "__main__":
    main()
