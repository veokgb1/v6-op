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
import re
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
        "概念名称", "指数简称", "指数名称", "指数代码名称",
        "sector_name", "sector", "name", "名称",
    ]

    def is_name_candidate(value: object) -> bool:
        sv = str(value).strip()
        if not sv or len(sv) < 2 or len(sv) > 20:
            return False
        if not re.search(r"[\u4e00-\u9fff]", sv):
            return False
        if any(token in sv for token in ("同花顺财经", "数据中心", "资金流向排行", "看主力资金")):
            return False
        if sv.replace(".", "").replace("-", "").isdigit():
            return False
        if re.match(r"^\d{6}(?:\.[A-Z]{2})?$", sv, flags=re.I):
            return False
        if sv.startswith(("http://", "https://")):
            return False
        return True

    for row in rows:
        name: str | None = None
        for field in name_fields:
            if field in row:
                candidate = str(row[field]).strip()
                if is_name_candidate(candidate):
                    name = candidate
                    break
        if name is None:
            # 启发式：只在像“名称/简称/板块/行业/概念/指数”的字段里找，
            # 避免把网页搜索结果的 title/summary 当成板块名。
            for key, v in row.items():
                key_s = str(key)
                if any(token in key_s.lower() for token in ("url", "content", "summary", "source", "uid", "jump")):
                    continue
                if not re.search(r"(名称|简称|板块|行业|概念|指数)", key_s):
                    continue
                if is_name_candidate(v):
                    name = str(v).strip()
                    break
        if name and name not in seen:
            seen.add(name)
            names.append(name)
        if len(names) >= top_n:
            break
    return names


def _rows_from_pywencai_result(result: Any) -> list[dict]:
    """把 pywencai 的多种返回形态统一成行 dict 列表。"""
    if result is None:
        return []
    if isinstance(result, list):
        return [row for row in result if isinstance(row, dict)]
    if hasattr(result, "to_dict"):
        return result.to_dict(orient="records")
    if isinstance(result, dict):
        rows: list[dict] = []
        for value in result.values():
            if isinstance(value, list):
                rows.extend(row for row in value if isinstance(row, dict))
            elif hasattr(value, "to_dict"):
                rows.extend(value.to_dict(orient="records"))
            elif isinstance(value, dict):
                for nested in value.values():
                    if isinstance(nested, list):
                        rows.extend(row for row in nested if isinstance(row, dict))
                    elif hasattr(nested, "to_dict"):
                        rows.extend(nested.to_dict(orient="records"))
        return rows
    return []


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
        # pywencai 的 sector 返回在部分环境中是包装对象，字段不稳定；
        # zhishu 对行业/概念板块查询通常直接返回含“指数简称”的 DataFrame。
        # 先按语义最直接的 sector 试一次，提取不到名称再用 zhishu 兜底。
        result = None
        rows: list[dict] = []
        query_types_tried: list[str] = []
        for query_type in ("sector", "zhishu"):
            query_types_tried.append(query_type)
            result = pywencai.get(
                query=sector_query,
                query_type=query_type,
                perpage=min(top_n * 3, 100),
                page=1,
            )
            rows = _rows_from_pywencai_result(result)
            if _extract_sector_names(rows, top_n):
                break

        if result is None:
            return {
                "sectors": [],
                "count": 0,
                "query": sector_query,
                "error": "板块扫描返回空结果，请调整查询语句",
                "elapsed_s": round(time.time() - t0, 2),
            }

        sectors = _extract_sector_names(rows, top_n)
        elapsed = round(time.time() - t0, 2)

        if not sectors:
            return {
                "sectors": [],
                "count": 0,
                "query": sector_query,
                "query_types_tried": query_types_tried,
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
            "query_types_tried": query_types_tried,
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
