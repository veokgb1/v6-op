#!/usr/bin/env python3
"""
run_query_lab.py — V2 QueryLab 主入口

用法:
  # 干跑
  python run_query_lab.py --dry-run --route astock --limit 20

  # 实测
  python run_query_lab.py --route astock --group A1_basic --limit 20 --sleep-ms 3000

  # 法典治理
  python run_query_lab.py canon propose
  python run_query_lab.py canon lint
  python run_query_lab.py canon diff
  python run_query_lab.py canon promote --skill astock --reviewer "user" --reason "..."
  python run_query_lab.py canon rollback --skill astock

  # 诊断（不请求问财）
  python run_query_lab.py diagnose --route astock --query "低位强势、资金关注、KDJ金叉、JMA向上的小盘股"
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

# Windows UTF-8
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

_SCRIPTS_DIR = Path(__file__).parent.resolve()
_QUERY_LAB_DIR = _SCRIPTS_DIR.parent
_PROJECT_ROOT = _QUERY_LAB_DIR.parent

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def cmd_run(args: argparse.Namespace) -> None:
    from query_runner import QueryRunner
    from result_analyzer import ResultAnalyzer
    from report_writer import ReportWriter

    runner = QueryRunner(
        project_root=_PROJECT_ROOT,
        dry_run=args.dry_run,
        sleep_ms=args.sleep_ms,
        fetch_limit=args.fetch_limit,
        query_timeout_sec=args.query_timeout_sec,
    )

    if args.dry_run:
        runner.dry_list(route=args.route, group=args.group, limit=args.limit)
        return

    # runner.run() → executes queries, writes query_results.jsonl + analyzed_results.jsonl
    analyzed = runner.run(
        route=args.route, group=args.group, limit=args.limit,
        repeat=args.repeat, replay_failed=args.replay_failed,
    )

    analyzer = ResultAnalyzer(_QUERY_LAB_DIR)
    failed_entries = analyzer.build_failed_replay(analyzed)
    runner.write_failed_replay(failed_entries, runner.run_dir)

    summary = analyzer.summary(analyzed)
    runner.mark_completed(summary)

    writer = ReportWriter(_QUERY_LAB_DIR)
    writer.write_all_reports(
        run_id=runner.run_id,
        run_dir=runner.run_dir,
        analyzed=analyzed,
        summary=summary,
        route=args.route,
        group=args.group,
    )
    runner.sync_latest(runner.run_dir)

    print(f"\n{'='*60}")
    print(f"[QueryLab] 完成  run_id={runner.run_id}")
    print(f"  总计={summary['total']}  stable={summary['stable']}  "
          f"risky={summary['risky']}  failed={summary['failed']}  "
          f"forbidden={summary['forbidden']}  invalid_query={summary['invalid_query']}")
    if summary.get("failure_types"):
        ft_str = "  ".join(f"{k}={v}" for k,v in summary["failure_types"].items())
        print(f"  failure_types: {ft_str}")
    print(f"  run_dir: {runner.run_dir}")
    print(f"{'='*60}\n")


def cmd_canon(args: argparse.Namespace) -> None:
    sub = args.canon_sub

    if sub == "propose":
        from canon_manager import CanonManager
        mgr = CanonManager(_QUERY_LAB_DIR)
        count = mgr.propose_from_candidates()
        print(f"[canon propose] 共 {count} 条候选变更")

    elif sub == "lint":
        from canon_linter import CanonLinter
        linter = CanonLinter(_QUERY_LAB_DIR)
        issues = linter.lint()
        errors = sum(1 for i in issues if i.severity == "error")
        warnings = sum(1 for i in issues if i.severity == "warning")
        print(f"[canon lint] errors={errors}  warnings={warnings}  total={len(issues)}")
        if errors > 0:
            sys.exit(1)

    elif sub == "diff":
        from canon_diff import CanonDiff
        CanonDiff(_QUERY_LAB_DIR).diff()

    elif sub == "promote":
        from canon_promote import CanonPromote
        skill = getattr(args, "skill", "astock")
        reviewer = getattr(args, "reviewer", "manual")
        reason = getattr(args, "reason", "手动发布")
        count = CanonPromote(_QUERY_LAB_DIR).promote(
            skill_key=skill, reviewer=reviewer, reason=reason)
        print(f"[canon promote] 发布 {count} 条到 skill={skill}")

    elif sub == "rollback":
        from canon_rollback import CanonRollback
        skill = getattr(args, "skill", "astock")
        version = getattr(args, "version", None)
        ok = CanonRollback(_QUERY_LAB_DIR).rollback(skill_key=skill, version_ts=version)
        if not ok:
            sys.exit(1)

    else:
        print(f"未知 canon 子命令: {sub!r}")
        sys.exit(1)


def cmd_diagnose(args: argparse.Namespace) -> None:
    from diagnose_astock import AstockDiagnoser
    query = args.query
    if not query:
        print("[diagnose] 请提供 --query 参数")
        sys.exit(1)
    diagnoser = AstockDiagnoser(_QUERY_LAB_DIR)
    result = diagnoser.diagnose(query)
    diagnoser.print_result(result)


def main() -> None:
    argv = sys.argv[1:]

    if argv and argv[0] == "canon":
        parser = argparse.ArgumentParser(prog="run_query_lab canon")
        sub = parser.add_subparsers(dest="canon_sub")
        sub.add_parser("propose")
        sub.add_parser("lint")
        sub.add_parser("diff")
        promote_p = sub.add_parser("promote")
        promote_p.add_argument("--skill", default="astock", choices=["astock", "sector"])
        promote_p.add_argument("--reviewer", required=True)
        promote_p.add_argument("--reason", required=True)
        rollback_p = sub.add_parser("rollback")
        rollback_p.add_argument("--skill", default="astock", choices=["astock", "sector"])
        rollback_p.add_argument("--version", default=None)
        args = parser.parse_args(argv[1:])
        cmd_canon(args)

    elif argv and argv[0] == "diagnose":
        parser = argparse.ArgumentParser(prog="run_query_lab diagnose")
        parser.add_argument("--route", default="astock", choices=["astock"])
        parser.add_argument("--query", required=True, help="要诊断的中文查询语句")
        args = parser.parse_args(argv[1:])
        cmd_diagnose(args)

    else:
        parser = argparse.ArgumentParser(prog="run_query_lab")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--route", default="all", choices=["astock", "sector", "all"])
        parser.add_argument("--group", default=None)
        parser.add_argument("--limit", type=int, default=0,
                            help="case_limit: 跑多少条 CSV 用例（0=全部）")
        parser.add_argument("--repeat", type=int, default=1)
        parser.add_argument("--sleep-ms", type=int, default=0)
        parser.add_argument("--replay-failed", action="store_true")
        parser.add_argument("--fetch-limit", type=int, default=300,
                            help="fetch_limit: 每条 Query 最多取多少只股票（0=不限，默认 300）")
        parser.add_argument("--query-timeout-sec", type=int, default=60,
                            help="query_timeout_sec: 单条 Query 最大等待秒数（0=不限，默认 60）")
        args = parser.parse_args(argv)
        cmd_run(args)


if __name__ == "__main__":
    main()
