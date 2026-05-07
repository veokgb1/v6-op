"""
wencai_sector_adapter.py — 问财选板块适配器

封装 pywencai sector/zhishu 查询，返回统一结果格式。
注意：部分板块查询可能需要 zhishu fallback，实际 backend 会记录在结果中。
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any


def _load_env(project_root: Path) -> dict[str, str]:
    env_path = project_root / ".env"
    if not env_path.exists():
        return {}
    result: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        result[k.strip()] = v.strip().strip('"').strip("'")
    return result


_NAME_FIELDS = [
    "板块名称", "行业板块", "板块", "概念板块", "行业名称",
    "概念名称", "指数简称", "指数名称", "指数代码名称",
    "sector_name", "sector", "name", "名称",
]

_CHINESE_RE = re.compile(r"[一-鿿]")


def _extract_sector_names(rows: list[dict]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for f in _NAME_FIELDS:
            if f in row:
                val = str(row[f]).strip()
                if (len(val) >= 2 and _CHINESE_RE.search(val)
                        and val not in seen
                        and not any(t in val for t in ("同花顺", "数据中心", "资金流向"))):
                    seen.add(val)
                    names.append(val)
                    break
    return names


class WencaiSectorAdapter:
    """
    问财选板块适配器。
    先尝试 sector 类型，失败时 fallback 到 zhishu。
    """

    def __init__(self, project_root: Path, dry_run: bool = False) -> None:
        self.project_root = project_root
        self.dry_run = dry_run
        env = _load_env(project_root)
        self.api_key = env.get("IWENCAI_API_KEY") or os.environ.get("IWENCAI_API_KEY", "")

    def query(self, query_text: str, limit: int = 20) -> dict[str, Any]:
        if self.dry_run:
            return {
                "status": "dry_run",
                "result_count": 0,
                "names": [],
                "elapsed_ms": 0.0,
                "raw_error": "",
                "query_text": query_text,
                "skill_type": "sector",
                "actual_query_backend": "sector(dry_run)",
            }

        if not self.api_key:
            return {
                "status": "key_missing",
                "result_count": 0,
                "names": [],
                "elapsed_ms": 0.0,
                "raw_error": "IWENCAI_API_KEY 未配置",
                "query_text": query_text,
                "skill_type": "sector",
                "actual_query_backend": "none",
            }

        t0 = time.time()
        for query_type in ("sector", "zhishu"):
            result = self._try_query(query_text, query_type, limit)
            if result["status"] == "ok":
                result["elapsed_ms"] = round((time.time() - t0) * 1000, 1)
                return result

        elapsed_ms = round((time.time() - t0) * 1000, 1)
        return {
            "status": "empty_result",
            "result_count": 0,
            "names": [],
            "elapsed_ms": elapsed_ms,
            "raw_error": "sector 和 zhishu 均无结果",
            "query_text": query_text,
            "skill_type": "sector",
            "actual_query_backend": "sector+zhishu_fallback",
        }

    def _try_query(self, query_text: str, query_type: str, limit: int) -> dict[str, Any]:
        try:
            import pywencai
            result = pywencai.get(
                query=query_text,
                query_type=query_type,
                perpage=min(max(limit, 1), 100),
                page=1,
            )
            if result is None:
                return {"status": "api_error", "names": [], "actual_query_backend": query_type}

            rows: list[dict] = []
            if isinstance(result, list):
                rows = result
            elif hasattr(result, "to_dict"):
                rows = result.to_dict(orient="records")
            elif isinstance(result, dict):
                for v in result.values():
                    if isinstance(v, list):
                        rows = v
                        break

            names = _extract_sector_names(rows)
            if limit > 0:
                names = names[:limit]

            if not names:
                return {"status": "empty_result", "names": [], "actual_query_backend": query_type}

            return {
                "status": "ok",
                "result_count": len(names),
                "names": names,
                "raw_error": "",
                "query_text": query_text,
                "skill_type": "sector",
                "actual_query_backend": query_type,
            }

        except ImportError:
            return {"status": "blocked", "names": [], "actual_query_backend": query_type}
        except Exception as exc:
            return {"status": "api_error", "names": [], "actual_query_backend": query_type,
                    "raw_error": str(exc)[:200]}
