"""
canon_manager.py — 法典管理器

负责法典的读取、候选提议、状态查询。
不直接修改 canon.csv，只能通过 canon_promote 发布。
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


CANON_FIELDS = [
    "canon_id", "skill_key", "skill_name_zh", "op_domain", "op_topic",
    "meaning_zh", "canonical_query_text", "allowed_variants", "risky_variants",
    "forbidden_variants", "reference_mode", "evidence_level", "status",
    "risk_level", "last_verified_run_id", "last_verified_at", "version",
    "supersedes", "deprecated", "reviewer", "review_reason", "notes",
]


@dataclass
class CanonEntry:
    canon_id: str
    skill_key: str
    skill_name_zh: str
    op_domain: str
    op_topic: str
    meaning_zh: str
    canonical_query_text: str
    allowed_variants: str = ""
    risky_variants: str = ""
    forbidden_variants: str = ""
    reference_mode: str = "pending"
    evidence_level: str = "none"
    status: str = "pending"
    risk_level: str = "low"
    last_verified_run_id: str = ""
    last_verified_at: str = ""
    version: str = "v1"
    supersedes: str = ""
    deprecated: str = "false"
    reviewer: str = ""
    review_reason: str = ""
    notes: str = ""


class CanonManager:
    def __init__(self, query_lab_dir: Path) -> None:
        self.query_lab_dir = query_lab_dir
        self.canon_dir = query_lab_dir / "canon"
        self.skills_dir = self.canon_dir / "skills"

    def read_canon(self, skill_key: str) -> list[CanonEntry]:
        skill_dir = self._skill_dir(skill_key)
        canon_csv = skill_dir / "canon.csv"
        if not canon_csv.exists():
            return []
        entries: list[CanonEntry] = []
        with canon_csv.open(encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                entries.append(CanonEntry(**{
                    k: row.get(k, "") for k in CANON_FIELDS
                    if k in CanonEntry.__dataclass_fields__
                }))
        return entries

    def read_candidates(self) -> list[dict]:
        path = self.canon_dir / "review_queue" / "candidate_changes.jsonl"
        if not path.exists():
            return []
        candidates: list[dict] = []
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    candidates.append(json.loads(line))
        return candidates

    def read_manual_overrides(self) -> list[dict]:
        path = self.canon_dir / "manual_overrides" / "manual_overrides.csv"
        if not path.exists():
            return []
        rows: list[dict] = []
        with path.open(encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(dict(row))
        return rows

    def propose_from_candidates(self) -> int:
        """将 candidate_changes.jsonl 中的条目整理为候选提议报告（不修改 canon.csv）"""
        candidates = self.read_candidates()
        if not candidates:
            print("[CanonManager] 当前无候选变更")
            return 0

        print(f"[CanonManager] 共 {len(candidates)} 条候选变更：")
        for c in candidates:
            qt = c.get("canonical_query_text") or c.get("new_value", "")
            print(f"  [{c.get('change_id','?')}] {c.get('change_type','')} "
                  f"skill={c.get('skill_key','')} "
                  f"query={qt[:60]!r} "
                  f"status={c.get('status','')}")
        return len(candidates)

    def _skill_dir(self, skill_key: str) -> Path:
        name_map = {
            "astock": "astock_问财选A股",
            "sector": "sector_问财选板块",
        }
        dir_name = name_map.get(skill_key, skill_key)
        return self.skills_dir / dir_name
