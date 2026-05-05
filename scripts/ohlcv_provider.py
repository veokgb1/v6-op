#!/usr/bin/env python3
"""
ohlcv_provider.py — V6OP A股 OHLCV 数据获取与缓存层

数据源优先级（自动降级）:
  1. baostock  — adjustflag="1"（后复权）
  2. akshare   — adjust="hfq"（后复权）
  3. yfinance  — auto_adjust=True（等效后复权）

缓存策略:
  pickle 本地缓存，默认 TTL=24h。
  三源全失败时降级使用过期缓存并标记 stale_cache。
  缓存目录: {project_root}/var/cache/kline_daily/

模式:
  READ_CACHE_ONLY=true  → 只读缓存，缓存未命中返回 None，零网络请求
  FAST_FULL_SCAN=true   → 只走 baostock，不走 akshare/yfinance 备用源

北交所(.BJ 结尾): 直接跳过，返回 None。
"""
from __future__ import annotations

import atexit
import contextlib
import io
import os
import pickle
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

# ── CST 时区 ──────────────────────────────────────────────────────────
_CST = timezone(timedelta(hours=8))


def _now_cst() -> datetime:
    return datetime.now(tz=_CST)


# ── 项目根自动检测 ────────────────────────────────────────────────────
def _find_project_root() -> Path:
    """向上找包含 scripts/ 子目录的目录作为 V6OP 项目根。"""
    anchor = Path(__file__).resolve()
    for parent in anchor.parents:
        if (parent / "scripts").exists() and (parent / "var").exists():
            return parent
        if (parent / "scripts").exists() and (parent / "requirements.txt").exists():
            return parent
    return anchor.parent.parent


_PROJECT_ROOT = _find_project_root()

# ── 缓存配置 ──────────────────────────────────────────────────────────
_CACHE_DIR = Path(
    os.environ.get("KLINE_CACHE_DIR", "") or str(_PROJECT_ROOT / "var" / "cache" / "kline_daily")
)
_CACHE_TTL_H = float(os.environ.get("KLINE_CACHE_TTL_H", "24"))

# ── 运行模式 ──────────────────────────────────────────────────────────
# 保留模块级变量以反映导入时状态，但 fetch_ohlcv() 在每次调用时动态重读环境变量
# 确保 execution_engine 在同进程内"先预热、后只读分析"的两阶段隔离可靠生效
_READ_CACHE_ONLY: bool = os.environ.get("READ_CACHE_ONLY", "false").lower() in ("1", "true", "yes")
_FAST_FULL_SCAN: bool = os.environ.get("FAST_FULL_SCAN", "false").lower() in ("1", "true", "yes")


def _read_cache_only() -> bool:
    """动态读取 READ_CACHE_ONLY，支持运行时切换（无需重新导入模块）。"""
    return os.environ.get("READ_CACHE_ONLY", "false").lower() in ("1", "true", "yes")


def _fast_full_scan() -> bool:
    """动态读取 FAST_FULL_SCAN，支持运行时切换。"""
    return os.environ.get("FAST_FULL_SCAN", "false").lower() in ("1", "true", "yes")

_AKSHARE_RETRY = int(os.environ.get("AKSHARE_RETRY", "3"))
_AKSHARE_RETRY_WAIT = float(os.environ.get("AKSHARE_RETRY_WAIT", "2.0"))

_COLS_OUT = ["open", "high", "low", "close", "volume", "amount"]
_MIN_BARS = 30

# ── 拉取汇总统计 ──────────────────────────────────────────────────────
_stats: dict[str, int] = {
    "cache_hit": 0,
    "stale_used": 0,
    "baostock_ok": 0,
    "akshare_ok": 0,
    "yfinance_ok": 0,
    "bj_skipped": 0,
    "three_source_fail": 0,
    "read_cache_miss": 0,
    "bs_reconnects": 0,
}

# ── baostock 会话复用 ─────────────────────────────────────────────────
_BS_LOGGED_IN: bool = False


def _bs_ensure_login(reconnect: bool = False) -> None:
    global _BS_LOGGED_IN
    if _BS_LOGGED_IN and not reconnect:
        return
    import baostock as bs
    with contextlib.redirect_stdout(io.StringIO()):
        lg = bs.login()
    if lg.error_code != "0":
        raise RuntimeError(f"baostock login failed: [{lg.error_code}] {lg.error_msg}")
    _BS_LOGGED_IN = True
    if reconnect:
        _stats["bs_reconnects"] += 1


