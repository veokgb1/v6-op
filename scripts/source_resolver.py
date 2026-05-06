#!/usr/bin/env python3
"""
source_resolver.py — V6OP 股票来源统一解析器

三种来源类型：
  all_a    -> 读取 data/ashare_codes.txt
  manual   -> 接收用户代码列表
  wencai   -> 调用 WencaiSource，失败时 blocked/error，不伪造

输出统一字段：
  scope_id, source_type, scope_codes, scope_count,
  status, error, generated_at
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable

_SCRIPTS_DIR = Path(__file__).parent.resolve()
_PROJECT_ROOT = _SCRIPTS_DIR.parent

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from time_utils import iso_cst

_CODE_PATTERN = re.compile(r"\b\d{6}\.(?:SZ|SH|BJ)\b", re.IGNORECASE)


def _read_ashare_codes(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8-sig")
    seen: set[str] = set()
    codes: list[str] = []
    for c in _CODE_PATTERN.findall(text):
        k = c.strip().upper()
        if k not in seen:
            seen.add(k)
            codes.append(k)
    return codes


def _make_scope_id(source_type: str, codes: list[str]) -> str:
    key = source_type + "|" + ",".join(sorted(codes[:30]))
    return hashlib.sha1(key.encode()).hexdigest()[:16]


def resolve(
    source_type: str,
    *,
    manual_codes: list[str] | None = None,
    wencai_query: str | None = None,
    wencai_limit: int = 300,
    ashare_path: Path | None = None,
    ashare_limit: int = 0,
    log_sink: Callable[[str, str], None] | None = None,
) -> dict:
    """
    统一解析股票来源，返回 scope dict。

    source_type:
      "all_a"    -> 读取 data/ashare_codes.txt
      "manual"   -> 使用 manual_codes 列表
      "wencai"   -> 调用 WencaiSource（失败时安全降级，不伪造）

    不论哪种 source_type，不得在 wencai 失败时伪造 scope。
    """
    ts = iso_cst()
    error = None
    codes: list[str] = []
    status = "ok"

    if source_type == "manual":
        if not manual_codes:
            return {
                "scope_id": _make_scope_id("manual", []),
                "source_type": "manual",
                "scope_codes": [],
                "scope_count": 0,
                "status": "error",
                "error": "manual 来源未提供代码列表",
                "generated_at": ts,
            }
        seen: set[str] = set()
        deduped: list[str] = []
        for c in manual_codes:
            k = c.strip().upper()
            if k and k not in seen:
                seen.add(k)
                deduped.append(k)
        codes = deduped

    elif source_type == "all_a":
        if ashare_path is None:
            ashare_path = _PROJECT_ROOT / "data" / "ashare_codes.txt"
        if not ashare_path.exists():
            return {
                "scope_id": _make_scope_id("all_a", []),
                "source_type": "all_a",
                "scope_codes": [],
                "scope_count": 0,
                "status": "error",
                "error": f"ashare_codes.txt 未找到: {ashare_path}",
                "generated_at": ts,
            }
        codes = _read_ashare_codes(ashare_path)
        if ashare_limit > 0:
            codes = codes[:ashare_limit]

    elif source_type == "wencai":
        try:
            if str(_SCRIPTS_DIR / "sources") not in sys.path:
                sys.path.insert(0, str(_SCRIPTS_DIR / "sources"))
            import wencai_source as _wencai_source  # type: ignore

            old_sink = getattr(_wencai_source, "_log_sink", None)
            if log_sink is not None:
                _wencai_source._log_sink = (
                    lambda level, msg: log_sink(level, f"  问财接口: {msg}")
                )
            try:
                result = _wencai_source.run(
                    query=wencai_query or "",
                    limit=wencai_limit,
                    out=None,
                )
            finally:
                _wencai_source._log_sink = old_sink
            codes = result.get("scope_codes", [])
            status = result.get("status", "error")
            if status not in ("ok",):
                error = result.get("note") or result.get("error") or f"wencai 返回 status={status}"
                # 保留所有已知具体失败状态，未知状态归为 error
                _known_fail = {"blocked", "key_missing", "auth_failed",
                               "empty_result", "network_error", "api_error", "error"}
                if status not in _known_fail:
                    status = "error"
                codes = []
        except Exception as exc:
            status = "error"
            error = str(exc)
            codes = []

    else:
        return {
            "scope_id": _make_scope_id("unknown", []),
            "source_type": source_type,
            "scope_codes": [],
            "scope_count": 0,
            "status": "error",
            "error": (
                f"不支持的 source_type: {source_type!r}，"
                "支持: all_a / manual / wencai"
            ),
            "generated_at": ts,
        }

    scope_id = _make_scope_id(source_type, codes)
    return {
        "scope_id": scope_id,
        "source_type": source_type,
        "scope_codes": codes,
        "scope_count": len(codes),
        "status": status,
        "error": error,
        "generated_at": ts,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="V6OP 来源解析器")
    parser.add_argument("--type", default="manual", choices=["all_a", "manual", "wencai"])
    parser.add_argument("--codes", nargs="*", default=[])
    parser.add_argument("--query", default="")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    result = resolve(
        args.type,
        manual_codes=args.codes,
        wencai_query=args.query,
        ashare_limit=args.limit,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
