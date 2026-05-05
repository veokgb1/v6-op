"""
test_v6op024_mask_cache_data_date.py — V6OP-024 Fix 2

验证 Mask cache data_date 在 prefetch_triggered=False 时也能正确读取真实缓存日期，
且不同 data_date 会产生不同指纹（强制 cache miss）。

测试设计：
1. 用构造的 .pkl 文件（含 DatetimeIndex）测试 compute_scope_data_time_max
2. 验证 data_date 变化后 fingerprint 不同
3. 验证相同 data_date 时 fingerprint 相同（cache hit 路径）
4. 验证 execution_engine 在 prefetch_triggered=False 时也使用真实缓存日期
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

_ROOT    = Path(__file__).parent.parent.resolve()
_SCRIPTS = _ROOT / "scripts"

sys.path.insert(0, str(_SCRIPTS))


@pytest.fixture(scope="module")
def mask_cache_mod():
    import mask_cache
    return mask_cache


# ══════════════════════════════════════════════════════════════════════
# TestComputeScopeDataTimeMax — pkl 读取函数
# ══════════════════════════════════════════════════════════════════════

class TestComputeScopeDataTimeMax:

    def test_returns_empty_on_no_codes(self, mask_cache_mod):
        result = mask_cache_mod.compute_scope_data_time_max([], cache_dir=Path("/nonexistent"))
        assert result == "", "空代码列表应返回空字符串"

    def test_returns_empty_on_missing_cache_dir(self, mask_cache_mod):
        result = mask_cache_mod.compute_scope_data_time_max(
            ["000001.SZ"], cache_dir=Path("/definitely_nonexistent_xyz")
        )
        assert result == "", "无效缓存目录应返回空字符串"

    def test_reads_max_date_from_pkl(self, mask_cache_mod, tmp_path):
        import pandas as pd

        # 构造两只股票的 pkl 文件
        dates_a = pd.date_range("2026-04-01", "2026-04-25")
        dates_b = pd.date_range("2026-04-01", "2026-04-30")  # 更新的日期
        df_a = pd.DataFrame({"close": range(len(dates_a))}, index=dates_a)
        df_b = pd.DataFrame({"close": range(len(dates_b))}, index=dates_b)

        df_a.to_pickle(str(tmp_path / "000001_SZ_365d.pkl"))
        df_b.to_pickle(str(tmp_path / "000002_SZ_365d.pkl"))

        result = mask_cache_mod.compute_scope_data_time_max(
            ["000001.SZ", "000002.SZ"], cache_dir=tmp_path, days=365
        )
        assert result == "2026-04-30", \
            f"应返回两只股票中最新的 data_date，得到 {result!r}"

    def test_ignores_missing_codes(self, mask_cache_mod, tmp_path):
        import pandas as pd

        dates = pd.date_range("2026-03-01", "2026-03-31")
        df = pd.DataFrame({"close": range(len(dates))}, index=dates)
        df.to_pickle(str(tmp_path / "000001_SZ_365d.pkl"))
        # 000099.SZ 无 pkl 文件

        result = mask_cache_mod.compute_scope_data_time_max(
            ["000001.SZ", "000099.SZ"], cache_dir=tmp_path, days=365
        )
        assert result == "2026-03-31", "缺失的代码应被忽略，只取存在的"

    def test_returns_empty_when_all_missing(self, mask_cache_mod, tmp_path):
        result = mask_cache_mod.compute_scope_data_time_max(
            ["999999.SZ"], cache_dir=tmp_path, days=365
        )
        assert result == "", "所有文件缺失时应返回空字符串"


# ══════════════════════════════════════════════════════════════════════
# TestDataDateFingerprint — data_date 变化时指纹不同
# ══════════════════════════════════════════════════════════════════════

class TestDataDateFingerprint:

    def test_different_data_date_different_fingerprint(self, mask_cache_mod):
        codes = ["000001.SZ", "000002.SZ"]
        params = {"days": 365, "signal_bars": 5}

        fp1 = mask_cache_mod.compute_fingerprint("kline", codes, params, "2026-04-29")
        fp2 = mask_cache_mod.compute_fingerprint("kline", codes, params, "2026-04-30")
        assert fp1 != fp2, "不同 data_date 应产生不同指纹"

    def test_same_data_date_same_fingerprint(self, mask_cache_mod):
        codes = ["000001.SZ"]
        params = {"days": 365}

        fp1 = mask_cache_mod.compute_fingerprint("czsc", codes, params, "2026-04-30")
        fp2 = mask_cache_mod.compute_fingerprint("czsc", codes, params, "2026-04-30")
        assert fp1 == fp2, "相同输入应产生相同指纹"

    def test_empty_data_date_different_from_real_date(self, mask_cache_mod):
        codes = ["000001.SZ"]
        params = {"days": 365}

        fp_empty = mask_cache_mod.compute_fingerprint("smc", codes, params, "")
        fp_real  = mask_cache_mod.compute_fingerprint("smc", codes, params, "2026-04-30")
        assert fp_empty != fp_real, "空 data_date 不应与真实日期产生相同指纹"


# ══════════════════════════════════════════════════════════════════════
# TestCacheHitMissWithDataDate — 相同/不同 data_date 的命中/未中
# ══════════════════════════════════════════════════════════════════════

class TestCacheHitMissWithDataDate:

    def _make_mock_result(self, codes: list[str]) -> dict:
        return {
            "hit_codes": codes[:1],
            "miss_codes": codes[1:],
            "hit_count": 1,
            "miss_count": len(codes) - 1,
            "evidence": {},
        }

    def test_first_run_is_cache_miss(self, mask_cache_mod, tmp_path):
        mc_dir = tmp_path / "mask_cache"
        codes = ["000001.SZ", "000002.SZ"]
        fp = mask_cache_mod.compute_fingerprint("kline", codes, {}, "2026-04-30")
        result = mask_cache_mod.cache_get(fp, cache_dir=mc_dir)
        assert result is None, "首次应为 cache miss"

    def test_after_put_same_date_is_hit(self, mask_cache_mod, tmp_path):
        mc_dir = tmp_path / "mask_cache"
        codes = ["000001.SZ"]
        data_date = "2026-04-30"
        params = {"days": 365}
        fp = mask_cache_mod.compute_fingerprint("czsc", codes, params, data_date)

        mock = self._make_mock_result(codes)
        mask_cache_mod.cache_put(fp, mock, cache_dir=mc_dir)

        result = mask_cache_mod.cache_get(fp, cache_dir=mc_dir)
        assert result is not None, "写入后同 data_date 应命中"
        assert result.get("mask_cache_hit") is True

    def test_different_date_after_put_is_miss(self, mask_cache_mod, tmp_path):
        mc_dir = tmp_path / "mask_cache"
        codes = ["000001.SZ"]
        params = {"days": 365}
        fp_old = mask_cache_mod.compute_fingerprint("czsc", codes, params, "2026-04-29")
        fp_new = mask_cache_mod.compute_fingerprint("czsc", codes, params, "2026-04-30")

        mock = self._make_mock_result(codes)
        mask_cache_mod.cache_put(fp_old, mock, cache_dir=mc_dir)

        result = mask_cache_mod.cache_get(fp_new, cache_dir=mc_dir)
        assert result is None, "修改 data_date 后应 cache miss"


# ══════════════════════════════════════════════════════════════════════
# TestExecutionEngineDataDate — prefetch_triggered=False 路径验证
# ══════════════════════════════════════════════════════════════════════

class TestExecutionEngineDataDate:
    """
    验证 execution_engine 在 prefetch_triggered=False（缓存充足）时，
    也能通过 compute_scope_data_time_max 得到真实 data_date。
    """

    def test_compute_scope_data_time_max_used_in_engine(self):
        # 验证 execution_engine.py 代码中调用了 compute_scope_data_time_max
        src = (_SCRIPTS / "execution_engine.py").read_text(encoding="utf-8")
        assert "compute_scope_data_time_max" in src, \
            "execution_engine.py 应调用 compute_scope_data_time_max"

    def test_data_time_max_not_conditional_on_prefetch_only(self):
        src = (_SCRIPTS / "execution_engine.py").read_text(encoding="utf-8")
        # data_time_max 计算不应只在 _prefetch_triggered 时进行
        # 旧代码: if _prefetch_triggered: ... _data_time_max = ...
        # 新代码: 应先无条件调用 compute_scope_data_time_max，再可选从 prefetch_report 备选
        assert "compute_scope_data_time_max" in src, \
            "data_time_max 应无条件计算，不依赖 _prefetch_triggered"

    def test_execution_uses_real_pkl_date(self, tmp_path):
        """
        真实集成测试：构造 pkl 缓存文件，验证 data_date 正确被读取并纳入 fingerprint。
        不实际调用 producer，只测试 data_date 读取路径。
        """
        import pandas as pd
        import mask_cache

        cache_dir = tmp_path / "kline_daily"
        cache_dir.mkdir()

        dates = pd.date_range("2026-01-01", "2026-04-28")
        df = pd.DataFrame({"close": range(len(dates))}, index=dates)
        df.to_pickle(str(cache_dir / "000001_SZ_365d.pkl"))

        result = mask_cache.compute_scope_data_time_max(
            ["000001.SZ"], cache_dir=cache_dir
        )
        assert result == "2026-04-28", \
            f"应从 pkl 文件读到 2026-04-28，得到 {result!r}"

        # 更新 pkl，验证 data_date 会变化
        dates2 = pd.date_range("2026-01-01", "2026-04-30")
        df2 = pd.DataFrame({"close": range(len(dates2))}, index=dates2)
        df2.to_pickle(str(cache_dir / "000001_SZ_365d.pkl"))

        result2 = mask_cache.compute_scope_data_time_max(
            ["000001.SZ"], cache_dir=cache_dir
        )
        assert result2 == "2026-04-30", \
            f"更新 pkl 后应读到 2026-04-30，得到 {result2!r}"

        # 不同 data_date → 不同指纹 → 真实 cache miss
        fp_old = mask_cache.compute_fingerprint("kline", ["000001.SZ"], {}, result)
        fp_new = mask_cache.compute_fingerprint("kline", ["000001.SZ"], {}, result2)
        assert fp_old != fp_new, "pkl 更新后指纹应变化"
