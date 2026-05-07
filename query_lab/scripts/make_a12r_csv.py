"""Generate A12R_code_pool_repair.csv — minimal repair test for code-pool requery."""
import csv, os

BASE = r"F:\v.6\v6-op\query_lab\cases\astock_问财选A股"

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

def row(qid, cat, qt, intent, cond, atoms, rl="medium", ru="pending", notes="", risk_tags=""):
    return [
        qid, "astock", "问财选A股", "stock",
        "wencai_query", "code_pool_repair", "seed_spec", "A12修复专项",
        "v3", "A12R_code_pool_repair",
        cat, qt, intent, cond, atoms,
        "pool_repair", "today", "定性", "pool_or_scope",
        "standard", risk_tags,
        "0","0","0","0","0","0","0","0","0",
        "pending", rl, ru, notes,
    ]

rows = [
    # ── 代码池中文写法修复 ─────────────────────────────────────────────────
    row("A12R-001","pool_code_field_or",
        "股票代码为000060或603399，今日成交额大于近5日平均成交额1.5倍",
        "代码为000060或603399+成交额>近5日均×1.5",2,
        "股票代码|成交额|近5日均成交额",
        "medium","pending","代码字段OR写法，期望只返回指定代码",""),
    row("A12R-002","pool_cert_field_or",
        "证券代码为000060或603399，今日成交额大于近5日平均成交额1.5倍",
        "证券代码为000060或603399+成交额>近5日均×1.5",2,
        "证券代码|成交额|近5日均成交额",
        "medium","pending","证券代码别称",""),
    row("A12R-003","pool_bare_or",
        "000060或603399，今日成交额大于近5日平均成交额1.5倍",
        "裸代码OR+成交额>近5日均×1.5",2,
        "股票代码|成交额|近5日均成交额",
        "medium","pending","裸代码OR写法",""),
    row("A12R-004","pool_code_list",
        "股票代码是000060、603399、600519、000858，今日成交额大于近5日平均成交额1.5倍",
        "代码列表+成交额>近5日均×1.5",2,
        "股票代码|成交额|近5日均成交额",
        "medium","pending","顿号分隔代码列表",""),
    row("A12R-005","pool_name_or",
        "股票简称为中金岭南或抚顺特钢，今日成交额大于近5日平均成交额1.5倍",
        "股票简称OR+成交额>近5日均×1.5",2,
        "股票简称|成交额|近5日均成交额",
        "medium","pending","简称OR写法（000060=中金岭南,603399=抚顺特钢）",""),
    # ── 单代码验证（确认000060/603399是否今日仍满足1.5倍条件）─────────────
    row("A12R-006","single_code_target",
        "股票代码为000060，今日成交额大于近5日平均成交额1.5倍",
        "000060+成交额>近5日均×1.5",2,
        "股票代码|成交额|近5日均成交额",
        "medium","pending","单代码验证命中",""),
    row("A12R-007","single_code_target",
        "股票代码为603399，今日成交额大于近5日平均成交额1.5倍",
        "603399+成交额>近5日均×1.5",2,
        "股票代码|成交额|近5日均成交额",
        "medium","pending","单代码验证命中",""),
    row("A12R-008","single_code_noise",
        "股票代码为600519，今日成交额大于近5日平均成交额1.5倍",
        "600519+成交额>近5日均×1.5",2,
        "股票代码|成交额|近5日均成交额",
        "medium","pending","对照噪声代码（茅台，不应命中）",""),
    # ── 非代码池缩圈对照（确认失败来源） ─────────────────────────────────
    row("A12R-009","scope_kcb",
        "科创板，今日成交额大于近5日平均成交额1.5倍",
        "科创板+成交额>近5日均×1.5",2,
        "科创板|成交额|近5日均成交额",
        "medium","pending","科创板缩圈对照（A11-002 已测rc=1）",""),
    row("A12R-010","scope_military",
        "军工板块，今日成交额大于近5日平均成交额1.5倍",
        "军工板块+成交额>近5日均×1.5",2,
        "军工板块|成交额|近5日均成交额",
        "medium","pending","军工板块对照（A11-003 已测rc=1）",""),
    # ── 军工 + 相对成交额 + 技术指标 ──────────────────────────────────────
    row("A12R-011","scope_military_macd",
        "军工板块，今日成交额大于近5日平均成交额1.5倍，MACD金叉",
        "军工板块+成交额>近5日均×1.5+MACD金叉",3,
        "军工板块|成交额|近5日均成交额|MACD",
        "medium","pending","军工+相对成交额+MACD金叉三条件",""),
    row("A12R-012","scope_military_kdj",
        "军工板块，今日成交额大于近5日平均成交额1.5倍，KDJ金叉",
        "军工板块+成交额>近5日均×1.5+KDJ金叉",3,
        "军工板块|成交额|近5日均成交额|KDJ",
        "medium","pending","军工+相对成交额+KDJ金叉",""),
    row("A12R-013","scope_military_macd_zero",
        "军工板块，今日成交额大于近5日平均成交额1.5倍，MACD在零轴之上",
        "军工板块+成交额>近5日均×1.5+MACD>0",3,
        "军工板块|成交额|近5日均成交额|MACD零轴",
        "medium","pending","MACD零轴字段是否被识别",""),
]

path = os.path.join(BASE, "A12R_code_pool_repair.csv")
with open(path, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(HEADER)
    for r in rows:
        w.writerow(r)
print(f"Written: {path} ({len(rows)} rows)")
