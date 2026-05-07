"""
query_runner.py — V2 QueryLab 查询执行器（闭环版）

闭环要求：
1. 每次 run 写 query_results.jsonl、analyzed_results.jsonl、failed_replay.jsonl、run_summary.md、astock_ceiling_report.md
2. latest/ 同步 query_results / analyzed_results / failed_replay
3. 全局 results/failed_replay.jsonl 追加失败记录
"""
from __future__ import annotations

import csv
import json
import time
import sys
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).parent
_QUERY_LAB_DIR = _SCRIPTS_DIR.parent
_PROJECT_ROOT = _QUERY_LAB_DIR.parent

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from validators.chinese_query_validator import ChineseQueryValidator
from validators.schema_validator import SchemaValidator
from adapters.wencai_astock_adapter import WencaiAstockAdapter
from adapters.wencai_sector_adapter import WencaiSectorAdapter


@dataclass
class QueryResult:
    run_id: str
    query_id: str
    skill_type: str
    skill_name_zh: str
    test_group: str
    category: str
    query_text: str
    normalized_intent: str
    actual_query_backend: str
    op_domain: str
    op_topic: str
    source_origin: str
    version: str
    condition_count: int
    field_atoms: str
    risk_tags: str
    exec_status: str
    result_count: int
    elapsed_ms: float
    raw_error: str
    status: str = "pending"
    risk_level: str = ""
    recommended_usage: str = ""
    notes: str = ""
    return_object_type: str = ""
    raw_columns: str = ""
    extracted_sector_names: str = ""
    extracted_index_codes: str = ""
    extracted_stock_codes: str = ""
    extracted_stock_names: str = ""
    extracted_reason_text: str = ""
    next_pipeline_route: str = ""


