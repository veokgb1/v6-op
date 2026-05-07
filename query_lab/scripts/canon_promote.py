"""
canon_promote.py — 法典发布工具

将 candidate_changes.jsonl 中的候选正式发布到 canon.csv。
操作步骤：
1. 备份旧版到 versions/
2. 写入 changelog.md
3. 更新 canon.csv
4. 清空已发布的 candidate

必须提供 --reviewer 和 --reason 才能发布。
"""
from __future__ import annotations

import csv
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from canon_manager import CanonManager, CanonEntry, CANON_FIELDS


class CanonPromote:
    def __init__(self, query_lab_dir: Path) -> None:
        self.query_lab_dir = query_lab_dir
        self.manager = CanonManager(query_lab_dir)

    def promote(
        self,
        skill_key: str,
        reviewer: str,
        reason: str,
        change_ids: list[str] | None = None,
    ) -> int:
        candidates = self.manager.read_candidates()
        skill_cands = [
            c for c in candidates
            if c.get("skill_key") == skill_key
            and c.get("status") == "candidate"
            and (change_ids is None or c.get("change_id") in change_ids)
        ]

        if not skill_cands:
            print(f"[CanonPromote] 无可发布的候选变更 (skill_key={skill_key})")
            return 0

        skill_dir = self.manager._skill_dir(skill_key)
        canon_csv = skill_dir / "canon.csv"
        versions_dir = skill_dir / "versions"
        versions_dir.mkdir(parents=True, exist_ok=True)

        # 1. 备份旧版
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        if canon_csv.exists():
            backup_path = versions_dir / f"canon_{ts}.csv"
            shutil.copy2(canon_csv, backup_path)
            print(f"[CanonPromote] 备份旧版: {backup_path}")

        # 2. 读取现有法典
        existing = self.manager.read_canon(skill_key)
        existing_texts = {e.canonical_query_text: e for e in existing}

        # 3. 应用变更
        promoted_ids: list[str] = []
        for c in skill_cands:
            change_type = c.get("change_type", "add")
            new_text = c.get("canonical_query_text") or c.get("new_value", "")
            meaning = c.get("meaning_zh", "")

            if change_type == "add" and new_text not in existing_texts:
                new_entry = CanonEntry(
                    canon_id=f"C-{uuid.uuid4().hex[:8].upper()}",
                    skill_key=skill_key,
                    skill_name_zh=c.get("skill_name_zh", ""),
                    op_domain="wencai_query",
                    op_topic="",
                    meaning_zh=meaning,
                    canonical_query_text=new_text,
                    reference_mode="weak",
                    evidence_level="auto_test",
                    status="stable",
                    risk_level="low",
                    last_verified_run_id="|".join(c.get("evidence_run_ids", [])),
                    last_verified_at=datetime.now().isoformat(),
                    version=ts,
                    reviewer=reviewer,
                    review_reason=reason,
                )
                existing.append(new_entry)
                existing_texts[new_text] = new_entry
                promoted_ids.append(c.get("change_id", ""))

        # 4. 写入 canon.csv
        with canon_csv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CANON_FIELDS)
            writer.writeheader()
            for e in existing:
                writer.writerow({k: getattr(e, k, "") for k in CANON_FIELDS})

        # 5. 写 changelog
        self._write_changelog(skill_dir, promoted_ids, skill_cands, reviewer, reason, ts)

        # 6. 更新 candidate_changes.jsonl（标记已发布）
        all_candidates = self.manager.read_candidates()
        queue_path = self.query_lab_dir / "canon" / "review_queue" / "candidate_changes.jsonl"
        with queue_path.open("w", encoding="utf-8") as f:
            for c in all_candidates:
                if c.get("change_id") in promoted_ids:
                    c["status"] = "promoted"
                f.write(json.dumps(c, ensure_ascii=False) + "\n")

        print(f"[CanonPromote] 发布完成: {len(promoted_ids)} 条  → {canon_csv}")
        return len(promoted_ids)

    def _write_changelog(
        self,
        skill_dir: Path,
        promoted_ids: list[str],
        cands: list[dict],
        reviewer: str,
        reason: str,
        ts: str,
    ) -> None:
        changelog = skill_dir / "changelog.md"
        entry = [
            f"\n## {ts}",
            f"**发布者**: {reviewer}",
            f"**原因**: {reason}",
            f"**发布条目**: {len(promoted_ids)} 条",
            "",
        ]
        for c in cands:
            if c.get("change_id") in promoted_ids:
                qt = c.get("canonical_query_text") or c.get("new_value", "")
                entry.append(f"- [{c.get('change_id','')}] {c.get('change_type','')} "
                              f"`{qt[:60]}`")
        entry.append("")

        with changelog.open("a", encoding="utf-8") as f:
            f.write("\n".join(entry))
