"""
canon_linter.py — V2 法典 Linter（增强版）

新增检测：
1. 候选重复 query（同 skill_key + canonical_query_text）
2. 同一 query 多个 meaning
3. 同一 meaning 多个 strong 候选
4. stable 与 forbidden 冲突
5. candidate 缺证据（无 evidence_run_ids）
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from canon_manager import CanonManager


@dataclass
class LintIssue:
    severity: str   # error | warning
    canon_id: str
    issue_type: str
    description: str


class CanonLinter:
    def __init__(self, query_lab_dir: Path) -> None:
        self.query_lab_dir = query_lab_dir
        self.manager = CanonManager(query_lab_dir)

    def lint(self) -> list[LintIssue]:
        issues: list[LintIssue] = []
        for skill_key in ("astock", "sector"):
            entries = self.manager.read_canon(skill_key)
            issues.extend(self._lint_entries(skill_key, entries))

        issues.extend(self._lint_candidates())
        self._write_conflict_report(issues)
        return issues

    def _lint_entries(self, skill_key: str, entries: list) -> list[LintIssue]:
        issues: list[LintIssue] = []
        required_fields = ["canon_id", "meaning_zh", "canonical_query_text", "status"]

        meaning_strong: dict[str, list] = {}
        text_meanings: dict[str, list] = {}

        for e in entries:
            # 必须字段
            for f in required_fields:
                if not getattr(e, f, ""):
                    issues.append(LintIssue("error", e.canon_id or "?",
                                            "missing_required_field", f"缺少必须字段: {f}"))

            # 路由检查
            if skill_key == "astock" and "板块" in (e.canonical_query_text or ""):
                issues.append(LintIssue("warning", e.canon_id,
                                        "route_mismatch",
                                        f"astock 法典中含板块表达: {e.canonical_query_text[:50]}"))

            # strong 唯一性
            if getattr(e, "reference_mode", "") == "strong":
                meaning_strong.setdefault(e.meaning_zh, []).append(e.canon_id)

            text_meanings.setdefault(e.canonical_query_text, []).append(e.meaning_zh)

            # strong 与 forbidden 冲突
            if getattr(e, "reference_mode", "") == "strong" and getattr(e, "status", "") == "forbidden":
                issues.append(LintIssue("error", e.canon_id,
                                        "strong_forbidden_conflict",
                                        "reference_mode=strong 但 status=forbidden"))

            # stable 与 forbidden 冲突
            if getattr(e, "status", "") == "stable" and getattr(e, "deprecated", "") == "true":
                issues.append(LintIssue("warning", e.canon_id,
                                        "stable_deprecated_conflict",
                                        "status=stable 但 deprecated=true"))

        for meaning, ids in meaning_strong.items():
            if len(ids) > 1:
                issues.append(LintIssue("warning", "|".join(ids),
                                        "multiple_strong_for_meaning",
                                        f"同一语义 '{meaning[:30]}' 有 {len(ids)} 个 strong: {ids}"))

        for text, meanings in text_meanings.items():
            if len(set(meanings)) > 1:
                issues.append(LintIssue("warning", "?",
                                        "ambiguous_query_text",
                                        f"同一 query '{text[:40]}' 对应多个语义: {meanings}"))

        return issues

    def _lint_candidates(self) -> list[LintIssue]:
        issues: list[LintIssue] = []
        candidates = self.manager.read_candidates()

        # 重复候选检测（同 skill_key + canonical_query_text）
        seen_key: dict[str, list] = {}
        for c in candidates:
            qt = c.get("canonical_query_text") or c.get("new_value", "")
            key = f"{c.get('skill_key','')}|{qt}"
            seen_key.setdefault(key, []).append(c.get("change_id", "?"))

        for key, ids in seen_key.items():
            if len(ids) > 1:
                issues.append(LintIssue("error", "|".join(ids),
                                        "duplicate_candidate",
                                        f"候选重复 query: {key.split('|',1)[-1][:60]}  ids={ids}"))

        # 同 query 多个 meaning
        qt_meanings: dict[str, set] = {}
        for c in candidates:
            qt = c.get("canonical_query_text") or c.get("new_value", "")
            meaning = c.get("meaning_zh", "")
            qt_meanings.setdefault(qt, set()).add(meaning)
        for qt, meanings in qt_meanings.items():
            if len(meanings) > 1:
                issues.append(LintIssue("warning", "?",
                                        "candidate_multiple_meanings",
                                        f"候选 query '{qt[:50]}' 对应多个语义: {list(meanings)}"))

        # 缺少证据
        for c in candidates:
            run_ids = c.get("evidence_run_ids", [])
            if isinstance(run_ids, str):
                run_ids = [x for x in run_ids.split("|") if x]
            if not run_ids:
                issues.append(LintIssue("warning", c.get("change_id", "?"),
                                        "candidate_missing_evidence",
                                        f"候选变更缺少 evidence_run_ids: {c.get('canonical_query_text','')[:50]}"))

        # 缺少 skill_key
        for c in candidates:
            if not c.get("skill_key"):
                issues.append(LintIssue("error", c.get("change_id", "?"),
                                        "candidate_missing_skill_key",
                                        "候选变更缺少 skill_key"))

        # stable 候选与 forbidden 冲突（检查是否同一 query 在 forbidden 中）
        canon_astock = self.manager.read_canon("astock")
        forbidden_texts = {e.canonical_query_text for e in canon_astock
                          if getattr(e, "status", "") == "forbidden"}
        for c in candidates:
            qt = c.get("canonical_query_text") or c.get("new_value", "")
            if qt in forbidden_texts and c.get("change_type") == "add":
                issues.append(LintIssue("error", c.get("change_id", "?"),
                                        "candidate_conflicts_with_forbidden",
                                        f"候选新增 '{qt[:50]}' 但该 query 在法典中已标记 forbidden"))

        return issues

    def _write_conflict_report(self, issues: list[LintIssue]) -> None:
        conflicts_dir = self.query_lab_dir / "canon" / "conflicts"
        conflicts_dir.mkdir(parents=True, exist_ok=True)

        items_path = conflicts_dir / "conflict_items.jsonl"
        with items_path.open("w", encoding="utf-8") as f:
            for i in issues:
                f.write(json.dumps({
                    "severity": i.severity, "canon_id": i.canon_id,
                    "issue_type": i.issue_type, "description": i.description,
                    "detected_at": datetime.now().isoformat(),
                }, ensure_ascii=False) + "\n")

        report_path = conflicts_dir / "conflict_report.md"
        errors = [i for i in issues if i.severity == "error"]
        warnings = [i for i in issues if i.severity == "warning"]
        lines = [
            "# 法典冲突报告",
            "",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"共发现 {len(issues)} 个问题（error={len(errors)}, warning={len(warnings)}）",
            "",
        ]
        if errors:
            lines += ["## Errors（必须修复）", ""]
            for i in errors:
                lines.append(f"- [{i.issue_type}] canon_id={i.canon_id}: {i.description}")
            lines.append("")
        if warnings:
            lines += ["## Warnings（建议检查）", ""]
            for i in warnings:
                lines.append(f"- [{i.issue_type}] canon_id={i.canon_id}: {i.description}")
            lines.append("")
        if not issues:
            lines.append("✓ 未发现问题")
        report_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"[CanonLinter] 冲突报告: {report_path}  (errors={len(errors)}, warnings={len(warnings)})")
