"""Generate S9_return_enrichment.csv for sector return enrichment tests."""
from __future__ import annotations
import csv
from pathlib import Path

OUT_DIR = Path(r"F:\v.6\v6-op\query_lab\cases\sector_问财选板块")

HEADER = [
    "query_id","skill_type","skill_name_zh","actual_query_backend",
    "op_domain","op_topic","source_origin","source_note","version",
    "test_group","category","query_text","normalized_intent",
    "condition_count","field_atoms","expression_type","time_window",
    "unit_type","operator_type","order_variant","risk_tags",
    "run_count","success_count","none_count","error_count","empty_count",
    "avg_result_count","min_result_count","max_result_count","avg_latency_ms",
    "status","risk_level","recommended_usage","notes",
]

def row(qid, cat, qt, intent, cond, atoms, rl="medium", ru="pending",
        notes="", risk_tags=""):
    return [
        qid, "sector", "问财选板块", "zhishu",
        "wencai_query", "return_enrichment", "seed_spec", "S9返回增强补测",
        "v1", "S9_return_enrichment", cat, qt, intent, cond, atoms,
        "filter", "today", "定性", "comparison", "none", risk_tags,
        "0","0","0","0","0","0","0","0","0",
        "pending", rl, ru, notes,
    ]

rows = [
    # ── 上涨原因类 ────────────────────────────────────────────────────────────
    row("S9-001","reason_query",
        "今日涨幅排名前10的板块，上涨原因是什么",
        "涨幅TOP10板块+上涨原因",1,"涨幅|原因",
        risk_tags="vague_word",
        notes="验证：原因文本是否返回，还是被忽略(reason_query_ignored)"),
    row("S9-002","reason_query",
        "今日涨停家数排名前10的板块，原因是什么",
        "涨停家数TOP10板块+原因",1,"涨停家数|原因",
        risk_tags="vague_word",
        notes="验证：原因被忽略还是有专列"),
    row("S9-003","reason_query",
        "今日主力净流入排名前10的板块，资金流入原因是什么",
        "主力净流入TOP10板块+资金原因",1,"主力净流入|原因",
        risk_tags="vague_word",
        notes="验证：资金原因文本是否返回"),
    # ── 指数字段类 ────────────────────────────────────────────────────────────
    row("S9-004","index_field_query",
        "今日涨幅排名前10的板块，返回板块指数代码",
        "涨幅TOP10板块+指数代码",1,"涨幅|指数代码",
        notes="验证：指数代码是否作为字段返回"),
    row("S9-005","index_field_query",
        "今日成交额排名前10的板块，返回指数代码和指数简称",
        "成交额TOP10板块+指数代码+指数简称",1,"成交额|指数代码|指数简称",
        notes="验证：指数代码/简称字段可访问性"),
    row("S9-006","index_field_query",
        "今日涨停家数排名前10的板块，返回涨停家数和上涨家数",
        "涨停家数TOP10板块+涨停家数+上涨家数",1,"涨停家数|上涨家数",
        notes="验证：情绪字段涨停家数/上涨家数是否在列"),
    # ── 龙头股/领涨股类 ───────────────────────────────────────────────────────
    row("S9-007","leader_query",
        "今日涨幅排名前5的板块及其领涨股",
        "涨幅TOP5板块+领涨股",2,"涨幅|领涨股",
        risk_tags="sector_route_ambiguous",
        notes="验证：sector能否返回股票，还是只返回板块(leader_query_not_supported_by_sector)"),
    row("S9-008","leader_query",
        "今日涨停家数排名前5的板块及其龙头股",
        "涨停家数TOP5板块+龙头股",2,"涨停家数|龙头股",
        risk_tags="sector_route_ambiguous",
        notes="验证：龙头股能否在sector路由返回"),
    row("S9-009","leader_query",
        "军工板块领涨股",
        "军工板块领涨股",1,"板块名|领涨股",
        risk_tags="sector_route_ambiguous",
        notes="验证：指定板块+领涨股，返回板块还是股票还是空"),
    row("S9-010","leader_query",
        "军工板块中今日涨幅排名前10的股票",
        "军工板块涨幅TOP10股",2,"板块名|涨幅",
        risk_tags="sector_route_ambiguous",
        notes="已知S8-006失败，二次确认must_split=true"),
    row("S9-011","leader_query",
        "今日涨幅排名前5的板块，然后查询每个板块中的今日涨幅排名前3股票",
        "涨幅TOP5板块→每板块涨幅TOP3股",2,"涨幅|板块内股票",
        risk_tags="sector_route_ambiguous",
        notes="最复杂的两步问法，sector路由应直接返回板块列表，不会执行第二步"),
]

path = OUT_DIR / "S9_return_enrichment.csv"
with open(path, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(HEADER)
    for r in rows:
        w.writerow(r)
print(f"Written: {path}  ({len(rows)} rows)")
