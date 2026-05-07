"""
result_analyzer.py — V2 查询结果分类器（闭环版）

闭环要求：
1. 每次 run 写 analyzed_results.jsonl（含 analysis_status / failure_type / failure_reason_zh）
2. 候选变更按 skill_key + canonical_query_text 去重合并证据
3. 提供 build_failed_replay() 生成真实可用的失败回放记录
4. stable_dictionary 累计逻辑由 report_writer 负责（此处只负责落盘分析结果）
"""
from __future__ import annotations

import json
import uuid
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


# ─── 高风险标签集合 ─────────────────────────────────────────────────────────
_RISK_TAGS_HIGH = {
    "vague_word", "sentiment_word", "prediction_word", "jma_unverified",
    "non_standard_field", "sector_route_ambiguous", "english_query", "empty_query",
    "vague_condition", "relative_condition",
}

# ─── failure_type 映射 ──────────────────────────────────────────────────────
_FAILURE_TYPE_MAP = {
    "empty_result":   "empty_result",
    "api_error":      "api_error",
    "auth_failed":    "api_error",
    "network_error":  "api_error",
    "blocked":        "api_error",
    "key_missing":    "api_error",
    "invalid_query":  "invalid_query",
    "pending":        "none",
    "dry_run":        "none",
    "ok":             "none",
}

_FAILURE_REASON_ZH = {
    "empty_result":  "问财返回0条结果，条件可能过严或字段不被识别",
    "api_error":     "问财 API 接口异常（session 耗尽 / 网络 / 认证失败）",
    "auth_failed":   "问财 API 认证失败（401 Unauthorized），请检查 API Key",
    "network_error": "网络连接失败，无法到达问财服务器",
    "blocked":       "pywencai 未安装或被阻断",
    "key_missing":   "IWENCAI_API_KEY 未配置",
    "invalid_query": "中文预检失败：query_text 不含中文或含英文整句",
    "pending":       "",
    "dry_run":       "",
    "ok":            "",
}


@dataclass
class AnalysisResult:
    run_id: str
    query_id: str
    skill_type: str
    skill_name_zh: str
    test_group: str
    category: str
    query_text: str
    normalized_intent: str
    condition_count: int
    field_atoms: str
    risk_tags: str
    actual_query_backend: str
    exec_status: str
    analysis_status: str       # stable / unstable / risky / failed / forbidden / invalid_query / pending
    risk_level: str
    recommended_usage: str
    result_count: int
    elapsed_ms: float
    raw_error: str
    failure_type: str          # none / api_error / session_error / empty_result / invalid_query
    failure_reason_zh: str
    notes: str
    return_object_type: str = ""
    raw_columns: str = ""
    extracted_sector_names: str = ""
    extracted_index_codes: str = ""
    extracted_stock_codes: str = ""
    extracted_stock_names: str = ""
    extracted_reason_text: str = ""
    next_pipeline_route: str = ""


@dataclass
class CandidateEntry:
    """候选法典变更条目（去重合并版）"""
    change_id: str
    change_type: str
    canon_id: str
    skill_key: str
    skill_name_zh: str
    meaning_zh: str
    canonical_query_text: str
    old_value: str
    evidence_run_ids: list
    evidence_query_ids: list
    success_count: int
    failed_count: int
    result_count_min: int
    result_count_max: int
    result_count_avg: float
    success_rate: float
    reason: str
    created_at: str
    updated_at: str
    status: str


@dataclass
class FailedReplayEntry:
    """失败回放记录"""
    query_id: str
    query_text: str
    skill_type: str
    skill_name_zh: str
    test_group: str
    category: str
    normalized_intent: str
    condition_count: int
    field_atoms: str
    exec_status: str
    failure_type: str
    failure_reason_zh: str
    raw_error: str
    run_id: str
    created_at: str
    replay_count: int
    next_replay_after: str


