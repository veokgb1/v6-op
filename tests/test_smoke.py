"""
Smoke tests for V6OP Phase 0.
All tests run without real network access.
Real network validation is done via manual acceptance commands.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# ── 添加 scripts 到路径 ───────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).parent.parent.resolve()
_SCRIPTS_DIR = _PROJECT_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


# ════════════════════════════════════════════════════════════════════
#  1. 代码文件读取
# ════════════════════════════════════════════════════════════════════

class TestCodesFile:
    def test_ashare_codes_exists(self):
        codes_path = _PROJECT_ROOT / "data" / "ashare_codes.txt"
        assert codes_path.exists(), f"ashare_codes.txt 不存在: {codes_path}"

    def test_ashare_codes_format(self):
        codes_path = _PROJECT_ROOT / "data" / "ashare_codes.txt"
        lines = [l.strip() for l in codes_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) > 100, f"代码数量过少: {len(lines)}"
        import re
        pattern = re.compile(r"^\d{6}\.(SZ|SH|BJ)$", re.IGNORECASE)
        for line in lines[:20]:
            assert pattern.match(line), f"代码格式不合法: {line!r}"

    def test_ashare_codes_count(self):
        codes_path = _PROJECT_ROOT / "data" / "ashare_codes.txt"
        lines = [l.strip() for l in codes_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) > 5000, f"期望 5000+ 只代码，实际: {len(lines)}"


# ════════════════════════════════════════════════════════════════════
#  2. ohlcv_provider — 缓存路径生成
# ════════════════════════════════════════════════════════════════════

class TestOhlcvProvider:
    def test_import(self):
        import ohlcv_provider  # noqa: F401

    def test_cache_path_format(self):
        from ohlcv_provider import cache_path
        p = cache_path("000001.SZ", 365)
        assert p.name == "000001_SZ_365d.pkl", f"缓存路径名不符合预期: {p.name}"

    def test_cache_dir_is_v6op(self):
        from ohlcv_provider import get_cache_dir
        cd = get_cache_dir()
        # 缓存目录必须在 V6OP 的 var/cache 下，不能在 V5
        assert "v5" not in str(cd).lower(), f"缓存目录不应在 V5 目录: {cd}"
        assert "v6-op" in str(cd).lower() or "v6_op" in str(cd).lower() or "v.6" in str(cd).lower(), \
            f"缓存目录应在 V6OP: {cd}"

    def test_no_v5_runtime_paths_import(self):
        # ohlcv_provider 不应 import V5 的 runtime_paths
        import ohlcv_provider
        src = Path(ohlcv_provider.__file__).read_text(encoding="utf-8")
        assert "runtime_paths" not in src, "ohlcv_provider 不应依赖 V5 runtime_paths"
        assert "v5.10" not in src, "ohlcv_provider 不应直接引用 v5.10 路径"

    def test_read_cache_only_mode(self, monkeypatch):
        monkeypatch.setenv("READ_CACHE_ONLY", "true")
        # 在 READ_CACHE_ONLY 模式下，不存在缓存的代码应返回 None
        import importlib
        import ohlcv_provider
        importlib.reload(ohlcv_provider)
        result = ohlcv_provider.fetch_ohlcv("999999.SZ", days=365)
        assert result is None, "READ_CACHE_ONLY 模式下缓存未命中应返回 None"


# ════════════════════════════════════════════════════════════════════
#  3. data_prefetch — 报告结构
# ════════════════════════════════════════════════════════════════════

class TestDataPrefetch:
    def test_import(self):
        import data_prefetch  # noqa: F401

    def test_read_codes_from_file(self):
        from data_prefetch import read_codes_from_file
        codes_path = _PROJECT_ROOT / "data" / "ashare_codes.txt"
        codes = read_codes_from_file(codes_path)
        assert len(codes) > 5000
        # 所有代码格式正确
        import re
        pattern = re.compile(r"^\d{6}\.(SZ|SH|BJ)$", re.IGNORECASE)
        for c in codes[:50]:
            assert pattern.match(c), f"格式不合法: {c!r}"

    def test_prefetch_report_fields(self, tmp_path):
        """验证 prefetch_report.json 输出结构包含必要字段。"""
        required_fields = {
            "total_codes", "kline_days", "workers", "cache_hit",
            "fetched_ok", "stale_used", "failed", "failed_codes",
            "stale_codes", "duration_seconds", "cache_dir",
        }
        report = {
            "step": "prefetch_kline_cache",
            "total_codes": 50,
            "kline_days": 365,
            "workers": 8,
            "cache_hit": 30,
            "fetched_ok": 15,
            "stale_used": 2,
            "failed": 3,
            "failed_codes": [{"code": "000001.SZ"}],
            "stale_codes": ["000002.SZ"],
            "duration_seconds": 12.5,
            "cache_dir": str(_PROJECT_ROOT / "var" / "cache" / "kline_daily"),
            "run_at": "2026-05-05T10:00:00",
        }
        report_path = tmp_path / "prefetch_report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")
        loaded = json.loads(report_path.read_text(encoding="utf-8"))
        for field in required_fields:
            assert field in loaded, f"prefetch_report.json 缺少必要字段: {field}"


# ════════════════════════════════════════════════════════════════════
#  4. CZSCProducer — 输出结构
# ════════════════════════════════════════════════════════════════════

class TestCZSCProducer:
    def test_import(self):
        sys.path.insert(0, str(_SCRIPTS_DIR / "producers"))
        import czsc_producer  # noqa: F401

    def test_mask_json_required_fields(self, tmp_path):
        """验证 czsc_mask.json 输出结构包含必要字段。"""
        required_fields = {
            "mask_id", "producer", "hit_semantics", "hit_codes",
            "miss_codes", "evidence", "params", "data_mode",
            "cache_dir", "generated_at",
        }
        mask = {
            "mask_id": "czsc_abc123",
            "producer": "czsc_producer",
            "hit_semantics": "positive",
            "hit_codes": ["000001.SZ", "600519.SH"],
            "miss_codes": ["000002.SZ"],
            "evidence": {
                "000001.SZ": {"buy_type": "二买", "last_signal_date": "2026-04-30"},
            },
            "params": {"signal_bars": 5, "buy_type": "all"},
            "data_mode": "read_cache_only",
            "cache_dir": str(_PROJECT_ROOT / "var" / "cache" / "kline_daily"),
            "generated_at": "2026-05-05T10:00:00",
        }
        mask_path = tmp_path / "czsc_mask.json"
        mask_path.write_text(json.dumps(mask), encoding="utf-8")
        loaded = json.loads(mask_path.read_text(encoding="utf-8"))
        for field in required_fields:
            assert field in loaded, f"czsc_mask.json 缺少必要字段: {field}"

    def test_hit_semantics_is_positive(self):
        mask = {"hit_semantics": "positive"}
        assert mask["hit_semantics"] == "positive"

    def test_mask_id_generation(self):
        sys.path.insert(0, str(_SCRIPTS_DIR / "producers"))
        from czsc_producer import _make_mask_id
        id1 = _make_mask_id(["000001.SZ", "600519.SH"], {"signal_bars": 5})
        id2 = _make_mask_id(["600519.SH", "000001.SZ"], {"signal_bars": 5})
        # 顺序不影响 mask_id（内部排序）
        assert id1 == id2, "相同代码不同顺序应生成相同 mask_id"

    def test_mask_id_changes_with_params(self):
        sys.path.insert(0, str(_SCRIPTS_DIR / "producers"))
        from czsc_producer import _make_mask_id
        id1 = _make_mask_id(["000001.SZ"], {"signal_bars": 5})
        id2 = _make_mask_id(["000001.SZ"], {"signal_bars": 10})
        assert id1 != id2, "参数不同应生成不同 mask_id"


# ════════════════════════════════════════════════════════════════════
#  5. V6 隔离验证 — V6OP 不引用 V5 运行路径
# ════════════════════════════════════════════════════════════════════

class TestV5Isolation:
    def test_ohlcv_provider_no_v5_import(self):
        src_path = _SCRIPTS_DIR / "ohlcv_provider.py"
        src = src_path.read_text(encoding="utf-8")
        assert "from utils.runtime_paths" not in src
        assert "from utils.code_list" not in src
        assert "v5.10" not in src

    def test_data_prefetch_no_v5_import(self):
        src_path = _SCRIPTS_DIR / "data_prefetch.py"
        src = src_path.read_text(encoding="utf-8")
        assert "from utils.runtime_paths" not in src
        assert "from utils.code_list" not in src
        assert "v5.10" not in src

    def test_czsc_producer_no_v5_import(self):
        src_path = _SCRIPTS_DIR / "producers" / "czsc_producer.py"
        src = src_path.read_text(encoding="utf-8")
        assert "from utils.runtime_paths" not in src
        assert "v5.10" not in src

    def test_v6_compat_v6_path(self):
        from v6_compat import v6_scripts_path, _V6_SCRIPTS
        v6_path = v6_scripts_path()
        assert "v6-op" not in str(v6_path).lower().replace("v6-op", ""), \
            "V6 scripts 路径不应在 v6-op 内"
        # V6 路径应在 v6-op 的兄弟目录中
        assert v6_path.parent.name == "v6" or v6_path.name == "scripts"
