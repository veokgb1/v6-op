"""
canon_rollback.py — 法典回滚工具

将 canon.csv 回滚到 versions/ 中的历史版本。
"""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from canon_manager import CanonManager


class CanonRollback:
    def __init__(self, query_lab_dir: Path) -> None:
        self.query_lab_dir = query_lab_dir
        self.manager = CanonManager(query_lab_dir)

    def list_versions(self, skill_key: str) -> list[Path]:
        skill_dir = self.manager._skill_dir(skill_key)
        versions_dir = skill_dir / "versions"
        if not versions_dir.exists():
            return []
        return sorted(versions_dir.glob("canon_*.csv"), reverse=True)

    def rollback(self, skill_key: str, version_ts: str | None = None) -> bool:
        skill_dir = self.manager._skill_dir(skill_key)
        versions = self.list_versions(skill_key)

        if not versions:
            print(f"[CanonRollback] 无历史版本可回滚 (skill_key={skill_key})")
            return False

        if version_ts:
            target = next((v for v in versions if version_ts in v.name), None)
            if not target:
                print(f"[CanonRollback] 未找到版本: {version_ts}")
                return False
        else:
            target = versions[0]  # 最新历史版本

        canon_csv = skill_dir / "canon.csv"

        # 备份当前版本
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        if canon_csv.exists():
            backup = skill_dir / "versions" / f"canon_{ts}_before_rollback.csv"
            shutil.copy2(canon_csv, backup)

        shutil.copy2(target, canon_csv)
        print(f"[CanonRollback] 已回滚到: {target.name}  → {canon_csv}")

        # 写 changelog
        changelog = skill_dir / "changelog.md"
        with changelog.open("a", encoding="utf-8") as f:
            f.write(f"\n## {ts}\n**回滚到**: {target.name}\n\n")

        return True
