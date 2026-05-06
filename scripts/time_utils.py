"""
time_utils.py — V6OP 时间口径

V5 报告统一使用中国时间（CST / UTC+08:00）。V6OP 的人读报告、
运行结果 JSON 和前端状态也沿用同一口径，避免出现 UTC / 本机无时区
裸时间混杂。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

CST = timezone(timedelta(hours=8))
TIMEZONE_LABEL = "Asia/Shanghai (CST, UTC+08:00)"


def now_cst() -> datetime:
    return datetime.now(tz=CST)


def today_cst() -> date:
    return now_cst().date()


def iso_cst(*, timespec: str = "seconds") -> str:
    return now_cst().isoformat(timespec=timespec)


def format_cst(dt: datetime | None = None) -> str:
    value = dt.astimezone(CST) if dt is not None else now_cst()
    return value.strftime("%Y-%m-%d %H:%M:%S CST")
