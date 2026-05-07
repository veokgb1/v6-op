"""Generate S5-S8 CSV files for sector ceiling run."""
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

def row(qid, group, cat, qt, intent, cond, atoms, rl="medium", ru="pending",
        notes="", risk_tags="", expr="filter", tw="today", unit="定性",
        op="comparison", order="none"):
    return [
        qid, "sector", "问财选板块", "zhishu",
        "wencai_query", "sector_ceiling", "seed_spec", "S5-S8扩展抽样",
        "v1", group, cat, qt, intent, cond, atoms,
        expr, tw, unit, op, order, risk_tags,
        "0","0","0","0","0","0","0","0","0",
        "pending", rl, ru, notes,
    ]


# ── S5: 情绪/涨停/上涨家数 ───────────────────────────────────────────────────
S5 = [
    row("S5-001","S5_emotion_style","emotion_upcount",
        "今日上涨家数排名前10的板块",
        "上涨家数TOP10板块",1,"上涨家数",
        notes="情绪指标：上涨家数"),
    row("S5-002","S5_emotion_style","emotion_limitup",
        "今日涨停家数排名前10的板块",
        "涨停家数TOP10板块",1,"涨停家数",
        notes="情绪指标：涨停家数"),
    row("S5-003","S5_emotion_style","emotion_limitup_thresh",
        "今日涨停家数大于3的板块",
        "涨停家数>3板块",1,"涨停家数",
        op="threshold",
        notes="涨停家数阈值过滤"),
    row("S5-004","S5_emotion_style","emotion_combo",
        "今日换手率排名前10且涨停家数排名前10的板块",
        "换手率TOP10+涨停家数TOP10",2,"换手率|涨停家数",
        notes="换手率+涨停家数双排名"),
    row("S5-005","S5_emotion_style","emotion_board",
        "连板股最多的板块",
        "连板家数最多板块",1,"连板家数",
        risk_tags="non_standard_field",
        notes="连板字段是否被识别"),
    row("S5-006","S5_emotion_style","emotion_limitup_thresh2",
        "涨停家数大于5的板块，今日成交额排名前10",
        "涨停家数>5+成交额TOP10",2,"涨停家数|成交额",
        op="threshold",
        notes="情绪+成交额组合"),
]

# ── S6: 必须拆成两步 (should_split=true) ────────────────────────────────────
S6 = [
    row("S6-001","S6_two_step","two_step_sector_stock",
        "人工智能板块龙头股",
        "AI板块龙头股",1,"板块名|龙头股",
        risk_tags="sector_route_ambiguous",
        notes="must_split=true: sector->astock"),
    row("S6-002","S6_two_step","two_step_top_sector_stock",
        "今日涨幅最大的板块中的龙头股",
        "涨幅最大板块龙头股",2,"涨幅|龙头股",
        risk_tags="sector_route_ambiguous",
        notes="must_split=true: sector->astock"),
    row("S6-003","S6_two_step","two_step_flow_sector_stock",
        "今日主力净流入最多的板块中的龙头股",
        "主力净流入最多板块龙头股",2,"主力净流入|龙头股",
        risk_tags="sector_route_ambiguous",
        notes="must_split=true: sector->astock"),
    row("S6-004","S6_two_step","two_step_sector_topstocks",
        "人工智能板块中今日涨幅排名前10的股票",
        "AI板块涨幅TOP10股",2,"板块名|涨幅",
        risk_tags="sector_route_ambiguous",
        notes="must_split=true: sector->astock phase B"),
    row("S6-005","S6_two_step","two_step_sector_volume",
        "人工智能板块中今日成交额排名前10的股票",
        "AI板块成交额TOP10股",2,"板块名|成交额",
        risk_tags="sector_route_ambiguous",
        notes="must_split=true: sector->astock phase B"),
    row("S6-006","S6_two_step","two_step_sector_flow",
        "人工智能板块中今日主力净流入排名前10的股票",
        "AI板块主力净流入TOP10股",2,"板块名|主力净流入",
        risk_tags="sector_route_ambiguous",
        notes="must_split=true: sector->astock phase B"),
]

