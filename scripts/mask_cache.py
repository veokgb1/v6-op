"""
mask_cache.py — V6OP 内容寻址 Mask 缓存（总纲第十章）

fingerprint = sha256(skill_id + sorted(scope_codes) + sorted+serialized(params)
                     + data_date + algo_version)

命中缓存时跳过 producer 重算，节省 CPU/IO。
非执行层账本体系，只是执行层内部复用。

ALGO_VERSION 来源：各 producer 模块内定义的 ALGO_VERSION 模块常量；
                   mask_cache 动态读取，不再集中硬编码。
"""
from __future__ import annotations

import hashlib
import importlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# producer 模块路径映射（skill_id → 模块路径）
_PRODUCER_MODULE_MAP: dict[str, str] = {
    "czsc":     "producers.czsc_producer",
    "smc":      "producers.smc_producer",
    "kline":    "producers.kline_producer",
    "wave":     "producers.wave_producer",
    "landmine": "producers.landmine_producer",
}

# 运行时版本缓存（避免重复 import）
_ALGO_VERSION_CACHE: dict[str, str] = {}


def _get_algo_version(skill_id: str) -> str:
    """从 producer 模块动态读取 ALGO_VERSION，fallback 到 '0.0.0'。"""
    if skill_id in _ALGO_VERSION_CACHE:
        return _ALGO_VERSION_CACHE[skill_id]
    module_path = _PRODUCER_MODULE_MAP.get(skill_id)
    if module_path:
        try:
            mod = importlib.import_module(module_path)
            ver = getattr(mod, "ALGO_VERSION", "0.0.0")
            _ALGO_VERSION_CACHE[skill_id] = str(ver)
            return _ALGO_VERSION_CACHE[skill_id]
        except Exception:
            pass
    _ALGO_VERSION_CACHE[skill_id] = "0.0.0"
    return "0.0.0"

_DEFAULT_CACHE_DIR: Path | None = None


def _get_cache_dir(cache_dir: Path | None = None) -> Path:
    if cache_dir is not None:
        return cache_dir
    if _DEFAULT_CACHE_DIR is not None:
        return _DEFAULT_CACHE_DIR
    return Path(__file__).parent.parent / "output" / "mask_cache"


def compute_fingerprint(
    skill_id: str,
    scope_codes: list[str],
    params: dict[str, Any],
    data_date: str | None,
    algo_version: str | None = None,
) -> str:
    """
    计算 producer 执行指纹（SHA256）。任一输入变化都会产生不同的 fingerprint → cache miss。

    algo_version 来自 producer 模块的 ALGO_VERSION 常量（动态读取），不传则自动解析。
    """
    if algo_version is None:
        algo_version = _get_algo_version(skill_id)

    parts = [
        f"skill_id={skill_id}",
        f"codes={json.dumps(sorted(scope_codes), ensure_ascii=False)}",
        f"params={json.dumps(dict(sorted(params.items())), ensure_ascii=False, sort_keys=True)}",
        f"data_date={data_date or ''}",
        f"algo_version={algo_version}",
    ]
    raw = "\n".join(parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def cache_get(
    fingerprint: str,
    cache_dir: Path | None = None,
) -> dict[str, Any] | None:
    """
    查找缓存。命中返回 dict（含原 producer 输出 + mask_cache_hit=True），未中返回 None。
    """
    cd = _get_cache_dir(cache_dir)
    cache_file = cd / f"{fingerprint}.json"
    if not cache_file.exists():
        return None
    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        data["mask_cache_hit"] = True
        return data
    except Exception:
        return None


def cache_put(
    fingerprint: str,
    result: dict[str, Any],
    cache_dir: Path | None = None,
) -> None:
    """
    将 producer 结果写入缓存（不含 mask_cache_hit 字段）。
    """
    cd = _get_cache_dir(cache_dir)
    cd.mkdir(parents=True, exist_ok=True)
    cache_file = cd / f"{fingerprint}.json"
    # 不缓存 mask_cache_hit 字段（避免循环写入）
    to_save = {k: v for k, v in result.items() if k != "mask_cache_hit"}
    to_save["_cached_at"] = datetime.now().isoformat(timespec="seconds")
    cache_file.write_text(
        json.dumps(to_save, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def compute_scope_data_time_max(
    codes: list[str],
    cache_dir: Path | None = None,
    days: int = 365,
) -> str:
    """
    从本地 OHLCV .pkl 缓存文件中读取 scope 内各股的最大数据日期。

    文件命名约定：{CODE_WITH_UNDERSCORES}_{days}d.pkl，例如 000001_SZ_365d.pkl。
    返回 'YYYY-MM-DD' 格式的最大日期，或空字符串（无法读取时）。

    无论 prefetch 是否触发，此函数都能得到真实的缓存数据日期。
    """
    if cache_dir is None:
        cache_dir = Path(__file__).parent.parent / "var" / "cache" / "kline_daily"

    if not codes:
        return ""

    try:
        import pandas as pd  # type: ignore
    except ImportError:
        return ""

    max_date: str = ""
    for code in codes:
        # 将 000001.SZ → 000001_SZ_{days}d.pkl
        stem = code.replace(".", "_")
        pkl_path = Path(cache_dir) / f"{stem}_{days}d.pkl"
        if not pkl_path.exists():
            continue
        try:
            df = pd.read_pickle(str(pkl_path))
            if df is not None and len(df) > 0:
                last = str(df.index[-1])[:10]  # YYYY-MM-DD
                if last > max_date:
                    max_date = last
        except Exception:
            continue

    return max_date


def run_with_cache(
    skill_id: str,
    scope_codes: list[str],
    params: dict[str, Any],
    data_time_max: str | None,
    run_fn,  # callable(codes, ...) -> dict
    run_kwargs: dict[str, Any] | None = None,
    cache_dir: Path | None = None,
) -> tuple[dict[str, Any], bool]:
    """
    运行 producer，优先返回缓存结果。

    Returns:
        (result_dict, was_cache_hit)
    """
    algo_version = _get_algo_version(skill_id)
    data_date = (data_time_max or "")[:10]  # 只用到日期（YYYY-MM-DD）
    fp = compute_fingerprint(
        skill_id=skill_id,
        scope_codes=scope_codes,
        params=params,
        data_date=data_date,
        algo_version=algo_version,
    )

    cached = cache_get(fp, cache_dir=cache_dir)
    if cached is not None:
        return cached, True

    # Cache miss — 运行 producer
    kwargs = run_kwargs or {}
    t0 = time.time()
    result = run_fn(codes=scope_codes, **kwargs)
    result["_fingerprint"] = fp
    result["_algo_version"] = algo_version
    result["_data_date"] = data_date
    result["duration_seconds"] = round(time.time() - t0, 2)

    cache_put(fp, result, cache_dir=cache_dir)
    return result, False
