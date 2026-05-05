"""
test_v6op023_mask_cache.py — V6OP-023 Task 3 内容寻址 Mask 缓存验证

验证总纲第十章要求：
- fingerprint = skill_id + sorted(scope_codes) + sorted(params) + data_date + algo_version
- cache hit: 跳过 producer，返回缓存结果
- cache miss: 执行 producer，写入缓存
- params/data_date/algo_version 变化时 miss
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(_ROOT / "scripts"))

import mask_cache


# ══════════════════════════════════════════════════════════════════════
# TestMaskCacheFingerprint — 指纹计算
# ══════════════════════════════════════════════════════════════════════

class TestMaskCacheFingerprint:
    CODES = ["000001.SZ", "000002.SZ", "600000.SH"]
    PARAMS = {"signal_bars": 5, "days": 365}
    DATA_DATE = "2026-04-30"

    def test_deterministic(self):
        fp1 = mask_cache.compute_fingerprint("kline", self.CODES, self.PARAMS, self.DATA_DATE)
        fp2 = mask_cache.compute_fingerprint("kline", self.CODES, self.PARAMS, self.DATA_DATE)
        assert fp1 == fp2, "相同输入应产生相同 fingerprint"

    def test_code_order_independent(self):
        fp1 = mask_cache.compute_fingerprint("kline", self.CODES, self.PARAMS, self.DATA_DATE)
        fp2 = mask_cache.compute_fingerprint("kline", list(reversed(self.CODES)), self.PARAMS, self.DATA_DATE)
        assert fp1 == fp2, "代码顺序不影响 fingerprint"

    def test_different_skill_different_fp(self):
        fp_kline = mask_cache.compute_fingerprint("kline", self.CODES, self.PARAMS, self.DATA_DATE)
        fp_czsc  = mask_cache.compute_fingerprint("czsc",  self.CODES, self.PARAMS, self.DATA_DATE)
        assert fp_kline != fp_czsc, "不同 skill_id 的 fingerprint 应不同"

    def test_different_params_different_fp(self):
        fp1 = mask_cache.compute_fingerprint("kline", self.CODES, {"signal_bars": 5},  self.DATA_DATE)
        fp2 = mask_cache.compute_fingerprint("kline", self.CODES, {"signal_bars": 10}, self.DATA_DATE)
        assert fp1 != fp2, "参数变化应产生不同 fingerprint（cache miss）"

    def test_different_data_date_different_fp(self):
        fp1 = mask_cache.compute_fingerprint("kline", self.CODES, self.PARAMS, "2026-04-29")
        fp2 = mask_cache.compute_fingerprint("kline", self.CODES, self.PARAMS, "2026-04-30")
        assert fp1 != fp2, "data_date 变化应产生不同 fingerprint（cache miss）"

    def test_different_algo_version_different_fp(self):
        fp1 = mask_cache.compute_fingerprint("kline", self.CODES, self.PARAMS, self.DATA_DATE, "1.0.0")
        fp2 = mask_cache.compute_fingerprint("kline", self.CODES, self.PARAMS, self.DATA_DATE, "2.0.0")
        assert fp1 != fp2, "algo_version 变化应产生不同 fingerprint（cache miss）"

    def test_different_code_pool_different_fp(self):
        fp1 = mask_cache.compute_fingerprint("kline", ["000001.SZ"],            self.PARAMS, self.DATA_DATE)
        fp2 = mask_cache.compute_fingerprint("kline", ["000001.SZ", "000002.SZ"], self.PARAMS, self.DATA_DATE)
        assert fp1 != fp2, "代码池变化应产生不同 fingerprint（cache miss）"

    def test_returns_sha256_hex_string(self):
        fp = mask_cache.compute_fingerprint("kline", self.CODES, self.PARAMS, self.DATA_DATE)
        assert len(fp) == 64, f"fingerprint 应为 64 位 sha256 hex，得到 {len(fp)} 位"
        assert fp.isalnum(), "fingerprint 应为十六进制字符串"


# ══════════════════════════════════════════════════════════════════════
# TestMaskCacheGetPut — cache_get / cache_put
# ══════════════════════════════════════════════════════════════════════

class TestMaskCacheGetPut:
    CODES = ["300083.SZ", "688400.SH"]
    PARAMS = {"signal_bars": 5, "days": 365}
    DATA_DATE = "2026-04-30"
    SKILL = "kline"

    @pytest.fixture
    def fp(self):
        return mask_cache.compute_fingerprint(self.SKILL, self.CODES, self.PARAMS, self.DATA_DATE)

    @pytest.fixture
    def cache_dir(self, tmp_path):
        return tmp_path / "mask_cache"

    def test_miss_returns_none(self, fp, cache_dir):
        result = mask_cache.cache_get(fp, cache_dir=cache_dir)
        assert result is None, "缓存不存在时 cache_get 应返回 None"

    def test_put_then_get_hit(self, fp, cache_dir):
        data = {"hit_codes": ["300083.SZ"], "hit_count": 1, "miss_count": 1}
        mask_cache.cache_put(fp, data, cache_dir=cache_dir)
        result = mask_cache.cache_get(fp, cache_dir=cache_dir)
        assert result is not None, "cache_put 后 cache_get 应命中"
        assert result["mask_cache_hit"] is True, "命中结果应包含 mask_cache_hit=True"
        assert result["hit_count"] == 1

    def test_put_does_not_store_mask_cache_hit(self, fp, cache_dir):
        data = {"hit_codes": [], "mask_cache_hit": True}
        mask_cache.cache_put(fp, data, cache_dir=cache_dir)
        cache_file = cache_dir / f"{fp}.json"
        raw = json.loads(cache_file.read_text(encoding="utf-8"))
        assert "mask_cache_hit" not in raw, "缓存文件不应存储 mask_cache_hit 字段（避免循环）"

    def test_cache_dir_created(self, fp, cache_dir):
        assert not cache_dir.exists()
        mask_cache.cache_put(fp, {"hit_codes": []}, cache_dir=cache_dir)
        assert cache_dir.exists(), "cache_put 应自动创建缓存目录"


# ══════════════════════════════════════════════════════════════════════
# TestMaskCacheRunWithCache — run_with_cache 集成
# ══════════════════════════════════════════════════════════════════════

class TestMaskCacheRunWithCache:
    CODES = ["000001.SZ", "000002.SZ"]
    PARAMS = {"signal_bars": 5, "days": 365}
    DATA_TIME_MAX = "2026-04-30"
    SKILL = "kline"

    @pytest.fixture
    def cache_dir(self, tmp_path):
        return tmp_path / "mask_cache"

    def _mock_run(self, codes, **kwargs):
        return {"hit_codes": codes[:1], "miss_codes": codes[1:], "hit_count": 1, "miss_count": 1}

    def test_first_call_is_miss(self, cache_dir):
        calls = []
        def mock_fn(codes, **kw):
            calls.append(codes)
            return {"hit_codes": codes[:1], "hit_count": 1, "miss_count": len(codes)-1, "miss_codes": codes[1:]}

        result, was_hit = mask_cache.run_with_cache(
            skill_id=self.SKILL,
            scope_codes=self.CODES,
            params=self.PARAMS,
            data_time_max=self.DATA_TIME_MAX,
            run_fn=mock_fn,
            cache_dir=cache_dir,
        )
        assert was_hit is False, "首次调用应 cache miss"
        assert len(calls) == 1, "应调用一次 producer"

    def test_second_call_is_hit(self, cache_dir):
        calls = []
        def mock_fn(codes, **kw):
            calls.append(codes)
            return {"hit_codes": codes[:1], "hit_count": 1, "miss_count": len(codes)-1, "miss_codes": codes[1:]}

        mask_cache.run_with_cache(
            skill_id=self.SKILL, scope_codes=self.CODES, params=self.PARAMS,
            data_time_max=self.DATA_TIME_MAX, run_fn=mock_fn, cache_dir=cache_dir,
        )
        result, was_hit = mask_cache.run_with_cache(
            skill_id=self.SKILL, scope_codes=self.CODES, params=self.PARAMS,
            data_time_max=self.DATA_TIME_MAX, run_fn=mock_fn, cache_dir=cache_dir,
        )
        assert was_hit is True, "第二次调用应 cache hit"
        assert len(calls) == 1, "命中缓存时不应再次调用 producer"
        assert result["mask_cache_hit"] is True

    def test_param_change_causes_miss(self, cache_dir):
        calls = []
        def mock_fn(codes, **kw):
            calls.append(codes)
            return {"hit_codes": [], "hit_count": 0, "miss_count": len(codes), "miss_codes": codes}

        mask_cache.run_with_cache(
            skill_id=self.SKILL, scope_codes=self.CODES,
            params={"signal_bars": 5}, data_time_max=self.DATA_TIME_MAX,
            run_fn=mock_fn, cache_dir=cache_dir,
        )
        _, was_hit = mask_cache.run_with_cache(
            skill_id=self.SKILL, scope_codes=self.CODES,
            params={"signal_bars": 10}, data_time_max=self.DATA_TIME_MAX,
            run_fn=mock_fn, cache_dir=cache_dir,
        )
        assert was_hit is False, "参数变化应 cache miss"
        assert len(calls) == 2, "参数变化时应再次调用 producer"

    def test_data_date_change_causes_miss(self, cache_dir):
        calls = []
        def mock_fn(codes, **kw):
            calls.append(codes)
            return {"hit_codes": [], "hit_count": 0, "miss_count": len(codes), "miss_codes": codes}

        mask_cache.run_with_cache(
            skill_id=self.SKILL, scope_codes=self.CODES, params=self.PARAMS,
            data_time_max="2026-04-29", run_fn=mock_fn, cache_dir=cache_dir,
        )
        _, was_hit = mask_cache.run_with_cache(
            skill_id=self.SKILL, scope_codes=self.CODES, params=self.PARAMS,
            data_time_max="2026-04-30", run_fn=mock_fn, cache_dir=cache_dir,
        )
        assert was_hit is False, "data_time_max 变化应 cache miss"
        assert len(calls) == 2


# ══════════════════════════════════════════════════════════════════════
# TestMaskCacheAlgoVersions — 算法版本号
# ══════════════════════════════════════════════════════════════════════

class TestMaskCacheAlgoVersions:
    """ALGO_VERSION 现在定义在各 producer 模块内，通过 _get_algo_version() 动态读取。"""

    def test_all_live_skills_have_algo_version(self):
        live_skills = ["czsc", "smc", "kline", "wave", "landmine"]
        for skill in live_skills:
            ver = mask_cache._get_algo_version(skill)
            assert ver != "0.0.0", \
                f"技能 {skill} 的 ALGO_VERSION 未定义（返回 fallback '0.0.0'）"

    def test_versions_are_semver_format(self):
        live_skills = ["czsc", "smc", "kline", "wave", "landmine"]
        for skill in live_skills:
            ver = mask_cache._get_algo_version(skill)
            parts = ver.split(".")
            assert len(parts) == 3, f"{skill} 的 algo_version {ver!r} 不是语义版本"
            for p in parts:
                assert p.isdigit(), f"{skill} 的版本 {ver!r} 包含非数字部分"

    def test_algo_version_change_causes_miss(self):
        """显式传入不同 algo_version 时产生不同指纹。"""
        codes = ["000001.SZ"]
        params = {"days": 365}
        fp1 = mask_cache.compute_fingerprint("kline", codes, params, "2026-04-30", algo_version="1.0.0")
        fp2 = mask_cache.compute_fingerprint("kline", codes, params, "2026-04-30", algo_version="1.0.1")
        assert fp1 != fp2, "algo_version 变化应导致 fingerprint 不同（cache miss）"


# ══════════════════════════════════════════════════════════════════════
# TestMaskCacheIntegration — execution_engine 集成（结构检查）
# ══════════════════════════════════════════════════════════════════════

class TestMaskCacheIntegration:
    """验证 execution_engine.py 已集成 mask_cache 的关键代码片段。"""

    @pytest.fixture(scope="class")
    def engine_src(self):
        return (_ROOT / "scripts" / "execution_engine.py").read_text(encoding="utf-8")

    def test_mask_cache_imported(self, engine_src):
        assert "import mask_cache" in engine_src, \
            "execution_engine.py 应 import mask_cache"

    def test_mask_cache_compute_fingerprint_called(self, engine_src):
        assert "_mask_cache.compute_fingerprint" in engine_src, \
            "execution_engine.py 应调用 _mask_cache.compute_fingerprint"

    def test_mask_cache_get_called(self, engine_src):
        assert "_mask_cache.cache_get" in engine_src, \
            "execution_engine.py 应调用 _mask_cache.cache_get"

    def test_mask_cache_put_called(self, engine_src):
        assert "_mask_cache.cache_put" in engine_src, \
            "execution_engine.py 应调用 _mask_cache.cache_put"

    def test_mask_cache_hit_logged(self, engine_src):
        assert "mask_cache_hit=true" in engine_src, \
            "execution_engine.py 应在日志中记录 mask_cache_hit=true"

    def test_mask_cache_hits_in_execution_result(self, engine_src):
        assert "mask_cache_hits" in engine_src, \
            "execution_engine.py 应将 mask_cache_hits 写入 execution_result"

    def test_algo_version_dynamic_loading(self, engine_src):
        mc_src = _ROOT.joinpath("scripts", "mask_cache.py").read_text(encoding="utf-8")
        assert "_get_algo_version" in mc_src, \
            "mask_cache.py 应有 _get_algo_version() 函数（从 producer 模块动态读取）"
        assert "ALGO_VERSION" in mc_src, \
            "mask_cache.py 应引用 ALGO_VERSION（producer 模块常量）"

    def test_run_report_has_mask_cache_hits(self):
        src = (_ROOT / "scripts" / "run_report.py").read_text(encoding="utf-8")
        assert "mask_cache_hits" in src, \
            "run_report.py 应输出 mask_cache_hits 字段"