def _bs_logout_atexit() -> None:
    global _BS_LOGGED_IN
    if not _BS_LOGGED_IN:
        return
    try:
        import baostock as bs
        with contextlib.redirect_stdout(io.StringIO()):
            bs.logout()
        _BS_LOGGED_IN = False
    except Exception:
        pass


atexit.register(_bs_logout_atexit)


# ── 代码格式转换 ──────────────────────────────────────────────────────

def _to_baostock(code: str) -> str:
    """000001.SZ → sz.000001"""
    num, mkt = code.split(".")
    return f"{mkt.lower()}.{num}"


def _to_akshare(code: str) -> str:
    """000001.SZ → 000001"""
    return code.split(".")[0]


def _to_yfinance(code: str) -> str:
    """000001.SZ → 000001.SZ; 600000.SH → 600000.SS"""
    num, mkt = code.split(".")
    yfmkt = "SS" if mkt.upper() == "SH" else "SZ"
    return f"{num}.{yfmkt}"


# ── 日付工具 ──────────────────────────────────────────────────────────

def _last_trading_day() -> str:
    d = datetime.today()
    wd = d.weekday()
    if wd == 5:
        d -= timedelta(days=1)
    elif wd == 6:
        d -= timedelta(days=2)
    return d.strftime("%Y-%m-%d")


# ── 缓存 I/O ──────────────────────────────────────────────────────────

def cache_path(code: str, days: int) -> Path:
    safe = code.replace(".", "_").replace("/", "_")
    return _CACHE_DIR / f"{safe}_{days}d.pkl"


def _read_cache(code: str, days: int, allow_stale: bool = False) -> Optional[pd.DataFrame]:
    cp = cache_path(code, days)
    if not cp.exists():
        return None
    try:
        age_h = (time.time() - cp.stat().st_mtime) / 3600
        with open(cp, "rb") as f:
            df = pickle.load(f)
        if df is None or len(df) < _MIN_BARS:
            return None
        if age_h <= _CACHE_TTL_H:
            df.attrs["source"] = "cache"
            df.attrs["adjust"] = "hfq"
            return df
        if allow_stale:
            df.attrs["source"] = "stale_cache"
            df.attrs["adjust"] = "hfq"
            df.attrs["cache_age_h"] = round(age_h, 1)
            return df
    except Exception:
        pass
    return None


def _write_cache(code: str, days: int, df: pd.DataFrame) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(cache_path(code, days), "wb") as f:
            pickle.dump(df, f)
    except Exception:
        pass


# ── 数据源实现 ────────────────────────────────────────────────────────

def _fetch_baostock(code: str, start: str, end: str) -> pd.DataFrame:
    global _BS_LOGGED_IN
    import baostock as bs
    rows: list = []
    for attempt in range(2):
        _bs_ensure_login(reconnect=(attempt > 0))
        try:
            rs = bs.query_history_k_data_plus(
                _to_baostock(code),
                "date,open,high,low,close,volume,amount",
                start_date=start,
                end_date=end,
                frequency="d",
                adjustflag="1",
            )
            if rs.error_code != "0":
                raise RuntimeError(f"baostock query failed: [{rs.error_code}] {rs.error_msg}")
            while rs.next():
                rows.append(rs.get_row_data())
            break
        except RuntimeError:
            raise
        except Exception as exc:
            _BS_LOGGED_IN = False
            if attempt == 1:
                raise RuntimeError(f"baostock connection failed: {exc}") from exc

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume", "amount"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    for col in _COLS_OUT:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df.dropna(subset=["open", "close"], inplace=True)
    return df[_COLS_OUT]


def _fetch_akshare(code: str, start: str, end: str) -> pd.DataFrame:
    import akshare as ak
    last_exc: Exception = RuntimeError("akshare retries exhausted")
    for attempt in range(_AKSHARE_RETRY):
        try:
            df_raw = ak.stock_zh_a_hist(
                symbol=_to_akshare(code),
                period="daily",
                start_date=start.replace("-", ""),
                end_date=end.replace("-", ""),
                adjust="hfq",
            )
            break
        except Exception as exc:
            last_exc = exc
            if attempt < _AKSHARE_RETRY - 1:
                time.sleep(_AKSHARE_RETRY_WAIT * (2 ** attempt))
    else:
        raise last_exc

    if df_raw is None or df_raw.empty:
        return pd.DataFrame()
    col_map = {
        "日期": "date", "开盘": "open", "最高": "high",
        "最低": "low", "收盘": "close", "成交量": "volume", "成交额": "amount",
    }
    df_raw.rename(columns=col_map, inplace=True)
    df_raw["date"] = pd.to_datetime(df_raw["date"])
    df_raw = df_raw.set_index("date")
    for col in _COLS_OUT:
        if col in df_raw.columns:
            df_raw[col] = pd.to_numeric(df_raw[col], errors="coerce")
    if "amount" not in df_raw.columns:
        df_raw["amount"] = 0.0
    df_raw.dropna(subset=["open", "close"], inplace=True)
    return df_raw[_COLS_OUT]


