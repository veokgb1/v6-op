#!/usr/bin/env python3
"""
wencai_source.py — V6OP 问财选股 Source

从 .env 读取 IWENCAI_API_KEY，调用同花顺问财 API，输出 scope_codes。
Key 缺失或接口失败时安全降级到 blocked 状态，不伪造结果。

用法:
  python scripts/sources/wencai_source.py \
    --query "近20日涨幅小于10%，成交额放大" \
    --limit 50 \
    --out output/current/wencai_scope.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# ── 项目路径 ──────────────────────────────────────────────────────────
_SOURCES_DIR = Path(__file__).parent.resolve()
_SCRIPTS_DIR = _SOURCES_DIR.parent
_PROJECT_ROOT = _SCRIPTS_DIR.parent

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from time_utils import iso_cst

# ── 颜色日志 ──────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
RESET  = "\033[0m"

# Optional realtime sink installed by source_resolver/execution_engine.
_log_sink = None


def _log(level: str, msg: str) -> None:
    color = {"INFO": GREEN, "WARN": YELLOW, "ERROR": RED, "HEAD": CYAN}.get(level, RESET)
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}]{color}[WencaiSource][{level}]{RESET} {msg}", flush=True)
    if callable(_log_sink):
        try:
            _log_sink(level, msg)
        except Exception:
            pass


# ── .env 加载 ─────────────────────────────────────────────────────────

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


# ── 代码解析 ──────────────────────────────────────────────────────────
_CODE_RE = re.compile(r"\b(\d{6})\b")
_CODE_FULL_RE = re.compile(r"\b\d{6}\.(?:SZ|SH|BJ)\b", re.IGNORECASE)


def _normalize_code(raw: str) -> str | None:
    raw = raw.strip()
    if re.match(r"^\d{6}$", raw):
        prefix = raw[:3]
        if prefix in ("600", "601", "603", "605", "688", "900"):
            return f"{raw}.SH"
        return f"{raw}.SZ"
    m = _CODE_FULL_RE.match(raw)
    if m:
        return raw.upper()
    return None


def _extract_codes(data: list[dict]) -> list[str]:
    """从 pywencai 返回的行数据中提取股票代码。"""
    codes: list[str] = []
    seen: set[str] = set()
    _field_candidates = ["股票代码", "证券代码", "代码", "symbol", "code"]

    for row in data:
        raw_code = None
        for field in _field_candidates:
            if field in row:
                raw_code = str(row[field])
                break
        if raw_code is None:
            # 尝试从任意字段找 6 位数字
            for v in row.values():
                m = _CODE_RE.search(str(v))
                if m:
                    raw_code = m.group(0)
                    break
        if raw_code:
            norm = _normalize_code(raw_code)
            if norm and norm not in seen:
                seen.add(norm)
                codes.append(norm)
    return codes


# ── 问财查询 ──────────────────────────────────────────────────────────

def _query_wencai(query: str, api_key: str, limit: int) -> tuple[list[str], str]:
    """
    调用 pywencai 接口查询。
    返回 (codes, status)，status in:
      "ok"               — 成功
      "blocked"          — pywencai 库未安装
      "auth_failed"      — API Key 无效或 401 Unauthorized
      "empty_result"     — API 正常但无股票结果
      "network_error"    — 网络连接失败（ConnectionError / TimeoutError）
      "api_error"        — 其他 API 级别错误
    """
    try:
        import pywencai
    except ImportError:
        _log("WARN", "pywencai 未安装，无法调用问财 API")
        return [], "blocked"

    try:
        _log("INFO", f"问财查询: {query[:80]}  limit={limit}")
        perpage = min(max(int(limit), 1), 100)
        max_pages = max(1, (int(limit) + perpage - 1) // perpage)
        all_rows: list[dict] = []
        codes: list[str] = []
        seen: set[str] = set()

        for page in range(1, max_pages + 1):
            result = pywencai.get(
                query=query,
                query_type="stock",
                perpage=perpage,
                page=page,
            )

            if result is None:
                if page == 1:
                    _log("WARN", "问财返回 None，视为空结果")
                    return [], "empty_result"
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

            all_rows.extend(rows)
            before = len(codes)
            for code in _extract_codes(rows):
                if code not in seen:
                    seen.add(code)
                    codes.append(code)
                    if len(codes) >= limit:
                        break

            _log("INFO", f"问财第 {page} 页返回 {len(rows)} 行，累计 {len(codes)} 只")
            if len(codes) >= limit or len(codes) == before:
                break

        codes = codes[:limit]
        _log("INFO", f"问财累计返回 {len(all_rows)} 行，提取到 {len(codes)} 只代码")

        if not codes:
            _log("WARN", "问财返回 0 只股票代码（empty_result）")
            return [], "empty_result"

        return codes, "ok"

    except Exception as exc:
        err_str = str(exc)
        # 脱敏：不打印可能含 key 的堆栈
        if "401" in err_str or "Unauthorized" in err_str or "auth" in err_str.lower():
            _log("ERROR", "问财 API 认证失败（401 Unauthorized）")
            return [], "auth_failed"
        if any(t in type(exc).__name__ for t in ("Connection", "Timeout", "Network")):
            _log("ERROR", f"问财网络连接失败: {type(exc).__name__}")
            return [], "network_error"
        _log("ERROR", f"问财接口异常: {err_str[:200]}")
        return [], "api_error"


# ── 输出 JSON 构建 ────────────────────────────────────────────────────

def _make_scope_json(
    query: str,
    codes: list[str],
    status: str,
    limit: int,
    elapsed: float,
) -> dict:
    qhash = hashlib.sha1(query.encode()).hexdigest()[:8]
    count = len(codes)
    # api_called: 是否真正尝试调用了 pywencai 接口
    api_called = status not in ("key_missing", "blocked")
    # count_note: 区分三种返回量级
    near_limit = count >= max(1, int(limit * 0.95))
    if count == 0:
        count_note = "问财返回 0 只股票，条件可能过严、查询不匹配或授权未生效"
    elif near_limit:
        count_note = f"接近上限（{count}/{limit}），实际符合股票可能更多，可尝试提高 limit"
    elif count < 50:
        count_note = f"问财仅返回少量股票（{count} 只），可考虑放宽查询条件"
    else:
        count_note = f"问财返回 {count} 只股票"

    return {
        "scope_id":      f"wencai_{qhash}",
        "source":        "wencai",
        "query_hash":    qhash,
        "query_text":    query,
        "actual_count":  count,
        "api_called":    api_called,
        "count_note":    count_note,
        "status":        status,
        "scope_codes":   codes,
        "scope_count":   count,
        "limit":         limit,
        "data_mode":     "live_api" if status == "ok" else status,
        "generated_at":  iso_cst(),
        "elapsed_s":     round(elapsed, 2),
        "note":          {
            "ok":           count_note,
            "key_missing":  "IWENCAI_API_KEY 未配置，请检查 .env 文件",
            "blocked":      "pywencai 库未安装，无法调用问财 API",
            "auth_failed":  "问财 API 认证失败（401 Unauthorized），请检查 API Key 是否有效",
            "empty_result": "问财查询无结果（条件过严或市场无符合股票）",
            "network_error":"问财网络连接失败，请检查网络或稍后重试",
            "api_error":    "问财 API 返回错误，请查看日志详情",
        }.get(status, "问财接口异常，返回空列表"),
    }


# ── 主入口 ────────────────────────────────────────────────────────────

def run(
    query: str,
    limit: int = 300,
    out: Path | None = None,
) -> dict:
    """可作为库函数调用。返回 scope JSON dict。"""
    t0 = time.time()
    env = _load_env()
    api_key = env.get("IWENCAI_API_KEY") or os.environ.get("IWENCAI_API_KEY", "")

    if not api_key:
        _log("WARN", "IWENCAI_API_KEY 未配置，返回 key_missing 状态")
        codes, status = [], "key_missing"
    else:
        codes, status = _query_wencai(query, api_key, limit)

    elapsed = time.time() - t0
    result = _make_scope_json(query, codes, status, limit, elapsed)

    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        _log("INFO", f"scope JSON → {out}  ({len(codes)} 只, status={status})")

    return result


def main() -> None:
    import io as _io
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="V6OP 问财选股 Source")
    parser.add_argument("--query",  required=True,       help="自然语言选股语句")
    parser.add_argument("--limit",  type=int, default=300, help="最大返回只数")
    parser.add_argument("--out",    default="output/current/wencai_scope.json")
    args = parser.parse_args()

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = _PROJECT_ROOT / out_path

    result = run(query=args.query, limit=args.limit, out=out_path)

    status = result["status"]
    _log("HEAD" if status == "ok" else "WARN",
         f"问财完成  status={status}  codes={result['scope_count']}  "
         f"elapsed={result['elapsed_s']}s")

    if status not in ("ok", "key_missing"):
        sys.exit(1)


if __name__ == "__main__":
    main()
