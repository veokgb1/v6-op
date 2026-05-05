"""
test_v6op024_mega_pack.py — V6OP-024 第一阶段总收口大包验证

覆盖 6 个大项的机器可检测验收点：
1. 技能 catalog：6 live（含 wencai），declared_total=27，missing_assets=5
2. Mask cache：SHA256，ALGO_VERSION 来自 producer 模块
3. V6 资产对齐：v6_asset_alignment.py 可运行，输出矩阵
4. Fetch Planner：data_requirement 驱动，不硬编码 _KLINE_SKILLS
5. readiness=aborted → Producer 不执行
6. strategy_graph_builder：execution_plan + topological_order 存在
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_ROOT    = Path(__file__).parent.parent.resolve()
_SCRIPTS = _ROOT / "scripts"

sys.path.insert(0, str(_SCRIPTS))


# ══════════════════════════════════════════════════════════════════════
# 大项 1 — 技能 catalog：6 live（含 wencai）
# ══════════════════════════════════════════════════════════════════════

class TestSkillCatalog024:
    """V6OP-024：catalog 必须含 wencai，declared_total=27，missing_assets 5 条。"""

    @pytest.fixture(scope="class")
    def catalog(self):
        import skill_catalog
        return skill_catalog.get_catalog()

    def test_live_count_is_6(self, catalog):
        assert catalog["live_count"] == 6, \
            f"live_count 应为 6，当前 {catalog['live_count']}"

    def test_wencai_in_live(self, catalog):
        ids = {s["skill_id"] for s in catalog["live"]}
        assert "wencai" in ids, "wencai 应在 live 列表中"

    def test_wencai_v6_id(self, catalog):
        wencai = next((s for s in catalog["live"] if s["skill_id"] == "wencai"), None)
        assert wencai is not None
        assert wencai["v6_skill_id"] == "hithink-astock-selector"

    def test_declared_total_27(self, catalog):
        assert catalog["declared_total"] == 27

    def test_missing_asset_count_5(self, catalog):
        assert catalog["missing_asset_count"] == 5

    def test_missing_assets_is_list_of_5(self, catalog):
        assert isinstance(catalog["missing_assets"], list)
        assert len(catalog["missing_assets"]) == 5

    def test_gray_count_is_17(self, catalog):
        # 22 V6 cards - 5 mapped = 17 gray (hithink-astock-selector → wencai)
        assert catalog["gray_count"] == 17

    def test_hithink_astock_not_in_gray(self, catalog):
        gray_ids = {s["skill_id"] for s in catalog["gray"]}
        assert "hithink-astock-selector" not in gray_ids, \
            "hithink-astock-selector 已映射为 wencai，不应留在 gray 中"

    def test_v6_total_still_22(self, catalog):
        assert catalog["v6_total"] == 22


# ══════════════════════════════════════════════════════════════════════
# 大项 2 — Mask cache：SHA256 + producer ALGO_VERSION
# ══════════════════════════════════════════════════════════════════════

class TestMaskCacheSHA256:
    """fingerprint 必须为 SHA256（64 hex 字符）；ALGO_VERSION 来自 producer 模块。"""

    def test_fingerprint_is_sha256(self):
        import mask_cache
        fp = mask_cache.compute_fingerprint("kline", ["000001.SZ"], {"days": 365}, "2026-04-30")
        assert len(fp) == 64, f"fingerprint 应为 64 位 SHA256，当前 {len(fp)} 位"
        assert all(c in "0123456789abcdef" for c in fp), "fingerprint 应为小写 hex"

    def test_algo_version_from_producer_czsc(self):
        import mask_cache
        ver = mask_cache._get_algo_version("czsc")
        assert ver != "0.0.0", "czsc ALGO_VERSION 应在 producer 模块中定义"
        assert len(ver.split(".")) == 3, f"应为语义版本格式，得到 {ver!r}"

    def test_algo_version_from_producer_smc(self):
        import mask_cache
        ver = mask_cache._get_algo_version("smc")
        assert ver != "0.0.0"

    def test_algo_version_from_producer_kline(self):
        import mask_cache
        ver = mask_cache._get_algo_version("kline")
        assert ver != "0.0.0"

    def test_algo_version_from_producer_wave(self):
        import mask_cache
        ver = mask_cache._get_algo_version("wave")
        assert ver != "0.0.0"

    def test_algo_version_from_producer_landmine(self):
        import mask_cache
        ver = mask_cache._get_algo_version("landmine")
        assert ver != "0.0.0"

    def test_producer_modules_have_algo_version_constant(self):
        producer_modules = [
            "producers.czsc_producer",
            "producers.smc_producer",
            "producers.kline_producer",
            "producers.wave_producer",
            "producers.landmine_producer",
        ]
        import importlib
        for mod_path in producer_modules:
            mod = importlib.import_module(mod_path)
            assert hasattr(mod, "ALGO_VERSION"), \
                f"模块 {mod_path} 缺少 ALGO_VERSION 常量"
            assert isinstance(mod.ALGO_VERSION, str), \
                f"{mod_path}.ALGO_VERSION 应为字符串"

    def test_algo_version_change_causes_fingerprint_miss(self):
        import mask_cache
        codes = ["000001.SZ"]
        params = {"days": 365}
        fp1 = mask_cache.compute_fingerprint("kline", codes, params, "2026-04-30", algo_version="1.0.0")
        fp2 = mask_cache.compute_fingerprint("kline", codes, params, "2026-04-30", algo_version="1.0.1")
        assert fp1 != fp2, "algo_version 变化必须导致 fingerprint 不同"

    def test_scope_change_causes_miss(self):
        import mask_cache
        fp1 = mask_cache.compute_fingerprint("kline", ["000001.SZ"], {}, "2026-04-30")
        fp2 = mask_cache.compute_fingerprint("kline", ["000001.SZ", "000002.SZ"], {}, "2026-04-30")
        assert fp1 != fp2

    def test_data_date_change_causes_miss(self):
        import mask_cache
        fp1 = mask_cache.compute_fingerprint("kline", ["000001.SZ"], {}, "2026-04-29")
        fp2 = mask_cache.compute_fingerprint("kline", ["000001.SZ"], {}, "2026-04-30")
        assert fp1 != fp2

    def test_params_change_causes_miss(self):
        import mask_cache
        fp1 = mask_cache.compute_fingerprint("kline", ["000001.SZ"], {"days": 365}, "2026-04-30")
        fp2 = mask_cache.compute_fingerprint("kline", ["000001.SZ"], {"days": 180}, "2026-04-30")
        assert fp1 != fp2


# ══════════════════════════════════════════════════════════════════════
# 大项 3 — V6 资产对齐审计脚本
# ══════════════════════════════════════════════════════════════════════

class TestV6AssetAlignment:

    @pytest.fixture(scope="class")
    def alignment_mod(self):
        import v6_asset_alignment
        return v6_asset_alignment

    def test_script_importable(self, alignment_mod):
        assert hasattr(alignment_mod, "get_alignment_report")
        assert hasattr(alignment_mod, "ASSET_MATRIX")

    def test_covers_10_assets(self, alignment_mod):
        assert len(alignment_mod.ASSET_MATRIX) == 10, \
            f"应审计 10 个 V6 资产，当前 {len(alignment_mod.ASSET_MATRIX)}"

    def test_required_assets_present(self, alignment_mod):
        asset_names = {a["asset"] for a in alignment_mod.ASSET_MATRIX}
        required = {
            "contracts.py", "expression_runner.py", "mask_store.py",
            "io_utils.py", "universe_provider.py", "secret_masking.py",
            "live_recapture.py", "selection_condition.py",
            "mask_expression_executor.py", "report_group_summary.py",
        }
        missing = required - asset_names
        assert not missing, f"ASSET_MATRIX 缺少以下资产: {missing}"

    def test_each_asset_has_status(self, alignment_mod):
        valid_statuses = {"used_in_mainline", "adapted", "read_only_reference", "deferred_phase"}
        for item in alignment_mod.ASSET_MATRIX:
            assert item["status"] in valid_statuses, \
                f"{item['asset']} 的状态 {item['status']!r} 不在有效范围内"

    def test_report_runs_without_error(self, alignment_mod):
        report = alignment_mod.get_alignment_report()
        assert "assets" in report
        assert "status_summary" in report
        assert report["total_assets"] == 10

    def test_adapted_assets_include_contracts(self, alignment_mod):
        adapted = [a["asset"] for a in alignment_mod.ASSET_MATRIX if a["status"] == "adapted"]
        assert "contracts.py" in adapted, "contracts.py 应标记为 adapted（已接入 SHA256 指纹）"

    def test_adapted_assets_include_expression_runner(self, alignment_mod):
        adapted = [a["asset"] for a in alignment_mod.ASSET_MATRIX if a["status"] == "adapted"]
        assert "expression_runner.py" in adapted


# ══════════════════════════════════════════════════════════════════════
# 大项 4a — Fetch Planner：data_requirement 驱动
# ══════════════════════════════════════════════════════════════════════

class TestFetchPlannerDataRequirement:

    def test_no_hardcoded_kline_skills_set(self):
        src = (_SCRIPTS / "fetch_planner.py").read_text(encoding="utf-8")
        assert "_KLINE_SKILLS = frozenset" not in src, \
            "fetch_planner.py 不应再有 _KLINE_SKILLS 硬编码集合"

    def test_uses_get_kline_skills_function(self):
        src = (_SCRIPTS / "fetch_planner.py").read_text(encoding="utf-8")
        assert "_get_kline_skills" in src, \
            "fetch_planner.py 应有 _get_kline_skills() 函数（从 skill_registry 推导）"

    def test_kline_skills_from_registry(self):
        import fetch_planner
        kline_set = fetch_planner._get_kline_skills()
        assert "czsc" in kline_set, "skill_registry 中 czsc 的 data_requirement=kline_daily，应在集合中"
        assert "smc" in kline_set
        assert "kline" in kline_set
        assert "wave" in kline_set
        assert "landmine" in kline_set

    def test_wencai_not_in_kline_skills(self):
        import fetch_planner
        kline_set = fetch_planner._get_kline_skills()
        assert "wencai" not in kline_set, \
            "wencai 的 data_requirement=none，不应在 kline_skills 中"

    def test_plan_identifies_kline_correctly(self, tmp_path):
        import fetch_planner
        result = fetch_planner.plan(
            scope_codes=["000001.SZ"],
            selected_skills=["czsc", "wencai"],
            cache_dir=tmp_path / "cache",
        )
        assert result["kline_skills"] == ["czsc"], \
            "只有 czsc 需要 K 线，wencai 不需要"


# ══════════════════════════════════════════════════════════════════════
# 大项 4b — readiness=aborted → Producer 不执行
# ══════════════════════════════════════════════════════════════════════

class TestAbortedStopsProducer:
    """readiness=aborted 时必须中止 Producer 执行，返回 status=aborted。"""

    def _make_aborted_fetch(self):
        return {
            "readiness": "aborted",
            "failure_rate": 0.25,
            "cached_codes": [],
            "missing_codes": [],
            "failed_codes": ["000001.SZ", "000002.SZ", "000003.SZ"],
            "stale_codes": [],
            "available_codes": [],
            "prefetch_required": False,
            "prefetch_plan": {},
            "prefetch_report": {},
            "kline_skills": ["czsc"],
            "lookback_days": 365,
            "cache_dir": "/tmp/fake",
            "generated_at": "2026-05-05T00:00:00",
        }

    def test_aborted_returns_aborted_status(self, tmp_path, monkeypatch):
        import execution_engine

        monkeypatch.setattr(execution_engine, "_OUTPUT_ROOT", tmp_path)
        monkeypatch.setattr(execution_engine, "_MASK_CACHE_DIR", tmp_path / "mask_cache")

        # mock source resolver
        with patch("source_resolver.resolve", return_value={
            "status": "ok",
            "scope_codes": ["000001.SZ", "000002.SZ", "000003.SZ"],
            "scope_count": 3,
        }):
            with patch("fetch_planner.plan", return_value=self._make_aborted_fetch()):
                strategy = {
                    "source": {"type": "manual", "codes": ["000001.SZ"]},
                    "skills": ["czsc"],
                    "path_type": "parallel_and",
                    "params": {},
                }
                result = execution_engine.execute(strategy)

        assert result["status"] == "aborted", \
            f"readiness=aborted 时 execute() 应返回 status=aborted，得到 {result['status']}"

    def test_aborted_has_zero_producer_results(self, tmp_path, monkeypatch):
        import execution_engine

        monkeypatch.setattr(execution_engine, "_OUTPUT_ROOT", tmp_path)
        monkeypatch.setattr(execution_engine, "_MASK_CACHE_DIR", tmp_path / "mask_cache")

        with patch("source_resolver.resolve", return_value={
            "status": "ok",
            "scope_codes": ["000001.SZ", "000002.SZ", "000003.SZ"],
            "scope_count": 3,
        }):
            with patch("fetch_planner.plan", return_value=self._make_aborted_fetch()):
                strategy = {
                    "source": {"type": "manual", "codes": ["000001.SZ"]},
                    "skills": ["czsc"],
                    "path_type": "parallel_and",
                    "params": {},
                }
                result = execution_engine.execute(strategy)

        assert result["producer_results"] == [], \
            "aborted 时不应运行任何 Producer"

    def test_aborted_has_zero_final_hits(self, tmp_path, monkeypatch):
        import execution_engine

        monkeypatch.setattr(execution_engine, "_OUTPUT_ROOT", tmp_path)
        monkeypatch.setattr(execution_engine, "_MASK_CACHE_DIR", tmp_path / "mask_cache")

        with patch("source_resolver.resolve", return_value={
            "status": "ok",
            "scope_codes": ["000001.SZ", "000002.SZ", "000003.SZ"],
            "scope_count": 3,
        }):
            with patch("fetch_planner.plan", return_value=self._make_aborted_fetch()):
                strategy = {
                    "source": {"type": "manual", "codes": ["000001.SZ"]},
                    "skills": ["czsc"],
                    "path_type": "parallel_and",
                    "params": {},
                }
                result = execution_engine.execute(strategy)

        assert result["final_hit_count"] == 0
        assert result["final_hit_codes"] == []


# ══════════════════════════════════════════════════════════════════════
# 大项 4c — strategy_graph_builder：execution_plan + topological_order
# ══════════════════════════════════════════════════════════════════════

class TestGraphTopologicalPlan:

    def _registry(self):
        from skill_registry import SKILL_REGISTRY
        return {s["skill_id"]: s for s in SKILL_REGISTRY}

    def test_graph_has_execution_plan(self):
        from strategy_graph_builder import build
        graph = build(["czsc", "kline", "landmine"], self._registry(), "parallel_and")
        assert "execution_plan" in graph, "graph 应含 execution_plan 字段"
        assert isinstance(graph["execution_plan"], list)

    def test_graph_has_topological_order(self):
        from strategy_graph_builder import build
        graph = build(["czsc", "kline", "landmine"], self._registry(), "parallel_and")
        assert "topological_order" in graph
        assert isinstance(graph["topological_order"], list)

    def test_execution_plan_contains_all_skills(self):
        from strategy_graph_builder import build
        graph = build(["czsc", "kline"], self._registry(), "parallel_and")
        plan_ids = [n["node_id"] for n in graph["execution_plan"] if n.get("type") == "producer"]
        assert "czsc" in plan_ids
        assert "kline" in plan_ids

    def test_execution_plan_sequential_order(self):
        from strategy_graph_builder import build
        graph = build(["czsc", "kline"], self._registry(), "sequential")
        plan = graph["execution_plan"]
        # 第一个 producer 节点的 input_scope 应为 scope（从原始 scope 开始）
        pos_nodes = [n for n in plan if n.get("type") == "producer" and n.get("hit_semantics") == "positive"]
        assert pos_nodes[0]["input_scope"] == "scope"
        if len(pos_nodes) > 1:
            assert pos_nodes[1]["input_scope"] == "prev_hit"

    def test_topological_order_includes_merge(self):
        from strategy_graph_builder import build
        graph = build(["czsc"], self._registry(), "parallel_and")
        assert "merge" in graph["topological_order"]

    def test_topological_order_includes_exclude_when_negative(self):
        from strategy_graph_builder import build
        graph = build(["czsc", "landmine"], self._registry(), "parallel_and")
        assert "exclude" in graph["topological_order"]
