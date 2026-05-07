"""
test_phase1_producers.py — V6OP 阶段 1 Smoke Tests

验证 6 个核心能力模块可导入、结构正确、不碰网络。
所有测试离线，不发起真实 API 请求。
"""
import json
import os
import sys
from pathlib import Path

import pytest

# ── 路径 ──────────────────────────────────────────────────────────────
_TESTS_DIR    = Path(__file__).parent.resolve()
_PROJECT_ROOT = _TESTS_DIR.parent
_SCRIPTS_DIR  = _PROJECT_ROOT / "scripts"

for p in [str(_SCRIPTS_DIR), str(_SCRIPTS_DIR / "producers"),
          str(_SCRIPTS_DIR / "sources")]:
    if p not in sys.path:
        sys.path.insert(0, p)

_CACHE_DIR  = _PROJECT_ROOT / "var" / "cache" / "kline_daily"
_OUTPUT_DIR = _PROJECT_ROOT / "output" / "current"


# ════════════════════════════════════════════════════════════════════
#  1. SkillRegistry 测试
# ════════════════════════════════════════════════════════════════════

class TestSkillRegistry:
    def test_import(self):
        from skill_registry import SKILL_REGISTRY, get_skill, list_skills
        assert SKILL_REGISTRY

    def test_six_skills(self):
        from skill_registry import SKILL_REGISTRY
        assert len(SKILL_REGISTRY) == 6

    def test_skill_ids(self):
        from skill_registry import list_skills
        ids = set(list_skills())
        assert ids == {"wencai", "czsc", "smc", "kline", "wave", "landmine"}

    def test_landmine_negative(self):
        from skill_registry import get_skill
        s = get_skill("landmine")
        assert s is not None
        assert s["hit_semantics"] == "negative"

    def test_wencai_lightweight(self):
        from skill_registry import get_skill
        s = get_skill("wencai")
        assert s is not None
        assert s["is_lightweight"] is True

    def test_required_fields(self):
        from skill_registry import SKILL_REGISTRY
        required = {"skill_id", "skill_name", "producer_class", "hit_semantics",
                    "data_requirement", "is_lightweight", "params"}
        for s in SKILL_REGISTRY:
            assert required.issubset(s.keys()), f"{s['skill_id']} 缺少字段"


# ════════════════════════════════════════════════════════════════════
#  2. WencaiSource 测试（离线）
# ════════════════════════════════════════════════════════════════════

class TestWencaiSource:
    def test_import(self):
        from wencai_source import run, _load_env
        assert callable(run)

    def test_normalize_code_handles_plain_a_share_markets(self):
        from wencai_source import _normalize_code
        assert _normalize_code("600519") == "600519.SH"
        assert _normalize_code("000001") == "000001.SZ"
        assert _normalize_code("300750") == "300750.SZ"
        assert _normalize_code("430047") == "430047.BJ"

    def test_key_missing_returns_blocked(self, monkeypatch):
        monkeypatch.delenv("IWENCAI_API_KEY", raising=False)
        from wencai_source import run
        import importlib
        import wencai_source as ws
        # 保证 _load_env 不返回 key
        monkeypatch.setattr(ws, "_load_env", lambda: {})
        result = ws.run(query="测试", limit=10)
        assert result["status"] in (
            "key_missing", "blocked", "auth_failed",
            "empty_result", "network_error", "api_error", "error",
        )
        assert result["scope_codes"] == []

    def test_output_structure(self, monkeypatch):
        from wencai_source import _make_scope_json
        r = _make_scope_json("测试query", [], "key_missing", 10, 0.1)
        required = {"scope_id", "source", "status", "scope_codes", "scope_count",
                    "data_mode", "generated_at"}
        assert required.issubset(r.keys())

    def test_no_key_no_network(self, monkeypatch):
        import wencai_source as ws
        monkeypatch.setattr(ws, "_load_env", lambda: {})
        monkeypatch.delenv("IWENCAI_API_KEY", raising=False)
        result = ws.run(query="近20日涨幅小于10%", limit=5)
        assert result["scope_codes"] == []

    def test_query_wencai_paginates_to_limit(self, monkeypatch):
        import types
        import wencai_source as ws

        calls = []

        def fake_get(query, query_type, perpage, page):
            calls.append({"perpage": perpage, "page": page})
            start = (page - 1) * perpage
            return [{"股票代码": f"{start + i:06d}.SZ"} for i in range(perpage)]

        monkeypatch.setitem(sys.modules, "pywencai", types.SimpleNamespace(get=fake_get))
        codes, status = ws._query_wencai("测试", "fake-key", 250)
        assert status == "ok"
        assert len(codes) == 250
        assert [c["page"] for c in calls] == [1, 2, 3]
        assert all(c["perpage"] == 100 for c in calls)