def _read_csv(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows


def _load_cases(cases_dir: Path, route: str, group: str | None, limit: int) -> list[dict]:
    route_map = {
        "astock": [cases_dir / "astock_问财选A股"],
        "sector": [cases_dir / "sector_问财选板块"],
        "all": [cases_dir / "astock_问财选A股", cases_dir / "sector_问财选板块"],
    }
    dirs = route_map.get(route, [])
    rows: list[dict] = []
    for d in dirs:
        if not d.exists():
            continue
        for csv_file in sorted(d.glob("*.csv")):
            file_rows = _read_csv(csv_file)
            for r in file_rows:
                if group and r.get("test_group", "") != group:
                    continue
                rows.append(r)
    if limit > 0:
        rows = rows[:limit]
    return rows


class QueryRunner:
    def __init__(
        self,
        project_root: Path,
        dry_run: bool = False,
        sleep_ms: int = 0,
        fetch_limit: int = 300,
        query_timeout_sec: int = 60,
        empty_result_retry: int = 1,
        empty_result_retry_sleep_sec: float = 2.0,
    ) -> None:
        self.project_root = project_root
        self.query_lab_dir = project_root / "query_lab"
        self.dry_run = dry_run
        self.sleep_ms = sleep_ms
        self.fetch_limit = fetch_limit
        self.query_timeout_sec = query_timeout_sec
        self.empty_result_retry = max(0, empty_result_retry)
        self.empty_result_retry_sleep_sec = max(0.0, empty_result_retry_sleep_sec)
        self._current_query_file = self.query_lab_dir / "results" / "current_query.json"

        self.validator = ChineseQueryValidator()
        self.schema_validator = SchemaValidator()
        self.astock_adapter = WencaiAstockAdapter(project_root, dry_run=dry_run)
        self.sector_adapter = WencaiSectorAdapter(project_root, dry_run=dry_run)

        self.run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
        self.run_dir = self.query_lab_dir / "results" / "runs" / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._write_manifest(status="running", completed=False)

    def run(
        self,
        route: str = "all",
        group: str | None = None,
        limit: int = 0,
        repeat: int = 1,
        replay_failed: bool = False,
    ) -> list[QueryResult]:
        cases_dir = self.query_lab_dir / "cases"

        if replay_failed:
            rows = self._load_failed_cases()
        else:
            rows = _load_cases(cases_dir, route, group, limit)

        print(f"[QueryRunner] run_id={self.run_id}  route={route}  "
              f"group={group}  cases={len(rows)}  repeat={repeat}  "
              f"dry_run={self.dry_run}")

        results: list[QueryResult] = []
        analyzed: list[Any] = []
        query_results_path = self.run_dir / "query_results.jsonl"
        analyzed_results_path = self.run_dir / "analyzed_results.jsonl"
        query_results_path.write_text("", encoding="utf-8")
        analyzed_results_path.write_text("", encoding="utf-8")

        from result_analyzer import ResultAnalyzer
        analyzer = ResultAnalyzer(self.query_lab_dir)

        for row in rows:
            for rep in range(max(1, repeat)):
                result = self._execute_with_empty_retry(row, rep + 1)
                results.append(result)
                self._append_jsonl(query_results_path, asdict(result))

                analyzed_result = analyzer._classify(asdict(result))
                analyzed.append(analyzed_result)
                self._append_jsonl(analyzed_results_path, asdict(analyzed_result))

                if self.sleep_ms > 0 and not self.dry_run:
                    time.sleep(self.sleep_ms / 1000.0)

        print(f"[QueryRunner] query_results → {query_results_path}  ({len(results)} 条)")
        print(f"[QueryRunner] analyzed_results → {analyzed_results_path}  ({len(analyzed)} 条)")
        analyzer._update_candidates(analyzed)
        return analyzed

    def _execute_with_empty_retry(self, row: dict, rep: int) -> QueryResult:
        """Retry transient empty_result once before recording a failed query.

        iWencai can occasionally return an empty page for a query that succeeds
        immediately before or after. A single empty response should not pollute
        the canon; only a confirmed empty result is treated as failed.
        """
        result = self._execute_one(row, rep)
        if self.dry_run or result.exec_status != "empty_result":
            return result

        last_result = result
        for attempt in range(1, self.empty_result_retry + 1):
            if self.empty_result_retry_sleep_sec > 0:
                time.sleep(self.empty_result_retry_sleep_sec)
            print(
                f"  [EMPTY_RETRY][{attempt}/{self.empty_result_retry}] "
                f"{row.get('query_id', '?')}  query={row.get('query_text', '')[:50]!r}"
            )
            retry_result = self._execute_one(row, rep)
            retry_result.notes = (
                f"empty_result_retry attempt={attempt}; "
                f"first_elapsed_ms={last_result.elapsed_ms:.0f}; "
                f"first_status={last_result.exec_status}"
            )
            if retry_result.exec_status != "empty_result":
                return retry_result
            last_result = retry_result

        last_result.notes = (
            f"empty_result confirmed after {self.empty_result_retry} retry; "
            f"first_elapsed_ms={result.elapsed_ms:.0f}"
        )
        return last_result

    def dry_list(
        self,
        route: str = "all",
        group: str | None = None,
        limit: int = 0,
    ) -> list[dict]:
        cases_dir = self.query_lab_dir / "cases"
        rows = _load_cases(cases_dir, route, group, limit)
        print(f"\n[DRY-RUN] 将要执行 {len(rows)} 条查询：\n")
        for i, r in enumerate(rows, 1):
            vr = self.validator.validate(r.get("query_text", ""))
            flag = "OK" if vr.valid else f"NG ({vr.reason})"
            print(f"  {i:3d}. [{r.get('test_group','')}][{r.get('query_id','')}] "
                  f"{flag}  {r.get('query_text','')[:80]}")
        return rows

    def _execute_one(self, row: dict, rep: int) -> QueryResult:
        query_text = row.get("query_text", "").strip()
        skill_type = row.get("skill_type", "").strip()
        query_id = row.get("query_id", "?")

        # 写 current_query.json，便于监控哪条 Query 正在执行
        self._write_current_query(query_id, query_text)

        vr = self.validator.validate(query_text)
        if not vr.valid:
            print(f"  [INVALID_QUERY] {query_id}: {vr.reason}  query={query_text[:60]!r}")
            return QueryResult(
                run_id=self.run_id, query_id=query_id,
                skill_type=skill_type, skill_name_zh=row.get("skill_name_zh", ""),
                test_group=row.get("test_group", ""), category=row.get("category", ""),
                query_text=query_text, normalized_intent=row.get("normalized_intent", ""),
                actual_query_backend="BLOCKED",
                op_domain=row.get("op_domain", ""), op_topic=row.get("op_topic", ""),
                source_origin=row.get("source_origin", ""), version=row.get("version", "v1"),
                condition_count=self._int(row.get("condition_count")),
                field_atoms=row.get("field_atoms", ""), risk_tags=row.get("risk_tags", ""),
                exec_status="invalid_query", result_count=0, elapsed_ms=0.0,
                raw_error=vr.reason, status="invalid_query",
                risk_level="critical", recommended_usage="forbidden",
                notes=f"中文预检失败: {vr.reason}",
            )

        api_result = self._call_adapter_with_timeout(skill_type, query_text)

        exec_status = api_result.get("status", "api_error")
        result_count = api_result.get("result_count", 0)
        elapsed_ms = api_result.get("elapsed_ms", 0.0)
        raw_error = api_result.get("raw_error", "")
        actual_backend = api_result.get("actual_query_backend", row.get("actual_query_backend", ""))
        return_object_type = api_result.get("return_object_type", "")
        raw_columns = api_result.get("raw_columns", "")
        extracted_sector_names = api_result.get("extracted_sector_names", "")
        extracted_index_codes = api_result.get("extracted_index_codes", "")
        extracted_stock_codes = api_result.get("extracted_stock_codes", "")
        extracted_stock_names = api_result.get("extracted_stock_names", "")
        extracted_reason_text = api_result.get("extracted_reason_text", "")
        next_pipeline_route = api_result.get("next_pipeline_route", "")

        mode = "DRY" if self.dry_run else "LIVE"
        print(f"  [{mode}][rep={rep}] {query_id}  status={exec_status}  "
              f"count={result_count}  {elapsed_ms:.0f}ms  {query_text[:50]!r}")

        return QueryResult(
            run_id=self.run_id, query_id=query_id,
            skill_type=skill_type, skill_name_zh=row.get("skill_name_zh", ""),
            test_group=row.get("test_group", ""), category=row.get("category", ""),
            query_text=query_text, normalized_intent=row.get("normalized_intent", ""),
            actual_query_backend=actual_backend,
            op_domain=row.get("op_domain", ""), op_topic=row.get("op_topic", ""),
            source_origin=row.get("source_origin", ""), version=row.get("version", "v1"),
            condition_count=self._int(row.get("condition_count")),
            field_atoms=row.get("field_atoms", ""), risk_tags=row.get("risk_tags", ""),
            exec_status=exec_status, result_count=result_count,
            elapsed_ms=elapsed_ms, raw_error=raw_error, status="pending",
            return_object_type=return_object_type,
            raw_columns=raw_columns,
            extracted_sector_names=extracted_sector_names,
            extracted_index_codes=extracted_index_codes,
            extracted_stock_codes=extracted_stock_codes,
            extracted_stock_names=extracted_stock_names,
            extracted_reason_text=extracted_reason_text,
            next_pipeline_route=next_pipeline_route,
        )

    def _call_adapter_with_timeout(self, skill_type: str, query_text: str) -> dict:
        """
        调用 adapter，并对单条 Query 强制 query_timeout_sec 超时。
        超时后返回 api_error，继续下一条，不中断整个 run。
        Windows 下用 daemon 线程实现（pywencai 网络调用无法强制中断，
        超时后该线程以 daemon 方式在后台继续并最终随进程退出）。
        """
        timeout = self.query_timeout_sec if self.query_timeout_sec > 0 else None

        result_box: list[dict] = []
        exc_box: list[BaseException] = []

        def _run() -> None:
            try:
                if skill_type == "astock":
                    result_box.append(
                        self.astock_adapter.query(query_text, limit=self.fetch_limit)
                    )
                elif skill_type == "sector":
                    result_box.append(
                        self.sector_adapter.query(query_text, limit=self.fetch_limit)
                    )
                else:
                    result_box.append({
                        "status": "pending", "result_count": 0,
                        "elapsed_ms": 0.0,
                        "raw_error": f"skill_type={skill_type!r} 未实现",
                    })
            except BaseException as exc:  # noqa: BLE001
                exc_box.append(exc)

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join(timeout=timeout)

        if t.is_alive():
            elapsed_ms = (self.query_timeout_sec or 0) * 1000.0
            print(f"  [TIMEOUT] query_timeout_sec={self.query_timeout_sec}s 超时，跳过")
            return {
                "status": "api_error",
                "result_count": 0,
                "codes": [],
                "elapsed_ms": elapsed_ms,
                "raw_error": f"query_timeout after {self.query_timeout_sec}s",
                "query_text": query_text,
                "skill_type": skill_type,
                "actual_query_backend": "stock" if skill_type == "astock" else skill_type,
            }

        if exc_box:
            raise exc_box[0]

        return result_box[0] if result_box else {
            "status": "api_error", "result_count": 0,
            "elapsed_ms": 0.0, "raw_error": "adapter returned nothing",
        }

    def _write_current_query(self, query_id: str, query_text: str) -> None:
        try:
            payload = {
                "run_id": self.run_id,
                "query_id": query_id,
                "query_text": query_text,
                "start_at": datetime.now().isoformat(),
            }
            self._current_query_file.parent.mkdir(parents=True, exist_ok=True)
            self._current_query_file.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _run_analyzer(self, results: list[QueryResult]) -> list:
        """调用 result_analyzer 对执行结果分析打标，写 analyzed_results.jsonl。"""
        try:
            from result_analyzer import ResultAnalyzer
            analyzer = ResultAnalyzer(self.query_lab_dir)
            analyzed = analyzer.analyze(results, self.run_dir)
        except Exception as e:
            print(f"[QueryRunner] result_analyzer 不可用，回退写原始结果: {e}")
            analyzed = results
            out = self.run_dir / "analyzed_results.jsonl"
            with out.open("w", encoding="utf-8") as f:
                for r in analyzed:
                    f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
            print(f"[QueryRunner] analyzed_results (fallback) → {out}  ({len(analyzed)} 条)")
        return analyzed

    def _load_failed_cases(self) -> list[dict]:
        failed_path = self.query_lab_dir / "results" / "failed_replay.jsonl"
        if not failed_path.exists():
            return []
        rows: list[dict] = []
        with failed_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    def _write_query_results(self, results: list[QueryResult]) -> None:
        out = self.run_dir / "query_results.jsonl"
        with out.open("w", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
        print(f"[QueryRunner] query_results → {out}  ({len(results)} 条)")

    def _append_jsonl(self, path: Path, payload: dict) -> None:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
            f.flush()

    def write_failed_replay(
        self,
        failed_entries: list[Any],
        run_dir: Path,
    ) -> None:
        """写 per-run failed_replay.jsonl 和全局 results/failed_replay.jsonl"""
        if not failed_entries:
            (run_dir / "failed_replay.jsonl").write_text("", encoding="utf-8")
            return

        def to_dict(e: Any) -> dict:
            return asdict(e) if hasattr(e, "__dataclass_fields__") else dict(e)

        # per-run
        run_path = run_dir / "failed_replay.jsonl"
        with run_path.open("w", encoding="utf-8") as f:
            for e in failed_entries:
                f.write(json.dumps(to_dict(e), ensure_ascii=False) + "\n")
        print(f"[QueryRunner] failed_replay → {run_path}  ({len(failed_entries)} 条)")

        # 全局追加
        global_path = self.query_lab_dir / "results" / "failed_replay.jsonl"
        with global_path.open("a", encoding="utf-8") as f:
            for e in failed_entries:
                f.write(json.dumps(to_dict(e), ensure_ascii=False) + "\n")

    def _write_ceiling_report(
        self,
        results: list[QueryResult],
        run_dir: Path,
    ) -> None:
        """生成 astock_ceiling_report.md 到 run_dir。"""
        astock = [r for r in results if r.skill_type == "astock"]
        total = len(astock)
        ok = sum(1 for r in astock if r.exec_status == "ok")
        empty = sum(1 for r in astock if r.exec_status == "empty_result")
        failed = sum(1 for r in astock if r.exec_status not in ("ok", "dry_run", "empty_result"))
        dry = sum(1 for r in astock if r.exec_status == "dry_run")

        pass_rate = f"{ok / total * 100:.1f}%" if total > 0 else "N/A"
        avg_ms = (
            sum(r.elapsed_ms for r in astock if r.elapsed_ms > 0) /
            max(1, sum(1 for r in astock if r.elapsed_ms > 0))
        )

        lines: list[str] = [
            f"# AStock Ceiling Report",
            f"",
            f"**run_id**: `{self.run_id}`  ",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"",
            f"## 汇总",
            f"",
            f"| 指标 | 值 |",
            f"|------|----|",
            f"| 总用例 | {total} |",
            f"| OK | {ok} |",
            f"| 空结果 | {empty} |",
            f"| 失败 | {failed} |",
            f"| DRY | {dry} |",
            f"| 通过率 | {pass_rate} |",
            f"| 平均耗时 | {avg_ms:.0f} ms |",
            f"",
            f"## 失败明细",
            f"",
        ]

        failed_rows = [r for r in astock if r.exec_status not in ("ok", "dry_run", "empty_result")]
        if failed_rows:
            lines.append("| query_id | exec_status | query_text | raw_error |")
            lines.append("|----------|-------------|------------|-----------|")
            for r in failed_rows:
                q = r.query_text[:40].replace("|", "｜")
                err = r.raw_error[:60].replace("|", "｜")
                lines.append(f"| {r.query_id} | {r.exec_status} | {q} | {err} |")
        else:
            lines.append("_无失败记录_")

        lines += [
            f"",
            f"## 空结果明细",
            f"",
        ]

        empty_rows = [r for r in astock if r.exec_status == "empty_result"]
        if empty_rows:
            lines.append("| query_id | query_text | notes |")
            lines.append("|----------|------------|-------|")
            for r in empty_rows:
                q = r.query_text[:40].replace("|", "｜")
                notes = r.notes[:60].replace("|", "｜")
                lines.append(f"| {r.query_id} | {q} | {notes} |")
        else:
            lines.append("_无空结果记录_")

        out = run_dir / "astock_ceiling_report.md"
        out.write_text("\n".join(lines), encoding="utf-8")
        print(f"[QueryRunner] astock_ceiling_report → {out}")

    def sync_latest(self, run_dir: Path) -> None:
        """把本次 run 的三个核心文件同步到 results/latest/"""
        if not (run_dir / "RUN_COMPLETE").exists():
            print(f"[QueryRunner] latest/ 未同步：run 未完成 {run_dir}")
            return
        latest_dir = self.query_lab_dir / "results" / "latest"
        latest_dir.mkdir(parents=True, exist_ok=True)
        for fname in ("query_results.jsonl", "analyzed_results.jsonl", "failed_replay.jsonl"):
            src = run_dir / fname
            dst = latest_dir / fname
            if src.exists():
                dst.write_bytes(src.read_bytes())
        print(f"[QueryRunner] latest/ 同步完成")

    def mark_completed(self, summary: dict | None = None) -> None:
        """只有完整跑完并生成报告后，才打完成标记。"""
        (self.run_dir / "RUN_COMPLETE").write_text(
            datetime.now().isoformat(), encoding="utf-8")
        self._write_manifest(status="completed", completed=True, summary=summary or {})

    def _write_manifest(
        self,
        status: str,
        completed: bool,
        summary: dict | None = None,
    ) -> None:
        payload = {
            "run_id": self.run_id,
            "status": status,
            "completed": completed,
            "updated_at": datetime.now().isoformat(),
            "run_dir": str(self.run_dir),
            "summary": summary or {},
        }
        (self.run_dir / "run_manifest.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _int(val: Any) -> int:
        try:
            return int(val)
        except (TypeError, ValueError):
            return 0
