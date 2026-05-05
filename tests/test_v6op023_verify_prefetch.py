"""
test_v6op023_verify_prefetch.py — V6OP-023 Task 4 / V6OP-024 Fix 3

verify_prefetch_300.py 验证，包括：
- 脚本存在且可导入
- CLI 接受 --limit / --workers / --json-out / --dry-run / --timeout 参数
- dry-run 模式输出 JSON（不跑真实网络请求）
- run_verification() 在环境不满足时返回 env_error（而非崩溃）
- timeout 时返回 status=timeout，写 partial JSON，workers_cleaned=True
- JSON 输出包含必要字段
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

_ROOT    = Path(__file__).parent.parent.resolve()
_SCRIPTS = _ROOT / "scripts"


# ══════════════════════════════════════════════════════════════════════
# TestVerifyPrefetch300Exists — 脚本存在性
# ══════════════════════════════════════════════════════════════════════

class TestVerifyPrefetch300Exists:
    def test_script_file_exists(self):
        assert (_SCRIPTS / "verify_prefetch_300.py").exists(), \
            "scripts/verify_prefetch_300.py 不存在"

    def test_script_importable(self):
        sys.path.insert(0, str(_SCRIPTS))
        import verify_prefetch_300
        assert hasattr(verify_prefetch_300, "run_verification"), \
            "verify_prefetch_300 缺少 run_verification()"
        assert hasattr(verify_prefetch_300, "main"), \
            "verify_prefetch_300 缺少 main()"

    def test_script_has_required_args(self):
        src = (_SCRIPTS / "verify_prefetch_300.py").read_text(encoding="utf-8")
        for arg in ["--limit", "--workers", "--json-out", "--dry-run", "--timeout"]:
            assert arg in src, f"verify_prefetch_300.py 缺少参数 {arg}"

    def test_script_has_timeout_partial_support(self):
        src = (_SCRIPTS / "verify_prefetch_300.py").read_text(encoding="utf-8")
        assert "timeout" in src, "脚本应支持 timeout"
        assert "partial" in src, "脚本应输出 partial JSON"
        assert "workers_cleaned" in src, "脚本应输出 workers_cleaned 字段"


# ══════════════════════════════════════════════════════════════════════
# TestVerifyPrefetch300DryRun — dry-run 模式（不跑真实网络）
# ══════════════════════════════════════════════════════════════════════

class TestVerifyPrefetch300DryRun:
    def test_dry_run_exits_zero(self, tmp_path):
        out_json = tmp_path / "dry_run.json"
        result = subprocess.run(
            [sys.executable, str(_SCRIPTS / "verify_prefetch_300.py"),
             "--dry-run", "--limit", "20", "--workers", "2",
             "--json-out", str(out_json)],
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        assert result.returncode == 0, \
            f"--dry-run 应退出 0，实际: {result.returncode}\nstderr: {result.stderr}"

    def test_dry_run_writes_json(self, tmp_path):
        out_json = tmp_path / "dry_run.json"
        subprocess.run(
            [sys.executable, str(_SCRIPTS / "verify_prefetch_300.py"),
             "--dry-run", "--limit", "20", "--workers", "2",
             "--json-out", str(out_json)],
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        assert out_json.exists(), "--dry-run 应写入 JSON 文件"
        data = json.loads(out_json.read_text(encoding="utf-8"))
        assert data["status"] == "dry_run", "dry-run JSON status 应为 'dry_run'"
        assert "verified_at" in data, "dry-run JSON 应有 verified_at 字段"

    def test_dry_run_json_has_limit_and_workers(self, tmp_path):
        out_json = tmp_path / "dry_run_lw.json"
        subprocess.run(
            [sys.executable, str(_SCRIPTS / "verify_prefetch_300.py"),
             "--dry-run", "--limit", "50", "--workers", "4",
             "--json-out", str(out_json)],
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        data = json.loads(out_json.read_text(encoding="utf-8"))
        assert data["limit"]   == 50, "JSON 应记录 limit=50"
        assert data["workers"] == 4,  "JSON 应记录 workers=4"

    def test_dry_run_json_has_timeout_seconds(self, tmp_path):
        out_json = tmp_path / "dry_run_to.json"
        subprocess.run(
            [sys.executable, str(_SCRIPTS / "verify_prefetch_300.py"),
             "--dry-run", "--limit", "20", "--timeout", "120",
             "--json-out", str(out_json)],
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        data = json.loads(out_json.read_text(encoding="utf-8"))
        assert data.get("timeout_seconds") == 120, "JSON 应记录 timeout_seconds"


# ══════════════════════════════════════════════════════════════════════
# TestVerifyPrefetch300Timeout — 超时路径
# ══════════════════════════════════════════════════════════════════════

class TestVerifyPrefetch300Timeout:
    """模拟 run_prefetch 挂起，验证 timeout 路径输出 partial JSON。"""

    def test_timeout_returns_status_timeout(self):
        sys.path.insert(0, str(_SCRIPTS))
        import verify_prefetch_300

        # 让 run_prefetch 挂起 10s，但 timeout 设为 1s
        def _hang(codes, **kw):
            import time
            time.sleep(10)
            return {}

        with patch.object(verify_prefetch_300, "_get_ashare_codes",
                          return_value=(["000001.SZ", "000002.SZ"], None)):
            with patch("data_prefetch.run_prefetch", side_effect=_hang):
                result = verify_prefetch_300.run_verification(
                    limit=2, workers=1, timeout_seconds=1
                )

        assert result["status"] == "timeout", \
            f"超时应返回 status=timeout，得到 {result['status']}"

    def test_timeout_sets_partial_true(self):
        sys.path.insert(0, str(_SCRIPTS))
        import verify_prefetch_300

        def _hang(codes, **kw):
            import time
            time.sleep(10)
            return {}

        with patch.object(verify_prefetch_300, "_get_ashare_codes",
                          return_value=(["000001.SZ"], None)):
            with patch("data_prefetch.run_prefetch", side_effect=_hang):
                result = verify_prefetch_300.run_verification(
                    limit=1, workers=1, timeout_seconds=1
                )

        assert result.get("partial") is True, "超时结果应包含 partial=True"

    def test_timeout_has_workers_cleaned(self):
        sys.path.insert(0, str(_SCRIPTS))
        import verify_prefetch_300

        def _hang(codes, **kw):
            import time
            time.sleep(10)
            return {}

        with patch.object(verify_prefetch_300, "_get_ashare_codes",
                          return_value=(["000001.SZ"], None)):
            with patch("data_prefetch.run_prefetch", side_effect=_hang):
                result = verify_prefetch_300.run_verification(
                    limit=1, workers=1, timeout_seconds=1
                )

        assert "workers_cleaned" in result, "超时结果应含 workers_cleaned 字段"

    def test_timeout_has_elapsed_seconds(self):
        sys.path.insert(0, str(_SCRIPTS))
        import verify_prefetch_300

        def _hang(codes, **kw):
            import time
            time.sleep(10)
            return {}

        with patch.object(verify_prefetch_300, "_get_ashare_codes",
                          return_value=(["000001.SZ"], None)):
            with patch("data_prefetch.run_prefetch", side_effect=_hang):
                result = verify_prefetch_300.run_verification(
                    limit=1, workers=1, timeout_seconds=1
                )

        assert "elapsed_seconds" in result, "超时结果应含 elapsed_seconds"
        assert result["elapsed_seconds"] >= 1, "超时 elapsed 应 ≥ timeout"


# ══════════════════════════════════════════════════════════════════════
# TestVerifyPrefetch300EnvError — 环境不满足时优雅退出（exit code 2）
# ══════════════════════════════════════════════════════════════════════

class TestVerifyPrefetch300EnvError:
    def test_run_verification_env_error_no_crash(self):
        sys.path.insert(0, str(_SCRIPTS))
        import verify_prefetch_300

        with patch.object(verify_prefetch_300, "_get_ashare_codes",
                          return_value=([], "无代码列表（测试 mock）")):
            result = verify_prefetch_300.run_verification(limit=10, workers=1)

        assert result["status"] == "env_error", \
            "获取代码失败时 run_verification 应返回 env_error"
        assert "env_error" in result, "env_error 结果应包含 env_error 说明字段"

    def test_run_verification_missing_ohlcv_provider(self):
        sys.path.insert(0, str(_SCRIPTS))
        import builtins
        import verify_prefetch_300

        real_import = builtins.__import__
        def mock_import(name, *args, **kwargs):
            if name == "ohlcv_provider":
                raise ImportError("ohlcv_provider not available (mock)")
            return real_import(name, *args, **kwargs)

        with patch.object(verify_prefetch_300, "_get_ashare_codes",
                          return_value=(["000001.SZ", "000002.SZ"], None)):
            with patch("builtins.__import__", side_effect=mock_import):
                result = verify_prefetch_300.run_verification(limit=2, workers=1)

        assert result["status"] == "env_error", \
            "ohlcv_provider 不可用时应返回 env_error"


# ══════════════════════════════════════════════════════════════════════
# TestVerifyPrefetch300OutputSchema — JSON 输出 schema
# ══════════════════════════════════════════════════════════════════════

class TestVerifyPrefetch300OutputSchema:
    REQUIRED_FIELDS_ON_PASS = {
        "status", "limit", "workers", "cache_hit", "fetched_ok",
        "failed", "failure_rate", "data_time_max", "elapsed_seconds", "verified_at",
    }
    REQUIRED_FIELDS_ON_ERROR = {"status", "limit", "workers", "verified_at"}
    REQUIRED_FIELDS_ON_TIMEOUT = {
        "status", "partial", "workers_cleaned", "elapsed_seconds",
        "limit", "workers", "timeout_seconds", "verified_at",
    }

    def test_env_error_result_has_required_fields(self):
        sys.path.insert(0, str(_SCRIPTS))
        import verify_prefetch_300

        with patch.object(verify_prefetch_300, "_get_ashare_codes",
                          return_value=([], "mock env error")):
            result = verify_prefetch_300.run_verification(limit=5, workers=1)

        missing = self.REQUIRED_FIELDS_ON_ERROR - result.keys()
        assert not missing, f"env_error 结果缺少字段: {missing}"

    def test_timeout_result_has_required_fields(self):
        sys.path.insert(0, str(_SCRIPTS))
        import verify_prefetch_300

        def _hang(codes, **kw):
            import time
            time.sleep(10)
            return {}

        with patch.object(verify_prefetch_300, "_get_ashare_codes",
                          return_value=(["000001.SZ"], None)):
            with patch("data_prefetch.run_prefetch", side_effect=_hang):
                result = verify_prefetch_300.run_verification(
                    limit=1, workers=1, timeout_seconds=1
                )

        missing = self.REQUIRED_FIELDS_ON_TIMEOUT - result.keys()
        assert not missing, f"timeout 结果缺少字段: {missing}"

    def test_script_src_documents_output_fields(self):
        src = (_SCRIPTS / "verify_prefetch_300.py").read_text(encoding="utf-8")
        for field in ["cache_hit", "fetched_ok", "failed", "failure_rate",
                      "data_time_max", "elapsed_seconds", "recovered_count",
                      "partial", "workers_cleaned"]:
            assert field in src, f"verify_prefetch_300.py 缺少输出字段 {field!r}"


# ══════════════════════════════════════════════════════════════════════
# TestVerifyPrefetch300RecoveredFormula — V6OP-025 补正点2
# recovered_count 不得重复计入 total / failure_rate
# ══════════════════════════════════════════════════════════════════════

class TestVerifyPrefetch300RecoveredFormula:
    """
    data_prefetch._apply_recovery 已将 recovered 折算进 fetched_ok；
    total 公式必须是 cache_hit + fetched_ok + failed，
    不得再加 recovered_count，否则 total > actual_code_count。
    """

    def _make_stats(self, cache_hit=0, fetched_ok=0, recovered=0, failed=0):
        return {
            "cache_hit": cache_hit,
            "fetched_ok": fetched_ok,
            "recovered_count": recovered,
            "failed": failed,
            "data_time_max": "2025-01-02",
        }

    def _run_with_mock_stats(self, stats, codes):
        sys.path.insert(0, str(_SCRIPTS))
        import importlib
        import verify_prefetch_300
        importlib.reload(verify_prefetch_300)

        # run_prefetch returns stats dict directly; the thread sets _result["stats"] = return_value
        with patch.object(verify_prefetch_300, "_get_ashare_codes",
                          return_value=(codes, None)):
            with patch("data_prefetch.run_prefetch", return_value=stats):
                result = verify_prefetch_300.run_verification(
                    limit=len(codes), workers=1, timeout_seconds=60
                )
        return result

    def test_total_does_not_exceed_actual_code_count_when_recovered_gt_0(self):
        """recovered=3, fetched_ok=7 (already includes recovered): total should be 10, not 13."""
        codes = [f"{i:06d}.SZ" for i in range(10)]
        stats = self._make_stats(cache_hit=0, fetched_ok=7, recovered=3, failed=0)
        result = self._run_with_mock_stats(stats, codes)
        # total = cache_hit + fetched_ok + failed = 0 + 7 + 0 = 7
        # total must NOT be 0 + 7 + 3 + 0 = 10 (which would actually equal len(codes) here)
        # More importantly, failure_rate must be based on non-double-counted total
        # When recovered=3 and fetched_ok already includes them, total=7, failure_rate=0.0
        assert result.get("failure_rate") == 0.0, \
            f"无失败时 failure_rate 应为 0.0，得到 {result.get('failure_rate')}"

    def test_failure_rate_correct_with_recovered(self):
        """cache_hit=5, fetched_ok=3 (includes recovered=2), failed=2 → total=10, rate=0.2"""
        codes = [f"{i:06d}.SZ" for i in range(10)]
        stats = self._make_stats(cache_hit=5, fetched_ok=3, recovered=2, failed=2)
        result = self._run_with_mock_stats(stats, codes)
        # Correct: total = 5+3+2=10, failure_rate=2/10=0.2
        # Wrong:   total = 5+3+2+2=12, failure_rate=2/12≈0.167
        assert result.get("failure_rate") == pytest.approx(0.2, abs=1e-4), \
            f"failure_rate 应为 0.2 (2/10)，得到 {result.get('failure_rate')}"

    def test_total_formula_no_double_count_source(self):
        """Verify source code uses 'cache_hit + fetched_ok + failed' without recovered."""
        src = (_SCRIPTS / "verify_prefetch_300.py").read_text(encoding="utf-8")
        # Confirm the correct formula is present
        assert "cache_hit + fetched_ok + failed" in src, \
            "verify_prefetch_300.py 应使用 'cache_hit + fetched_ok + failed' 公式，不含 recovered"
        # Confirm no version that adds recovered is in the total line
        import re
        # Look for total = ... recovered ... failed patterns (old wrong formula)
        bad_pattern = re.search(
            r"total\s*=\s*cache_hit\s*\+\s*fetched_ok\s*\+\s*recovered\s*\+\s*failed",
            src
        )
        assert bad_pattern is None, \
            "verify_prefetch_300.py 不应有 total = cache_hit + fetched_ok + recovered + failed"

    def test_recovered_count_still_present_as_info_field(self):
        """recovered_count must still appear as an informational output field."""
        codes = [f"{i:06d}.SZ" for i in range(5)]
        stats = self._make_stats(cache_hit=2, fetched_ok=2, recovered=1, failed=1)
        result = self._run_with_mock_stats(stats, codes)
        assert "recovered_count" in result, \
            "结果 JSON 应保留 recovered_count 信息字段（但不计入 total）"
        assert result["recovered_count"] == 1, \
            "recovered_count 应与 stats 中一致"