# ════════════════════════════════════════════════════════════════════
#  2b. SectorScanSource 测试（离线）
# ════════════════════════════════════════════════════════════════════

class TestSectorScanSource:
    def test_extract_sector_names_handles_index_short_name(self):
        import sector_scan_source as ss
        rows = [
            {"指数代码": "881281.TI", "指数简称": "电池"},
            {"指数代码": "881271.TI", "指数简称": "IT服务"},
        ]
        assert ss._extract_sector_names(rows, 2) == ["电池", "IT服务"]

    def test_rows_from_dict_dataframe_like_value(self):
        import sector_scan_source as ss

        class FakeFrame:
            def to_dict(self, orient):
                assert orient == "records"
                return [{"指数简称": "电力"}]

        assert ss._rows_from_pywencai_result({"title_content": FakeFrame()}) == [
            {"指数简称": "电力"}
        ]

    def test_scan_falls_back_to_zhishu_when_sector_has_no_names(self, monkeypatch):
        import types
        import sector_scan_source as ss

        calls = []

        def fake_get(query, query_type, perpage, page):
            calls.append(query_type)
            if query_type == "sector":
                return {"title_content": [{"uid": "x", "jumpUrl": "https://example.com"}]}
            return [{"指数简称": "电池"}, {"指数简称": "IT服务"}]

        monkeypatch.setattr(ss, "_load_env", lambda: {"IWENCAI_API_KEY": "fake"})
        monkeypatch.setitem(sys.modules, "pywencai", types.SimpleNamespace(get=fake_get))

        result = ss.scan("今日主力资金净流入排名前十的行业板块", top_n=2)
        assert result["error"] is None
        assert result["sectors"] == ["电池", "IT服务"]
        assert result["query_types_tried"] == ["sector", "zhishu"]


# ════════════════════════════════════════════════════════════════════
#  3. SMCProducer 测试
# ════════════════════════════════════════════════════════════════════

class TestSMCProducer:
    def test_import(self):
        from smc_producer import run, _make_mask_id
        assert callable(run)

    def test_mask_id_stable(self):
        from smc_producer import _make_mask_id
        codes = ["000001.SZ", "600519.SH"]
        p = {"signal_bars": 15, "swing_length": 10, "mode": "soft_filter", "days": 365}
        id1 = _make_mask_id(codes, p)
        id2 = _make_mask_id(codes, p)
        assert id1 == id2
        assert id1.startswith("smc_")

    def test_output_structure_blocked(self):
        from smc_producer import run
        os.environ["READ_CACHE_ONLY"] = "true"
        result = run(codes=[], cache_dir=_CACHE_DIR)
        assert "mask_id" in result
        assert "hit_codes" in result
        assert "miss_codes" in result
        assert result["hit_semantics"] == "positive"
        assert result["data_mode"] == "read_cache_only"
        assert result.get("adjust") == "hfq"

    @pytest.mark.skipif(not _CACHE_DIR.exists(), reason="缓存目录不存在")
    def test_run_with_cache(self):
        from smc_producer import run
        cached_codes = [p.stem.upper() for p in list(_CACHE_DIR.glob("*.pkl"))[:5]]
        if not cached_codes:
            pytest.skip("无缓存文件")
        result = run(codes=cached_codes, cache_dir=_CACHE_DIR)
        assert "hit_codes" in result
        assert "evidence" in result
        assert result["data_mode"] == "read_cache_only"


# ════════════════════════════════════════════════════════════════════
#  4. KlineProducer 测试
# ════════════════════════════════════════════════════════════════════

