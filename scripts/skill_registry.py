"""
skill_registry.py — V6OP 核心能力注册表

6 个核心技能的元数据，不依赖运行时，纯声明。
"""
from __future__ import annotations

from typing import Any

SKILL_REGISTRY: list[dict[str, Any]] = [
    {
        "skill_id":         "wencai",
        "skill_name":       "问财选股",
        "producer_class":   "WencaiSource",
        "module":           "sources.wencai_source",
        "hit_semantics":    "positive",
        "data_requirement": "none",
        "is_lightweight":   True,
        "is_live":          True,
        "params": {
            "query":  {"type": "str",  "default": "",    "desc": "自然语言选股语句"},
            "limit":  {"type": "int",  "default": 300,   "desc": "最大返回只数"},
        },
        "notes": "需要 IWENCAI_API_KEY；key 缺失时安全降级到 blocked 状态",
    },
    {
        "skill_id":         "czsc",
        "skill_name":       "缠论买点",
        "producer_class":   "CZSCProducer",
        "module":           "producers.czsc_producer",
        "hit_semantics":    "positive",
        "data_requirement": "kline_daily",
        "is_lightweight":   False,
        "is_live":          True,
        "params": {
            "signal_bars": {"type": "int",  "default": 5,      "desc": "近 N 根 K 线内有买点才保留"},
            "buy_type":    {"type": "str",  "default": "all",  "desc": "一买/二买/三买/all"},
            "days":        {"type": "int",  "default": 365,    "desc": "回看天数"},
        },
        "notes": "仅读本地缓存（READ_CACHE_ONLY），后复权",
    },
    {
        "skill_id":         "smc",
        "skill_name":       "SMC聪明钱",
        "producer_class":   "SMCProducer",
        "module":           "producers.smc_producer",
        "hit_semantics":    "positive",
        "data_requirement": "kline_daily",
        "is_lightweight":   False,
        "is_live":          True,
        "params": {
            "signal_bars":   {"type": "int",  "default": 15,           "desc": "近 N 根有信号才保留"},
            "swing_length":  {"type": "int",  "default": 10,           "desc": "Swing 窗口大小"},
            "close_break":   {"type": "bool", "default": True,         "desc": "是否要求收盘价突破"},
            "mode":          {"type": "str",  "default": "soft_filter","desc": "strict/soft_filter/bypass"},
            "days":          {"type": "int",  "default": 365,          "desc": "回看天数"},
        },
        "notes": "依赖 smartmoneyconcepts 库，仅读本地缓存",
    },
    {
        "skill_id":         "kline",
        "skill_name":       "K线形态",
        "producer_class":   "KlineProducer",
        "module":           "producers.kline_producer",
        "hit_semantics":    "positive",
        "data_requirement": "kline_daily",
        "is_lightweight":   False,
        "is_live":          True,
        "params": {
            "signal_bars":   {"type": "int",   "default": 5,    "desc": "近 N 根统计窗口"},
            "body_pct":      {"type": "float", "default": 0.1,  "desc": "十字星实体/振幅阈值"},
            "shadow_ratio":  {"type": "float", "default": 2.0,  "desc": "影线/实体倍数阈值"},
            "pass_neutral":  {"type": "bool",  "default": False,"desc": "中性得分是否晋级"},
            "days":          {"type": "int",   "default": 365,  "desc": "回看天数"},
        },
        "notes": "15 种形态纯 pandas 实现，仅读本地缓存",
    },
    {
        "skill_id":         "wave",
        "skill_name":       "波浪分析",
        "producer_class":   "WaveProducer",
        "module":           "producers.wave_producer",
        "hit_semantics":    "positive",
        "data_requirement": "kline_daily",
        "is_lightweight":   False,
        "is_live":          True,
        "params": {
            "signal_bars":   {"type": "int",   "default": 20,   "desc": "近 N 根检查窗口"},
            "swing_window":  {"type": "int",   "default": 10,   "desc": "Swing 检测半径"},
            "fib_tolerance": {"type": "float", "default": 0.15, "desc": "Fibonacci 容差"},
            "min_wave_bars": {"type": "int",   "default": 5,    "desc": "每浪最少 K 线数"},
            "days":          {"type": "int",   "default": 365,  "desc": "回看天数"},
        },
        "notes": "Elliott Wave + Zigzag，纯 pandas/numpy，仅读本地缓存",
    },
    {
        "skill_id":         "landmine",
        "skill_name":       "排雷过滤",
        "producer_class":   "LandmineProducer",
        "module":           "producers.landmine_producer",
        "hit_semantics":    "negative",
        "data_requirement": "kline_daily",
        "is_lightweight":   False,
        "is_live":          True,
        "params": {},
        "notes": "负向技能：命中=应剔除。检测 ST/退市/次新股/K线不足/缓存缺失",
    },
]

_REGISTRY_BY_ID: dict[str, dict] = {s["skill_id"]: s for s in SKILL_REGISTRY}


def get_skill(skill_id: str) -> dict | None:
    return _REGISTRY_BY_ID.get(skill_id)


def list_skills() -> list[str]:
    return [s["skill_id"] for s in SKILL_REGISTRY]


def live_skills() -> list[dict]:
    return [s for s in SKILL_REGISTRY if s["is_live"]]
