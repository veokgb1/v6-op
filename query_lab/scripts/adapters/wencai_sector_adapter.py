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

_STOCK_CODE_FIELDS = ["股票代码", "代码", "symbol", "code"]
_STOCK_NAME_FIELDS = ["股票简称", "简称"]
_LEADER_NAME_RE = re.compile(r"指数@领涨股简称")  # zhishu leader-stock name column
_INDEX_CODE_FIELDS = ["指数代码", "code"]
_REASON_COL_KEYWORDS = ("原因", "reason", "理由", "解析", "分析")
_INDEX_FIELD_MARKERS = ("指数代码", "指数简称", "指数@", "sector_code", "index_code")

_CHINESE_RE = re.compile(r"[一-鿿]")
_CODE_RE = re.compile(r"^\d{6}$")
# A-share codes start with: 000,001,002,003,300,301,600,601,603,605,688
# Sector/index codes start with 88x or 884 — exclude them
_STOCK_CODE_PREFIXES = (
    "000", "001", "002", "003", "300", "301",
    "600", "601", "603", "605", "688",
)
# Index codes are 6-digit starting with 88 (concept/sector) or 884 (industry)
_INDEX_CODE_PREFIXES = ("88",)


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


def _extract_stock_codes(rows: list[dict]) -> list[str]:
    codes: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for f in _STOCK_CODE_FIELDS:
            if f in row:
                val = str(row[f]).strip()
                clean = re.sub(r"\.(SZ|SH|BJ)$", "", val.upper())
                if (
                    _CODE_RE.match(clean)
                    and clean.startswith(_STOCK_CODE_PREFIXES)
                    and clean not in seen
                ):
                    seen.add(clean)
                    codes.append(clean)
                    break
    return codes


