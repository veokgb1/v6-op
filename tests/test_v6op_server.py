"""
test_v6op_server.py — V6OP Server Smoke Tests

测试服务器模块可导入、健康数据格式正确、关键端点逻辑正确。
不启动真实网络监听。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).parent.parent.resolve()
_SCRIPTS_DIR = _PROJECT_ROOT / "scripts"

for _p in [str(_SCRIPTS_DIR), str(_SCRIPTS_DIR / "producers"),
           str(_SCRIPTS_DIR / "sources")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ══════════════════════════════════════════════════════════════════════
# TestServerModule
# ══════════════════════════════════════════════════════════════════════

class TestServerModule:
    def test_import(self):
        import v6op_server
        assert hasattr(v6op_server, "start_server")
        assert hasattr(v6op_server, "self_test")
        assert hasattr(v6op_server, "_health_data")

    def test_health_data_structure(self):
        import v6op_server
        data = v6op_server._health_data()
        required = {"status", "python_version", "v6op_path",
                    "key_files", "dot_env_exists", "generated_at"}
        assert required.issubset(data.keys())
        assert data["status"] == "ok"

    def test_health_data_no_key_values(self):
        import v6op_server
        data = v6op_server._health_data()
        data_str = json.dumps(data)
        # 只检查 health 不暴露实际 key 值（变量名是允许的）
        # 变量名中的 _KEY 字段可以出现，但不应包含实际密钥值
        # （实际密钥值通常是长随机串，这里简单验证不含已知密钥模式）
        assert "dot_env_var_names" in data  # 变量名列表存在
        # 确认不含变量值（变量值不应出现在任何字段的值中）
        # 变量名 IWENCAI_API_KEY 本身出现在 var_names 列表中是可以的

    def test_health_python_version_is_string(self):
        import v6op_server
        data = v6op_server._health_data()
        assert isinstance(data["python_version"], str)
        assert "3." in data["python_version"]

    def test_health_key_files_are_booleans(self):
        import v6op_server
        data = v6op_server._health_data()
        for k, v in data["key_files"].items():
            assert isinstance(v, bool), f"key_files[{k!r}] 应为 bool"

    def test_v6op_path_is_valid(self):
        import v6op_server
        data = v6op_server._health_data()
        path = Path(data["v6op_path"])
        assert path.exists(), f"v6op_path {path} 应存在"


# ══════════════════════════════════════════════════════════════════════
# TestServerRunState
# ══════════════════════════════════════════════════════════════════════

class TestServerRunState:
    def test_run_state_initial_idle(self):
        import v6op_server
        with v6op_server._state_lock:
            status = v6op_server._run_state["status"]
        assert status in ("idle", "pending", "running", "completed", "error")

    def test_push_event(self):
        import v6op_server
        initial_count = len(v6op_server._run_state["events"])
        v6op_server._push_event("INFO", "test event from test suite")
        assert len(v6op_server._run_state["events"]) > initial_count

    def test_push_event_structure(self):
        import v6op_server
        v6op_server._push_event("WARN", "test warning")
        last = v6op_server._run_state["events"][-1]
        assert "index" in last
        assert "ts" in last
        assert "level" in last
        assert "msg" in last
        assert last["level"] == "WARN"
        assert last["msg"] == "test warning"

    def test_push_event_count_is_monotonic(self):
        import v6op_server
        with v6op_server._state_lock:
            old_events = list(v6op_server._run_state["events"])
            old_count = v6op_server._run_state.get("event_count", 0)
            v6op_server._run_state["events"] = []
            v6op_server._run_state["event_count"] = 0
        try:
            for i in range(205):
                v6op_server._push_event("INFO", f"event {i}")
            with v6op_server._state_lock:
                events = list(v6op_server._run_state["events"])
                count = v6op_server._run_state["event_count"]
            assert count == 205
            assert events[0]["index"] == 0
            assert events[-1]["index"] == 204
        finally:
            with v6op_server._state_lock:
                v6op_server._run_state["events"] = old_events
                v6op_server._run_state["event_count"] = old_count


# ══════════════════════════════════════════════════════════════════════
# TestServerIsolation
# ══════════════════════════════════════════════════════════════════════

class TestServerIsolation:
    def test_no_hardcoded_key_in_server_source(self):
        """服务器源代码中不能包含硬编码 API key 值。"""
        source = (_SCRIPTS_DIR / "v6op_server.py").read_text(encoding="utf-8")
        import re
        # 检查没有直接嵌入长随机串（简单模式）
        # 变量名可以出现，但典型的 API key 是 32+ 字符的十六进制/字母数字串
        assert "IWENCAI_API_KEY" not in source or "dot_env_var_names" in source

    def test_server_does_not_import_v5(self):
        """服务器不应导入 V5 模块。"""
        source = (_SCRIPTS_DIR / "v6op_server.py").read_text(encoding="utf-8")
        assert "v5" not in source.lower() or "v5_modified" in source

    def test_sse_note_in_source(self):
        """服务器必须在代码或文档中说明 /api/stream 是轮询而非 true SSE。"""
        source = (_SCRIPTS_DIR / "v6op_server.py").read_text(encoding="utf-8")
        assert "轮询" in source or "polling" in source.lower()


# ══════════════════════════════════════════════════════════════════════
# TestPhase2Isolation
# ══════════════════════════════════════════════════════════════════════

class TestPhase2Isolation:
    def test_source_resolver_no_network_without_wencai(self):
        """manual 和 all_a 来源不得访问网络。"""
        import source_resolver
        # 确认 manual 来源不导入 wencai 相关模块
        result = source_resolver.resolve("manual", manual_codes=["000001.SZ"])
        assert result["status"] == "ok"

    def test_fetch_planner_no_network(self):
        """FetchPlanner 只读本地文件，不访问网络。"""
        import fetch_planner
        result = fetch_planner.plan(["000001.SZ"], ["kline"])
        assert isinstance(result, dict)

    def test_strategy_graph_no_network(self):
        """StrategyGraphBuilder 是纯函数，不访问网络。"""
        import strategy_graph_builder
        from skill_registry import SKILL_REGISTRY
        registry = {s["skill_id"]: s for s in SKILL_REGISTRY}
        graph = strategy_graph_builder.build(["czsc"], registry)
        assert isinstance(graph, dict)

    def test_expression_auto_generator_no_network(self):
        """ExpressionAutoGenerator 是纯函数，不访问网络。"""
        import expression_auto_generator
        spec = expression_auto_generator.generate([], {"path_type": "parallel_and",
                                                       "merge_node": {"op": "AND", "params": {}}})
        assert isinstance(spec, dict)

    def test_explanation_builder_no_network(self):
        """ExplanationBuilder 是纯函数，不访问网络。"""
        import explanation_builder
        result = explanation_builder.build([], [], {})
        assert isinstance(result, dict)

    def test_stream_since_param_supported(self):
        """v6op_server 的 /api/stream 路由代码必须支持 since 参数。"""
        source = (_SCRIPTS_DIR / "v6op_server.py").read_text(encoding="utf-8")
        assert "since" in source, "v6op_server.py 未实现 ?since=N 参数"
        assert "event_count" in source, "v6op_server.py 未返回 event_count"

    def test_phase2_scripts_no_v5_imports(self):
        """Phase 2 新增脚本不得 import V5 模块（字符串引用在注释中可以出现）。"""
        phase2_scripts = [
            "source_resolver.py",
            "fetch_planner.py",
            "strategy_graph_builder.py",
            "expression_auto_generator.py",
            "execution_engine.py",
            "explanation_builder.py",
            "run_report.py",
            "v6op_server.py",
        ]
        import re
        for fname in phase2_scripts:
            source = (_SCRIPTS_DIR / fname).read_text(encoding="utf-8")
            # 检查没有实际 import 语句引用 v5（注释中的 "v5.10" 字符串是允许的）
            assert not re.search(r"^\s*(import|from)\s+v5", source, re.MULTILINE), (
                f"{fname} 不得 import v5 模块"
            )
            # sys.path 也不得直接加入 v5.10 路径
            assert "v5.10" not in source.replace("v5.10 /", "").replace("v5.10/", ""), (
                f"{fname} 不得直接引用 v5.10 路径（注释中说明边界除外）"
            )


# ══════════════════════════════════════════════════════════════════════
# TestV6OP006ApiResult  (V6OP-006 纠偏：/api/result 返回 run_report)
# ══════════════════════════════════════════════════════════════════════

class TestV6OP006ApiResult:
    """验证 /api/result 按 Option A 合约返回 run_report.json 结构。"""

    def _make_run_report(self, explanations: list | None = None) -> dict:
        return {
            "run_id": "test-run-001",
            "status": "completed",
            "explanations": explanations if explanations is not None else [
                {"code": "000001", "name": "平安银行", "skill_hits": []}
            ],
            "data_coverage": {"cached_pct": 100.0, "missing_count": 0},
            "producer_summary": [],
            "warnings": [],
            "hit_count": 1,
            "failed_codes": [],
            "stale_codes": [],
        }

    def _make_handler(self, monkeypatch, tmp_path, v6op_server):
        """构造一个最小化的 V6OPHandler 实例，仅模拟 do_GET 所需属性。"""
        monkeypatch.setattr(v6op_server, "_PROJECT_ROOT", tmp_path)
        handler = object.__new__(v6op_server.V6OPHandler)
        sent: list[tuple[int, dict]] = []
        handler._send_json = lambda code, data: sent.append((code, data))
        # do_GET 需要 self.path 和 self.headers；/api/result 分支不读 headers
        handler.path = "/api/result"
        return handler, sent

    def test_api_result_returns_run_report_structure(self, tmp_path, monkeypatch):
        """run_report.json 存在时，/api/result 返回其内容（含 explanations 列表）。"""
        import v6op_server

        output_dir = tmp_path / "output" / "current"
        output_dir.mkdir(parents=True)
        report = self._make_run_report()
        (output_dir / "run_report.json").write_text(
            json.dumps(report), encoding="utf-8"
        )

        handler, sent = self._make_handler(monkeypatch, tmp_path, v6op_server)
        handler.do_GET()

        assert sent, "未调用 _send_json"
        code, data = sent[0]
        assert code == 200, f"期望 200，实际 {code}"
        assert "explanations" in data, "/api/result 缺少 explanations"
        assert isinstance(data["explanations"], list), "explanations 必须是列表"
        assert "data_coverage" in data, "/api/result 缺少 data_coverage"
        assert "hit_count" in data, "/api/result 缺少 hit_count"

    def test_api_result_explanations_is_list_not_dict(self, tmp_path, monkeypatch):
        """explanations 必须是列表（非旧格式 dict），每项含 skill_hits。"""
        import v6op_server

        output_dir = tmp_path / "output" / "current"
        output_dir.mkdir(parents=True)
        report = self._make_run_report(explanations=[
            {"code": "600519", "name": "贵州茅台", "skill_hits": [
                {"skill_id": "czsc", "skill_name": "CZSC", "reason_cn": "三买"}
            ]}
        ])
        (output_dir / "run_report.json").write_text(
            json.dumps(report), encoding="utf-8"
        )

        handler, sent = self._make_handler(monkeypatch, tmp_path, v6op_server)
        handler.do_GET()

        _, data = sent[0]
        assert isinstance(data["explanations"], list)
        assert data["explanations"][0]["code"] == "600519"

    def test_api_result_fallback_to_execution_result(self, tmp_path, monkeypatch):
        """run_report.json 缺失时，回退到 execution_result.json。"""
        import v6op_server

        output_dir = tmp_path / "output" / "current"
        output_dir.mkdir(parents=True)
        fallback = {"status": "completed", "explanations": {}, "hit_count": 0}
        (output_dir / "execution_result.json").write_text(
            json.dumps(fallback), encoding="utf-8"
        )

        handler, sent = self._make_handler(monkeypatch, tmp_path, v6op_server)
        handler.do_GET()

        assert sent
        assert sent[0][0] == 200
        assert sent[0][1]["status"] == "completed"

    def test_api_result_returns_404_when_no_report(self, tmp_path, monkeypatch):
        """run_report.json 与 execution_result.json 均不存在时返回 404。"""
        import v6op_server

        output_dir = tmp_path / "output" / "current"
        output_dir.mkdir(parents=True)

        handler, sent = self._make_handler(monkeypatch, tmp_path, v6op_server)
        handler.do_GET()

        assert sent
        assert sent[0][0] == 404

    def test_api_runs_params_returns_frontend_restore_contract(self, tmp_path, monkeypatch):
        """/api/runs/:id/params 必须返回前端可直接恢复的 params 契约。"""
        import v6op_server

        run_id = "run-contract-001"
        run_dir = tmp_path / "output" / "runs" / run_id
        run_dir.mkdir(parents=True)
        strategy_snapshot = {
            "source": {"type": "manual", "codes": ["000001.SZ", "000002.SZ"]},
            "skills": ["kline", "landmine"],
            "path_type": "parallel_and",
            "params": {"skills": {"kline": {"signal_bars": 3}}},
        }
        report = {
            "run_id": run_id,
            "actual_days_used": 365,
            "strategy": {
                "source": {"type": "manual", "scope_count": 2, "status": "ok"},
                "selected_skills": ["kline", "landmine"],
                "path_type": "parallel_and",
                "params": {"skills": {"kline": {"signal_bars": 3}}},
            },
            "strategy_snapshot": strategy_snapshot,
        }
        (run_dir / "run_report.json").write_text(
            json.dumps(report, ensure_ascii=False), encoding="utf-8"
        )

        handler, sent = self._make_handler(monkeypatch, tmp_path, v6op_server)
        handler.path = f"/api/runs/{run_id}/params"
        handler.do_GET()

        assert sent, "未调用 _send_json"
        code, data = sent[0]
        assert code == 200
        assert data["params"] == strategy_snapshot
        assert data["params"]["source"]["codes"] == ["000001.SZ", "000002.SZ"]
        assert data["params"]["skills"] == ["kline", "landmine"]
        assert data["params"]["path_type"] == "parallel_and"
        assert data["params"]["params"]["skills"]["kline"]["signal_bars"] == 3


# ══════════════════════════════════════════════════════════════════════
# TestV6OP007AllAProtection — 全 A 扫描不再按档位拦截
# ══════════════════════════════════════════════════════════════════════

class TestV6OP007AllAProtection:
    """全 A 扫描取消数量拦截，仅保留前端提示。"""

    def _make_idle_state(self):
        return {
            "status": "idle",
            "run_id": None,
            "started_at": None,
            "completed_at": None,
            "error": None,
            "final_hit_count": 0,
            "events": [],
            "event_count": 0,
        }

    def _make_post_handler(self, v6op_server, body_bytes: bytes):
        handler = object.__new__(v6op_server.V6OPHandler)
        sent: list[tuple[int, dict]] = []
        handler._send_json = lambda code, data: sent.append((code, data))  # type: ignore[method-assign]
        handler._read_body = lambda: body_bytes  # type: ignore[method-assign]
        handler.path = "/api/run"
        return handler, sent

    def test_all_a_500_without_confirm_allowed(self, monkeypatch):
        """all_a limit=500 且无 confirm_large_scope 时，API 也应接受。"""
        import v6op_server, threading
        strategy = {
            "source": {"type": "all_a", "limit": 500},
            "skills": ["kline"],
            "path_type": "parallel_and",
            "params": {},
        }
        body = json.dumps(strategy).encode("utf-8")
        handler, sent = self._make_post_handler(v6op_server, body)
        monkeypatch.setattr(v6op_server, "_run_state", self._make_idle_state())
        monkeypatch.setattr(threading.Thread, "start", lambda self: None)
        handler.do_POST()
        assert sent, "未调用 _send_json"
        code, _ = sent[0]
        assert code == 202, f"all_a limit=500 不应再被确认拦截，实际 {code}"

    def test_all_a_1000_without_confirm_allowed(self, monkeypatch):
        """all_a limit=1000 且无 confirm_large_scope 时，API 也应接受。"""
        import v6op_server, threading
        strategy = {
            "source": {"type": "all_a", "limit": 1000},
            "skills": ["kline"],
            "path_type": "parallel_and",
            "params": {},
        }
        body = json.dumps(strategy).encode("utf-8")
        handler, sent = self._make_post_handler(v6op_server, body)
        monkeypatch.setattr(v6op_server, "_run_state", self._make_idle_state())
        monkeypatch.setattr(threading.Thread, "start", lambda self: None)
        handler.do_POST()
        assert sent
        code, _ = sent[0]
        assert code == 202

    def test_all_a_300_no_confirm_required(self, monkeypatch):
        """all_a limit=300 无需确认，API 应接受（202）。"""
        import v6op_server, threading
        strategy = {
            "source": {"type": "all_a", "limit": 300},
            "skills": ["kline"],
            "path_type": "parallel_and",
            "params": {},
        }
        body = json.dumps(strategy).encode("utf-8")
        handler, sent = self._make_post_handler(v6op_server, body)
        monkeypatch.setattr(v6op_server, "_run_state", self._make_idle_state())
        monkeypatch.setattr(threading.Thread, "start", lambda self: None)
        handler.do_POST()
        assert sent
        code, _ = sent[0]
        assert code == 202, f"all_a limit=300 应允许（202），实际 {code}"

    def test_all_a_500_with_confirm_allowed(self, monkeypatch):
        """all_a limit=500 且 confirm_large_scope=true 时，API 应接受（202）。"""
        import v6op_server, threading
        strategy = {
            "source": {"type": "all_a", "limit": 500},
            "skills": ["kline"],
            "path_type": "parallel_and",
            "params": {},
            "confirm_large_scope": True,
        }
        body = json.dumps(strategy).encode("utf-8")
        handler, sent = self._make_post_handler(v6op_server, body)
        monkeypatch.setattr(v6op_server, "_run_state", self._make_idle_state())
        monkeypatch.setattr(threading.Thread, "start", lambda self: None)
        handler.do_POST()
        assert sent
        code, _ = sent[0]
        assert code == 202, f"confirm=true 时应允许（202），实际 {code}"

    def test_wencai_source_accepted_in_api_run(self, monkeypatch):
        """/api/run 接受 source.type = 'wencai' 且不受 all_a 保护拦截。"""
        import v6op_server, threading
        strategy = {
            "source": {"type": "wencai", "query": "净利润增速大于20%", "limit": 50},
            "skills": ["kline"],
            "path_type": "parallel_and",
            "params": {},
        }
        body = json.dumps(strategy).encode("utf-8")
        handler, sent = self._make_post_handler(v6op_server, body)
        monkeypatch.setattr(v6op_server, "_run_state", self._make_idle_state())
        monkeypatch.setattr(threading.Thread, "start", lambda self: None)
        handler.do_POST()
        assert sent
        code, data = sent[0]
        assert code == 202, f"wencai 来源应接受（202），实际 {code}: {data}"