# ── S7: 低位/回流/预期差 ─────────────────────────────────────────────────────
S7 = [
    row("S7-001","S7_low_reversal","low_reversal_combo",
        "近60日涨幅小于20%，今日涨幅大于3%的板块",
        "近60日涨幅<20%+今日涨幅>3%",2,"近60日涨幅|今日涨幅",
        tw="multi_window",
        notes="低位回流：历史弱+今日强"),
    row("S7-002","S7_low_reversal","low_flow_combo",
        "近60日涨幅小于20%，今日主力净流入排名前10的板块",
        "近60日涨幅<20%+主力净流入TOP10",2,"近60日涨幅|主力净流入",
        tw="multi_window",
        notes="低位回流+资金流入"),
    row("S7-003","S7_low_reversal","low_volume_combo",
        "近20日涨幅小于5%，今日成交额排名前10的板块",
        "近20日涨幅<5%+成交额TOP10",2,"近20日涨幅|成交额",
        tw="multi_window",
        notes="短期弱势+放量"),
    row("S7-004","S7_low_reversal","flow_reversal",
        "近5日主力净流入小于0，今日主力净流入大于0的板块",
        "近5日净流入<0+今日净流入>0",2,"近5日主力净流入|今日主力净流入",
        tw="multi_window",
        notes="资金由流出转流入"),
    row("S7-005","S7_low_reversal","triple_low_combo",
        "近5日涨幅小于5%，今日成交额排名前10，今日涨幅大于3%的板块",
        "近5日涨幅<5%+成交额TOP10+今日涨幅>3%",3,"近5日涨幅|成交额|今日涨幅",
        tw="multi_window",
        notes="三条件低位启动筛选"),
]

# ── S8: 专门测返回对象类型 ────────────────────────────────────────────────────
S8 = [
    row("S8-001","S8_return_contract","sector_only_test",
        "今日涨幅排名前10的板块",
        "涨幅TOP10板块",1,"涨幅",
        notes="期望sector_only"),
    row("S8-002","S8_return_contract","sector_only_test",
        "今日成交额排名前10的板块",
        "成交额TOP10板块",1,"成交额",
        notes="期望sector_only"),
    row("S8-003","S8_return_contract","sector_stock_mix_test",
        "今日涨停家数排名前10的板块",
        "涨停家数TOP10板块",1,"涨停家数",
        notes="期望sector_only；验证涨停家数字段"),
    row("S8-004","S8_return_contract","forbidden_test",
        "今日最强板块",
        "最强板块",1,"最强",
        risk_tags="vague_word",
        notes="期望forbidden/empty_or_error"),
    row("S8-005","S8_return_contract","two_step_test",
        "军工板块龙头股",
        "军工板块龙头",1,"板块名|龙头",
        risk_tags="sector_route_ambiguous",
        notes="期望stock_only或mixed；验证need_split"),
    row("S8-006","S8_return_contract","two_step_test",
        "军工板块中今日涨幅排名前10的股票",
        "军工板块涨幅TOP10股",2,"板块名|涨幅",
        risk_tags="sector_route_ambiguous",
        notes="期望stock_only；should_split=true"),
    row("S8-007","S8_return_contract","text_test",
        "今日主力净流入最多的板块有哪些，原因是什么",
        "主力净流入最多板块+原因",1,"主力净流入",
        risk_tags="vague_word",
        notes="期望text_explanation或sector_only"),
    row("S8-008","S8_return_contract","forbidden_test",
        "哪些板块值得关注",
        "值得关注的板块",1,"值得关注",
        risk_tags="vague_word",
        notes="期望empty_or_error"),
]


def write_csv(name: str, rows: list) -> None:
    path = OUT_DIR / f"{name}.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for r in rows:
            w.writerow(r)
    print(f"Written: {path}  ({len(rows)} rows)")


write_csv("S5_emotion_style", S5)
write_csv("S6_two_step", S6)
write_csv("S7_low_reversal", S7)
write_csv("S8_return_contract", S8)
