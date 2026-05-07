"""
quote_adapter.py — 行情快照适配器（占位）

当前 status=pending，尚未接入。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


class QuoteAdapter:
    """行情快照适配器（pending 占位）"""

    def __init__(self, project_root: Path, dry_run: bool = False) -> None:
        self.project_root = project_root
        self.dry_run = dry_run

    def query(self, symbol: str, **kwargs: Any) -> dict[str, Any]:
        return {
            "status": "pending",
            "result_count": 0,
            "data": {},
            "raw_error": "quote_adapter 尚未实现（status=pending）",
            "skill_type": "quote",
        }