class TestKlineProducer:
    def test_import(self):
        from kline_producer import run, _make_mask_id
        assert callable(run)

    def test_mask_id_stable(self):
        from kline_producer import _make_mask_id
        codes = ["000001.SZ"]
        p = {"signal_bars": 5, "body_pct": 0.1, "shadow_ratio": 2.0, "days": 365}
        assert _make_mask_id(codes, p) == _make_mask_id(codes, p)
        assert _make_mask_id(codes, p).startswith("kline_")

    def test_empty_input(self):
        from kline_producer import run
        result = run(codes=[], cache_dir=_CACHE_DIR)
        assert result["hit_codes"] == []
        assert result["miss_codes"] == []
        assert result["hit_semantics"] == "positive"
        assert result.get("adjust") == "hfq"

    @pytest.mark.skipif(not _CACHE_DIR.exists(), reason="缓存目录不存在")
    def test_run_with_cache(self):
        from kline_producer import run
        cached_codes = [p.stem.upper() for p in list(_CACHE_DIR.glob("*.pkl"))[:5]]
        if not cached_codes:
            pytest.skip("无缓存文件")
        result = run(codes=cached_codes, cache_dir=_CACHE_DIR)
        assert "hit_codes" in result
        assert "evidence" in result
        assert result["data_mode"] == "read_cache_only"


# ════════════════════════════════════════════════════════════════════
#  5. WaveProducer 测试
# ════════════════════════════════════════════════════════════════════

class TestWaveProducer:
    def test_import(self):
        from wave_producer import run, _find_swings
        assert callable(run)
        assert callable(_find_swings)

    def test_empty_input(self):
        from wave_producer import run
        result = run(codes=[], cache_dir=_CACHE_DIR)
        assert result["hit_codes"] == []
        assert result["hit_semantics"] == "positive"
        assert result.get("adjust") == "hfq"

    def test_mask_id_prefix(self):
        from wave_producer import _make_mask_id
        assert _make_mask_id(["000001.SZ"], {}).startswith("wave_")

    @pytest.mark.skipif(not _CACHE_DIR.exists(), reason="缓存目录不存在")
    def test_run_with_cache(self):
        from wave_producer import run
        cached_codes = [p.stem.upper() for p in list(_CACHE_DIR.glob("*.pkl"))[:5]]
        if not cached_codes:
            pytest.skip("无缓存文件")
        result = run(codes=cached_codes, cache_dir=_CACHE_DIR)
        assert "evidence" in result
        assert result["data_mode"] == "read_cache_only"


# ════════════════════════════════════════════════════════════════════
#  6. LandmineProducer 测试
# ════════════════════════════════════════════════════════════════════

class TestLandmineProducer:
    def test_import(self):
        from landmine_producer import run, _load_prefetch_failures
        assert callable(run)
        assert callable(_load_prefetch_failures)

    def test_negative_semantics(self):
        from landmine_producer import run
        result = run(codes=[], cache_dir=_CACHE_DIR)
        assert result["hit_semantics"] == "negative"

    def test_known_unavailable_flagged(self):
        """V6OP-003: 已知不可用代码通过动态 prefetch_report 加载，BJ 代码仍被直接识别。"""
        from landmine_producer import run
        # BJ 交所代码始终被检测到（规则 1 不依赖 prefetch_report）
        bj_codes = ["430047.BJ", "832027.BJ", "430399.BJ"]
        result = run(codes=bj_codes, cache_dir=_CACHE_DIR)
        for code in bj_codes:
            assert code in result["hit_codes"], f"{code} 应被排雷命中（北交所）"

    def test_bj_code_flagged(self):
        from landmine_producer import run
        codes = ["430047.BJ"]
        result = run(codes=codes, cache_dir=_CACHE_DIR)
        assert "430047.BJ" in result["hit_codes"]

    def test_adjust_field(self):
        from landmine_producer import run
        result = run(codes=[], cache_dir=_CACHE_DIR)
        assert result.get("adjust") == "hfq"


# ════════════════════════════════════════════════════════════════════
#  7. run_core_producers 模块可导入
# ════════════════════════════════════════════════════════════════════

