"""Pytest configuration for V6OP tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure scripts directory is on the path for all tests
_PROJECT_ROOT = Path(__file__).parent.parent.resolve()
_SCRIPTS_DIR = _PROJECT_ROOT / "scripts"

for path_str in [str(_SCRIPTS_DIR), str(_SCRIPTS_DIR / "producers"),
                 str(_SCRIPTS_DIR / "sources")]:
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


@pytest.fixture(autouse=True)
def _isolate_execution_engine_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """把 execution_engine 写输出根目录重定向到 tmp_path。

    防止任何测试（无论是真实 execute() 还是 mock execute()）
    覆盖 output/current/run_report.md 和 output/runs/<run_id>/ 等真实运行产物。
    同时隔离 mask_cache 目录，防止 mock 结果写入真实缓存后在下次测试中产生假命中。
    测试结束后 monkeypatch 自动恢复，不影响下一个测试或真实运行。
    """
    import execution_engine
    monkeypatch.setattr(execution_engine, "_OUTPUT_ROOT", tmp_path)
    monkeypatch.setattr(execution_engine, "_MASK_CACHE_DIR", tmp_path / "mask_cache")