def _fetch_yfinance(code: str, start: str, end: str) -> pd.DataFrame:
    import yfinance as yf
    ticker = yf.Ticker(_to_yfinance(code))
    df_raw = ticker.history(start=start, end=end, auto_adjust=True)
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()
    df_raw.index = pd.to_datetime(df_raw.index)
    if df_raw.index.tz is not None:
        df_raw.index = df_raw.index.tz_localize(None)
    df_raw = df_raw.rename(columns={"Open": "open", "High": "high", "Low": "low",
                                     "Close": "close", "Volume": "volume"})
    df_raw["amount"] = 0.0
    df_raw.dropna(subset=["open", "close"], inplace=True)
    return df_raw[_COLS_OUT]


_FETCHERS = [
    ("baostock", _fetch_baostock),
    ("akshare", _fetch_akshare),
    ("yfinance", _fetch_yfinance),
]


# ── 公共接口 ──────────────────────────────────────────────────────────

def fetch_ohlcv(
    code: str,
    days: int = 365,
    min_bars: int = _MIN_BARS,
    verbose: bool = False,
) -> Optional[pd.DataFrame]:
    """获取 A 股后复权日线 OHLCV。

    优先级: 新鲜缓存 → baostock → akshare → yfinance → 过期缓存 → None
    READ_CACHE_ONLY: 新鲜缓存 → None
    FAST_FULL_SCAN: 新鲜缓存 → baostock → None
    """
    # 北交所跳过
    if "." in code and code.split(".")[-1].upper() == "BJ":
        _stats["bj_skipped"] += 1
        return None

    # 读新鲜缓存
    cached = _read_cache(code, days, allow_stale=False)
    if cached is not None:
        _stats["cache_hit"] += 1
        if verbose:
            print(f"  [ohlcv] {code} ← cache  {len(cached)} 根", flush=True)
        return cached

    # READ_CACHE_ONLY 模式（动态读取，支持同进程两阶段切换）
    if _read_cache_only():
        _stats["read_cache_miss"] += 1
        return None

    # 日期区间
    end = _last_trading_day()
    start = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")

    # FAST_FULL_SCAN 模式: 只走 baostock（动态读取）
    if _fast_full_scan():
        try:
            df = _fetch_baostock(code, start, end)
            if df is not None and not df.empty and len(df) >= min_bars:
                df = df.sort_index()
                df.attrs["source"] = "baostock"
                df.attrs["adjust"] = "hfq"
                _write_cache(code, days, df)
                _stats["baostock_ok"] += 1
                if verbose:
                    print(f"  [ohlcv] {code} ← baostock  {len(df)} 根", flush=True)
                return df
        except Exception:
            pass
        return None

    # 标准模式: 三源降级
    for name, fn in _FETCHERS:
        try:
            df = fn(code, start, end)
            if df is not None and not df.empty and len(df) >= min_bars:
                df = df.sort_index()
                df.attrs["source"] = name
                df.attrs["adjust"] = "hfq"
                _write_cache(code, days, df)
                _stats[f"{name}_ok"] = _stats.get(f"{name}_ok", 0) + 1
                if verbose:
                    print(f"  [ohlcv] {code} ← {name}  {len(df)} 根", flush=True)
                return df
        except ImportError:
            print(f"  [ohlcv] ⚠ {name} 未安装，跳过", flush=True)
        except Exception as exc:
            if verbose:
                print(f"  [ohlcv] {code} {name} 异常: {exc}", flush=True)

    # 兜底: 过期缓存
    stale = _read_cache(code, days, allow_stale=True)
    if stale is not None:
        _stats["stale_used"] += 1
        print(f"  [ohlcv] ⚠ {code} 使用过期缓存({stale.attrs.get('cache_age_h', '?')}h)", flush=True)
        return stale

    _stats["three_source_fail"] += 1
    return None


def get_cache_dir() -> Path:
    return _CACHE_DIR


def get_stats() -> dict:
    return dict(_stats)
