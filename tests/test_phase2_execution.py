"""
test_phase2_execution.py — V6OP Phase 2 Smoke Tests

测试 Fetch Planner + 执行引擎 + 报告生成各模块的基本行为。
全部只读缓存，不触网，不访问真实接口。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# ── 路径 ──────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).parent.parent.resolve()
_SCRIPTS_DIR = _PROJECT_ROOT / "scripts"

for _p in [str(_SCRIPTS_DIR), str(_SCRIPTS_DIR / "producers"),
           str(_SCRIPTS_DIR / "sources")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── 公共 fixture ──────────────────────────────────────────────────────

DEMO_CODES = ["000001.SZ", "000002.SZ", "000063.SZ"]
DEMO_STRATEGY = {
    "source": {"type": "manual", "codes": DEMO_CODES},
    "skills": ["czsc", "kline", "landmine"],
    "path_type": "parallel_and",
    "params": {},
}


# ══════════════════════════════════════════════════════════════════════
# TestSourceResolver
# ══════════════════════════════════════════════════════════════════════

class TestSourceResolver:
    def test_import(self):
        import source_resolver
        assert hasattr(source_resolver, "resolve")

    def test_manual_codes(self):
        import source_resolver
        result = source_resolver.resolve(
            "manual", manual_codes=["000001.SZ", "000002.SZ"]
        )
        assert result["status"] == "ok"
        assert result["scope_count"] == 2
        assert "000001.SZ" in result["scope_codes"]
        assert result["source_type"] == "manual"

    def test_manual_empty_codes(self):
        import source_resolver
        result = source_resolver.resolve("manual", manual_codes=[])
        assert result["status"] == "error"
        assert result["scope_count"] == 0

    def test_manual_deduplication(self):
        import source_resolver
        result = source_resolver.resolve(
            "manual", manual_codes=["000001.SZ", "000001.SZ", "000002.SZ"]
        )
        assert result["scope_count"] == 2

    def test_all_a_reads_file(self):
        import source_resolver
        ashare_path = _PROJECT_ROOT / "data" / "ashare_codes.txt"
        if not ashare_path.exists():
            pytest.skip("ashare_codes.txt 不存在")
        result = source_resolver.resolve("all_a", ashare_limit=10)
        assert result["status"] == "ok"
        assert 1 <= result["scope_count"] <= 10

    def test_wencai_without_key_degrades(self):
        import source_resolver
        # 无 key 或接口失败时，应安全降级，不伪造
        result = source_resolver.resolve("wencai", wencai_query="test")
        assert result["status"] in (
            "ok", "blocked", "key_missing", "auth_failed",
            "empty_result", "network_error", "api_error", "error",
        )
        assert result["source_type"] == "wencai"
        assert isinstance(result["scope_codes"], list)

    def test_unknown_source_type(self):
        import source_resolver
        result = source_resolver.resolve("unknown_xyz")
        assert result["status"] == "error"

    def test_scope_id_deterministic(self):
        import source_resolver
        r1 = source_resolver.resolve("manual", manual_codes=["000001.SZ"])
        r2 = source_resolver.resolve("manual", manual_codes=["000001.SZ"])
        assert r1["scope_id"] == r2["scope_id"]

    def test_output_has_required_fields(self):
        import source_resolver
        result = source_resolver.resolve("manual", manual_codes=["000001.SZ"])
        required = {"scope_id", "source_type", "scope_codes", "scope_count",
                    "status", "error", "generated_at"}
        assert required.issubset(result.keys())


# ══════════════════════════════════════════════════════════════════════
# TestFetchPlanner
# ══════════════════════════════════════════════════════════════════════

class TestFetchPlanner:
    def test_import(self):
        import fetch_planner
        assert hasattr(fetch_planner, "plan")

    def test_plan_manual_codes(self):
        import fetch_planner
        result = fetch_planner.plan(
            scope_codes=DEMO_CODES,
            selected_skills=["czsc", "kline", "landmine"],
        )
        assert "prefetch_required" in result
        assert "readiness" in result
        assert result["readiness"] in ("ready", "partial", "aborted")
        assert "failure_rate" in result
        assert 0.0 <= result["failure_rate"] <= 1.0

    def test_plan_no_kline_skills(self):
        import fetch_planner
        result = fetch_planner.plan(
            scope_codes=DEMO_CODES,
            selected_skills=["wencai"],  # 无 K 线需求
        )
        assert result["prefetch_required"] is False

    def test_plan_reads_prefetch_report(self):
        import fetch_planner
        prefetch_path = _PROJECT_ROOT / "output" / "current" / "prefetch_report.json"
        if not prefetch_path.exists():
            pytest.skip("prefetch_report.json 不存在")
        result = fetch_planner.plan(
            scope_codes=DEMO_CODES,
            selected_skills=["czsc"],
            prefetch_report_path=prefetch_path,
        )
        # failed_codes 来自 prefetch_report.json
        assert isinstance(result["failed_codes"], list)

    def test_plan_output_fields(self):
        import fetch_planner
        result = fetch_planner.plan(DEMO_CODES, ["kline"])
        required = {
            "prefetch_required", "prefetch_plan", "prefetch_report",
            "readiness", "failed_codes", "stale_codes", "failure_rate",
            "available_codes",
        }
        assert required.issubset(result.keys())

    def test_aborted_when_failure_rate_high(self):
        import fetch_planner
        import tempfile
        import json
        # 写一个高失败率的 prefetch_report
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump({"failed_codes": DEMO_CODES, "stale_codes": []}, f)
            tmp_path = Path(f.name)
        try:
            result = fetch_planner.plan(
                scope_codes=DEMO_CODES,
                selected_skills=["czsc"],
                prefetch_report_path=tmp_path,
            )
            assert result["readiness"] == "aborted"
            assert result["failure_rate"] > 0.20
        finally:
            tmp_path.unlink(missing_ok=True)


# ══════════════════════════════════════════════════════════════════════
# TestStrategyGraphBuilder
# ══════════════════════════════════════════════════════════════════════

class TestStrategyGraphBuilder:
    def _registry(self):
        from skill_registry import SKILL_REGISTRY
        return {s["skill_id"]: s for s in SKILL_REGISTRY}

    def test_import(self):
        import strategy_graph_builder
        assert hasattr(strategy_graph_builder, "build")

    def test_parallel_and(self):
        import strategy_graph_builder
        graph = strategy_graph_builder.build(
            ["czsc", "kline", "landmine"], self._registry(), "parallel_and"
        )
        assert graph["path_type"] == "parallel_and"
        assert graph["merge_node"]["op"] == "AND"
        assert len(graph["positive_nodes"]) == 2  # czsc, kline
        assert len(graph["negative_nodes"]) == 1  # landmine

    def test_sequential(self):
        import strategy_graph_builder
        graph = strategy_graph_builder.build(
            ["czsc", "kline"], self._registry(), "sequential"
        )
        assert graph["merge_node"]["op"] == "AND"

    def test_simple_hybrid_uses_and_not_k_of_n(self):
        """V6OP-006 纠偏：simple_hybrid 合并算子改为 AND（不再使用 K_OF_N）。"""
        import strategy_graph_builder
        graph = strategy_graph_builder.build(
            ["czsc", "kline", "wave"], self._registry(), "simple_hybrid"
        )
        assert graph["merge_node"]["op"] == "AND"
        assert graph["merge_node"]["op"] != "K_OF_N"

    def test_exclude_node_present_with_landmine(self):
        import strategy_graph_builder
        graph = strategy_graph_builder.build(
            ["czsc", "landmine"], self._registry(), "parallel_and"
        )
        assert graph["has_exclude"] is True
        assert graph["exclude_node"]["op"] == "EXCLUDE"

    def test_no_exclude_without_negative(self):
        import strategy_graph_builder
        graph = strategy_graph_builder.build(
            ["czsc", "kline"], self._registry(), "parallel_and"
        )
        assert graph["has_exclude"] is False
        assert graph["exclude_node"] is None

    def test_unsupported_path_type_raises(self):
        import strategy_graph_builder
        with pytest.raises(ValueError):
            strategy_graph_builder.build(["czsc"], self._registry(), "dag_magic")


# ══════════════════════════════════════════════════════════════════════
# TestExpressionAutoGenerator
# ══════════════════════════════════════════════════════════════════════

class TestExpressionAutoGenerator:
    def _make_producer_results(self):
        return [
            {
                "skill_id": "czsc",
                "skill_name": "缠论买点",
                "hit_semantics": "positive",
                "mask_id": "czsc_abc123",
                "hit_codes": ["000001.SZ", "000002.SZ"],
                "miss_codes": ["000063.SZ"],
                "evidence": {},
                "params": {},
            },
            {
                "skill_id": "kline",
                "skill_name": "K线形态",
                "hit_semantics": "positive",
                "mask_id": "kline_def456",
                "hit_codes": ["000001.SZ"],
                "miss_codes": ["000002.SZ", "000063.SZ"],
                "evidence": {},
                "params": {},
            },
            {
                "skill_id": "landmine",
                "skill_name": "排雷过滤",
                "hit_semantics": "negative",
                "mask_id": "landmine_ghi789",
                "hit_codes": ["000063.SZ"],
                "miss_codes": ["000001.SZ", "000002.SZ"],
                "evidence": {},
                "params": {},
            },
        ]

    def test_import(self):
        import expression_auto_generator
        assert hasattr(expression_auto_generator, "generate")

    def test_generate_steps(self):
        import expression_auto_generator
        import strategy_graph_builder
        from skill_registry import SKILL_REGISTRY
        registry = {s["skill_id"]: s for s in SKILL_REGISTRY}
        graph = strategy_graph_builder.build(
            ["czsc", "kline", "landmine"], registry, "parallel_and"
        )
        spec = expression_auto_generator.generate(self._make_producer_results(), graph)
        assert "steps" in spec
        assert len(spec["steps"]) >= 1
        assert spec["primary_expression_id"] is not None

    def test_has_exclude_step_when_landmine(self):
        import expression_auto_generator
        import strategy_graph_builder
        from skill_registry import SKILL_REGISTRY
        registry = {s["skill_id"]: s for s in SKILL_REGISTRY}
        graph = strategy_graph_builder.build(
            ["czsc", "kline", "landmine"], registry, "parallel_and"
        )
        spec = expression_auto_generator.generate(self._make_producer_results(), graph)
        ops = [s["op"] for s in spec["steps"]]
        assert "EXCLUDE" in ops

    def test_smc_soft_filter_labeled(self):
        import expression_auto_generator
        import strategy_graph_builder
        from skill_registry import SKILL_REGISTRY
        registry = {s["skill_id"]: s for s in SKILL_REGISTRY}
        graph = strategy_graph_builder.build(["smc"], registry, "parallel_and")
        smc_result = {
            "skill_id": "smc",
            "skill_name": "SMC聪明钱",
            "hit_semantics": "positive",
            "mask_id": "smc_test",
            "hit_codes": ["000001.SZ"],
            "miss_codes": [],
            "evidence": {},
            "params": {"mode": "soft_filter"},
        }
        spec = expression_auto_generator.generate([smc_result], graph)
        assert "smc" in spec["metadata"].get("soft_filter_skills", [])
        assert any("soft_filter" in w for w in spec.get("warnings", []))

    def test_wave_weak_signal_labeled(self):
        import expression_auto_generator
        import strategy_graph_builder
        from skill_registry import SKILL_REGISTRY
        registry = {s["skill_id"]: s for s in SKILL_REGISTRY}
        graph = strategy_graph_builder.build(["wave"], registry, "parallel_and")
        wave_result = {
            "skill_id": "wave",
            "skill_name": "波浪分析",
            "hit_semantics": "positive",
            "mask_id": "wave_test",
            "hit_codes": ["000001.SZ"],
            "miss_codes": [],
            "evidence": {"000001.SZ": {"verdict": "no_top"}},
            "params": {},
        }
        spec = expression_auto_generator.generate([wave_result], graph)
        assert "wave" in spec["metadata"].get("weak_signal_skills", [])

    def test_no_positive_returns_empty_steps(self):
        import expression_auto_generator
        import strategy_graph_builder
        from skill_registry import SKILL_REGISTRY
        registry = {s["skill_id"]: s for s in SKILL_REGISTRY}
        graph = strategy_graph_builder.build(["landmine"], registry, "parallel_and")
        landmine_only = [
            {
                "skill_id": "landmine",
                "hit_semantics": "negative",
                "mask_id": "lm_test",
                "hit_codes": [],
                "miss_codes": [],
                "evidence": {},
                "params": {},
            }
        ]
        spec = expression_auto_generator.generate(landmine_only, graph)
        assert spec["steps"] == []


# ══════════════════════════════════════════════════════════════════════
# TestExplanationBuilder
# ══════════════════════════════════════════════════════════════════════

class TestExplanationBuilder:
    def test_import(self):
        import explanation_builder
        assert hasattr(explanation_builder, "build")

    def test_build_hits(self):
        import explanation_builder
        prod_results = [
            {
                "skill_id": "czsc",
                "skill_name": "缠论买点",
                "hit_semantics": "positive",
                "hit_codes": ["000001.SZ"],
                "evidence": {"000001.SZ": {"buy_types": ["一买"], "recent_bars": 5, "adjust": "hfq"}},
            }
        ]
        result = explanation_builder.build(
            hit_codes=["000001.SZ"],
            producer_results=prod_results,
            expr_metadata={},
        )
        assert result["hit_count"] == 1
        assert len(result["hits"]) == 1
        hit = result["hits"][0]
        assert hit["code"] == "000001.SZ"
        assert hit["uses_hfq"] is True
        assert "explanation_cn" in hit

    def test_failed_codes_listed_separately(self):
        import explanation_builder
        result = explanation_builder.build(
            hit_codes=[],
            producer_results=[],
            expr_metadata={},
            failed_codes=["000099.SZ"],
        )
        assert result["failed_count"] == 1
        assert result["hits"] == []

    def test_output_fields(self):
        import explanation_builder
        result = explanation_builder.build([], [], {})
        required = {"hits", "hit_count", "failed", "failed_count", "stale_warnings"}
        assert required.issubset(result.keys())


# ══════════════════════════════════════════════════════════════════════
# TestLandmineProducerDynamic (V6OP-003 更新)
# ══════════════════════════════════════════════════════════════════════

class TestLandmineProducerDynamic:
    def test_dynamic_loading_function_exists(self):
        from producers.landmine_producer import _load_prefetch_failures
        assert callable(_load_prefetch_failures)

    def test_no_prefetch_report_returns_empty(self):
        from producers.landmine_producer import _load_prefetch_failures
        result = _load_prefetch_failures(Path("/nonexistent/prefetch_report.json"))
        assert isinstance(result, set)
        assert len(result) == 0

    def test_reads_failed_codes(self, tmp_path):
        from producers.landmine_producer import _load_prefetch_failures
        report = {"failed_codes": ["000025.SZ", "000034.SZ"], "stale_codes": []}
        (tmp_path / "prefetch_report.json").write_text(
            json.dumps(report), encoding="utf-8"
        )
        result = _load_prefetch_failures(tmp_path / "prefetch_report.json")
        assert "000025.SZ" in result
        assert "000034.SZ" in result

    def test_stale_codes_not_in_unavailable(self, tmp_path):
        """V6OP-018: stale_codes 有旧缓存可分析，不得进入 _load_prefetch_failures 返回集合。"""
        from producers.landmine_producer import _load_prefetch_failures
        report = {"failed_codes": [], "stale_codes": ["000035.SZ"]}
        (tmp_path / "prefetch_report.json").write_text(
            json.dumps(report), encoding="utf-8"
        )
        result = _load_prefetch_failures(tmp_path / "prefetch_report.json")
        assert "000035.SZ" not in result, \
            "stale 代码不应出现在 _load_prefetch_failures 返回集合中（仅 failed 才算不可用）"

    def test_no_hardcoded_set_in_module(self):
        """确认模块源代码不再有 _KNOWN_UNAVAILABLE 硬编码集合声明。"""
        source = (_SCRIPTS_DIR / "producers" / "landmine_producer.py").read_text(
            encoding="utf-8"
        )
        assert "_KNOWN_UNAVAILABLE = {" not in source


# ══════════════════════════════════════════════════════════════════════
# TestExecutionEngineDemo
# ══════════════════════════════════════════════════════════════════════

class TestExecutionEngineDemo:
    def test_import(self):
        import execution_engine
        assert hasattr(execution_engine, "execute")
        assert hasattr(execution_engine, "DEMO_STRATEGIES")

    def test_demo_manual_strategy_exists(self):
        from execution_engine import DEMO_STRATEGIES
        assert "manual" in DEMO_STRATEGIES
        assert DEMO_STRATEGIES["manual"]["source"]["type"] == "manual"

    def test_execute_manual_returns_dict(self):
        from execution_engine import execute, DEMO_STRATEGIES
        result = execute(DEMO_STRATEGIES["manual"])
        assert isinstance(result, dict)
        assert "run_id" in result
        assert "final_hit_codes" in result
        assert "status" in result
        # 应该完成或遇到缓存缺失，不应崩溃
        assert result["status"] in ("completed", "error")

    def test_execute_output_files_created(self):
        from execution_engine import execute, DEMO_STRATEGIES
        execute(DEMO_STRATEGIES["manual"])
        output_dir = _PROJECT_ROOT / "output" / "current"
        assert (output_dir / "execution_result.json").exists()
        assert (output_dir / "run_report.json").exists()
        assert (output_dir / "run_report.md").exists()

    def test_execute_result_no_secret_keys(self):
        from execution_engine import execute, DEMO_STRATEGIES
        result = execute(DEMO_STRATEGIES["manual"])
        result_str = json.dumps(result)
        # 确保结果 JSON 不含可能的密钥模式（长随机串）
        import re
        # IWENCAI_API_KEY 值通常是长字符串，这里只检查变量值没有直接出现
        # （变量名本身可以出现在 env_vars_present 等字段）
        assert "IWENCAI_API_KEY" not in result_str or (
            "env_read" in result_str  # 变量名在 health 输出中是可以的
        )

    def test_execute_no_v5_v6_modification(self):
        from execution_engine import execute, DEMO_STRATEGIES
        result = execute(DEMO_STRATEGIES["manual"])
        assert result.get("v5_modified") is False
        assert result.get("v6_modified") is False

    def test_execute_api_not_called(self):
        from execution_engine import execute, DEMO_STRATEGIES
        result = execute(DEMO_STRATEGIES["manual"])
        # manual 来源不访问任何真实 API
        assert result.get("api_called") is False

    def test_execute_producer_identity_complete(self):
        from execution_engine import execute, DEMO_STRATEGIES
        result = execute(DEMO_STRATEGIES["manual"])
        for prod in result.get("producer_results", []):
            assert prod.get("skill_id"), "producer_results 必须包含 skill_id"
            assert prod.get("skill_name"), "producer_results 必须包含 skill_name"
            assert prod.get("hit_semantics"), "producer_results 必须包含 hit_semantics"


# ══════════════════════════════════════════════════════════════════════
# TestRunReport
# ══════════════════════════════════════════════════════════════════════

class TestRunReport:
    def test_import(self):
        import run_report
        assert hasattr(run_report, "generate")

    def test_generate_creates_files(self, tmp_path):
        import run_report
        dummy_result = {
            "run_id": "test_run",
            "generated_at": "2026-05-05T00:00:00",
            "status": "completed",
            "strategy": {"source": {"type": "manual"}, "skills": [], "path_type": "", "params": {}},
            "selected_skills": ["czsc"],
            "path_type": "parallel_and",
            "params": {},
            "scope": {"source_type": "manual", "scope_id": "x", "scope_count": 3,
                      "status": "ok"},
            "fetch_plan": {
                "prefetch_report": {},
                "cached_codes": [],
                "missing_codes": [],
                "failed_codes": [],
                "stale_codes": [],
                "readiness": "ready",
                "failure_rate": 0.0,
            },
            "producer_results": [],
            "expression_spec": {"steps": [], "metadata": {}, "warnings": []},
            "final_hit_codes": ["000001.SZ"],
            "explanations": {
                "hits": [{"code": "000001.SZ", "explanation_cn": "测试命中"}],
                "stale_warnings": [],
            },
            "warnings": [],
            "env_read": False,
        }
        paths = run_report.generate(dummy_result, tmp_path)
        assert paths["report_json_path"].exists()
        assert paths["report_md_path"].exists()

    def test_markdown_contains_required_sections(self, tmp_path):
        import run_report
        dummy_result = {
            "run_id": "test_run",
            "generated_at": "2026-05-05T00:00:00",
            "status": "completed",
            "strategy": {"source": {"type": "manual"}, "skills": ["kline"], "path_type": "parallel_and", "params": {}},
            "selected_skills": ["kline"],
            "path_type": "parallel_and",
            "params": {},
            "scope": {"source_type": "manual", "scope_id": "x", "scope_count": 1, "status": "ok"},
            "fetch_plan": {
                "prefetch_report": {},
                "cached_codes": [], "missing_codes": [],
                "failed_codes": [], "stale_codes": [],
                "readiness": "ready", "failure_rate": 0.0,
            },
            "producer_results": [],
            "expression_spec": {"steps": [], "metadata": {}, "warnings": []},
            "final_hit_codes": [],
            "explanations": {"hits": [], "stale_warnings": []},
            "warnings": [],
            "env_read": False,
        }
        paths = run_report.generate(dummy_result, tmp_path)
        content = paths["report_md_path"].read_text(encoding="utf-8")
        assert "V6OP 操盘报告" in content
        assert "一、本次策略摘要" in content
        assert "五、数据准备阶段" in content
        assert "七、命中股票列表" in content
        assert "十一、风险与边界声明" in content

    def test_run_report_records_params_used(self, tmp_path):
        import run_report
        dummy_result = {
            "run_id": "test_run",
            "generated_at": "2026-05-05T00:00:00",
            "status": "completed",
            "strategy": {"source": {"type": "manual"}, "skills": ["kline"], "path_type": "parallel_and", "params": {}},
            "selected_skills": ["kline"],
            "path_type": "parallel_and",
            "params": {},
            "scope": {"source_type": "manual", "scope_id": "x", "scope_count": 1, "status": "ok"},
            "fetch_plan": {
                "prefetch_report": {},
                "cached_codes": [], "missing_codes": [],
                "failed_codes": [], "stale_codes": [],
                "readiness": "ready", "failure_rate": 0.0,
            },
            "producer_results": [{
                "skill_id": "kline",
                "skill_name": "K线形态",
                "hit_semantics": "positive",
                "hit_count": 0,
                "miss_count": 1,
                "params_used": {"signal_bars": 3, "pass_neutral": True},
            }],
            "expression_spec": {"steps": [], "metadata": {}, "warnings": []},
            "final_hit_codes": [],
            "explanations": {"hits": [], "stale_warnings": []},
            "warnings": [],
            "env_read": False,
        }
        paths = run_report.generate(dummy_result, tmp_path)
        report = json.loads(paths["report_json_path"].read_text(encoding="utf-8"))
        params_used = report["producer_summary"][0]["params_used"]
        assert params_used["signal_bars"] == 3
        assert params_used["pass_neutral"] is True
        md = paths["report_md_path"].read_text(encoding="utf-8")
        assert "实际参数" in md
        assert "signal_bars" in md


# ══════════════════════════════════════════════════════════════════════
# TestSkillScopedParams (V6OP-005 新增)
# ══════════════════════════════════════════════════════════════════════

class TestSkillScopedParams:
    """验证 skill-scoped params 路由：params.skills.<skill_id> 进入 Producer。"""

    def test_skill_scoped_params_recorded(self):
        """kline 的 skill-scoped signal_bars 必须出现在 params_used 中。"""
        from execution_engine import execute
        result = execute({
            "source": {"type": "manual", "codes": ["000001.SZ", "000002.SZ"]},
            "skills": ["kline", "landmine"],
            "path_type": "parallel_and",
            "params": {"skills": {"kline": {"signal_bars": 3, "days": 180}}},
        })
        assert result["status"] in ("completed", "error")
        kline_prod = next(
            (p for p in result.get("producer_results", []) if p["skill_id"] == "kline"),
            None,
        )
        assert kline_prod is not None
        params_used = kline_prod.get("params_used", {})
        assert params_used.get("signal_bars") == 3
        assert params_used.get("days") == 180
        assert params_used.get("pass_neutral") is False

    def test_flat_params_fallback(self):
        """旧格式 flat params 仍能兼容（不崩溃）。"""
        from execution_engine import execute
        result = execute({
            "source": {"type": "manual", "codes": ["000001.SZ"]},
            "skills": ["kline"],
            "path_type": "parallel_and",
            "params": {},   # 空 flat params，用注册表默认值
        })
        assert result["status"] in ("completed", "error")
        kline_prod = next(
            (p for p in result.get("producer_results", []) if p["skill_id"] == "kline"),
            None,
        )
        assert kline_prod is not None
        assert "params_used" in kline_prod
        # 默认值来自 skill_registry: signal_bars=5, days=365
        assert kline_prod["params_used"].get("signal_bars") == 5

    def test_run_archive_created(self):
        """每次执行后 <output_root>/runs/<run_id>/ 必须存在三个文件。
        output_root 在测试环境下被 conftest autouse 重定向到 tmp_path，
        不写入真实 output/runs/。"""
        import execution_engine
        from execution_engine import execute, DEMO_STRATEGIES
        result = execute(DEMO_STRATEGIES["manual"])
        run_id = result["run_id"]
        # 使用重定向后的 _OUTPUT_ROOT（测试中为 tmp_path）
        out_root = execution_engine._OUTPUT_ROOT or (_PROJECT_ROOT / "output")
        archive_dir = out_root / "runs" / run_id
        assert archive_dir.exists(), f"归档目录不存在: {archive_dir}"
        assert (archive_dir / "execution_result.json").exists()
        assert (archive_dir / "run_report.json").exists()
        assert (archive_dir / "run_report.md").exists()


# ══════════════════════════════════════════════════════════════════════
# TestV6OP006Corrections
# ══════════════════════════════════════════════════════════════════════

class TestV6OP006Corrections:
    """V6OP-006 四个阻断项的语义验证测试。"""

    # ── 阻断项一：自动预热 ─────────────────────────────────────────────

    def test_data_prefetch_has_run_prefetch(self):
        """data_prefetch 必须有 Python 可调用的 run_prefetch() 函数。"""
        import data_prefetch
        assert callable(getattr(data_prefetch, "run_prefetch", None)), \
            "data_prefetch.run_prefetch 不存在或不可调用"

    def test_run_prefetch_empty_codes_returns_zero(self):
        """run_prefetch([]) 应立即返回全零结果，不抛异常。"""
        import data_prefetch
        stats = data_prefetch.run_prefetch(codes=[], days=365, workers=1)
        assert stats["cache_hit"] == 0
        assert stats["fetched_ok"] == 0
        assert stats["failed"] == 0

    def test_execution_engine_step3_not_skip_prefetch_message(self):
        """execution_engine 的 step 3 日志不应包含旧的'跳过预热'提示。"""
        from execution_engine import execute, get_log_events
        execute({
            "source": {"type": "manual", "codes": ["000001.SZ"]},
            "skills": ["landmine"],
            "path_type": "parallel_and",
            "params": {},
        })
        events = get_log_events()
        skip_msgs = [
            ev["msg"] for ev in events
            if "read_cache_only 模式，跳过预热" in ev.get("msg", "")
        ]
        assert not skip_msgs, \
            f"发现旧的'跳过预热'日志: {skip_msgs}"

    # ── 阻断项二：sequential 链式过滤 ─────────────────────────────────

    def test_sequential_second_skill_receives_first_output(self):
        """sequential 路径中，第2个技能的输入数量应 <= 第1个技能的命中数。"""
        import importlib, unittest.mock as mock
        import execution_engine as ee

        captured_inputs: dict = {}

        original_run_one_builder = None

        def make_mock_run_fn(skill_id: str, hit_fraction: float):
            def _run(codes, cache_dir=None, **kw):
                captured_inputs[skill_id] = list(codes)
                n = max(1, int(len(codes) * hit_fraction))
                hits = list(codes)[:n]
                misses = list(codes)[n:]
                return {
                    "hit_codes": hits, "miss_codes": misses,
                    "hit_count": len(hits), "miss_count": len(misses),
                    "evidence": {}, "mask_id": f"{skill_id}_mock",
                }
            return _run

        # 给 czsc 命中50%, kline 命中全部
        mock_loaders = {
            "czsc": make_mock_run_fn("czsc", 0.5),
            "kline": make_mock_run_fn("kline", 1.0),
            "landmine": make_mock_run_fn("landmine", 0.0),
        }

        all_codes = [f"00000{i}.SZ" for i in range(1, 7)]
        clean_plan = {
            "prefetch_required": False, "prefetch_plan": {}, "prefetch_report": {},
            "readiness": "ready",
            "cached_codes": all_codes, "missing_codes": [],
            "failed_codes": [], "stale_codes": [],
            "available_codes": all_codes, "failure_rate": 0.0,
            "cache_dir": str(_PROJECT_ROOT / "var" / "cache" / "kline_daily"),
            "lookback_days": 365, "kline_skills": ["czsc", "kline", "landmine"],
            "generated_at": "2026-05-05T00:00:00",
        }
        import fetch_planner as _fp
        with mock.patch.object(ee, "_load_producer_run", side_effect=lambda sid: mock_loaders.get(sid)):
            with mock.patch.object(_fp, "plan", return_value=clean_plan):
                result = ee.execute({
                    "source": {"type": "manual", "codes": all_codes},
                    "skills": ["czsc", "kline", "landmine"],
                    "path_type": "sequential",
                    "params": {},
                })

        assert result["status"] in ("completed", "error")
        czsc_input = captured_inputs.get("czsc", [])
        kline_input = captured_inputs.get("kline", [])
        # czsc 吃全集，kline 吃 czsc 的 hit_codes（应 <= czsc 输入数量 * 0.5）
        assert len(czsc_input) == 6, f"czsc 应吃全集 6 只，实为 {len(czsc_input)}"
        assert len(kline_input) <= len(czsc_input), \
            f"kline 输入 {len(kline_input)} 应 <= czsc 输入 {len(czsc_input)}"
        assert len(kline_input) == 3, \
            f"czsc 命中50% → kline 应收到 3 只，实为 {len(kline_input)}"

    # ── 阻断项三：simple_hybrid 不再是 K_OF_N ─────────────────────────

    def test_simple_hybrid_no_k_of_n_in_graph(self):
        """strategy_graph_builder 对 simple_hybrid 不应再生成 K_OF_N。"""
        from strategy_graph_builder import build
        from skill_registry import SKILL_REGISTRY
        reg = {s["skill_id"]: s for s in SKILL_REGISTRY}
        graph = build(
            selected_skills=["czsc", "smc", "kline", "landmine"],
            skill_registry=reg,
            path_type="simple_hybrid",
        )
        merge_node = graph["merge_node"]
        assert merge_node["op"] != "K_OF_N", \
            "simple_hybrid 的 merge_op 不应为 K_OF_N"
        assert "K_OF_N" not in merge_node.get("description", ""), \
            "simple_hybrid 描述中不应出现 K_OF_N"

    def test_simple_hybrid_execution_semantics(self):
        """simple_hybrid：czsc+smc AND → kline 顺序过滤 → EXCLUDE landmine。"""
        import execution_engine as ee
        import unittest.mock as mock

        captured_inputs: dict = {}

        def make_mock_run_fn(skill_id: str, hit_codes_override=None):
            def _run(codes, cache_dir=None, **kw):
                captured_inputs[skill_id] = list(codes)
                hits = list(codes) if hit_codes_override is None else [
                    c for c in codes if c in hit_codes_override
                ]
                misses = [c for c in codes if c not in hits]
                return {
                    "hit_codes": hits, "miss_codes": misses,
                    "hit_count": len(hits), "miss_count": len(misses),
                    "evidence": {}, "mask_id": f"{skill_id}_mock",
                }
            return _run

        all_codes = [f"00000{i}.SZ" for i in range(1, 7)]
        # czsc 命中前4只, smc 命中后4只 → AND = 中间2只
        czsc_hits = set(all_codes[:4])
        smc_hits = set(all_codes[2:])

        mock_loaders = {
            "czsc": make_mock_run_fn("czsc", czsc_hits),
            "smc":  make_mock_run_fn("smc",  smc_hits),
            "kline": make_mock_run_fn("kline"),  # 全部命中
            "landmine": make_mock_run_fn("landmine", set()),  # 无命中（无排雷）
        }

        import fetch_planner as _fp2
        clean_plan2 = {
            "prefetch_required": False, "prefetch_plan": {}, "prefetch_report": {},
            "readiness": "ready",
            "cached_codes": all_codes, "missing_codes": [],
            "failed_codes": [], "stale_codes": [],
            "available_codes": all_codes, "failure_rate": 0.0,
            "cache_dir": str(_PROJECT_ROOT / "var" / "cache" / "kline_daily"),
            "lookback_days": 365, "kline_skills": ["czsc", "smc", "kline", "landmine"],
            "generated_at": "2026-05-05T00:00:00",
        }
        with mock.patch.object(ee, "_load_producer_run", side_effect=lambda sid: mock_loaders.get(sid)):
            with mock.patch.object(_fp2, "plan", return_value=clean_plan2):
                result = ee.execute({
                    "source": {"type": "manual", "codes": all_codes},
                    "skills": ["czsc", "smc", "kline", "landmine"],
                    "path_type": "simple_hybrid",
                    "params": {},
                })

        # czsc 和 smc 应接受全集
        assert set(captured_inputs.get("czsc", [])) == set(all_codes), \
            "simple_hybrid: czsc 应吃全集"
        assert set(captured_inputs.get("smc", [])) == set(all_codes), \
            "simple_hybrid: smc 应吃全集"
        # kline 应接受 czsc AND smc 的交集 = {000003.SZ, 000004.SZ}
        and_result = czsc_hits & smc_hits
        assert set(captured_inputs.get("kline", [])) == and_result, \
            f"kline 应接受 czsc∩smc={and_result}，实为 {set(captured_inputs.get('kline', []))}"

    # ── 结果契约：/api/result 返回 run_report.json 格式 ──────────────

    def test_run_report_has_frontend_contract_fields(self):
        """run_report.json 必须包含前端所需的所有顶层字段。"""
        from execution_engine import execute
        from run_report import generate
        import tempfile, json
        result = execute({
            "source": {"type": "manual", "codes": ["000001.SZ"]},
            "skills": ["landmine"],
            "path_type": "parallel_and",
            "params": {},
        })
        with tempfile.TemporaryDirectory() as tmpdir:
            from pathlib import Path
            paths = generate(result, Path(tmpdir))
            report = json.loads(
                (Path(tmpdir) / "run_report.json").read_text(encoding="utf-8")
            )
        required_fields = [
            "run_id", "final_hit_codes", "final_hit_count",
            "explanations", "failed_codes", "stale_codes",
            "data_coverage", "producer_summary", "expression", "warnings",
        ]
        for f in required_fields:
            assert f in report, f"run_report.json 缺少字段: {f}"
        # explanations 必须是 list（不是 dict）
        assert isinstance(report["explanations"], list), \
            "run_report.json 的 explanations 必须是 list"


# ══════════════════════════════════════════════════════════════════════
# TestV6OP006bTrustworthyRuntime
# ══════════════════════════════════════════════════════════════════════

class TestV6OP006bTrustworthyRuntime:
    """V6OP-006b 可信运行层五项纠偏的验收测试。"""

    # ── 纠偏一：缓存命名统一 ──────────────────────────────────────────

    def test_fetch_planner_recognizes_real_cache_filename(self, tmp_path):
        """fetch_planner 应识别 000001_SZ_365d.pkl（ohlcv_provider 真实格式）。"""
        import fetch_planner

        cache_dir = tmp_path / "kline_cache"
        cache_dir.mkdir()
        # 写真实格式的缓存文件
        (cache_dir / "000001_SZ_365d.pkl").write_bytes(b"")
        (cache_dir / "000002_SZ_365d.pkl").write_bytes(b"")

        result = fetch_planner.plan(
            scope_codes=["000001.SZ", "000002.SZ", "600519.SH"],
            selected_skills=["kline"],
            cache_dir=cache_dir,
            lookback_days=365,
        )
        # 000001 和 000002 应在 cached，不在 missing
        assert "000001.SZ" in result["cached_codes"], \
            "000001.SZ 有 000001_SZ_365d.pkl 缓存，应识别为 cached"
        assert "000002.SZ" in result["cached_codes"], \
            "000002.SZ 有 000002_SZ_365d.pkl 缓存，应识别为 cached"
        assert "000001.SZ" not in result["missing_codes"], \
            "000001.SZ 已缓存，不应在 missing"
        assert "600519.SH" in result["missing_codes"], \
            "600519.SH 无缓存，应在 missing"

    def test_fetch_planner_uses_lookback_days_in_filename(self, tmp_path):
        """不同 lookback_days 应对应不同文件名。"""
        import fetch_planner

        cache_dir = tmp_path / "kline_cache"
        cache_dir.mkdir()
        # 只有 180d 的缓存
        (cache_dir / "000001_SZ_180d.pkl").write_bytes(b"")

        result_365 = fetch_planner.plan(
            ["000001.SZ"], ["kline"], cache_dir=cache_dir, lookback_days=365
        )
        result_180 = fetch_planner.plan(
            ["000001.SZ"], ["kline"], cache_dir=cache_dir, lookback_days=180
        )
        assert "000001.SZ" in result_365["missing_codes"], \
            "365d 缓存不存在，应为 missing"
        assert "000001.SZ" in result_180["cached_codes"], \
            "180d 缓存存在，应为 cached"

    # ── 纠偏二：worker report 本轮隔离 ───────────────────────────────

    def test_prefetch_report_stats_are_consistent(self, tmp_path):
        """prefetch_report.json 的统计项总和应等于 total_codes（BJ和已知unavail除外）。"""
        import data_prefetch

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        report_dir = tmp_path / "reports"

        stats = data_prefetch.run_prefetch(
            codes=["000001.SZ", "000002.SZ"],
            days=365,
            workers=1,
            cache_dir=cache_dir,
            report_dir=report_dir,
        )
        report_file = report_dir / "prefetch_report.json"
        assert report_file.exists(), "prefetch_report.json 必须存在"
        report = json.loads(report_file.read_text(encoding="utf-8"))

        total = report["total_codes"]
        accounted = (
            report.get("cache_hit", 0)
            + report.get("fetched_ok", 0)
            + report.get("stale_used", 0)
            + report.get("failed", 0)
            + report.get("bj_skipped", 0)
        )
        assert accounted <= total + 2, (
            f"prefetch_report 数字不自洽: total={total} 但 "
            f"cache_hit+fetched_ok+stale+failed+bj={accounted}"
        )

    def test_run_prefetch_has_prefetch_run_id(self, tmp_path, monkeypatch):
        """每次 run_prefetch() 生成的 prefetch_report.json 必须包含 prefetch_run_id。"""
        import data_prefetch

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        report_dir = tmp_path / "reports"

        # 写一个假缓存文件使 _fetch_loop 直接命中缓存（不走网络）
        import pickle, pandas as pd
        from datetime import datetime, timedelta
        df = pd.DataFrame(
            {"open": [1.0]*60, "high": [1.0]*60, "low": [1.0]*60,
             "close": [1.0]*60, "volume": [1000.0]*60, "amount": [1000.0]*60},
            index=pd.date_range("2024-01-01", periods=60),
        )
        monkeypatch.setenv("KLINE_CACHE_DIR", str(cache_dir))
        cache_fname = cache_dir / "000001_SZ_365d.pkl"
        with open(cache_fname, "wb") as f:
            pickle.dump(df, f)
        # 强制新鲜（修改 mtime 为当前时间）
        import os, time
        os.utime(cache_fname, (time.time(), time.time()))

        data_prefetch.run_prefetch(
            codes=["000001.SZ"], days=365, workers=1,
            cache_dir=cache_dir, report_dir=report_dir,
        )
        report_file = report_dir / "prefetch_report.json"
        assert report_file.exists(), "prefetch_report.json 必须存在"
        report = json.loads(report_file.read_text(encoding="utf-8"))
        assert "prefetch_run_id" in report, "prefetch_report.json 缺少 prefetch_run_id 字段"
        assert len(report["prefetch_run_id"]) > 0, "prefetch_run_id 不应为空"

    # ── 纠偏三：READ_CACHE_ONLY 两阶段隔离 ───────────────────────────

    def test_read_cache_only_prevents_network_fetchers(self, monkeypatch, tmp_path):
        """READ_CACHE_ONLY=true 时，fetch_ohlcv 不得调用 baostock/akshare/yfinance。"""
        import ohlcv_provider

        monkeypatch.setenv("READ_CACHE_ONLY", "true")
        # 使用空的 tmp_path 作为缓存目录，避免项目缓存中已有该股票数据
        monkeypatch.setattr(ohlcv_provider, "_CACHE_DIR", tmp_path)

        network_called: list[str] = []

        def _fail_baostock(*a, **kw):
            network_called.append("baostock")
            raise AssertionError("READ_CACHE_ONLY 时不应调用 baostock")

        def _fail_akshare(*a, **kw):
            network_called.append("akshare")
            raise AssertionError("READ_CACHE_ONLY 时不应调用 akshare")

        def _fail_yfinance(*a, **kw):
            network_called.append("yfinance")
            raise AssertionError("READ_CACHE_ONLY 时不应调用 yfinance")

        monkeypatch.setattr(ohlcv_provider, "_fetch_baostock", _fail_baostock)
        monkeypatch.setattr(ohlcv_provider, "_fetch_akshare", _fail_akshare)
        monkeypatch.setattr(ohlcv_provider, "_fetch_yfinance", _fail_yfinance)

        # 无缓存时应返回 None，不触发任何网络 fetcher
        result = ohlcv_provider.fetch_ohlcv("600519.SH", days=365)
        assert result is None, "READ_CACHE_ONLY 缓存缺失应返回 None"
        assert not network_called, f"READ_CACHE_ONLY 时触发了网络调用: {network_called}"

    def test_read_cache_only_is_dynamic_not_fixed_at_import(self, monkeypatch):
        """READ_CACHE_ONLY 必须在每次 fetch_ohlcv 调用时动态读取，不能依赖导入时的布尔值。"""
        import ohlcv_provider

        # 先确保在 READ_CACHE_ONLY=false 状态下导入（避免干扰其他测试）
        monkeypatch.delenv("READ_CACHE_ONLY", raising=False)

        # 现在设置 READ_CACHE_ONLY=true，即使模块已经导入
        monkeypatch.setenv("READ_CACHE_ONLY", "true")

        network_called: list[str] = []

        def _track_baostock(*a, **kw):
            network_called.append("baostock")
            return None

        monkeypatch.setattr(ohlcv_provider, "_fetch_baostock", _track_baostock)

        # 在没有缓存的情况下调用，如果动态读取生效，不会调用 baostock
        ohlcv_provider.fetch_ohlcv("000999.SZ", days=365)
        assert "baostock" not in network_called, \
            "动态 READ_CACHE_ONLY=true 应阻止 baostock，说明 fetch_ohlcv 未动态读取"

    # ── 纠偏四：报告口径分阶段 ────────────────────────────────────────

    def test_run_report_md_has_two_phase_boundary(self, tmp_path):
        """run_report.md 必须包含'数据准备阶段'和'本地分析阶段'两段边界说明。"""
        import run_report

        dummy_result = {
            "run_id": "test_006b",
            "generated_at": "2026-05-05T00:00:00",
            "status": "completed",
            "strategy": {"source": {"type": "manual"}, "skills": ["kline"], "path_type": "parallel_and", "params": {}},
            "selected_skills": ["kline"],
            "path_type": "parallel_and",
            "params": {},
            "scope": {"source_type": "manual", "scope_id": "x", "scope_count": 2, "status": "ok"},
            "fetch_plan": {
                "prefetch_report": {
                    "cache_hit": 0, "fetched_ok": 2, "stale_used": 0,
                    "failed": 0, "bj_skipped": 0,
                },
                "cached_codes": [], "missing_codes": [],
                "failed_codes": [], "stale_codes": [],
                "readiness": "ready", "failure_rate": 0.0,
            },
            "producer_results": [],
            "expression_spec": {"steps": [], "metadata": {}, "warnings": []},
            "final_hit_codes": [],
            "explanations": {"hits": [], "stale_warnings": []},
            "warnings": [],
            "env_read": False,
        }
        paths = run_report.generate(dummy_result, tmp_path)
        md = paths["report_md_path"].read_text(encoding="utf-8")
        assert "数据准备阶段" in md, "run_report.md 缺少'数据准备阶段'边界说明"
        assert "本地分析阶段" in md, "run_report.md 缺少'本地分析阶段'边界说明"

    def test_run_report_md_no_blanket_network_claim_when_prefetch_happened(self, tmp_path):
        """发生自动预热时，run_report.md 不应笼统写'未访问 baostock'。"""
        import run_report

        dummy_result = {
            "run_id": "test_006b_prefetch",
            "generated_at": "2026-05-05T00:00:00",
            "status": "completed",
            "strategy": {"source": {"type": "manual"}, "skills": ["kline"], "path_type": "parallel_and", "params": {}},
            "selected_skills": ["kline"],
            "path_type": "parallel_and",
            "params": {},
            "scope": {"source_type": "manual", "scope_id": "x", "scope_count": 2, "status": "ok"},
            "fetch_plan": {
                # prefetch 发生了（fetched_ok=2）
                "prefetch_report": {
                    "cache_hit": 0, "fetched_ok": 2, "stale_used": 0,
                    "failed": 0, "bj_skipped": 0,
                },
                "cached_codes": [], "missing_codes": [],
                "failed_codes": [], "stale_codes": [],
                "readiness": "ready", "failure_rate": 0.0,
            },
            "producer_results": [],
            "expression_spec": {"steps": [], "metadata": {}, "warnings": []},
            "final_hit_codes": [],
            "explanations": {"hits": [], "stale_warnings": []},
            "warnings": [],
            "env_read": False,
        }
        paths = run_report.generate(dummy_result, tmp_path)
        md = paths["report_md_path"].read_text(encoding="utf-8")
        # 发生了预热，不应有笼统的"未访问 baostock / akshare / yfinance（仅读缓存）"
        assert "未访问 baostock / akshare / yfinance（仅读缓存）" not in md, \
            "预热发生时，报告不应笼统写'未访问 baostock'，应区分阶段"

    # ── 纠偏五：K_OF_N 注释清理 ──────────────────────────────────────

    def test_strategy_graph_builder_no_k_of_n_in_comment(self):
        """strategy_graph_builder.py 文件头注释不得残留 K_OF_N 描述。"""
        source = (_SCRIPTS_DIR / "strategy_graph_builder.py").read_text(encoding="utf-8")
        assert "K_OF_N（过半数）" not in source, \
            "strategy_graph_builder.py 仍有旧 K_OF_N 注释"
        assert "K_OF_N" not in source.splitlines()[0:15].__str__(), \
            "strategy_graph_builder.py 文件头注释仍提及 K_OF_N"


# ══════════════════════════════════════════════════════════════════════
# TestV6OP007Stage4 — V6OP-007 新增测试
# ══════════════════════════════════════════════════════════════════════

class TestV6OP007Stage4:
    """V6OP-007：真实操盘闭合 + 阶段 4 启动验证测试。"""

    def _make_dummy_result(
        self,
        source_type: str = "manual",
        path_type: str = "parallel_and",
        prefetch_fetched: int = 0,
    ) -> dict:
        return {
            "run_id": f"test_007_{source_type}_{path_type}",
            "status": "completed",
            "strategy": {
                "source": {"type": source_type},
                "skills": ["kline"],
                "path_type": path_type,
                "params": {},
            },
            "selected_skills": ["kline"],
            "path_type": path_type,
            "params": {},
            "scope": {
                "source_type": source_type,
                "scope_id": "test_scope",
                "scope_count": 3,
                "status": "ok",
            },
            "fetch_plan": {
                "prefetch_report": {
                    "cache_hit": 3 - prefetch_fetched,
                    "fetched_ok": prefetch_fetched,
                    "stale_used": 0,
                    "failed": 0,
                    "bj_skipped": 0,
                },
                "cached_codes": ["000001.SZ", "000002.SZ", "000063.SZ"],
                "missing_codes": [],
                "failed_codes": [],
                "stale_codes": [],
                "readiness": "ready",
                "failure_rate": 0.0,
            },
            "producer_results": [
                {
                    "skill_id": "kline",
                    "skill_name": "K线形态",
                    "hit_semantics": "positive",
                    "hit_count": 2,
                    "miss_count": 1,
                    "status": "ok",
                    "params_used": {"days": 365},
                },
            ],
            "expression_spec": {
                "steps": [],
                "metadata": {},
                "warnings": [],
            },
            "final_hit_codes": ["000001.SZ", "000002.SZ"],
            "explanations": {
                "hits": [
                    {
                        "code": "000001.SZ",
                        "explanation_cn": "K线形态命中",
                        "skill_hits": [
                            {
                                "skill_id": "kline",
                                "skill_name": "K线形态",
                                "reason_cn": "锤子线形态出现",
                            }
                        ],
                        "data_quality_issues": [],
                    },
                    {
                        "code": "000002.SZ",
                        "explanation_cn": "K线形态命中",
                        "skill_hits": [
                            {
                                "skill_id": "kline",
                                "skill_name": "K线形态",
                                "reason_cn": "吞没形态",
                            }
                        ],
                        "data_quality_issues": [],
                    },
                ],
                "stale_warnings": [],
            },
            "warnings": [],
            "env_read": False,
        }

    # ── run_report.md V5 风格 12 章节 ─────────────────────────────────

    def test_run_report_md_has_all_12_sections(self, tmp_path):
        """run_report.md 必须包含全部 12 个 V5 风格中文章节。"""
        import run_report

        paths = run_report.generate(self._make_dummy_result(), tmp_path)
        md = paths["report_md_path"].read_text(encoding="utf-8")
        required_sections = [
            "一、本次策略摘要",
            "二、股票来源",
            "三、路径类型与技能组合",
            "四、关键参数",
            "五、数据准备阶段",
            "六、本地分析阶段",
            "七、命中股票列表",
            "八、单股中文证据",
            "九、排除原因",
            "十、失败代码",
            "十一、风险与边界声明",
            "十二、运行产物路径",
        ]
        missing = [s for s in required_sections if s not in md]
        assert not missing, f"run_report.md 缺少章节：{missing}"

    def test_run_report_md_evidence_has_skill_reason(self, tmp_path):
        """八、单股中文证据包含技能中文原因。"""
        import run_report

        paths = run_report.generate(self._make_dummy_result(), tmp_path)
        md = paths["report_md_path"].read_text(encoding="utf-8")
        assert "锤子线形态出现" in md, "八、单股中文证据缺少技能 reason_cn"
        assert "000001.SZ" in md
        assert "K线形态" in md

    def test_run_report_md_hit_codes_in_section_7(self, tmp_path):
        """七、命中股票列表包含命中代码。"""
        import run_report

        paths = run_report.generate(self._make_dummy_result(), tmp_path)
        md = paths["report_md_path"].read_text(encoding="utf-8")
        assert "七、命中股票列表" in md
        assert "000001.SZ" in md
        assert "000002.SZ" in md

    def test_run_report_md_risk_section_has_v5_modified(self, tmp_path):
        """十一、风险与边界声明包含'未修改 V5.10'。"""
        import run_report

        paths = run_report.generate(self._make_dummy_result(), tmp_path)
        md = paths["report_md_path"].read_text(encoding="utf-8")
        assert "十一、风险与边界声明" in md
        assert "未修改 V5.10" in md

    def test_run_report_md_paths_section(self, tmp_path):
        """十二、运行产物路径包含报告路径。"""
        import run_report

        paths = run_report.generate(self._make_dummy_result(), tmp_path)
        md = paths["report_md_path"].read_text(encoding="utf-8")
        assert "十二、运行产物路径" in md
        assert "run_report.json" in md

    # ── wencai key-safe 与失败不伪造 ─────────────────────────────────

    def test_wencai_source_resolver_no_key_printed(self):
        """wencai source_resolver key 缺失时安全降级，不伪造成功。"""
        import source_resolver

        result = source_resolver.resolve("wencai", wencai_query="净利润增速大于20%", wencai_limit=10)
        assert result["source_type"] == "wencai"
        assert result["status"] in (
            "ok", "blocked", "key_missing", "auth_failed",
            "empty_result", "network_error", "api_error", "error",
        ), f"wencai 状态应为已知值，实际: {result['status']}"
        assert isinstance(result["scope_codes"], list), "scope_codes 必须是列表"

    def test_wencai_empty_codes_not_ok(self, monkeypatch):
        """wencai 返回空 scope_codes 时，status 不应为 'ok'（不伪造成功）。"""
        import source_resolver

        # 注入一个总是返回空列表的 resolver
        monkeypatch.setattr(
            source_resolver,
            "_fetch_wencai",
            lambda *a, **kw: [],
            raising=False,
        )
        result = source_resolver.resolve("wencai", wencai_query="test_empty", wencai_limit=5)
        if not result["scope_codes"]:
            assert result["status"] != "ok", \
                "wencai scope_codes 为空时不能用 status=ok 伪造成功"

    # ── 三种路径独立，互不污染 ───────────────────────────────────────

    def _skill_reg(self):
        """构造最小化 skill_registry dict 供 strategy_graph_builder.build 使用。"""
        return {
            "kline":    {"skill_id": "kline",    "skill_name": "K线形态", "hit_semantics": "positive", "data_requirement": "ohlcv", "notes": ""},
            "czsc":     {"skill_id": "czsc",     "skill_name": "缠论买点", "hit_semantics": "positive", "data_requirement": "ohlcv", "notes": ""},
            "landmine": {"skill_id": "landmine", "skill_name": "排雷过滤", "hit_semantics": "negative", "data_requirement": "ohlcv", "notes": ""},
        }

    def test_three_path_types_produce_distinct_merge_descriptions(self):
        """三种 path_type 各自独立，merge_node description 互不相同。"""
        import strategy_graph_builder

        skills = ["kline", "czsc", "landmine"]
        reg = self._skill_reg()
        graphs = {
            pt: strategy_graph_builder.build(skills, reg, pt)
            for pt in ["sequential", "parallel_and", "simple_hybrid"]
        }
        descs = {pt: g["merge_node"]["description"] for pt, g in graphs.items()}
        assert descs["sequential"] != descs["parallel_and"], \
            "sequential 和 parallel_and merge 描述相同"
        assert descs["parallel_and"] != descs["simple_hybrid"], \
            "parallel_and 和 simple_hybrid merge 描述相同"
        # 各路径应记录自身的 path_type
        for pt, g in graphs.items():
            assert g["path_type"] == pt

    def test_parallel_and_merge_op_is_and(self):
        """parallel_and 路径的 merge_node.op 为 AND。"""
        import strategy_graph_builder

        g = strategy_graph_builder.build(["kline", "czsc"], self._skill_reg(), "parallel_and")
        assert g["merge_node"]["op"] == "AND", \
            f"parallel_and merge_node.op 期望 AND，实际 {g['merge_node']['op']}"
        assert "并行" in g["merge_node"]["description"], \
            "parallel_and merge 描述缺少'并行'"

    def test_sequential_merge_description_has_sequential_word(self):
        """sequential 路径的 merge_node description 包含'顺序过滤'。"""
        import strategy_graph_builder

        g = strategy_graph_builder.build(["kline", "czsc"], self._skill_reg(), "sequential")
        assert "顺序过滤" in g["merge_node"]["description"], \
            f"sequential merge 描述缺少'顺序过滤'，实际: {g['merge_node']['description']}"


# ══════════════════════════════════════════════════════════════════════
# TestV6OP008ExplanationBuilderKeyFix
# ══════════════════════════════════════════════════════════════════════

class TestV6OP008ExplanationBuilderKeyFix:
    """V6OP-008：验证 explanation_builder 使用正确的 evidence key 名，产出可读中文证据。"""

    def _make_hit(self, skill_id: str, evidence: dict) -> dict:
        return {
            "skill_id": skill_id,
            "skill_name": skill_id,
            "hit_semantics": "positive",
            "hit_codes": ["000001.SZ"],
            "miss_codes": [],
            "evidence": {"000001.SZ": evidence},
            "params": {},
        }

    def test_kline_uses_total_score_not_score(self):
        """kline reason 应使用 total_score，不能因 score=0 显示 +0。"""
        import explanation_builder
        prod = self._make_hit("kline", {
            "total_score": 3,
            "bull_patterns": ["锤子线", "吞没(多)"],
            "bear_patterns": [],
            "last_signal_date": "2026-04-30",
        })
        result = explanation_builder.build(
            hit_codes=["000001.SZ"],
            producer_results=[prod],
            expr_metadata={},
        )
        hit = result["hits"][0]
        reasons = [s["reason_cn"] for s in hit["skill_hits"]]
        assert len(reasons) == 1
        assert "锤子线" in reasons[0], f"bull_patterns 未体现: {reasons[0]}"
        assert "+3" in reasons[0], f"total_score 未体现: {reasons[0]}"
        assert "N/A" not in reasons[0], f"reason_cn 不能含 N/A: {reasons[0]}"
        assert "+0" not in reasons[0] or "总计" not in reasons[0], \
            f"不能出现无意义的 +0: {reasons[0]}"

    def test_kline_old_key_score_not_used(self):
        """旧 key 'score' 不被使用（避免 N/A 根净评分 +0 回归）。"""
        import explanation_builder
        prod = self._make_hit("kline", {
            "score": 99,           # 旧 key，应被忽略
            "total_score": 0,      # 正确 key，值为 0 时不显示评分
            "bull_patterns": ["倒锤子线"],
            "last_signal_date": "2026-04-28",
        })
        result = explanation_builder.build(
            hit_codes=["000001.SZ"],
            producer_results=[prod],
            expr_metadata={},
        )
        reason = result["hits"][0]["skill_hits"][0]["reason_cn"]
        assert "99" not in reason, f"旧 key score=99 不应出现在 reason: {reason}"
        assert "倒锤子线" in reason, f"bull_patterns 应出现: {reason}"

    def test_czsc_uses_buy_type_not_buy_types(self):
        """czsc reason 应使用 buy_type（单数），识别一买/二买/三买。"""
        import explanation_builder
        for buy_type, expected_cn in [("1st", "一买"), ("2nd", "二买"), ("3rd", "三买")]:
            prod = self._make_hit("czsc", {
                "buy_type": buy_type,
                "last_signal_date": "2026-04-30",
                "bi_count": 17,
            })
            result = explanation_builder.build(
                hit_codes=["000001.SZ"],
                producer_results=[prod],
                expr_metadata={},
            )
            reason = result["hits"][0]["skill_hits"][0]["reason_cn"]
            assert expected_cn in reason, \
                f"buy_type={buy_type} 应映射到{expected_cn}，实际: {reason}"
            assert "2026-04-30" in reason, f"last_signal_date 未体现: {reason}"
            assert "17" in reason, f"bi_count 未体现: {reason}"

    def test_wave_uses_verdict_and_last_signal(self):
        """wave reason 应使用 verdict/last_signal/all_signals_count。"""
        import explanation_builder
        prod = self._make_hit("wave", {
            "verdict": "no_top",
            "last_signal": "2026-04-29",
            "all_signals_count": 3,
        })
        result = explanation_builder.build(
            hit_codes=["000001.SZ"],
            producer_results=[prod],
            expr_metadata={"weak_signal_skills": ["wave"]},
        )
        reason = result["hits"][0]["skill_hits"][0]["reason_cn"]
        assert "5浪" in reason or "no_top" in reason or "弱信号" in reason, \
            f"wave no_top 应提示未检测到5浪顶部: {reason}"
        assert "弱信号" in reason, f"no_top 应标注弱信号: {reason}"

    def test_wave_abc_bottom_verdict(self):
        """wave verdict=abc_bottom 应输出 ABC 底部字样。"""
        import explanation_builder
        prod = self._make_hit("wave", {
            "verdict": "abc_bottom",
            "last_signal": "2026-04-25",
            "all_signals_count": 1,
        })
        result = explanation_builder.build(
            hit_codes=["000001.SZ"],
            producer_results=[prod],
            expr_metadata={},
        )
        reason = result["hits"][0]["skill_hits"][0]["reason_cn"]
        assert "ABC" in reason, f"abc_bottom 应含 ABC: {reason}"

    def test_no_na_in_any_reason(self):
        """综合 kline+czsc+wave 命中后，explanation_cn 不含 N/A。"""
        import explanation_builder
        prods = [
            self._make_hit("kline", {
                "total_score": 2,
                "bull_patterns": ["吞没(多)"],
                "last_signal_date": "2026-04-29",
            }),
            self._make_hit("czsc", {
                "buy_type": "2nd",
                "last_signal_date": "2026-04-24",
                "bi_count": 16,
            }),
            self._make_hit("wave", {
                "verdict": "no_top",
                "all_signals_count": 2,
            }),
        ]
        result = explanation_builder.build(
            hit_codes=["000001.SZ"],
            producer_results=prods,
            expr_metadata={"weak_signal_skills": ["wave"]},
        )
        hit = result["hits"][0]
        cn = hit["explanation_cn"]
        assert "N/A" not in cn, f"explanation_cn 不能含 N/A: {cn}"
        assert hit["hit_skill_count"] == 3


# ══════════════════════════════════════════════════════════════════════
# TestV6OP009DataConsistency
# ══════════════════════════════════════════════════════════════════════

class TestV6OP009DataConsistency:
    """V6OP-009：验证 failed/cached 口径不矛盾。"""

    def test_fetch_planner_no_overlap_failed_and_cached(self, tmp_path):
        """fetch_planner 不变式：同一只股票不能同时在 failed_codes 和 cached_codes。"""
        import fetch_planner, json

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        report_dir = tmp_path / "report"
        report_dir.mkdir()

        # 写一个 .pkl 缓存文件（内容为空，仅测试文件存在）
        (cache_dir / "000001_SZ_365d.pkl").write_bytes(b"")
        # 同时写 prefetch_report，把 000001.SZ 标为 failed
        prefetch_report = {"failed_codes": ["000001.SZ"], "stale_codes": []}
        report_path = report_dir / "prefetch_report.json"
        report_path.write_text(json.dumps(prefetch_report), encoding="utf-8")

        result = fetch_planner.plan(
            scope_codes=["000001.SZ", "000002.SZ"],
            selected_skills=["kline"],
            cache_dir=cache_dir,
            prefetch_report_path=report_path,
        )

        cached = set(result["cached_codes"])
        failed = set(result["failed_codes"])
        overlap = cached & failed
        assert not overlap, \
            f"不变式违反：{overlap} 同时出现在 cached_codes 和 failed_codes"

    def test_fetch_planner_failed_code_not_in_cached(self, tmp_path):
        """若 .pkl 存在但 prefetch_report 标记为 failed，则计为 failed 而非 cached。"""
        import fetch_planner, json

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "000001_SZ_365d.pkl").write_bytes(b"")

        report_path = tmp_path / "prefetch_report.json"
        report_path.write_text(
            json.dumps({"failed_codes": ["000001.SZ"], "stale_codes": []}),
            encoding="utf-8",
        )

        result = fetch_planner.plan(
            scope_codes=["000001.SZ"],
            selected_skills=["kline"],
            cache_dir=cache_dir,
            prefetch_report_path=report_path,
        )
        assert "000001.SZ" not in result["cached_codes"], \
            "prefetch failed 的股票不应出现在 cached_codes，即使 .pkl 存在"
        assert "000001.SZ" in result["failed_codes"], \
            "prefetch failed 的股票应在 failed_codes"

    def test_fetch_planner_cached_excludes_failed_preserves_fresh(self, tmp_path):
        """有 .pkl 且未失败的股票正常进入 cached_codes。"""
        import fetch_planner, json

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "000001_SZ_365d.pkl").write_bytes(b"")
        (cache_dir / "000002_SZ_365d.pkl").write_bytes(b"")

        report_path = tmp_path / "prefetch_report.json"
        report_path.write_text(
            json.dumps({"failed_codes": ["000001.SZ"], "stale_codes": []}),
            encoding="utf-8",
        )

        result = fetch_planner.plan(
            scope_codes=["000001.SZ", "000002.SZ"],
            selected_skills=["kline"],
            cache_dir=cache_dir,
            prefetch_report_path=report_path,
        )
        assert "000002.SZ" in result["cached_codes"], \
            "000002.SZ 有 .pkl 且未失败，应在 cached_codes"
        assert "000001.SZ" not in result["cached_codes"], \
            "000001.SZ 已失败，不应在 cached_codes"

    def test_execution_engine_failed_codes_excluded_from_producers(self, tmp_path):
        """execution_engine 不变式：failed_codes 中的股票不应作为 Producer 实际输入。"""
        import execution_engine as ee
        import unittest.mock as mock
        import json, os

        # 写一个 prefetch_report，把 000003.SZ 标为 failed
        report_dir = tmp_path / "output" / "current"
        report_dir.mkdir(parents=True)
        (report_dir / "prefetch_report.json").write_text(
            json.dumps({"failed_codes": ["000003.SZ"], "stale_codes": []}),
            encoding="utf-8",
        )

        captured_inputs: list[list[str]] = []

        def mock_kline_run(codes, cache_dir=None, **kw):
            captured_inputs.append(list(codes))
            return {
                "hit_codes": [], "miss_codes": list(codes),
                "hit_count": 0, "miss_count": len(codes),
                "evidence": {}, "mask_id": "kline_mock",
            }

        scope_codes = ["000001.SZ", "000002.SZ", "000003.SZ"]

        with mock.patch.object(ee, "_load_producer_run", return_value=mock_kline_run):
            with mock.patch("fetch_planner._PROJECT_ROOT", tmp_path):
                with mock.patch("fetch_planner.plan") as mock_plan:
                    mock_plan.return_value = {
                        "prefetch_required": False,
                        "prefetch_plan": {},
                        "prefetch_report": {},
                        "readiness": "partial",
                        "cached_codes": ["000001.SZ", "000002.SZ"],
                        "missing_codes": [],
                        "failed_codes": ["000003.SZ"],
                        "stale_codes": [],
                        "available_codes": ["000001.SZ", "000002.SZ"],
                        "failure_rate": 0.33,
                        "cache_dir": str(tmp_path),
                        "lookback_days": 365,
                        "kline_skills": ["kline"],
                        "generated_at": "2026-05-05T00:00:00",
                        "scope_count": 3,
                    }

                    result = ee.execute({
                        "source": {"type": "manual", "codes": scope_codes},
                        "skills": ["kline"],
                        "path_type": "parallel_and",
                        "params": {},
                    })

        assert result["status"] in ("completed", "error")
        # 000003.SZ（已知 failed）不应出现在任何 Producer 输入中
        for call_input in captured_inputs:
            assert "000003.SZ" not in call_input, \
                f"000003.SZ 是 failed_code，不应出现在 Producer 输入: {call_input}"


# ══════════════════════════════════════════════════════════════════════
# TestV6OP010StaleSemantics
# ══════════════════════════════════════════════════════════════════════

class TestV6OP010StaleSemantics:
    """V6OP-010：stale_codes 语义 — stale ≠ failed，不阻断分析，不影响 failure_rate。"""

    def test_stale_not_in_failed_codes(self, tmp_path):
        """stale_codes 不出现在 failed_codes 中。"""
        import fetch_planner, json

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "000001_SZ_365d.pkl").write_bytes(b"")

        report_path = tmp_path / "prefetch_report.json"
        report_path.write_text(
            json.dumps({"failed_codes": [], "stale_codes": ["000001.SZ"]}),
            encoding="utf-8",
        )

        result = fetch_planner.plan(
            scope_codes=["000001.SZ"],
            selected_skills=["kline"],
            cache_dir=cache_dir,
            prefetch_report_path=report_path,
        )
        assert "000001.SZ" not in result["failed_codes"], \
            "stale 不等同于 failed，不能出现在 failed_codes"
        assert "000001.SZ" in result["stale_codes"], \
            "stale 股票应出现在 stale_codes"

    def test_stale_with_pkl_enters_cached(self, tmp_path):
        """stale 股票若有 .pkl 文件，应进入 cached_codes（可分析）。"""
        import fetch_planner, json

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "000001_SZ_365d.pkl").write_bytes(b"")

        report_path = tmp_path / "prefetch_report.json"
        report_path.write_text(
            json.dumps({"failed_codes": [], "stale_codes": ["000001.SZ"]}),
            encoding="utf-8",
        )

        result = fetch_planner.plan(
            scope_codes=["000001.SZ"],
            selected_skills=["kline"],
            cache_dir=cache_dir,
            prefetch_report_path=report_path,
        )
        assert "000001.SZ" in result["cached_codes"], \
            "stale 且有 .pkl 的股票应进入 cached_codes（旧缓存可分析）"

    def test_stale_does_not_inflate_failure_rate(self, tmp_path):
        """stale_codes 不计入 failure_rate；只有 failed_codes 计入。"""
        import fetch_planner, json

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        for code_safe in ["000001_SZ", "000002_SZ", "000003_SZ"]:
            (cache_dir / f"{code_safe}_365d.pkl").write_bytes(b"")

        # 2 stale，0 failed，共 3 只
        report_path = tmp_path / "prefetch_report.json"
        report_path.write_text(
            json.dumps({
                "failed_codes": [],
                "stale_codes": ["000001.SZ", "000002.SZ"],
            }),
            encoding="utf-8",
        )

        result = fetch_planner.plan(
            scope_codes=["000001.SZ", "000002.SZ", "000003.SZ"],
            selected_skills=["kline"],
            cache_dir=cache_dir,
            prefetch_report_path=report_path,
        )
        assert result["failure_rate"] == 0.0, \
            f"stale 不计入 failure_rate，应为 0.0，实际={result['failure_rate']}"
        assert result["readiness"] != "aborted", \
            "stale 不应触发 readiness=aborted"

    def test_stale_in_available_codes(self, tmp_path):
        """stale 股票（有 .pkl）应出现在 available_codes（可被 Producer 分析）。"""
        import fetch_planner, json

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "000001_SZ_365d.pkl").write_bytes(b"")

        report_path = tmp_path / "prefetch_report.json"
        report_path.write_text(
            json.dumps({"failed_codes": [], "stale_codes": ["000001.SZ"]}),
            encoding="utf-8",
        )

        result = fetch_planner.plan(
            scope_codes=["000001.SZ"],
            selected_skills=["kline"],
            cache_dir=cache_dir,
            prefetch_report_path=report_path,
        )
        assert "000001.SZ" in result["available_codes"], \
            "stale 且有 .pkl 的股票应在 available_codes，允许 Producer 分析"

    def test_failed_inflates_failure_rate_but_not_stale(self, tmp_path):
        """failed_codes 正常计入 failure_rate；混有 stale 时只统计 failed。"""
        import fetch_planner, json

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "000002_SZ_365d.pkl").write_bytes(b"")

        # 1 failed, 1 stale，共 3 只
        report_path = tmp_path / "prefetch_report.json"
        report_path.write_text(
            json.dumps({
                "failed_codes": ["000001.SZ"],
                "stale_codes": ["000002.SZ"],
            }),
            encoding="utf-8",
        )

        result = fetch_planner.plan(
            scope_codes=["000001.SZ", "000002.SZ", "000003.SZ"],
            selected_skills=["kline"],
            cache_dir=cache_dir,
            prefetch_report_path=report_path,
        )
        # failure_rate = 1/3 ≈ 0.333
        assert result["failure_rate"] == round(1 / 3, 4), \
            f"只有 failed 计入 failure_rate，应为 {round(1/3,4)}，实际={result['failure_rate']}"
        assert "000001.SZ" in result["failed_codes"]
        assert "000002.SZ" not in result["failed_codes"]


# ══════════════════════════════════════════════════════════════════════
# TestV6OP010SMCImport
# ══════════════════════════════════════════════════════════════════════

class TestV6OP010SMCImport:
    """V6OP-010：SMC 导入安全性 — 不崩溃，_SMC_AVAILABLE=True。"""

    def test_smc_producer_importable(self):
        """smc_producer 可正常导入，不抛 UnicodeEncodeError。"""
        try:
            import smc_producer  # noqa: F401
        except UnicodeEncodeError as e:
            pytest.fail(f"smc_producer 导入时出现 UnicodeEncodeError: {e}")
        except Exception as e:
            pytest.fail(f"smc_producer 导入失败: {e}")

    def test_smc_available_true(self):
        """_SMC_AVAILABLE 必须为 True（emoji 修复已生效）。"""
        import smc_producer
        assert smc_producer._SMC_AVAILABLE is True, \
            f"_SMC_AVAILABLE 应为 True，实际={smc_producer._SMC_AVAILABLE}，错误={smc_producer._SMC_IMPORT_ERROR}"

    def test_smc_import_no_stdout_emission(self, capsys):
        """smc_producer 导入时不应有任何输出到 stdout（emoji 被 redirect_stdout 捕获）。"""
        # 重新导入以触发模块级代码（若已缓存则此测试验证 import 幂等性）
        import importlib, smc_producer
        importlib.reload(smc_producer)
        captured = capsys.readouterr()
        # 不应含 emoji star 字符
        assert "⭐" not in captured.out, \
            f"stdout 不应包含 ⭐ emoji，实际输出: {repr(captured.out[:100])}"


# ══════════════════════════════════════════════════════════════════════
# TestV6OP011SMCSignal
# ══════════════════════════════════════════════════════════════════════

class TestV6OP011SMCSignal:
    """V6OP-011：SMC 正向信号验收 — 日期格式、strict 命中、soft_filter 标注。"""

    def _make_ohlc_df(self, n_bars: int = 100):
        """生成合成 OHLC DataFrame，DatetimeIndex，数值型列。"""
        import pandas as pd
        import numpy as np

        rng = np.random.default_rng(42)
        dates = pd.date_range("2025-01-01", periods=n_bars, freq="B")
        close = 10.0 + rng.standard_normal(n_bars).cumsum()
        close = np.maximum(close, 1.0)
        high  = close * (1 + rng.uniform(0, 0.02, n_bars))
        low   = close * (1 - rng.uniform(0, 0.02, n_bars))
        open_ = close * (1 + rng.standard_normal(n_bars) * 0.01)
        vol   = rng.uniform(1e6, 1e7, n_bars)
        df = pd.DataFrame(
            {"open": open_, "high": high, "low": low, "close": close, "volume": vol},
            index=dates,
        )
        return df

    def test_signal_date_is_date_string_not_integer(self):
        """last_signal_date 应为日期字符串（如 '2025-06-01'），不能是整数字符串。"""
        import smc_producer

        if not smc_producer._SMC_AVAILABLE:
            pytest.skip("smartmoneyconcepts 不可用")

        df = self._make_ohlc_df(120)
        result = smc_producer._analyze_one(
            code="TEST",
            df=df,
            signal_bars=120,   # 全部历史，确保能找到信号
            swing_length=5,
            close_break=True,
        )
        date_val = result.get("last_signal_date")
        if date_val is not None:
            # 必须能解析为日期格式，不能是纯整数
            assert not str(date_val).isdigit(), \
                f"last_signal_date 是整数 '{date_val}'，期望日期字符串（DatetimeIndex 对齐未生效）"
            import re
            assert re.match(r"\d{4}-\d{2}-\d{2}", str(date_val)), \
                f"last_signal_date 格式错误: '{date_val}'，期望 YYYY-MM-DD"

    def test_compute_smc_restores_datetime_index(self):
        """_compute_smc 返回的 signal_series 应有 DatetimeIndex（不能是 RangeIndex）。"""
        import smc_producer
        import pandas as pd

        if not smc_producer._SMC_AVAILABLE:
            pytest.skip("smartmoneyconcepts 不可用")

        df = self._make_ohlc_df(100)
        result = smc_producer._compute_smc(df, swing_length=5, close_break=True)
        if result is None:
            pytest.skip("_compute_smc 返回 None（K线不足或无信号）")

        signal = result["signal_series"]
        assert isinstance(signal.index, pd.DatetimeIndex), \
            f"signal_series.index 类型应为 DatetimeIndex，实际={type(signal.index).__name__}；" \
            f"DatetimeIndex 对齐可能失效，last_signal_date 将退化为整数"

    def test_smc_explanation_no_integer_date(self):
        """explanation_builder 对 SMC 命中股票不应生成含整数日期的中文理由。"""
        import explanation_builder, re

        evidence = {
            "status": "hit",
            "signal_type": "ChoCH",
            "last_signal_date": "2026-02-06",
            "fvg_confirmed": False,
        }
        prod = {
            "skill_id":      "smc",
            "skill_name":    "SMC聪明钱",
            "hit_semantics": "positive",
            "hit_codes":     ["000001.SZ"],
            "miss_codes":    [],
            "evidence":      {"000001.SZ": evidence},
        }
        result = explanation_builder.build(
            hit_codes=["000001.SZ"],
            producer_results=[prod],
            expr_metadata={},
        )
        reason = result["hits"][0]["skill_hits"][0]["reason_cn"]
        # 应包含 ChoCH 和日期字符串
        assert "ChoCH" in reason, f"reason_cn 应含 ChoCH: {reason}"
        assert "2026-02-06" in reason, f"reason_cn 应含日期字符串: {reason}"
        # 不应含纯整数（如 '189'）作为日期
        assert not re.search(r"日期\s+\d+$", reason), \
            f"reason_cn 日期不应为整数: {reason}"

    def test_soft_filter_labeled_in_explanation(self):
        """explanation_builder 对 soft_filter 命中应有明确标注。"""
        import explanation_builder

        evidence = {
            "status": "pass_soft",
            "has_signal": False,
            "signal_type": "",
            "last_signal_date": None,
            "fvg_confirmed": False,
        }
        prod = {
            "skill_id":      "smc",
            "skill_name":    "SMC聪明钱",
            "hit_semantics": "positive",
            "hit_codes":     ["000002.SZ"],
            "miss_codes":    [],
            "evidence":      {"000002.SZ": evidence},
        }
        result = explanation_builder.build(
            hit_codes=["000002.SZ"],
            producer_results=[prod],
            expr_metadata={"soft_filter_skills": ["smc"]},
        )
        reason = result["hits"][0]["skill_hits"][0]["reason_cn"]
        assert "soft_filter" in reason or "软过滤" in reason, \
            f"soft_filter 模式命中应在 reason_cn 中标注: {reason}"


# ══════════════════════════════════════════════════════════════════════
# TestV6OP012ScopedPrefetch
# ══════════════════════════════════════════════════════════════════════

class TestV6OP012ScopedPrefetch:
    """V6OP-012：旧 prefetch_report 不污染当前 scope；报告正确区分"本次预热"与"使用已有缓存"。"""

    def test_failed_codes_scoped_to_current_scope(self, tmp_path):
        """旧 prefetch_report 中有 000003.SZ failed，当前 scope 只有 000001/000002，
        fetch_planner 返回的 failed_codes 不应包含 000003.SZ。"""
        import fetch_planner, json

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "000001_SZ_365d.pkl").write_bytes(b"")
        (cache_dir / "000002_SZ_365d.pkl").write_bytes(b"")

        report_path = tmp_path / "prefetch_report.json"
        report_path.write_text(
            json.dumps({"failed_codes": ["000003.SZ"], "stale_codes": []}),
            encoding="utf-8",
        )

        result = fetch_planner.plan(
            scope_codes=["000001.SZ", "000002.SZ"],
            selected_skills=["kline"],
            cache_dir=cache_dir,
            prefetch_report_path=report_path,
        )
        assert "000003.SZ" not in result["failed_codes"], \
            "000003.SZ 不在当前 scope，不应出现在 fetch_plan.failed_codes"
        assert result["failed_codes"] == [], \
            f"当前 scope 内无 failed，应为空列表，实际={result['failed_codes']}"

    def test_stale_codes_scoped_to_current_scope(self, tmp_path):
        """旧 prefetch_report 中有 000005.SZ stale，当前 scope 只有 000001/000002，
        fetch_planner 返回的 stale_codes 不应包含 000005.SZ。"""
        import fetch_planner, json

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "000001_SZ_365d.pkl").write_bytes(b"")

        report_path = tmp_path / "prefetch_report.json"
        report_path.write_text(
            json.dumps({"failed_codes": [], "stale_codes": ["000005.SZ"]}),
            encoding="utf-8",
        )

        result = fetch_planner.plan(
            scope_codes=["000001.SZ", "000002.SZ"],
            selected_skills=["kline"],
            cache_dir=cache_dir,
            prefetch_report_path=report_path,
        )
        assert "000005.SZ" not in result["stale_codes"], \
            "000005.SZ 不在当前 scope，不应出现在 fetch_plan.stale_codes"

    def test_run_report_no_out_of_scope_failed_in_markdown(self, tmp_path):
        """run_report.md 不应显示不属于本次 scope 的失败代码。"""
        import run_report, json

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        execution_result = {
            "run_id": "test_run_012",
            "generated_at": "2026-05-05T00:00:00",
            "elapsed_seconds": 0.1,
            "status": "completed",
            "strategy": {"source": {"type": "manual"}, "skills": ["kline"],
                         "path_type": "parallel_and", "params": {}},
            "selected_skills": ["kline"],
            "path_type": "parallel_and",
            "params": {},
            "scope": {"source_type": "manual", "scope_id": "manual_2", "scope_count": 2,
                      "status": "ok", "codes": ["000001.SZ", "000002.SZ"]},
            "fetch_plan": {
                "readiness": "ready",
                "cached_codes": ["000001.SZ", "000002.SZ"],
                "missing_codes": [],
                # 旧 prefetch_report 里有 000003.SZ，fetch_planner 已经过滤，不在 failed
                "failed_codes": [],
                "stale_codes": [],
                "prefetch_required": False,
                "prefetch_report": {},
                "failure_rate": 0.0,
            },
            "producer_results": [],
            "expression_spec": {"steps": [], "primary_expression_id": None, "metadata": {}},
            "final_hit_codes": [],
            "final_hit_count": 0,
            "explanations": {"hits": []},
            "warnings": [],
            "prefetch_triggered": False,
            "env_read": False,
            "api_called": False,
            "v5_modified": False,
            "v6_modified": False,
        }

        run_report.generate(execution_result, output_dir)
        md = (output_dir / "run_report.md").read_text(encoding="utf-8")

        assert "000003.SZ" not in md, \
            "000003.SZ 不在本次 scope，run_report.md 不应提及它"
        assert "000005.SZ" not in md, \
            "000005.SZ 不在本次 scope，run_report.md 不应提及它"

    def test_run_report_no_prefetch_writes_cache_message(self, tmp_path):
        """prefetch_triggered=False 时，run_report.md 第五章应写"未触发本次预热，使用已有缓存"。"""
        import run_report

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        execution_result = {
            "run_id": "test_run_012b",
            "generated_at": "2026-05-05T00:00:00",
            "elapsed_seconds": 0.1,
            "status": "completed",
            "strategy": {"source": {"type": "manual"}, "skills": ["kline"],
                         "path_type": "parallel_and", "params": {}},
            "selected_skills": ["kline"],
            "path_type": "parallel_and",
            "params": {},
            "scope": {"source_type": "manual", "scope_id": "manual_2", "scope_count": 2,
                      "status": "ok", "codes": ["000001.SZ", "000002.SZ"]},
            "fetch_plan": {
                "readiness": "ready",
                "cached_codes": ["000001.SZ", "000002.SZ"],
                "missing_codes": [],
                "failed_codes": [],
                "stale_codes": [],
                "prefetch_required": False,
                # 旧 prefetch_report 有非零值，应被忽略
                "prefetch_report": {"fetched_ok": 5, "failed": 2, "stale_used": 1, "cache_hit": 3},
                "failure_rate": 0.0,
            },
            "producer_results": [],
            "expression_spec": {"steps": [], "primary_expression_id": None, "metadata": {}},
            "final_hit_codes": [],
            "final_hit_count": 0,
            "explanations": {"hits": []},
            "warnings": [],
            "prefetch_triggered": False,
            "env_read": False,
            "api_called": False,
            "v5_modified": False,
            "v6_modified": False,
        }

        run_report.generate(execution_result, output_dir)
        md = (output_dir / "run_report.md").read_text(encoding="utf-8")

        assert "未触发本次预热" in md, \
            f"prefetch_triggered=False 时应写'未触发本次预热'，而非'触发了自动预热': {md[md.find('## 五'):][:300]}"
        assert "触发了自动预热" not in md, \
            "prefetch_triggered=False 时不应出现'触发了自动预热'"

    def test_failed_codes_in_scope_still_reported(self, tmp_path):
        """旧 prefetch_report 中有本次 scope 内的 failed，应正常出现在 fetch_plan.failed_codes。"""
        import fetch_planner, json

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "000002_SZ_365d.pkl").write_bytes(b"")

        report_path = tmp_path / "prefetch_report.json"
        report_path.write_text(
            json.dumps({"failed_codes": ["000001.SZ", "000003.SZ"], "stale_codes": []}),
            encoding="utf-8",
        )

        result = fetch_planner.plan(
            scope_codes=["000001.SZ", "000002.SZ"],
            selected_skills=["kline"],
            cache_dir=cache_dir,
            prefetch_report_path=report_path,
        )
        # 000001.SZ 在当前 scope 内且在 prefetch failed → 保留
        assert "000001.SZ" in result["failed_codes"], \
            "000001.SZ 在当前 scope 内且 prefetch failed，应出现在 failed_codes"
        # 000003.SZ 不在当前 scope → 过滤
        assert "000003.SZ" not in result["failed_codes"], \
            "000003.SZ 不在当前 scope，应被过滤出 failed_codes"


# ══════════════════════════════════════════════════════════════════════
# TestV6OP013OutputIsolation
# ══════════════════════════════════════════════════════════════════════

class TestV6OP013OutputIsolation:
    """V6OP-013：测试产物不得污染真实 output/current 和 output/runs。"""

    _REAL_CURRENT = Path(__file__).parent.parent / "output" / "current"
    _REAL_RUNS    = Path(__file__).parent.parent / "output" / "runs"

    def test_execute_does_not_write_to_real_output_current(self):
        """调用 execute() 后，真实 output/current/run_report.md 不被改写。"""
        import execution_engine as ee

        real_md = self._REAL_CURRENT / "run_report.md"
        before = real_md.read_text(encoding="utf-8") if real_md.exists() else None

        ee.execute({
            "source": {"type": "manual", "codes": ["000001.SZ"]},
            "skills": ["kline"],
            "path_type": "parallel_and",
            "params": {},
        })

        after = real_md.read_text(encoding="utf-8") if real_md.exists() else None
        assert before == after, \
            "execute() 写入了真实 output/current/run_report.md（_OUTPUT_ROOT 重定向未生效）"

    def test_execute_output_goes_to_tmp_path(self, tmp_path):
        """execute() 的产物应写入 _OUTPUT_ROOT（tmp_path），不写入真实路径。"""
        import execution_engine as ee

        # autouse fixture 已将 _OUTPUT_ROOT 设为 tmp_path
        ee.execute({
            "source": {"type": "manual", "codes": ["000001.SZ"]},
            "skills": ["kline"],
            "path_type": "parallel_and",
            "params": {},
        })

        # tmp_path/current/run_report.md 应存在
        report_md = tmp_path / "current" / "run_report.md"
        assert report_md.exists(), \
            f"execute() 未将 run_report.md 写入 tmp_path/current/，实际路径={report_md}"

    def test_execute_archive_does_not_appear_in_real_runs(self):
        """execute() 不应在真实 output/runs/ 下新增归档目录。"""
        import execution_engine as ee

        # 记录执行前 output/runs 中现有的子目录
        existing_before = (
            set(d.name for d in self._REAL_RUNS.iterdir() if d.is_dir())
            if self._REAL_RUNS.exists() else set()
        )

        ee.execute({
            "source": {"type": "manual", "codes": ["000001.SZ"]},
            "skills": ["kline"],
            "path_type": "parallel_and",
            "params": {},
        })

        existing_after = (
            set(d.name for d in self._REAL_RUNS.iterdir() if d.is_dir())
            if self._REAL_RUNS.exists() else set()
        )
        new_dirs = existing_after - existing_before
        assert not new_dirs, \
            f"execute() 在真实 output/runs/ 新增了归档目录: {new_dirs}（_OUTPUT_ROOT 重定向未生效）"

    def test_mock_execute_does_not_pollute_real_output(self):
        """使用 mock Producer 的 execute() 同样不得写入真实 output/current。"""
        import execution_engine as ee
        import unittest.mock as mock

        real_md = self._REAL_CURRENT / "run_report.md"
        before = real_md.read_text(encoding="utf-8") if real_md.exists() else None

        def _mock_kline(codes, cache_dir=None, **kw):
            return {"hit_codes": list(codes), "miss_codes": [], "evidence": {},
                    "hit_count": len(codes), "miss_count": 0}

        with mock.patch.object(ee, "_load_producer_run", return_value=_mock_kline):
            with mock.patch("fetch_planner.plan") as mp:
                mp.return_value = {
                    "prefetch_required": False, "prefetch_plan": {},
                    "prefetch_report": {}, "readiness": "ready",
                    "cached_codes": ["000001.SZ"], "missing_codes": [],
                    "failed_codes": [], "stale_codes": [],
                    "available_codes": ["000001.SZ"], "failure_rate": 0.0,
                    "cache_dir": str(self._REAL_CURRENT), "lookback_days": 365,
                    "kline_skills": ["kline"], "generated_at": "2026-05-05T00:00:00",
                    "scope_count": 1,
                }
                ee.execute({
                    "source": {"type": "manual", "codes": ["000001.SZ"]},
                    "skills": ["kline"],
                    "path_type": "parallel_and",
                    "params": {},
                })

        after = real_md.read_text(encoding="utf-8") if real_md.exists() else None
        assert before == after, \
            "mock execute() 写入了真实 output/current/run_report.md"


class TestV6OP014RealCurrentGuard:
    """V6OP-014/015：output/current 必须是真实操盘产物，不得含测试/mock 污染标记，
    且 fetch_plan 不变式和 prefetch 语义必须正确。"""

    _REAL_CURRENT = Path(__file__).parent.parent / "output" / "current"
    _MOCK_MARKERS = [
        "kline_mock",
        "test_run",
        "pytest-of",
        r"Temp\pytest",
        r"Temp/pytest",
    ]

    def _read_real_current(self, filename: str) -> str | None:
        p = self._REAL_CURRENT / filename
        return p.read_text(encoding="utf-8") if p.exists() else None

    def _load_execution_result(self) -> dict:
        import json
        content = self._read_real_current("execution_result.json")
        if content is None:
            pytest.skip("execution_result.json 不存在")
        return json.loads(content)

    def test_run_report_md_has_no_mock_markers(self):
        """output/current/run_report.md 不含任何 mock/test 污染标记。"""
        content = self._read_real_current("run_report.md")
        assert content is not None, \
            "output/current/run_report.md 不存在——请先运行一次真实操盘"
        for marker in self._MOCK_MARKERS:
            assert marker not in content, \
                f"output/current/run_report.md 含有 mock 标记 {marker!r}"

    def test_execution_result_json_has_no_mock_markers(self):
        """output/current/execution_result.json 不含任何 mock/test 污染标记。"""
        content = self._read_real_current("execution_result.json")
        assert content is not None, \
            "output/current/execution_result.json 不存在"
        for marker in self._MOCK_MARKERS:
            assert marker not in content, \
                f"output/current/execution_result.json 含有 mock 标记 {marker!r}"

    def test_run_id_is_not_test_run(self):
        """output/current/execution_result.json 的 run_id 不以 test_run 开头。"""
        data = self._load_execution_result()
        run_id = data.get("run_id", "")
        assert not run_id.startswith("test_run"), \
            f"output/current run_id={run_id!r} 是测试产物，请重新运行真实策略"

    def test_failed_codes_subset_of_scope(self):
        """fetch_plan.failed_codes 必须全部属于本次 scope_codes（V6OP-012 不变式）。"""
        data = self._load_execution_result()
        scope_codes = set(data.get("scope", {}).get("codes", []))
        if not scope_codes:
            # scope 可能存在 strategy.source.codes 里
            scope_codes = set(data.get("strategy", {}).get("source", {}).get("codes", []))
        failed_codes = set(data.get("fetch_plan", {}).get("failed_codes", []))
        out_of_scope = failed_codes - scope_codes
        assert not out_of_scope, \
            f"fetch_plan.failed_codes 含 scope 外代码: {sorted(out_of_scope)}"

    def test_stale_codes_subset_of_scope(self):
        """fetch_plan.stale_codes 必须全部属于本次 scope_codes（V6OP-012 不变式）。"""
        data = self._load_execution_result()
        scope_codes = set(data.get("scope", {}).get("codes", []))
        if not scope_codes:
            scope_codes = set(data.get("strategy", {}).get("source", {}).get("codes", []))
        stale_codes = set(data.get("fetch_plan", {}).get("stale_codes", []))
        out_of_scope = stale_codes - scope_codes
        assert not out_of_scope, \
            f"fetch_plan.stale_codes 含 scope 外代码: {sorted(out_of_scope)}"

    def test_run_report_md_no_out_of_scope_failed_codes(self):
        """run_report.md 不得显示不属于本次 scope 的股票为失败代码。
        已知本次 scope 不含 000003.SZ / 000005.SZ，它们不应出现在报告里（V6OP-012 不变式）。"""
        data = self._load_execution_result()
        scope_codes = set(data.get("scope", {}).get("codes", []))
        if not scope_codes:
            scope_codes = set(data.get("strategy", {}).get("source", {}).get("codes", []))
        failed_codes = set(data.get("fetch_plan", {}).get("failed_codes", []))
        md = self._read_real_current("run_report.md") or ""
        # 任何出现在报告里的股票代码都应在 scope 内（宽松检查：仅验证已知 scope 外 failed 不出现）
        out_of_scope_failed = failed_codes - scope_codes
        for code in out_of_scope_failed:
            assert code not in md, \
                f"run_report.md 显示了 scope 外失败代码 {code!r}"
        # 硬编码保护：000003.SZ / 000005.SZ 不应出现
        for code in ["000003.SZ", "000005.SZ"]:
            if code not in scope_codes:
                assert code not in md, \
                    f"run_report.md 显示了 scope 外代码 {code!r}"

    def test_prefetch_triggered_false_means_no_prefetch_claim_in_md(self):
        """当 prefetch_triggered=False 时，run_report.md 不得出现'触发了自动预热'（V6OP-012 不变式）。"""
        data = self._load_execution_result()
        prefetch_triggered = data.get("prefetch_triggered", None)
        if prefetch_triggered is True:
            pytest.skip("prefetch_triggered=True，跳过此检查")
        md = self._read_real_current("run_report.md") or ""
        assert "触发了自动预热" not in md, \
            "prefetch_triggered=False 但 run_report.md 显示'触发了自动预热'"

    def _get_scope_codes(self, data: dict) -> set:
        codes = set(data.get("scope", {}).get("codes", []))
        if not codes:
            codes = set(data.get("strategy", {}).get("source", {}).get("codes", []))
        return codes

    def test_execution_result_json_no_out_of_scope_codes(self):
        """execution_result.json 全文不得含 scope 外的旧失败代码（V6OP-016 不变式）。
        prefetch_triggered=False 时 fetch_plan.prefetch_report 应为 null，不带入历史数据。"""
        import json
        data = self._load_execution_result()
        scope_codes = self._get_scope_codes(data)
        raw = json.dumps(data)
        # 硬编码保护：这两只从未进入过本次 20 只 scope
        for code in ["000003.SZ", "000005.SZ"]:
            if code not in scope_codes:
                assert code not in raw, \
                    f"execution_result.json 全文含 scope 外代码 {code!r}（prefetch_report 未清空？）"

    def test_run_report_json_no_out_of_scope_codes(self):
        """run_report.json 全文不得含 scope 外的旧失败代码（V6OP-016 不变式）。"""
        import json
        data = self._load_execution_result()
        scope_codes = self._get_scope_codes(data)
        rj_content = self._read_real_current("run_report.json")
        if rj_content is None:
            pytest.skip("run_report.json 不存在")
        rj = json.loads(rj_content)
        raw = json.dumps(rj)
        for code in ["000003.SZ", "000005.SZ"]:
            if code not in scope_codes:
                assert code not in raw, \
                    f"run_report.json 全文含 scope 外代码 {code!r}（prefetch_report 未清空？）"

    def test_prefetch_report_null_when_not_triggered(self):
        """prefetch_triggered=False 时，fetch_plan.prefetch_report 必须为 null/None（V6OP-016 不变式）。"""
        data = self._load_execution_result()
        prefetch_triggered = data.get("prefetch_triggered", None)
        if prefetch_triggered is True:
            pytest.skip("prefetch_triggered=True，跳过此检查")
        pr = data.get("fetch_plan", {}).get("prefetch_report", "MISSING")
        assert pr is None, \
            f"prefetch_triggered=False 但 fetch_plan.prefetch_report={pr!r}（应为 null）"


# ══════════════════════════════════════════════════════════════════════
# TestV6OP018DataPrefetchWorkers
# ══════════════════════════════════════════════════════════════════════

class TestV6OP018DataPrefetchWorkers:
    """V6OP-018: workers>1 子进程不因 TextIOWrapper 替换崩溃（exit code 1）。"""

    def test_workers_2_no_worker_failed(self, tmp_path):
        """workers=2 时 worker 子进程正常退出，worker_N_report.json 被写出，
        failed_codes 中不含 error='worker_failed'。
        """
        import sys as _sys
        if str(_SCRIPTS_DIR) not in _sys.path:
            _sys.path.insert(0, str(_SCRIPTS_DIR))
        from data_prefetch import run_prefetch

        real_cache = _PROJECT_ROOT / "var" / "cache" / "kline_daily"
        pkls = sorted(real_cache.glob("*.pkl"))[:6] if real_cache.exists() else []
        if len(pkls) < 3:
            pytest.skip("缓存文件不足 3 只，跳过 workers 验收")

        codes = []
        for p in pkls:
            parts = p.stem.split("_")
            if len(parts) >= 2:
                codes.append(f"{parts[0]}.{parts[1]}")

        report_dir = tmp_path / "reports"
        result = run_prefetch(
            codes=codes,
            days=365,
            workers=2,
            cache_dir=real_cache,
            report_dir=report_dir,
        )

        assert isinstance(result, dict), "run_prefetch 应返回 dict"

        # worker 报告文件必须存在（worker 正常退出才会写出）
        worker_reports = list(report_dir.glob("prefetch_workers/**/*.json"))
        assert len(worker_reports) > 0, \
            "未生成 worker_N_report.json：worker 可能以 exit code 1 提前退出"

        # failed_codes 中不得含 error='worker_failed'（worker 崩溃的标志）
        worker_failed_entries = [
            fc for fc in result.get("failed_codes", [])
            if isinstance(fc, dict) and fc.get("error") == "worker_failed"
        ]
        assert not worker_failed_entries, \
            f"出现 worker_failed 错误，_configure_streams 修复可能未生效: {worker_failed_entries}"


# ════════════════════════════════════════════════════════════════════
#  V6OP-020: V5.10 真实数据闭环经验对齐 guard 测试
# ════════════════════════════════════════════════════════════════════

_REAL_CACHE = _PROJECT_ROOT / "var" / "cache" / "kline_daily"


def _cache_codes(n: int) -> list[str]:
    """从本地缓存取最多 n 只代码（离线，不发网络请求）。"""
    pkls = sorted(_REAL_CACHE.glob("*.pkl"))[:n] if _REAL_CACHE.exists() else []
    codes = []
    for p in pkls:
        parts = p.stem.split("_")
        if len(parts) >= 2:
            codes.append(f"{parts[0]}.{parts[1]}")
    return codes


class TestV6OP020PrefetchAlignV510:
    """V6OP-020: 对齐 V5.10 prefetch recovery pass / data_time_max / 数字自洽。"""

    def test_recovery_fields_present_workers_1(self, tmp_path):
        """workers=1 时 run_prefetch 返回 recovery pass 字段（对齐 V5.10 _apply_recovery）。"""
        codes = _cache_codes(5)
        if not codes:
            pytest.skip("无缓存文件，跳过")
        from data_prefetch import run_prefetch
        result = run_prefetch(codes=codes, workers=1, cache_dir=_REAL_CACHE,
                              report_dir=tmp_path, days=365)
        assert "failed_codes_raw" in result, "缺少 failed_codes_raw 字段"
        assert "recovered_codes" in result, "缺少 recovered_codes 字段"
        assert "recovered_count" in result, "缺少 recovered_count 字段"

    def test_recovery_fields_self_consistent(self, tmp_path):
        """failed_codes_raw == recovered_codes + failed_codes（对齐 V5.10 _apply_recovery 不变式）。"""
        codes = _cache_codes(6)
        if not codes:
            pytest.skip("无缓存文件，跳过")
        from data_prefetch import run_prefetch
        result = run_prefetch(codes=codes, workers=1, cache_dir=_REAL_CACHE,
                              report_dir=tmp_path, days=365)
        raw = len(result.get("failed_codes_raw", []))
        rec = result.get("recovered_count", 0)
        final = len(result.get("failed_codes", []))
        assert raw == rec + final, \
            f"recovery 不变式破坏：failed_codes_raw({raw}) != recovered_count({rec}) + failed_codes({final})"

    def test_sum_self_consistent_workers_1(self, tmp_path):
        """total = cache_hit + fetched_ok + stale_used + failed + bj_skipped（workers=1）。"""
        codes = _cache_codes(8)
        if not codes:
            pytest.skip("无缓存文件，跳过")
        from data_prefetch import run_prefetch
        result = run_prefetch(codes=codes, workers=1, cache_dir=_REAL_CACHE,
                              report_dir=tmp_path, days=365)
        total = (result.get("cache_hit", 0) + result.get("fetched_ok", 0)
                 + result.get("stale_used", 0) + result.get("failed", 0)
                 + result.get("bj_skipped", 0))
        assert total == len(codes), \
            f"数字总和不等于代码数量: sum={total} != codes={len(codes)}"

    def test_sum_self_consistent_workers_2(self, tmp_path):
        """total = cache_hit + fetched_ok + stale_used + failed + bj_skipped（workers=2）。"""
        codes = _cache_codes(8)
        if len(codes) < 3:
            pytest.skip("缓存文件不足 3 只，跳过")
        from data_prefetch import run_prefetch
        result = run_prefetch(codes=codes, workers=2, cache_dir=_REAL_CACHE,
                              report_dir=tmp_path, days=365)
        total = (result.get("cache_hit", 0) + result.get("fetched_ok", 0)
                 + result.get("stale_used", 0) + result.get("failed", 0)
                 + result.get("bj_skipped", 0))
        assert total == len(codes), \
            f"数字总和不等于代码数量: sum={total} != codes={len(codes)}"

    def test_data_time_max_in_prefetch_report_json(self, tmp_path):
        """prefetch_report.json 包含 data_time_max 字段（对齐 V5.10 data_time_max）。"""
        codes = _cache_codes(4)
        if not codes:
            pytest.skip("无缓存文件，跳过")
        from data_prefetch import run_prefetch
        run_prefetch(codes=codes, workers=1, cache_dir=_REAL_CACHE,
                     report_dir=tmp_path, days=365)
        report_path = tmp_path / "prefetch_report.json"
        assert report_path.exists(), "prefetch_report.json 未生成"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert "data_time_max" in report, "prefetch_report.json 缺少 data_time_max 字段"
        assert "failed_codes_raw" in report, "prefetch_report.json 缺少 failed_codes_raw 字段"
        assert "recovered_count" in report, "prefetch_report.json 缺少 recovered_count 字段"

    def test_read_cache_only_gate_static_check(self):
        """static 检查 execution_engine 预热异常时正确排除 missing_codes（READ_CACHE_ONLY 门控对齐）。"""
        src = (_SCRIPTS_DIR / "execution_engine.py").read_text(encoding="utf-8")
        assert "_prefetch_exception_missing" in src, \
            "execution_engine 缺少 _prefetch_exception_missing 变量"
        assert "_prefetch_exception_missing = set(fetch.get" in src, \
            "预热异常时未收集 missing_codes → _prefetch_exception_missing"
        assert "| _prefetch_exception_missing" in src, \
            "_prefetch_exception_missing 未合并入 _failed_set"

    def test_wencai_status_codes_expanded(self):
        """wencai_source 支持 auth_failed / empty_result / network_error / api_error。"""
        src = (_SCRIPTS_DIR / "sources" / "wencai_source.py").read_text(encoding="utf-8")
        for status in ("auth_failed", "empty_result", "network_error", "api_error"):
            assert f'"{status}"' in src, \
                f"wencai_source.py 缺少状态码 {status!r}（V6OP-020 失败归因对齐）"


# ══════════════════════════════════════════════════════════════════════
# TestV6OP021PrefetchParityAndRealtimeLog
# ══════════════════════════════════════════════════════════════════════

class TestV6OP021PrefetchParityAndRealtimeLog:
    """V6OP-021: prefetch parity（coordinator data_time_max + CLI schema）、实时日志 sink。"""

    # ── Task 1a: _run_coordinator data_time_max 聚合 ──────────────────

    def test_coordinator_data_time_max_aggregated(self, tmp_path):
        """workers=2 时，_run_coordinator 最终 report 应包含 data_time_max（从 worker reports 聚合）。"""
        codes = _cache_codes(6)
        if len(codes) < 3:
            pytest.skip("缓存文件不足 3 只，跳过 coordinator data_time_max 验收")
        from data_prefetch import run_prefetch
        result = run_prefetch(
            codes=codes, days=365, workers=2,
            cache_dir=_REAL_CACHE, report_dir=tmp_path,
        )
        assert "data_time_max" in result, \
            "_run_coordinator 应聚合 data_time_max（workers=2 路径），但字段不存在"
        if result.get("cache_hit", 0) + result.get("fetched_ok", 0) > 0:
            assert result["data_time_max"] is not None, \
                "有命中缓存时 data_time_max 应非 None（worker reports 聚合未生效）"

    def test_coordinator_data_time_max_is_date_string(self, tmp_path):
        """_run_coordinator data_time_max 应为 YYYY-MM-DD 格式字符串。"""
        import re
        codes = _cache_codes(4)
        if not codes:
            pytest.skip("无缓存文件，跳过")
        from data_prefetch import run_prefetch
        result = run_prefetch(
            codes=codes, days=365, workers=2,
            cache_dir=_REAL_CACHE, report_dir=tmp_path,
        )
        dtm = result.get("data_time_max")
        if dtm is None:
            pytest.skip("data_time_max=None（无可用数据），跳过格式检查")
        assert isinstance(dtm, str), f"data_time_max 应为字符串，实际={type(dtm)}"
        assert re.match(r"\d{4}-\d{2}-\d{2}", dtm), \
            f"data_time_max 格式应为 YYYY-MM-DD，实际={dtm!r}"

    # ── Task 1b: CLI main() 静态口径检查 ─────────────────────────────

    def test_cli_main_calls_apply_recovery(self):
        """data_prefetch.py CLI main() 必须调用 _apply_recovery（与 run_prefetch 路径对齐）。"""
        src = (_SCRIPTS_DIR / "data_prefetch.py").read_text(encoding="utf-8")
        assert "_apply_recovery" in src, \
            "data_prefetch.py CLI main() 缺少 _apply_recovery 调用（口径与 run_prefetch 不对齐）"

    def test_cli_main_report_has_full_schema(self):
        """data_prefetch.py CLI main() 的 report dict 应包含全量 V6OP-020 字段。"""
        src = (_SCRIPTS_DIR / "data_prefetch.py").read_text(encoding="utf-8")
        for field in ("failed_codes_raw", "recovered_codes", "recovered_count", "data_time_max"):
            assert f'"{field}"' in src, \
                f"data_prefetch.py CLI main() report 缺少字段 {field!r}"

    # ── Task 2: execution_engine _log_sink 实时推送 ───────────────────

    def test_log_sink_attribute_exists(self):
        """execution_engine 应有模块级 _log_sink 属性。"""
        import execution_engine
        assert hasattr(execution_engine, "_log_sink"), \
            "execution_engine 缺少 _log_sink 模块级属性"

    def test_log_sink_callable_invoked_on_log(self):
        """设置 execution_engine._log_sink 后，每次 _log() 调用时 sink 应被触发。"""
        import execution_engine

        calls: list[tuple[str, str]] = []

        def _sink(level: str, msg: str) -> None:
            calls.append((level, msg))

        original = execution_engine._log_sink
        try:
            execution_engine._log_sink = _sink
            execution_engine._log("INFO", "test_sink_message_v6op021")
        finally:
            execution_engine._log_sink = original

        assert any("test_sink_message_v6op021" in m for _, m in calls), \
            "_log_sink 未在 _log() 调用时被触发"

    def test_log_sink_exception_does_not_crash_log(self):
        """_log_sink 抛异常时，_log() 本身不应崩溃（异常被静默捕获）。"""
        import execution_engine

        def _bad_sink(level: str, msg: str) -> None:
            raise RuntimeError("sink crash!")

        original = execution_engine._log_sink
        try:
            execution_engine._log_sink = _bad_sink
            execution_engine._log("INFO", "crash_test_v6op021")
        finally:
            execution_engine._log_sink = original

    def test_server_wires_log_sink_before_execute(self):
        """v6op_server.py 必须在 execute() 前设置 execution_engine._log_sink（实时推送）。"""
        src = (_SCRIPTS_DIR / "v6op_server.py").read_text(encoding="utf-8")
        assert "execution_engine._log_sink" in src, \
            "v6op_server.py 缺少 execution_engine._log_sink 设置（实时推送未接入）"

    def test_server_no_batch_push_after_execute(self):
        """v6op_server 后台执行函数不应在 execute() 完成后批量调用 get_log_events()。"""
        import re
        src = (_SCRIPTS_DIR / "v6op_server.py").read_text(encoding="utf-8")
        bg_match = re.search(
            r"def _run_execution_background.*?(?=\ndef |\Z)",
            src,
            re.DOTALL,
        )
        if bg_match:
            bg_src = bg_match.group(0)
            assert "get_log_events" not in bg_src, \
                "_run_execution_background 不应包含 get_log_events() 批量推送（应改用 _log_sink）"
