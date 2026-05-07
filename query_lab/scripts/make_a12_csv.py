"""Generate A12 CSV using real codes from A11 results."""
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

# A11-005 满足条件的代码（已实测）
# 另外混入 8 个大盘蓝筹（今日大概率不满足 1.5 倍成交额条件）
TARGET_CODES = ["000060", "603399"]
NOISE_CODES  = ["600519", "000858", "600036", "601318", "000333", "600276", "000001", "600000"]

# 两种分隔符格式（测试问财是否都能识别）
POOL_CN   = "、".join(TARGET_CODES + NOISE_CODES)  # 顿号
POOL_COMMA = "，".join(TARGET_CODES + NOISE_CODES)  # 中文逗号

def base(qid, cat, qt, intent, cond, atoms, expr, op, rl="medium", ru="pending", notes="", risk_tags=""):
    return [
        qid, "astock", "问财选A股", "stock",
        "wencai_query", "code_pool", "seed_spec", "第三批深测",
        "v3", "A12_code_pool_requery",
        cat, qt, intent, cond, atoms, expr, "today", "定性", op,
        "standard", risk_tags,
        "0","0","0","0","0","0","0","0","0",
        "pending", rl, ru, notes,
    ]

rows = [
    base("A12-001","pool_relative",
         f"在以下股票代码中，哪些今日成交额大于近5日平均成交额1.5倍：{POOL_CN}",
         "代码池+成交额>近5日均×1.5",2,
         "股票代码池|成交额|近5日均成交额",
         "pool+relative","relative_gt","medium","pending",
         f"期望返回 {TARGET_CODES}；代码池:{POOL_CN[:30]}..."),
    base("A12-002","pool_relative_ma",
         f"在以下股票代码中，哪些今日成交额大于近5日平均成交额1.5倍，且今日收盘价站上5日均线：{POOL_CN}",
         "代码池+成交额>近5日均×1.5+收盘>MA5",3,
         "股票代码池|成交额|近5日均成交额|MA5",
         "pool+relative+compare","relative_gt+gt","medium","pending",
         "双条件代码池"),
    base("A12-003","pool_pullback",
         f"在以下股票代码中，哪些近3日股价回撤大于3%：{POOL_CN}",
         "代码池+近3日回撤>3%",2,
         "股票代码池|近3日股价回撤",
         "pool+simple","gt","medium","pending",
         "回撤条件代码池"),
    base("A12-004","pool_limitup",
         f"在以下股票代码中，哪些近10日有涨停：{POOL_CN}",
         "代码池+近10日有涨停",2,
         "股票代码池|近10日涨停",
         "pool+pattern","pattern","medium","pending",
         "涨停条件代码池"),
    base("A12-005","pool_shrink",
         f"在以下股票代码中，哪些近3日缩量：{POOL_CN}",
         "代码池+近3日缩量",2,
         "股票代码池|近3日缩量",
         "pool+vague","vague","high","manual_only",
         "缩量字段代码池","non_standard_field"),
    base("A12-006","pool_ma_not_break",
         f"在以下股票代码中，哪些没有跌破10日均线：{POOL_CN}",
         "代码池+未破MA10",2,
         "股票代码池|10日均线",
         "pool+compare_neg","not_break","medium","pending",
         "均线不破代码池"),
]

path = os.path.join(BASE, "A12_code_pool_requery.csv")
with open(path, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(HEADER)
    for r in rows:
        w.writerow(r)
print(f"Written: {path} ({len(rows)} rows)")
print(f"Target codes (should be returned): {TARGET_CODES}")
print(f"Noise codes: {NOISE_CODES}")
