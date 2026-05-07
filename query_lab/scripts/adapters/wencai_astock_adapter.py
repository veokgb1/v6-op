"""
wencai_astock_adapter.py — 问财选A股适配器

封装 pywencai stock 查询，返回统一结果格式供 query_runner 使用。
不写 output/current，不影响主策略台。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

# 允许从 query_lab/scripts 调用
_SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


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


class WencaiAstockAdapter:
    """
    问财选A股适配器。
    dry_run=True 时不实际调用问财，返回模拟结构。
    """

    def __init__(self, project_root: Path, dry_run: bool = False) -> None:
        self.project_root = project_root
        self.dry_run = dry_run
        env = _load_env(project_root)
        import os
        self.api_key = env.get("IWENCAI_API_KEY") or os.environ.get("IWENCAI_API_KEY", "")

    def query(self, query_text: str, limit: int = 0) -> dict[str, Any]:
        """
        发送问财查询（选A股）。

        返回字典包含：
          status: ok | empty_result | api_error | key_missing | blocked | dry_run
          result_count: int
          codes: list[str]
          elapsed_ms: float
          raw_error: str
        """
        if self.dry_run:
            return {
                "status": "dry_run",
                "result_count": 0,
                "codes": [],
                "elapsed_ms": 0.0,
                "raw_error": "",
                "query_text": query_text,
                "skill_type": "astock",
                "actual_query_backend": "stock",
            }

        if not self.api_key:
            return {
                "status": "key_missing",
                "result_count": 0,
                "codes": [],
                "elapsed_ms": 0.0,
                "raw_error": "IWENCAI_API_KEY 未配置",
                "query_text": query_text,
                "skill_type": "astock",
                "actual_query_backend": "stock",
            }

        t0 = time.time()
        try:
            import pywencai
            perpage = 100 if limit <= 0 else min(max(limit, 1), 100)
            max_pages = 100 if limit <= 0 else max(1, (limit + perpage - 1) // perpage)

            codes: list[str] = []
            seen: set[str] = set()

            for page in range(1, max_pages + 1):
                result = pywencai.get(
                    query=query_text,
                    query_type="stock",
                    perpage=perpage,
                    page=page,
                )
                if result is None:
                    break

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

                if not rows:
                    break

                for row in rows:
                    code = self._extract_code(row)
                    if code and code not in seen:
                        seen.add(code)
                        codes.append(code)
                        if limit > 0 and len(codes) >= limit:
                            break

                if limit > 0 and len(codes) >= limit:
                    break

            if limit > 0:
                codes = codes[:limit]

            elapsed_ms = (time.time() - t0) * 1000
            if not codes:
                return {
                    "status": "empty_result",
                    "result_count": 0,
                    "codes": [],
                    "elapsed_ms": round(elapsed_ms, 1),
                    "raw_error": "",
                    "query_text": query_text,
                    "skill_type": "astock",
                    "actual_query_backend": "stock",
                }
            return {
                "status": "ok",
                "result_count": len(codes),
                "codes": codes,
                "elapsed_ms": round(elapsed_ms, 1),
                "raw_error": "",
                "query_text": query_text,
                "skill_type": "astock",
                "actual_query_backend": "stock",
            }

        except ImportError:
            elapsed_ms = (time.time() - t0) * 1000
            return {
                "status": "blocked",
                "result_count": 0,
                "codes": [],
                "elapsed_ms": round(elapsed_ms, 1),
                "raw_error": "pywencai 未安装",
                "query_text": query_text,
                "skill_type": "astock",
                "actual_query_backend": "stock",
            }
        except Exception as exc:
            elapsed_ms = (time.time() - t0) * 1000
            err = str(exc)
            if "401" in err or "Unauthorized" in err:
                status = "auth_failed"
            elif any(t in type(exc).__name__ for t in ("Connection", "Timeout", "Network")):
                status = "network_error"
            else:
                status = "api_error"
            return {
                "status": status,
                "result_count": 0,
                "codes": [],
                "elapsed_ms": round(elapsed_ms, 1),
                "raw_error": err[:200],
                "query_text": query_text,
                "skill_type": "astock",
                "actual_query_backend": "stock",
            }

    def _extract_code(self, row: dict) -> str | None:
        import re
        CODE_RE = re.compile(r"\b(\d{6})\b")
        CODE_FULL_RE = re.compile(r"\b\d{6}\.(?:SZ|SH|BJ)\b", re.IGNORECASE)
        for field in ["股票代码", "证券代码", "代码", "symbol", "code"]:
            if field in row:
                raw = str(row[field]).strip()
                if re.match(r"^\d{6}$", raw):
                    return self._normalize(raw)
                m = CODE_FULL_RE.match(raw)
                if m:
                    return raw.upper()
        for v in row.values():
            m = CODE_RE.search(str(v))
            if m:
                return self._normalize(m.group(0))
        return None

    def _normalize(self, raw: str) -> str:
        p = raw[:3]
        if p in ("600", "601", "603", "605", "688", "689", "900"):
            return f"{raw}.SH"
        if p.startswith("8") or p.startswith("4"):
            return f"{raw}.BJ"
        return f"{raw}.SZ"
