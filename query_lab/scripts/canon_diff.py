"""
canon_diff.py — 法典 Diff 工具

对比 candidate_changes.jsonl 和当前 canon.csv，
生成变更差异报告。
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from canon_manager import CanonManager


class CanonDiff:
    def __init__(self, query_lab_dir: Path) -> None:
        self.query_lab_dir = query_lab_dir
        self.manager = CanonManager(query_lab_dir)

    def diff(self) -> None:
        candidates = self.manager.read_candidates()
        print(f"\n[CanonDiff] 候选变更 vs 当前法典\n{'='*60}")

        if not candidates:
            print("  (当前无候选变更)")
            return

        for skill_key in ("astock", "sector"):
            canon_entries = self.manager.read_canon(skill_key)
            canon_texts = {e.canonical_query_text for e in canon_entries}

            skill_cands = [c for c in candidates if c.get("skill_key") == skill_key]
            if not skill_cands:
                continue

            print(f"\n[{skill_key}] 候选变更 {len(skill_cands)} 条：")
            for c in skill_cands:
                qt = c.get("canonical_query_text") or c.get("new_value", "")
                change_type = c.get("change_type", "")
                sr = c.get("success_rate", 0)
                sc = c.get("success_count", 0)
                if qt in canon_texts:
                    symbol = "~"
                    desc = "已存在于法典"
                else:
                    symbol = "+"
                    desc = f"新增  success={sc}  rate={sr:.0%}"
                print(f"  {symbol} [{c.get('change_id','')}][{change_type}] {qt[:60]!r}  → {desc}")

        print(f"\n{'='*60}")