class TestRunCoreProducers:
    def test_import(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "run_core_producers",
            _SCRIPTS_DIR / "run_core_producers.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "main")

    def test_skill_registry_covers_producers(self):
        from skill_registry import SKILL_REGISTRY
        producer_skill_ids = {"czsc", "smc", "kline", "wave", "landmine"}
        registry_ids = {s["skill_id"] for s in SKILL_REGISTRY}
        assert producer_skill_ids.issubset(registry_ids)


# ════════════════════════════════════════════════════════════════════
#  8. V5 / V6 隔离验证
# ════════════════════════════════════════════════════════════════════

class TestPhase1Isolation:
    def test_no_v5_imports_in_smc(self):
        src = (Path(_SCRIPTS_DIR) / "producers" / "smc_producer.py").read_text(encoding="utf-8")
        assert "from shared_data" not in src
        assert "utils.code_list" not in src

    def test_no_v5_imports_in_kline(self):
        src = (Path(_SCRIPTS_DIR) / "producers" / "kline_producer.py").read_text(encoding="utf-8")
        assert "from shared_data" not in src

    def test_no_v5_imports_in_wave(self):
        src = (Path(_SCRIPTS_DIR) / "producers" / "wave_producer.py").read_text(encoding="utf-8")
        assert "from shared_data" not in src

    def test_no_v5_imports_in_landmine(self):
        src = (Path(_SCRIPTS_DIR) / "producers" / "landmine_producer.py").read_text(encoding="utf-8")
        assert "from shared_data" not in src

    def test_env_not_hardcoded_in_source(self):
        """验证源码中没有硬编码的 API key 值。"""
        import re
        fake_key_pattern = re.compile(r'(?:api_key|secret)\s*=\s*["\'][a-zA-Z0-9]{20,}["\']', re.I)
        for py_file in (_SCRIPTS_DIR).rglob("*.py"):
            src = py_file.read_text(encoding="utf-8", errors="replace")
            assert not fake_key_pattern.search(src), f"{py_file} 疑似硬编码 key"


# ════════════════════════════════════════════════════════════════════
#  V6OP-018: LandmineProducer stale/failed 语义验收
# ════════════════════════════════════════════════════════════════════

class TestV6OP018LandmineStale:
    """V6OP-018: failed_codes 仍被排雷；stale_codes 不因 stale 被排雷。"""

    def test_failed_code_hits_landmine(self, tmp_path):
        """failed_codes 必须被 landmine 排雷命中（不可用 = 负向）。"""
        from landmine_producer import run, _load_prefetch_failures
        report = {
            "failed_codes": [{"code": "430047.BJ", "error": "baostock_timeout"}],
            "stale_codes": [],
        }
        report_path = tmp_path / "prefetch_report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")

        failures = _load_prefetch_failures(report_path)
        assert "430047.BJ" in failures, "failed_codes 应在 _load_prefetch_failures 返回集合中"

        result = run(
            codes=["430047.BJ"],
            cache_dir=_CACHE_DIR,
            prefetch_report_path=report_path,
        )
        assert "430047.BJ" in result["hit_codes"], \
            "failed_codes 中的代码应被排雷命中"

    def test_stale_code_not_hit_by_landmine(self, tmp_path):
        """stale_codes 有旧缓存可分析，不得仅因 stale 进入 hit_codes。"""
        import json as _json
        from landmine_producer import run, _load_prefetch_failures

        # 从本地缓存取一只有数据的代码
        pkls = sorted(_CACHE_DIR.glob("*.pkl")) if _CACHE_DIR.exists() else []
        if not pkls:
            pytest.skip("无缓存文件，跳过 stale 语义验收")
        stem = pkls[0].stem  # "000001_SZ_365d"
        parts = stem.split("_")
        code = f"{parts[0]}.{parts[1]}" if len(parts) >= 2 else None
        if not code:
            pytest.skip("无法解析缓存文件名")

        report = {"failed_codes": [], "stale_codes": [code]}
        report_path = tmp_path / "prefetch_report.json"
        report_path.write_text(_json.dumps(report), encoding="utf-8")

        failures = _load_prefetch_failures(report_path)
        assert code not in failures, \
            f"{code} 仅在 stale_codes，不应出现在 _load_prefetch_failures 返回集合"

        result = run(
            codes=[code],
            cache_dir=_CACHE_DIR,
            prefetch_report_path=report_path,
        )
        # stale 代码有缓存：如果 K 线足够，不应被排雷命中
        if code in result["hit_codes"]:
            reasons = result.get("evidence", {}).get(code, {}).get("reasons", [])
            stale_reason = any("stale" in r.lower() for r in reasons)
            assert not stale_reason, \
                f"{code} 不应因 stale 被排雷，但 reasons={reasons}"