class ResultAnalyzer:
    """V2 结果分类器（闭环版）"""

    def __init__(self, query_lab_dir: Path) -> None:
        self.query_lab_dir = query_lab_dir
        self.review_queue_dir = query_lab_dir / "canon" / "review_queue"
        self.review_queue_dir.mkdir(parents=True, exist_ok=True)

    # ─── 主分析入口 ──────────────────────────────────────────────────────────

    def analyze(self, results: list[Any], run_dir: Path) -> list[AnalysisResult]:
        """
        分析执行结果，返回 AnalysisResult 列表。
        同时写 analyzed_results.jsonl 到 run_dir。
        """
        analyzed: list[AnalysisResult] = []
        for r in results:
            d = asdict(r) if hasattr(r, "__dataclass_fields__") else dict(r)
            ar = self._classify(d)
            analyzed.append(ar)

        # 写 analyzed_results.jsonl
        self._write_analyzed(analyzed, run_dir)
        # 更新 candidate_changes.jsonl（去重合并）
        self._update_candidates(analyzed)
        return analyzed

    def build_failed_replay(self, analyzed: list[AnalysisResult]) -> list[FailedReplayEntry]:
        """从分析结果中提取失败项，构建回放记录。"""
        entries: list[FailedReplayEntry] = []
        for ar in analyzed:
            if ar.analysis_status in ("failed", "invalid_query"):
                entries.append(FailedReplayEntry(
                    query_id=ar.query_id,
                    query_text=ar.query_text,
                    skill_type=ar.skill_type,
                    skill_name_zh=ar.skill_name_zh,
                    test_group=ar.test_group,
                    category=ar.category,
                    normalized_intent=ar.normalized_intent,
                    condition_count=ar.condition_count,
                    field_atoms=ar.field_atoms,
                    exec_status=ar.exec_status,
                    failure_type=ar.failure_type,
                    failure_reason_zh=ar.failure_reason_zh,
                    raw_error=ar.raw_error,
                    run_id=ar.run_id,
                    created_at=datetime.now().isoformat(),
                    replay_count=0,
                    next_replay_after="",
                ))
        return entries

    def summary(self, analyzed: list[AnalysisResult]) -> dict:
        from collections import Counter
        counts = Counter(a.analysis_status for a in analyzed)
        failure_counts = Counter(a.failure_type for a in analyzed
                                 if a.failure_type and a.failure_type != "none")
        return {
            "total": len(analyzed),
            "stable": counts.get("stable", 0),
            "unstable": counts.get("unstable", 0),
            "risky": counts.get("risky", 0),
            "failed": counts.get("failed", 0),
            "forbidden": counts.get("forbidden", 0),
            "invalid_query": counts.get("invalid_query", 0),
            "pending": counts.get("pending", 0),
            "failure_types": dict(failure_counts),
        }

    # ─── 分类逻辑 ─────────────────────────────────────────────────────────────

    def _classify(self, d: dict) -> AnalysisResult:
        exec_status = d.get("exec_status", "") or ""
        risk_tags_str = d.get("risk_tags", "") or ""
        risk_tags = set(t.strip() for t in risk_tags_str.split("|") if t.strip())
        result_count = int(d.get("result_count", 0))
        category = d.get("category", "") or ""
        raw_error = d.get("raw_error", "") or ""

        failure_type = _FAILURE_TYPE_MAP.get(exec_status, "api_error")
        failure_reason_zh = _FAILURE_REASON_ZH.get(exec_status, "")
        # session 耗尽特征：耗时极短（<500ms）且是 api_error
        elapsed_ms = float(d.get("elapsed_ms", 0))
        if exec_status == "api_error" and elapsed_ms < 5000:
            failure_type = "session_error"
            failure_reason_zh = "pywencai session 耗尽或 token 过期，需等待后重试"

        base = dict(
            run_id=d.get("run_id", ""),
            query_id=d.get("query_id", "?"),
            skill_type=d.get("skill_type", ""),
            skill_name_zh=d.get("skill_name_zh", ""),
            test_group=d.get("test_group", ""),
            category=category,
            query_text=d.get("query_text", ""),
            normalized_intent=d.get("normalized_intent", ""),
            condition_count=int(d.get("condition_count", 0) or 0),
            field_atoms=d.get("field_atoms", ""),
            risk_tags=risk_tags_str,
            actual_query_backend=d.get("actual_query_backend", ""),
            exec_status=exec_status,
            result_count=result_count,
            elapsed_ms=elapsed_ms,
            raw_error=raw_error,
            return_object_type=d.get("return_object_type", ""),
            raw_columns=d.get("raw_columns", ""),
            extracted_sector_names=d.get("extracted_sector_names", ""),
            extracted_index_codes=d.get("extracted_index_codes", ""),
            extracted_stock_codes=d.get("extracted_stock_codes", ""),
            extracted_stock_names=d.get("extracted_stock_names", ""),
            extracted_reason_text=d.get("extracted_reason_text", ""),
            next_pipeline_route=d.get("next_pipeline_route", ""),
        )

        # ── invalid_query ──
        if exec_status == "invalid_query":
            return AnalysisResult(**base,
                analysis_status="invalid_query", risk_level="critical",
                recommended_usage="forbidden",
                failure_type="invalid_query",
                failure_reason_zh=_FAILURE_REASON_ZH["invalid_query"],
                notes=raw_error or "中文预检失败")

        # ── forbidden category ──
        if category in ("forbidden_word", "invalid_query"):
            return AnalysisResult(**base,
                analysis_status="forbidden", risk_level="high",
                recommended_usage="forbidden",
                failure_type="none",
                failure_reason_zh="模糊词/预测词/英文查询，属于禁用分类",
                notes="禁用分类：不得自动生成")

        # ── 高风险标签（未实测或 pending）──
        if risk_tags & _RISK_TAGS_HIGH and exec_status in ("pending", "dry_run", ""):
            return AnalysisResult(**base,
                analysis_status="risky", risk_level="high",
                recommended_usage="manual_only",
                failure_type="none", failure_reason_zh="",
                notes=f"风险标签: {risk_tags_str}")

        # ── dry_run / pending ──
        if exec_status in ("dry_run", "pending", ""):
            return AnalysisResult(**base,
                analysis_status="pending", risk_level="low",
                recommended_usage="pending",
                failure_type="none", failure_reason_zh="",
                notes="dry_run 或尚未实测")

        # ── 失败状态 ──
        if exec_status in ("empty_result", "api_error", "auth_failed",
                           "network_error", "blocked", "key_missing"):
            return AnalysisResult(**base,
                analysis_status="failed", risk_level="medium",
                recommended_usage="review",
                failure_type=failure_type,
                failure_reason_zh=failure_reason_zh,
                notes=f"失败: {exec_status}  {raw_error[:80]}")

        # ── ok ──
        if exec_status == "ok":
            if result_count > 0:
                has_risk = bool(risk_tags & _RISK_TAGS_HIGH)
                if has_risk:
                    return AnalysisResult(**base,
                        analysis_status="risky", risk_level="high",
                        recommended_usage="manual_only",
                        failure_type="none", failure_reason_zh="",
                        notes=f"返回 {result_count} 条但含风险标签: {risk_tags_str}")
                return AnalysisResult(**base,
                    analysis_status="stable", risk_level="low",
                    recommended_usage="strong",
                    failure_type="none", failure_reason_zh="",
                    notes=f"返回 {result_count} 条，语义稳定")
            else:
                return AnalysisResult(**base,
                    analysis_status="failed", risk_level="medium",
                    recommended_usage="review",
                    failure_type="empty_result",
                    failure_reason_zh=_FAILURE_REASON_ZH["empty_result"],
                    notes="问财 ok 但返回 0 条")

        # ── 兜底 ──
        return AnalysisResult(**base,
            analysis_status="unstable", risk_level="medium",
            recommended_usage="review",
            failure_type="api_error",
            failure_reason_zh=f"未知 exec_status: {exec_status}",
            notes=f"未知状态: {exec_status}")

    # ─── 写文件 ───────────────────────────────────────────────────────────────

    def _write_analyzed(self, analyzed: list[AnalysisResult], run_dir: Path) -> None:
        out = run_dir / "analyzed_results.jsonl"
        with out.open("w", encoding="utf-8") as f:
            for ar in analyzed:
                f.write(json.dumps(asdict(ar), ensure_ascii=False) + "\n")
        print(f"[ResultAnalyzer] analyzed_results → {out}  ({len(analyzed)} 条)")

    def _update_candidates(self, analyzed: list[AnalysisResult]) -> None:
        """候选去重合并：按 skill_key + canonical_query_text 唯一键合并证据。"""
        queue_path = self.review_queue_dir / "candidate_changes.jsonl"

        # 读取已有候选
        existing: dict[str, dict] = {}
        if queue_path.exists():
            with queue_path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        c = json.loads(line)
                        key = f"{c.get('skill_key','')}|{c.get('canonical_query_text', c.get('new_value',''))}"
                        existing[key] = c
                    except Exception:
                        pass

        # 新增 / 更新
        changed = False
        for ar in analyzed:
            if ar.analysis_status not in ("stable", "risky"):
                continue
            key = f"{ar.skill_type}|{ar.query_text}"
            now = datetime.now().isoformat()
            if key in existing:
                c = existing[key]
                # 合并证据
                run_ids = c.get("evidence_run_ids", [])
                if isinstance(run_ids, str):
                    run_ids = run_ids.split("|")
                q_ids = c.get("evidence_query_ids", [])
                if isinstance(q_ids, str):
                    q_ids = q_ids.split("|")

                if ar.run_id and ar.run_id not in run_ids:
                    run_ids.append(ar.run_id)
                if ar.query_id and ar.query_id not in q_ids:
                    q_ids.append(ar.query_id)

                old_min = int(c.get("result_count_min", ar.result_count) or 0)
                old_max = int(c.get("result_count_max", ar.result_count) or 0)
                old_sc = int(c.get("success_count", 0) or 0)
                old_fc = int(c.get("failed_count", 0) or 0)

                if ar.analysis_status == "stable":
                    old_sc += 1
                else:
                    old_fc += 1
                total = old_sc + old_fc
                old_min = min(old_min, ar.result_count)
                old_max = max(old_max, ar.result_count)

                c["evidence_run_ids"] = run_ids
                c["evidence_query_ids"] = q_ids
                c["success_count"] = old_sc
                c["failed_count"] = old_fc
                c["result_count_min"] = old_min
                c["result_count_max"] = old_max
                c["result_count_avg"] = round((old_min + old_max) / 2, 1)
                c["success_rate"] = round(old_sc / max(total, 1), 3)
                c["updated_at"] = now
                existing[key] = c
                changed = True
            else:
                change_type = "add" if ar.analysis_status == "stable" else "mark_risky"
                existing[key] = {
                    "change_id": f"CAND-{uuid.uuid4().hex[:8].upper()}",
                    "change_type": change_type,
                    "canon_id": "",
                    "skill_key": ar.skill_type,
                    "skill_name_zh": ar.skill_name_zh,
                    "meaning_zh": ar.normalized_intent,
                    "canonical_query_text": ar.query_text,
                    "old_value": "",
                    "evidence_run_ids": [ar.run_id] if ar.run_id else [],
                    "evidence_query_ids": [ar.query_id] if ar.query_id else [],
                    "success_count": 1 if ar.analysis_status == "stable" else 0,
                    "failed_count": 0 if ar.analysis_status == "stable" else 1,
                    "result_count_min": ar.result_count,
                    "result_count_max": ar.result_count,
                    "result_count_avg": float(ar.result_count),
                    "success_rate": 1.0 if ar.analysis_status == "stable" else 0.0,
                    "reason": f"自动测试 analysis_status={ar.analysis_status}",
                    "created_at": now,
                    "updated_at": now,
                    "status": "candidate",
                }
                changed = True

        if changed:
            with queue_path.open("w", encoding="utf-8") as f:
                for c in existing.values():
                    f.write(json.dumps(c, ensure_ascii=False) + "\n")
            print(f"[ResultAnalyzer] 候选更新 → {queue_path}  ({len(existing)} 条去重后)")