def _extract_stock_names(rows: list[dict]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for row in rows:
        # Check explicit stock name fields first
        for f in _STOCK_NAME_FIELDS:
            if f in row:
                val = str(row[f]).strip()
                if len(val) >= 2 and val not in seen:
                    seen.add(val)
                    names.append(val)
                break
        else:
            # Check for leader-stock name column (指数@领涨股简称[YYYYMMDD])
            for key in row:
                if _LEADER_NAME_RE.search(str(key)):
                    val = str(row[key]).strip()
                    if len(val) >= 2 and val not in seen and val.lower() not in ("nan", "none", ""):
                        seen.add(val)
                        names.append(val)
                    break
    return names


def _extract_index_codes(rows: list[dict]) -> list[str]:
    """Extract zhishu index codes (88xxxx / 884xxx)."""
    codes: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for f in _INDEX_CODE_FIELDS:
            if f in row:
                val = str(row[f]).strip()
                clean = re.sub(r"\.(SZ|SH|BJ)$", "", val.upper())
                if (
                    _CODE_RE.match(clean)
                    and clean.startswith(_INDEX_CODE_PREFIXES)
                    and clean not in seen
                ):
                    seen.add(clean)
                    codes.append(clean)
                    break
    return codes


def _detect_reason_cols(raw_cols: list[str]) -> str:
    """Return matched reason column name, or empty string."""
    for col in raw_cols:
        col_str = str(col)
        if any(kw in col_str for kw in _REASON_COL_KEYWORDS):
            return col_str
    return ""


def _detect_index_fields(raw_cols: list[str]) -> bool:
    """True if raw_cols contains zhishu index field markers."""
    for col in raw_cols:
        col_str = str(col)
        if any(marker in col_str for marker in _INDEX_FIELD_MARKERS):
            return True
    return False


def _classify_return_type(
    sector_names: list[str],
    stock_codes: list[str],
    stock_names: list[str],
    raw_cols: list[str],
    result_count: int,
    reason_col: str = "",
    has_index_fields: bool = False,
) -> tuple[str, str]:
    """Returns (return_object_type, next_pipeline_route)."""
    if result_count == 0:
        return "empty_or_error", "failed: 记录原因，不进入 pipeline"

    has_sectors = bool(sector_names)
    has_stocks = bool(stock_codes or stock_names)

    if has_sectors and not has_stocks:
        if reason_col:
            return (
                "sector_with_reason",
                "sector_to_phase_b: 返回板块+原因列，原因文本可作注释，板块名可接 Phase B",
            )
        if has_index_fields:
            return (
                "sector_with_index_fields",
                "sector_to_phase_b: 返回板块指数代码/简称/行情字段，可接 Phase B",
            )
        return (
            "sector_only",
            "sector_to_phase_b: 可接入 Phase B/问财选A股，"
            "如：{sector}中今日收盘价站上5日均线的股票",
        )
    if has_stocks and not has_sectors:
        return (
            "stock_only",
            "stock_to_local_skill: 直接进入本地技能 kline/smc/wave/landmine，"
            "不可再送回问财选A股",
        )
    if has_sectors and has_stocks:
        return (
            "mixed_sector_stock",
            "review: 拆开记录，板块部分进 Phase B，股票部分进本地技能",
        )
    if raw_cols:
        return "table_unknown", "review: 先修 extractor 或人工确认列含义"
    return "text_explanation", "text_only: 只能作为解释，不可进入 pipeline"


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

    def _empty_contract(self) -> dict[str, Any]:
        return {
            "return_object_type": "empty_or_error",
            "raw_columns": "",
            "extracted_sector_names": "",
            "extracted_index_codes": "",
            "extracted_stock_codes": "",
            "extracted_stock_names": "",
            "extracted_reason_text": "",
            "next_pipeline_route": "failed: 记录原因，不进入 pipeline",
        }

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
                **self._empty_contract(),
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
                **self._empty_contract(),
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
            **self._empty_contract(),
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
                return {"status": "api_error", "names": [], "actual_query_backend": query_type,
                        **self._empty_contract()}

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

            raw_cols = list(rows[0].keys())[:20] if rows else []
            raw_cols_str = "|".join(str(c) for c in raw_cols)

            names = _extract_sector_names(rows)
            stock_codes = _extract_stock_codes(rows)
            stock_names = _extract_stock_names(rows)
            index_codes = _extract_index_codes(rows)
            reason_col = _detect_reason_cols(raw_cols)
            has_index_fields = _detect_index_fields(raw_cols)

            if limit > 0:
                names = names[:limit]
                stock_codes = stock_codes[:limit]
                stock_names = stock_names[:limit]
                index_codes = index_codes[:limit]

            total_count = len(rows)
            ret_type, next_route = _classify_return_type(
                names, stock_codes, stock_names, raw_cols, total_count,
                reason_col=reason_col, has_index_fields=has_index_fields,
            )

            contract = {
                "return_object_type": ret_type,
                "raw_columns": raw_cols_str,
                "extracted_sector_names": "|".join(names[:10]),
                "extracted_index_codes": "|".join(index_codes[:10]),
                "extracted_stock_codes": "|".join(stock_codes[:10]),
                "extracted_stock_names": "|".join(stock_names[:10]),
                "extracted_reason_text": reason_col,
                "next_pipeline_route": next_route,
            }

            if not names and not stock_codes and not stock_names:
                return {"status": "empty_result", "names": [], "actual_query_backend": query_type,
                        **contract}

            result_count = len(names) if names else len(stock_codes) if stock_codes else total_count
            return {
                "status": "ok",
                "result_count": result_count,
                "names": names,
                "raw_error": "",
                "query_text": query_text,
                "skill_type": "sector",
                "actual_query_backend": query_type,
                **contract,
            }

        except ImportError:
            return {"status": "blocked", "names": [], "actual_query_backend": query_type,
                    **self._empty_contract()}
        except Exception as exc:
            return {"status": "api_error", "names": [], "actual_query_backend": query_type,
                    "raw_error": str(exc)[:200], **self._empty_contract()}
