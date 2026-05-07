"""
diagnose_astock.py — A股诊断工具

不请求问财，只查法典和字典。
输入用户自然语言 → 输出各片段分类和建议改写。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ─── 内置规则 ─────────────────────────────────────────────────────────────────

# 常见字段关键词 → 对应稳定写法
_FIELD_PATTERNS: list[tuple[str, str, str]] = [
    # (关键词正则, 建议改写, 类型)
    (r"今日?涨幅大于\d+%",        "",                              "stable_candidate"),
    (r"涨幅大于\d+%",             "今日涨幅大于X%",                "synonym_candidate"),
    (r"涨幅超过\d+%",             "今日涨幅大于X%",                "synonym_candidate"),
    (r"今日?成交额大于[\d.]+亿",   "",                              "stable_candidate"),
    (r"成交额超过[\d.]+亿",        "今日成交额大于X亿",              "synonym_candidate"),
    (r"今日?换手率大于\d+%",       "",                              "stable_candidate"),
    (r"今日?量比大于[\d.]+",       "",                              "stable_candidate"),
    (r"流通市值在[\d.]+亿到[\d.]+亿之间", "",                       "stable_candidate"),
    (r"今日?主力净流入大于[\d.]+[亿万]", "",                        "stable_candidate"),
    (r"今日?主力净流入为正",        "",                              "stable_candidate"),
    (r"近\d+日涨幅大于\d+%",       "",                              "stable_candidate"),
    (r"非ST",                     "",                              "stable_candidate"),
    (r"非停牌",                    "",                              "stable_candidate"),
    (r"上市超过\d+天",             "",                              "stable_candidate"),
    (r"今日?收盘价大于\d+日均线",   "",                              "stable_candidate"),
    # 模糊词 → risky/forbidden
    (r"强势股",                    "今日涨幅大于3%，今日成交额大于3亿", "risky"),
    (r"低位强势",                  "流通市值在30亿到150亿之间，近20日涨幅小于20%，今日涨幅大于3%", "risky"),
    (r"放量上涨",                  "今日涨幅大于3%，今日量比大于1.5，今日成交额大于3亿", "risky"),
    (r"资金关注",                  "今日主力净流入为正，今日成交额大于3亿", "risky"),
    (r"主力关注",                  "今日主力净流入大于1亿",           "risky"),
    (r"龙头",                      "",                              "forbidden"),
    (r"妖股",                      "",                              "forbidden"),
    (r"启动股",                    "",                              "forbidden"),
    (r"热门",                      "",                              "forbidden"),
    (r"明天.{0,5}(上涨|涨停)",     "",                              "forbidden"),
    (r"可能.{0,5}(涨停|上涨)",     "",                              "forbidden"),
    (r"有可能",                    "",                              "forbidden"),
    # 技术指标
    (r"KDJ金叉",                   "今日KDJ金叉",                   "pending"),
    (r"MACD金叉",                  "今日MACD金叉",                  "pending"),
    (r"JMA",                       "",                              "pending_high_risk"),
    (r"BOLL",                      "收盘价突破布林线上轨",            "pending"),
    (r"均线多头",                   "5日均线大于20日均线",             "pending"),
    # 小盘股
    (r"小盘股",                    "流通市值在30亿到150亿之间",        "risky"),
]

_STATUS_ZH = {
    "stable":           "稳定（可直接使用）",
    "stable_candidate": "稳定候选（需查法典确认）",
    "synonym_candidate":"同义写法（建议改写为标准写法）",
    "risky":            "高风险（需改写）",
    "pending":          "待测（问财是否支持未知）",
    "pending_high_risk":"待测-高风险（非标准字段）",
    "forbidden":        "禁止（不得使用）",
}


@dataclass
class DiagnoseSegment:
    original: str
    matched_pattern: str
    segment_type: str    # stable / risky / forbidden / pending / pending_high_risk / synonym_candidate / unknown
    suggested_rewrite: str
    reason_zh: str
    evidence_canon_id: str = ""
    evidence_run_id: str = ""


@dataclass
class DiagnoseResult:
    input_query: str
    skill_type: str
    segments: list[DiagnoseSegment]
    suggested_final_query: str
    summary_zh: str
    can_use_directly: bool
    needs_rewrite: bool
    has_forbidden: bool
    has_pending: bool


class AstockDiagnoser:
    """A股查询诊断器（不请求问财）"""

    def __init__(self, query_lab_dir: Path) -> None:
        self.query_lab_dir = query_lab_dir
        self._stable_texts: set[str] = set()
        self._forbidden_texts: set[str] = set()
        self._load_dictionaries()

    def _load_dictionaries(self) -> None:
        """从法典和历史 analyzed_results 加载已知稳定/禁用集合。"""
        # 从 canon.csv
        canon_csv = self.query_lab_dir / "canon" / "skills" / "astock_问财选A股" / "canon.csv"
        if canon_csv.exists():
            import csv
            with canon_csv.open(encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    if row.get("status") == "stable":
                        self._stable_texts.add(row.get("canonical_query_text", ""))
                    if row.get("status") == "forbidden":
                        self._forbidden_texts.add(row.get("canonical_query_text", ""))

        # 从 analyzed_results
        runs_dir = self.query_lab_dir / "results" / "runs"
        if runs_dir.exists():
            for run_dir in sorted(runs_dir.iterdir()):
                if not self._is_completed_run(run_dir):
                    continue
                ar_file = run_dir / "analyzed_results.jsonl"
                if not ar_file.exists():
                    continue
                with ar_file.open(encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            r = json.loads(line)
                            if r.get("analysis_status") == "stable":
                                self._stable_texts.add(r.get("query_text", ""))
                            elif r.get("analysis_status") in ("forbidden", "invalid_query"):
                                self._forbidden_texts.add(r.get("query_text", ""))
                        except Exception:
                            pass

    def _is_completed_run(self, run_dir: Path) -> bool:
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

    def diagnose(self, query: str) -> DiagnoseResult:
        segments: list[DiagnoseSegment] = []
        unmatched_parts: list[str] = []

        # 逐条尝试匹配模式
        remaining = query
        for pattern_str, suggested, seg_type in _FIELD_PATTERNS:
            pattern = re.compile(pattern_str)
            m = pattern.search(remaining)
            if m:
                matched_text = m.group(0)
                # 查法典确认是否已验证
                actual_type = seg_type
                evidence_run = ""
                evidence_canon = ""

                if matched_text in self._stable_texts:
                    actual_type = "stable"
                elif matched_text in self._forbidden_texts:
                    actual_type = "forbidden"

                # 查候选
                cand_path = self.query_lab_dir / "canon" / "review_queue" / "candidate_changes.jsonl"
                if cand_path.exists():
                    with cand_path.open(encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                c = json.loads(line)
                                qt = c.get("canonical_query_text") or c.get("new_value", "")
                                if qt == matched_text and c.get("success_count", 0) > 0:
                                    actual_type = "stable"
                                    rids = c.get("evidence_run_ids", [])
                                    if isinstance(rids, list) and rids:
                                        evidence_run = rids[-1]
                                    evidence_canon = c.get("change_id", "")
                            except Exception:
                                pass

                reason_zh = _STATUS_ZH.get(actual_type, "未知")
                if actual_type == "forbidden":
                    reason_zh = "模糊/预测词，禁止自动生成"
                elif actual_type == "pending_high_risk":
                    reason_zh = "非问财标准字段，风险高，需实测验证"
                elif actual_type == "risky":
                    reason_zh = "含模糊语义，建议改写为具体条件"
                elif actual_type == "stable":
                    reason_zh = "已实测稳定，可直接使用"

                segments.append(DiagnoseSegment(
                    original=matched_text,
                    matched_pattern=pattern_str,
                    segment_type=actual_type,
                    suggested_rewrite=suggested,
                    reason_zh=reason_zh,
                    evidence_canon_id=evidence_canon,
                    evidence_run_id=evidence_run,
                ))
                remaining = remaining.replace(matched_text, "", 1).strip("，, 、")

        # 剩余未匹配部分
        if remaining.strip():
            for part in re.split(r"[，,、\s]+", remaining.strip()):
                if part:
                    unmatched_parts.append(part)
                    segments.append(DiagnoseSegment(
                        original=part,
                        matched_pattern="",
                        segment_type="unknown",
                        suggested_rewrite="",
                        reason_zh="未知/待测，需手动验证",
                    ))

        # 构建建议最终 Query
        rewrite_parts: list[str] = []
        has_forbidden = False
        has_pending = False
        needs_rewrite = False
        can_use_directly = True

        for seg in segments:
            if seg.segment_type in ("stable", "stable_candidate"):
                rewrite_parts.append(seg.original)
            elif seg.segment_type == "synonym_candidate" and seg.suggested_rewrite:
                rewrite_parts.append(seg.suggested_rewrite)
                needs_rewrite = True
                can_use_directly = False
            elif seg.segment_type == "risky" and seg.suggested_rewrite:
                rewrite_parts.append(seg.suggested_rewrite)
                needs_rewrite = True
                can_use_directly = False
            elif seg.segment_type == "forbidden":
                has_forbidden = True
                can_use_directly = False
            elif seg.segment_type in ("pending", "pending_high_risk", "unknown"):
                has_pending = True
                can_use_directly = False

        # Deduplicate while preserving order
        seen_parts: set[str] = set()
        deduped: list[str] = []
        for p in rewrite_parts:
            if p not in seen_parts:
                seen_parts.add(p)
                deduped.append(p)
        suggested_final = "，".join(deduped) if deduped else ""

        if has_forbidden:
            summary_zh = "包含禁用词，不得直接发送给问财。建议移除禁用片段后使用改写版。"
        elif has_pending:
            summary_zh = "包含待测字段，建议先实测验证后再使用。"
        elif needs_rewrite:
            summary_zh = "包含模糊表达，已建议改写。使用改写版发送给问财。"
        elif can_use_directly:
            summary_zh = "所有片段均稳定，可直接使用。"
        else:
            summary_zh = "部分片段未知，建议手动验证后使用。"

        return DiagnoseResult(
            input_query=query,
            skill_type="astock",
            segments=segments,
            suggested_final_query=suggested_final,
            summary_zh=summary_zh,
            can_use_directly=can_use_directly,
            needs_rewrite=needs_rewrite,
            has_forbidden=has_forbidden,
            has_pending=has_pending,
        )

    def print_result(self, result: DiagnoseResult) -> None:
        print(f"\n{'='*70}")
        print(f"[诊断] 输入 Query: {result.input_query}")
        print(f"[诊断] 技能: {result.skill_type}")
        print(f"{'='*70}\n")

        print("【片段分类】")
        for seg in result.segments:
            status_label = _STATUS_ZH.get(seg.segment_type, seg.segment_type)
            print(f"  片段: {seg.original!r}")
            print(f"    类型: {seg.segment_type}  ({status_label})")
            print(f"    说明: {seg.reason_zh}")
            if seg.suggested_rewrite:
                print(f"    建议改写: {seg.suggested_rewrite!r}")
            if seg.evidence_run_id:
                print(f"    证据 run_id: {seg.evidence_run_id}")
            if seg.evidence_canon_id:
                print(f"    证据 canon_id: {seg.evidence_canon_id}")
            print()

        print("【汇总】")
        print(f"  可直接使用: {'是' if result.can_use_directly else '否'}")
        print(f"  需要改写:   {'是' if result.needs_rewrite else '否'}")
        print(f"  含禁用词:   {'是' if result.has_forbidden else '否'}")
        print(f"  含待测字段: {'是' if result.has_pending else '否'}")
        print(f"  说明: {result.summary_zh}")

        if result.suggested_final_query:
            print(f"\n【建议改写后的中文 Query】")
            print(f"  {result.suggested_final_query!r}")
        print(f"{'='*70}\n")
