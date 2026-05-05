"""
v6_compat.py — V6OP → V6 合约引用层

V6OP 通过这个兼容层引用 V6 的稳定合约（contracts.py 等），
不复制 V6 文件，不修改 V6 文件。

V6 后台能力库路径: F:/v.6/v6/scripts
V6OP 项目路径:    F:/v.6/v6-op

如果 V6 路径不可用，提供 ImportError 并给出诊断信息。
"""
from __future__ import annotations

import sys
from pathlib import Path

# V6 scripts 路径 (相对于 V6OP 项目根的兄弟目录)
_V6OP_ROOT = Path(__file__).parent.parent.resolve()
_V6_SCRIPTS = _V6OP_ROOT.parent / "v6" / "scripts"

_V6_AVAILABLE = False
_V6_IMPORT_ERROR: str | None = None

if _V6_SCRIPTS.exists():
    if str(_V6_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_V6_SCRIPTS))
    try:
        from v6.contracts import (  # type: ignore[import]
            Mask,
            MaskExpression,
            ScopeRef,
            Universe,
            ExpressionOp,
            normalize_codes,
            fingerprint_codes,
            combine_code_sets,
        )
        _V6_AVAILABLE = True
    except ImportError as e:
        _V6_IMPORT_ERROR = str(e)
else:
    _V6_IMPORT_ERROR = f"V6 scripts 目录不存在: {_V6_SCRIPTS}"


def check_v6_available() -> None:
    """如果 V6 合约不可用，抛出带诊断信息的 ImportError。"""
    if not _V6_AVAILABLE:
        raise ImportError(
            f"V6 contracts 不可用: {_V6_IMPORT_ERROR}\n"
            f"预期路径: {_V6_SCRIPTS}\n"
            f"请确认 V6 项目在 {_V6OP_ROOT.parent / 'v6'}"
        )


def v6_available() -> bool:
    return _V6_AVAILABLE


def v6_scripts_path() -> Path:
    return _V6_SCRIPTS
