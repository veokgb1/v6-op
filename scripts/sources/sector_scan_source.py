#!/usr/bin/env python3
"""
sector_scan_source.py — V6OP Phase A 板块扫描

只做查询，不启动管道，不写 output，不改 _run_state，
不调用 execution_engine.execute()，不改 source_resolver。

IWENCAI_API_KEY 缺失或 pywencai 未安装时返回清晰中文错误，
不伪造板块列表。
"""
from __future__ import annotations

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

_SOURCES_DIR = Path(__file__).parent.resolve()
_SCRIPTS_DIR = _SOURCES_DIR.parent
_PROJECT_ROOT = _SCRIPTS_DIR.parent

DEFAULT_SECTOR_QUERY = (
    "今日主力资金净流入排名前十的行业板块，按净流入金额降序排列"
)


def _load_env() -> dict[str, str]:
    env_path = _PROJECT_ROOT / ".env"
    if not env_path.exists():
        return {}
    result: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        result[key.strip()] = val.strip().strip('"').strip("'")
    return result


def _extract_sector_names(rows: list[dict], top_n: int) -> list[str]:
    """从 pywencai 返回行中提取板块名称字符串。"""
    names: list[str] = []
    seen: set[str] = set()
    name_fields = [
        "板块名称", "行业板块", "板块", "概念板块", "行业名称",
        "概念名称", "sector_name", "sector", "name", "名称",
    ]
    for row in rows:
        name: str | None = None
        for field in name_fields:
            if field in row:
                candidate = str(row[field]).strip()
                if candidate and len(candidate) >= 2 and not candidate.replace(".", "").isdigit():
                    name = candidate
                    break
        if name is None:
            # 启发式：找最短的中文字符串字段
            for v in row.values():
                sv = str(v).strip()
                if len(sv) >= 2 and len(sv) <= 15 and not sv.replace(".", "").isdigit():
                    import re
                    if re.search(r"[一-鿿]", sv):
                        name = sv
                        break
        if name and name not in seen:
            seen.add(name)
            names.append(name)
        if len(names) >= top_n:
            break
    return names


def scan(sector_query: str = "", top_n: int = 10) -> dict[str, Any]:
    """
    Phase A 板块扫描。

    返回：
      {
        "sectors":   ["银行", "半导体", ...],   # 可能为空
        "count":     N,
        "query":     sector_query,
        "error":     None | "错误描述",
        "elapsed_s": float,
      }
    """
    t0 = time.time()
    sector_query = sector_query.strip() or DEFAULT_SECTOR_QUERY

    # ── 依赖检查：pywencai ────────────────────────────────────────────
    try:
        import pywencai  # noqa: F401
    except ImportError:
        return {
            "sectors": [],
            "count": 0,
            "query": sector_query,
            "error": "板块扫描依赖未安装（pywencai 未安装），请执行: pip install pywencai",
            "elapsed_s": round(time.time() - t0, 2),
        }

    # ── API Key 检查 ──────────────────────────────────────────────────
    env = _load_env()
    api_key = env.get("IWENCAI_API_KEY") or os.environ.get("IWENCAI_API_KEY", "")
    if not api_key:
        return {
            "sectors": [],
            "count": 0,
            "query": sector_query,
            "error": "IWENCAI_API_KEY 未配置，请检查 .env 文件",
            "elapsed_s": round(time.time() - t0, 2),
        }

    # ── 调用问财板块查询 ──────────────────────────────────────────────
    try:
        import pywencai
        result = pywencai.get(
            query=sector_query,
            query_type="sector",
            perpage=min(top_n * 3, 100),
            page=1,
        )

        if result is None:
            return {
                "sectors": [],
                "count": 0,
                "query": sector_query,
                "error": "板块扫描返回空结果，请调整查询语句",
                "elapsed_s": round(time.time() - t0, 2),
            }

        rows: list[dict] = []
        if isinstance(result, list):
            rows = result
        elif hasattr(result, "to_dict"):
            rows = result.to_dict(orient="records")
        elif isinstance(result, dict):
            for v in result.values():
                if isinstance(v, list) and v:
                    rows = v
                    break

        sectors = _extract_sector_names(rows, top_n)
        elapsed = round(time.time() - t0, 2)

        if not sectors:
            return {
                "sectors": [],
                "count": 0,
                "query": sector_query,
                "error": (
                    "板块扫描返回数据但无法提取板块名称，"
                    "请确认问财板块 API 可用，或尝试调整查询语句"
                ),
                "elapsed_s": elapsed,
            }

        return {
            "sectors": sectors,
            "count": len(sectors),
            "query": sector_query,
            "error": None,
            "elapsed_s": elapsed,
        }

    except Exception as exc:
        err_str = str(exc)
        if "401" in err_str or "Unauthorized" in err_str or "auth" in err_str.lower():
            msg = "问财 API 认证失败（401），请检查 IWENCAI_API_KEY 是否有效"
        else:
            msg = f"板块扫描失败：{err_str[:200]}"
        return {
            "sectors": [],
            "count": 0,
            "query": sector_query,
            "error": msg,
            "elapsed_s": round(time.time() - t0, 2),
        }
