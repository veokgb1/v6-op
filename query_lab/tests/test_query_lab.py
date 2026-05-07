"""
test_query_lab.py — QueryLab 离线测试

测试目标：
1. 中文 Query 预检器正确工作
2. schema 校验器正确工作
3. CSV 用例文件可正常读取
4. 结果分类器正确分类
5. dry-run 路由正确
6. 英文 Query 被 invalid_query 拦截
7. A股和板块路由分离
8. 法典文件可读取
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

# 路径设置
_TESTS_DIR = Path(__file__).parent.resolve()
_QUERY_LAB_DIR = _TESTS_DIR.parent
_SCRIPTS_DIR = _QUERY_LAB_DIR / "scripts"
_PROJECT_ROOT = _QUERY_LAB_DIR.parent

sys.path.insert(0, str(_SCRIPTS_DIR))

from validators.chinese_query_validator import ChineseQueryValidator
from validators.schema_validator import SchemaValidator


# ─────────────────────────────────────────────────────────────────────────────
# 1. 中文 Query 预检器测试
# ─────────────────────────────────────────────────────────────────────────────

class TestChineseQueryValidator:
    def setup_method(self):
        self.validator = ChineseQueryValidator()

    def test_valid_simple_chinese(self):
        """基础中文 Query 通过预检"""
        result = self.validator.validate("今日涨幅大于3%")
        assert result.valid is True
        assert result.status == "ok"

    def test_valid_with_whitelist_abbrev(self):
        """含白名单缩写的 Query 通过预检"""
        for q in [
            "非ST，今日涨幅大于3%",
            "今日MACD金叉",
            "今日KDJ金叉",
            "流通市值在30亿到150亿之间的A股",
            "ETF持仓占比高的股票",
        ]:
            result = self.validator.validate(q)
            assert result.valid is True, f"应通过但未通过: {q!r}  reason={result.reason}"

    def test_invalid_english_sentence(self):
        """英文整句被拦截"""
        for q in [
            "A-shares with market cap between 3 and 15 billion",
            "stocks with volume ratio greater than 2",
            "select stocks with high turnover rate today",
        ]:
            result = self.validator.validate(q)
            assert result.valid is False, f"应被拦截但通过: {q!r}"
            assert result.status == "invalid_query"

    def test_invalid_empty(self):
        """空 Query 被拦截"""
        result = self.validator.validate("")
        assert result.valid is False
        assert result.status == "invalid_query"

    def test_invalid_whitespace_only(self):
        """纯空白 Query 被拦截"""
        result = self.validator.validate("   ")
        assert result.valid is False
        assert result.status == "invalid_query"

    def test_invalid_no_chinese(self):
        """无中文字符的 Query 被拦截"""
        result = self.validator.validate("MACD KDJ ST")
        assert result.valid is False
        assert result.status == "invalid_query"

    def test_valid_with_numbers_and_percent(self):
        """含数字和百分号的中文 Query 通过"""
        result = self.validator.validate("今日换手率大于5%，成交额大于3亿")
        assert result.valid is True

    def test_valid_complex_combo(self):
        """复杂组合 Query 通过"""
        q = "非ST，非停牌，今日涨幅大于3%，今日成交额大于3亿，今日换手率大于5%，流通市值在30亿到150亿之间"
        result = self.validator.validate(q)
        assert result.valid is True

    def test_invalid_mixed_english_sentence(self):
        """混有英文整句的 Query 被拦截"""
        result = self.validator.validate("today is good day and stock rise more than three percent")
        assert result.valid is False


# ─────────────────────────────────────────────────────────────────────────────
# 2. Schema 校验器测试
# ─────────────────────────────────────────────────────────────────────────────

class TestSchemaValidator:
    def setup_method(self):
        self.validator = SchemaValidator()

    def _valid_row(self) -> dict:
        return {
            "query_id": "A1-001",
            "skill_type": "astock",
            "skill_name_zh": "问财选A股",
            "op_domain": "wencai_query",
            "test_group": "A1_basic",
            "category": "single_field",
            "query_text": "今日涨幅大于3%",
            "normalized_intent": "今日涨幅>3%",
            "status": "pending",
        }

    def test_valid_row(self):
        result = self.validator.validate_row(self._valid_row())
        assert result.valid is True

    def test_missing_required_field(self):
        row = self._valid_row()
        del row["query_text"]
        result = self.validator.validate_row(row)
        assert result.valid is False
        assert any("query_text" in e for e in result.errors)

    def test_invalid_skill_type(self):
        row = self._valid_row()
        row["skill_type"] = "unknown_skill"
        result = self.validator.validate_row(row)
        assert result.valid is False

    def test_invalid_status(self):
        row = self._valid_row()
        row["status"] = "invented_status"
        result = self.validator.validate_row(row)
        assert result.valid is False

    def test_valid_sector_skill(self):
        row = self._valid_row()
        row["skill_type"] = "sector"
        row["skill_name_zh"] = "问财选板块"
        result = self.validator.validate_row(row)
        assert result.valid is True


# ─────────────────────────────────────────────────────────────────────────────
# 3. CSV 用例文件读取测试
# ─────────────────────────────────────────────────────────────────────────────

class TestCaseFiles:
    CASES_DIR = _QUERY_LAB_DIR / "cases"
    REQUIRED_CSV_FIELDS = ["query_id", "skill_type", "query_text", "status"]

    def _read_csv(self, path: Path) -> list[dict]:
        rows = []
        with path.open(encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(dict(row))
        return rows

    def test_astock_a1_basic_exists(self):
        p = self.CASES_DIR / "astock_问财选A股" / "A1_basic.csv"
        assert p.exists(), f"文件不存在: {p}"

    def test_astock_a2_synonym_exists(self):
        p = self.CASES_DIR / "astock_问财选A股" / "A2_synonym.csv"
        assert p.exists(), f"文件不存在: {p}"

    def test_astock_a3_combo_exists(self):
        p = self.CASES_DIR / "astock_问财选A股" / "A3_combo.csv"
        assert p.exists(), f"文件不存在: {p}"

    def test_sector_s1_basic_exists(self):
        p = self.CASES_DIR / "sector_问财选板块" / "S1_basic.csv"
        assert p.exists(), f"文件不存在: {p}"

    def test_astock_a1_has_required_fields(self):
        p = self.CASES_DIR / "astock_问财选A股" / "A1_basic.csv"
        rows = self._read_csv(p)
        assert len(rows) > 0, "A1_basic.csv 为空"
        for field in self.REQUIRED_CSV_FIELDS:
            assert field in rows[0], f"缺少字段: {field}"

    def test_all_astock_queries_are_chinese(self):
        """A股 CSV 中 query_text 必须通过中文预检（A5_forbidden.csv 除外）"""
        validator = ChineseQueryValidator()
        for csv_file in sorted((self.CASES_DIR / "astock_问财选A股").glob("*.csv")):
            if "forbidden" in csv_file.name or "A5" in csv_file.name:
                continue
            rows = self._read_csv(csv_file)
            for row in rows:
                qt = row.get("query_text", "").strip()
                if not qt:
                    continue
                result = validator.validate(qt)
                assert result.valid, (
                    f"文件={csv_file.name} query_id={row.get('query_id','')} "
                    f"query_text={qt!r} 未通过中文预检: {result.reason}"
                )

    def test_sector_queries_are_chinese(self):
        """板块 CSV 中 query_text 通过中文预检（risky 文件的 forbidden_word 除外）"""
        validator = ChineseQueryValidator()
        for csv_file in sorted((self.CASES_DIR / "sector_问财选板块").glob("*.csv")):
            rows = self._read_csv(csv_file)
            for row in rows:
                qt = row.get("query_text", "").strip()
                category = row.get("category", "")
                if not qt or category in ("forbidden_word", "invalid_query"):
                    continue
                result = validator.validate(qt)
                assert result.valid, (
                    f"文件={csv_file.name} query_id={row.get('query_id','')} "
                    f"query_text={qt!r} 未通过中文预检: {result.reason}"
                )

    def test_astock_and_sector_are_separate(self):
        """A股和板块 skill_type 不混用"""
        astock_rows = []
        sector_rows = []
        for csv_file in (self.CASES_DIR / "astock_问财选A股").glob("*.csv"):
            astock_rows.extend(self._read_csv(csv_file))
        for csv_file in (self.CASES_DIR / "sector_问财选板块").glob("*.csv"):
            sector_rows.extend(self._read_csv(csv_file))

        for row in astock_rows:
            assert row.get("skill_type") == "astock", (
                f"A股目录中发现非 astock: {row.get('query_id')} skill_type={row.get('skill_type')}"
            )
        for row in sector_rows:
            assert row.get("skill_type") == "sector", (
                f"板块目录中发现非 sector: {row.get('query_id')} skill_type={row.get('skill_type')}"
            )

    def test_query_ids_unique(self):
        """所有用例的 query_id 不重复"""
        ids: list[str] = []
        for sub in ["astock_问财选A股", "sector_问财选板块"]:
            for csv_file in (self.CASES_DIR / sub).glob("*.csv"):
                rows = self._read_csv(csv_file)
                ids.extend(r.get("query_id", "") for r in rows)
        duplicates = [qid for qid in ids if ids.count(qid) > 1]
        assert not duplicates, f"发现重复 query_id: {list(set(duplicates))}"

    def test_pending_queries_csv_exists(self):
        p = self.CASES_DIR / "extensions" / "pending_queries.csv"
        assert p.exists(), f"pending_queries.csv 不存在: {p}"


# ─────────────────────────────────────────────────────────────────────────────
# 4. 结果分类器测试
# ─────────────────────────────────────────────────────────────────────────────

class TestResultAnalyzer:
    def setup_method(self):
        from result_analyzer import ResultAnalyzer
        self.analyzer = ResultAnalyzer(_QUERY_LAB_DIR)

    def _make_result(self, **kwargs) -> dict:
        base = {
            "run_id": "run_test",
            "query_id": "TEST-001",
            "skill_type": "astock",
            "skill_name_zh": "问财选A股",
            "test_group": "A1_basic",
            "category": "single_field",
            "query_text": "今日涨幅大于3%",
            "normalized_intent": "涨幅>3%",
            "actual_query_backend": "stock",
            "op_domain": "wencai_query",
            "op_topic": "price_change",
            "source_origin": "test",
            "version": "v1",
            "condition_count": 1,
            "field_atoms": "今日涨幅",
            "risk_tags": "",
            "exec_status": "ok",
            "result_count": 50,
            "elapsed_ms": 1200.0,
            "raw_error": "",
            "status": "pending",
            "risk_level": "",
            "recommended_usage": "",
            "notes": "",
        }
        base.update(kwargs)
        return base

    def _make_ar(self, **kwargs):
        from result_analyzer import AnalysisResult
        defaults = dict(
            run_id="run_test", query_id="TEST-001", skill_type="astock",
            skill_name_zh="问财选A股", test_group="A1_basic", category="single_field",
            query_text="今日涨幅大于3%", normalized_intent="涨幅>3%",
            condition_count=1, field_atoms="今日涨幅", risk_tags="",
            actual_query_backend="stock", exec_status="ok",
            analysis_status="stable", risk_level="low", recommended_usage="strong",
            result_count=50, elapsed_ms=1200.0, raw_error="",
            failure_type="none", failure_reason_zh="", notes="",
        )
        defaults.update(kwargs)
        return AnalysisResult(**defaults)

    def test_ok_with_results_is_stable(self):
        result = self._make_result(exec_status="ok", result_count=50, risk_tags="")
        ar = self.analyzer._classify(result)
        assert ar.analysis_status == "stable"
        assert ar.recommended_usage == "strong"

    def test_empty_result_is_failed(self):
        result = self._make_result(exec_status="empty_result", result_count=0)
        ar = self.analyzer._classify(result)
        assert ar.analysis_status == "failed"

    def test_invalid_query_status(self):
        result = self._make_result(exec_status="invalid_query", result_count=0)
        ar = self.analyzer._classify(result)
        assert ar.analysis_status == "invalid_query"
        assert ar.risk_level == "critical"

    def test_forbidden_word_category(self):
        result = self._make_result(
            exec_status="pending",
            category="forbidden_word",
            result_count=0,
        )
        ar = self.analyzer._classify(result)
        assert ar.analysis_status == "forbidden"

    def test_risky_tag_causes_risky_status(self):
        # risky tags on an ok result with results
        result = self._make_result(
            exec_status="ok",
            risk_tags="vague_word|sentiment_word",
            result_count=100,
        )
        ar = self.analyzer._classify(result)
        assert ar.analysis_status == "risky"

    def test_dry_run_is_pending(self):
        result = self._make_result(exec_status="dry_run", result_count=0)
        ar = self.analyzer._classify(result)
        assert ar.analysis_status == "pending"

    def test_api_error_is_failed(self):
        result = self._make_result(exec_status="api_error", result_count=0, elapsed_ms=8000.0)
        ar = self.analyzer._classify(result)
        assert ar.analysis_status == "failed"
        assert ar.failure_type == "api_error"

    def test_session_error_detection(self):
        """api_error with elapsed < 5000ms → session_error"""
        result = self._make_result(exec_status="api_error", result_count=0, elapsed_ms=2500.0)
        ar = self.analyzer._classify(result)
        assert ar.analysis_status == "failed"
        assert ar.failure_type == "session_error"

    def test_summary_counts(self):
        analyzed = [
            self._make_ar(query_id="1", analysis_status="stable"),
            self._make_ar(query_id="2", analysis_status="invalid_query",
                          exec_status="invalid_query", risk_level="critical",
                          recommended_usage="forbidden", failure_type="invalid_query"),
            self._make_ar(query_id="3", analysis_status="forbidden",
                          exec_status="pending", risk_level="high",
                          recommended_usage="forbidden", failure_type="none"),
        ]
        summary = self.analyzer.summary(analyzed)
        assert summary["total"] == 3
        assert summary["stable"] == 1
        assert summary["invalid_query"] == 1
        assert summary["forbidden"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# 5. 注册表文件测试
# ─────────────────────────────────────────────────────────────────────────────

class TestRegistry:
    REGISTRY_DIR = _QUERY_LAB_DIR / "registry"

    def _read_csv(self, path: Path) -> list[dict]:
        with path.open(encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))

    def test_skills_registry_exists(self):
        p = self.REGISTRY_DIR / "skills_registry.csv"
        assert p.exists()

    def test_skills_registry_has_astock_and_sector(self):
        rows = self._read_csv(self.REGISTRY_DIR / "skills_registry.csv")
        skill_keys = {r["skill_key"] for r in rows}
        assert "astock" in skill_keys
        assert "sector" in skill_keys

    def test_fields_registry_exists(self):
        p = self.REGISTRY_DIR / "fields_registry.csv"
        assert p.exists()

    def test_status_rules_exists(self):
        p = self.REGISTRY_DIR / "status_rules.json"
        assert p.exists()
        data = json.loads(p.read_text(encoding="utf-8"))
        assert "status_definitions" in data
        assert "stable" in data["status_definitions"]
        assert "forbidden" in data["status_definitions"]
        assert "invalid_query" in data["status_definitions"]

    def test_chinese_whitelist_in_status_rules(self):
        data = json.loads((self.REGISTRY_DIR / "status_rules.json").read_text(encoding="utf-8"))
        whitelist = data.get("chinese_whitelist_abbrev", [])
        assert "A股" in whitelist
        assert "ST" in whitelist
        assert "MACD" in whitelist


# ─────────────────────────────────────────────────────────────────────────────
# 6. 法典文件测试
# ─────────────────────────────────────────────────────────────────────────────

class TestCanonFiles:
    CANON_DIR = _QUERY_LAB_DIR / "canon"

    def test_astock_canon_csv_exists(self):
        p = self.CANON_DIR / "skills" / "astock_问财选A股" / "canon.csv"
        assert p.exists()

    def test_sector_canon_csv_exists(self):
        p = self.CANON_DIR / "skills" / "sector_问财选板块" / "canon.csv"
        assert p.exists()

    def test_astock_canon_has_correct_headers(self):
        p = self.CANON_DIR / "skills" / "astock_问财选A股" / "canon.csv"
        with p.open(encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
        assert "canon_id" in headers
        assert "canonical_query_text" in headers
        assert "reference_mode" in headers
        assert "status" in headers

    def test_review_queue_dir_exists(self):
        p = self.CANON_DIR / "review_queue"
        assert p.exists()

    def test_manual_overrides_csv_exists(self):
        p = self.CANON_DIR / "manual_overrides" / "manual_overrides.csv"
        assert p.exists()

    def test_conflicts_dir_exists(self):
        p = self.CANON_DIR / "conflicts"
        assert p.exists()


# ─────────────────────────────────────────────────────────────────────────────
# 7. dry-run 路由测试
# ─────────────────────────────────────────────────────────────────────────────

class TestDryRun:
    def test_dry_run_loads_astock_cases(self):
        from query_runner import _load_cases
        cases_dir = _QUERY_LAB_DIR / "cases"
        rows = _load_cases(cases_dir, route="astock", group=None, limit=0)
        assert len(rows) > 0
        for r in rows:
            assert r["skill_type"] == "astock"

    def test_dry_run_loads_sector_cases(self):
        from query_runner import _load_cases
        cases_dir = _QUERY_LAB_DIR / "cases"
        rows = _load_cases(cases_dir, route="sector", group=None, limit=0)
        assert len(rows) > 0
        for r in rows:
            assert r["skill_type"] == "sector"

    def test_dry_run_limit(self):
        from query_runner import _load_cases
        cases_dir = _QUERY_LAB_DIR / "cases"
        rows = _load_cases(cases_dir, route="all", group=None, limit=5)
        assert len(rows) <= 5

    def test_dry_run_group_filter(self):
        from query_runner import _load_cases
        cases_dir = _QUERY_LAB_DIR / "cases"
        rows = _load_cases(cases_dir, route="astock", group="A1_basic", limit=0)
        assert len(rows) > 0
        for r in rows:
            assert r["test_group"] == "A1_basic"

    def test_dry_run_adapter_returns_dry_run_status(self):
        from adapters.wencai_astock_adapter import WencaiAstockAdapter
        adapter = WencaiAstockAdapter(_PROJECT_ROOT, dry_run=True)
        result = adapter.query("今日涨幅大于3%")
        assert result["status"] == "dry_run"
        assert result["result_count"] == 0
        assert result["skill_type"] == "astock"

    def test_sector_adapter_dry_run(self):
        from adapters.wencai_sector_adapter import WencaiSectorAdapter
        adapter = WencaiSectorAdapter(_PROJECT_ROOT, dry_run=True)
        result = adapter.query("今日涨幅大于3%的板块")
        assert result["status"] == "dry_run"
        assert result["skill_type"] == "sector"
