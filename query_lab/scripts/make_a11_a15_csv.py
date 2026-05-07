"""Generate A11 / A13 / A14 / A15 CSV files with UTF-8 BOM."""
import csv, io, os

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

def row(qid, topic, category, query, intent, cond, atoms, expr, tw, unit, op,
        risk_tags="", order="standard", risk_level="medium",
        recommended_usage="pending", notes=""):
    return [
        qid, "astock", "问财选A股", "stock",
        "wencai_query", topic, "seed_spec", "第三批深测",
        "v3", qid.split("-")[0] + "_" + {
            "A11":"relative_amount_scoped",
            "A12":"code_pool_requery",
            "A13":"limitup_pullback",
            "A14":"ma_pullback_boundary",
            "A15":"practical_combo_ceiling",
        }[qid.split("-")[0]],
        category, query, intent, cond, atoms, expr, tw, unit, op,
        order, risk_tags,
        "0","0","0","0","0","0","0","0","0",
        "pending", risk_level, recommended_usage, notes,
    ]

def write_csv(name, rows):
    path = os.path.join(BASE, name)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for r in rows:
            w.writerow(r)
    print(f"Written: {path} ({len(rows)} rows)")

# ── A11: 相对成交额 + 缩圈 ──────────────────────────────────────────────────
a11 = [
    row("A11-001","volume","scoped_relative",
        "创业板，今日成交额大于近5日平均成交额1.5倍",
        "创业板+成交额>近5日均×1.5",2,"今日成交额|近5日平均成交额|创业板",
        "relative","5d","倍数","relative_gt","","standard","medium","pending","缩圈创业板"),
    row("A11-002","volume","scoped_relative",
        "科创板，今日成交额大于近5日平均成交额1.5倍",
        "科创板+成交额>近5日均×1.5",2,"今日成交额|近5日平均成交额|科创板",
        "relative","5d","倍数","relative_gt","","standard","medium","pending","缩圈科创板"),
    row("A11-003","volume","scoped_relative",
        "军工板块，今日成交额大于近5日平均成交额1.5倍",
        "军工板块+成交额>近5日均×1.5",2,"今日成交额|近5日平均成交额|军工板块",
        "relative","5d","倍数","relative_gt","","standard","medium","pending","板块缩圈"),
    row("A11-004","volume","scoped_relative",
        "半导体板块，今日成交额大于近5日平均成交额1.5倍",
        "半导体板块+成交额>近5日均×1.5",2,"今日成交额|近5日平均成交额|半导体板块",
        "relative","5d","倍数","relative_gt","","standard","medium","pending","板块缩圈"),
    row("A11-005","volume","scoped_relative",
        "非ST，今日成交额大于近5日平均成交额1.5倍",
        "非ST+成交额>近5日均×1.5",2,"今日成交额|近5日平均成交额|非ST",
        "relative","5d","倍数","relative_gt","","standard","medium","pending","过滤缩圈"),
    row("A11-006","volume","scoped_relative",
        "流通市值在30亿到150亿之间，今日成交额大于近5日平均成交额1.5倍",
        "市值30~150亿+成交额>近5日均×1.5",2,"今日成交额|近5日平均成交额|流通市值",
        "relative","5d","倍数","relative_gt","","standard","medium","pending","市值缩圈"),
    row("A11-007","volume","scoped_relative",
        "今日成交额大于近5日平均成交额1.5倍，今日收盘价站上5日均线",
        "成交额>近5日均×1.5+收盘>MA5",2,"今日成交额|近5日平均成交额|MA5",
        "relative+compare","mixed","混合","relative_gt+gt","","standard","medium","pending","组合均线"),
    row("A11-008","volume","scoped_relative",
        "今日成交额大于近5日平均成交额1.5倍，近3日涨幅小于10%",
        "成交额>近5日均×1.5+近3日涨<10%",2,"今日成交额|近5日平均成交额|近3日涨幅",
        "relative+simple","mixed","混合","relative_gt+lt","","standard","medium","pending","组合涨幅过滤"),
]
write_csv("A11_relative_amount_scoped.csv", a11)

# ── A13: 涨停后回撤/缩量 ────────────────────────────────────────────────────
a13 = [
    row("A13-001","limitup","limitup_basic",
        "近10日有涨停","近10日有涨停",1,"近10日涨停",
        "pattern","10d","定性","pattern","","standard","medium","pending","基础涨停识别"),
    row("A13-002","limitup","limitup_pullback",
        "近10日有涨停，近3日股价回撤大于3%",
        "近10日涨停+近3日回撤>3%",2,"近10日涨停|近3日股价回撤",
        "pattern+simple","mixed","百分比","pattern+gt","","standard","medium","pending","回撤3%"),
    row("A13-003","limitup","limitup_pullback",
        "近10日有涨停，近3日股价回撤大于5%",
        "近10日涨停+近3日回撤>5%",2,"近10日涨停|近3日股价回撤",
        "pattern+simple","mixed","百分比","pattern+gt","","standard","medium","pending","回撤5%"),
    row("A13-004","limitup","limitup_shrink",
        "近10日有涨停，近3日缩量",
        "近10日涨停+近3日缩量",2,"近10日涨停|近3日缩量",
        "pattern+vague","mixed","定性","pattern+vague","non_standard_field","standard","high","manual_only","缩量字段测试"),
    row("A13-005","limitup","limitup_shrink",
        "近10日有涨停，近3日成交量逐日缩小",
        "近10日涨停+近3日量递减",2,"近10日涨停|近3日成交量",
        "pattern+consecutive","mixed","定性","pattern+decreasing","non_standard_field","standard","high","manual_only","连续递减"),
    row("A13-006","limitup","limitup_combo",
        "近10日有涨停，近3日股价回撤大于3%，近3日缩量",
        "近10日涨停+回撤>3%+缩量",3,"近10日涨停|近3日回撤|近3日缩量",
        "pattern+simple+vague","mixed","混合","pattern+gt+vague","non_standard_field","standard","high","manual_only","三条件组合"),
    row("A13-007","limitup","limitup_ma",
        "近10日有涨停，今日收盘价没有跌破5日均线",
        "近10日涨停+收盘>MA5(负向)",2,"近10日涨停|收盘价|5日均线",
        "pattern+compare","mixed","价格","pattern+not_break","","standard","medium","pending","均线不破表达"),
    row("A13-008","limitup","limitup_ma",
        "近10日有涨停，今日收盘价没有跌破10日均线",
        "近10日涨停+收盘>MA10(负向)",2,"近10日涨停|收盘价|10日均线",
        "pattern+compare","mixed","价格","pattern+not_break","","standard","medium","pending","10日均线不破"),
]
write_csv("A13_limitup_pullback.csv", a13)

# ── A14: 回撤 / 均线边界 ────────────────────────────────────────────────────
a14 = [
    row("A14-001","price_change","pullback",
        "近3日跌幅大于3%","近3日跌幅>3%",1,"近3日跌幅",
        "simple","3d","百分比","gt","","standard","low","pending","跌幅字段基础"),
    row("A14-002","price_change","pullback",
        "近3日跌幅大于5%","近3日跌幅>5%",1,"近3日跌幅",
        "simple","3d","百分比","gt","","standard","low","pending","跌幅5%"),
    row("A14-003","price_change","pullback_vague",
        "近3日股价回撤大于3%","近3日股价回撤>3%",1,"近3日股价回撤",
        "simple","3d","百分比","gt","non_standard_field","standard","medium","pending","回撤字段是否识别"),
    row("A14-004","price_change","pullback_vague",
        "近3日股价回撤大于5%","近3日股价回撤>5%",1,"近3日股价回撤",
        "simple","3d","百分比","gt","non_standard_field","standard","medium","pending","回撤5%字段"),
    row("A14-005","ma","ma_compare",
        "今日收盘价大于5日均线","收盘>MA5",1,"收盘价|5日均线",
        "compare","today","价格","gt","","standard","low","pending","正向均线比较"),
    row("A14-006","ma","ma_compare",
        "今日收盘价大于10日均线","收盘>MA10",1,"收盘价|10日均线",
        "compare","today","价格","gt","","standard","low","pending","10日均线正向"),
    row("A14-007","ma","ma_not_break",
        "今日收盘价没有跌破5日均线","收盘未跌破MA5",1,"收盘价|5日均线",
        "compare_negative","today","价格","not_break","","standard","medium","pending","负向均线表达"),
    row("A14-008","ma","ma_not_break",
        "今日收盘价没有跌破10日均线","收盘未跌破MA10",1,"收盘价|10日均线",
        "compare_negative","today","价格","not_break","","standard","medium","pending","10日均线负向"),
]
write_csv("A14_ma_pullback_boundary.csv", a14)

# ── A15: 实战组合天花板 ─────────────────────────────────────────────────────
a15_combo = [
    row("A15-001","volume","combo_3cond",
        "创业板，今日成交额大于近5日平均成交额1.5倍，今日收盘价站上5日均线",
        "创业板+成交额>近5日均×1.5+收盘>MA5",3,"创业板|成交额|近5日均成交额|MA5",
        "scoped+relative+compare","mixed","混合","scoped+relative_gt+gt","","standard","medium","pending","3条件实战"),
    row("A15-002","limitup","combo_3cond",
        "军工板块，近10日有涨停，近3日股价回撤大于3%",
        "军工+涨停+回撤>3%",3,"军工板块|近10日涨停|近3日回撤",
        "scoped+pattern+simple","mixed","混合","scoped+pattern+gt","","standard","medium","pending","板块+涨停+回撤"),
    row("A15-003","limitup","combo_4cond",
        "半导体板块，近10日有涨停，近3日缩量，今日收盘价大于10日均线",
        "半导体+涨停+缩量+收盘>MA10",4,"半导体板块|近10日涨停|缩量|MA10",
        "scoped+pattern+vague+compare","mixed","混合","scoped+pattern+vague+gt","non_standard_field","standard","high","manual_only","4条件含缩量"),
    row("A15-004","volume","combo_3cond",
        "非ST，流通市值在30亿到150亿之间，今日成交额大于近5日平均成交额1.5倍",
        "非ST+市值30~150亿+成交额>近5日均×1.5",3,"非ST|流通市值|成交额|近5日均成交额",
        "filter+range+relative","mixed","混合","filter+between+relative_gt","","standard","medium","pending","过滤+市值+相对"),
    row("A15-005","limitup","combo_3cond",
        "近10日有涨停，近3日股价回撤大于3%，今日收盘价大于5日均线",
        "涨停+回撤>3%+收盘>MA5",3,"近10日涨停|近3日回撤|MA5",
        "pattern+simple+compare","mixed","混合","pattern+gt+gt","","standard","medium","pending","涨停+回撤+均线"),
    row("A15-006","limitup","combo_3cond",
        "近10日有涨停，近3日成交量逐日缩小，今日收盘价大于10日均线",
        "涨停+量递减+收盘>MA10",3,"近10日涨停|近3日成交量|MA10",
        "pattern+consecutive+compare","mixed","混合","pattern+decreasing+gt","non_standard_field","standard","high","manual_only","涨停+缩量+均线"),
    row("A15-007","volume","combo_3cond",
        "今日成交额大于近5日平均成交额1.5倍，近3日涨幅小于10%，今日收盘价大于5日均线",
        "成交额>近5日均×1.5+近3日涨<10%+收盘>MA5",3,"成交额|近5日均成交额|近3日涨幅|MA5",
        "relative+simple+compare","mixed","混合","relative_gt+lt+gt","","standard","medium","pending","相对+涨幅+均线3条"),
    row("A15-008","limitup","combo_4cond",
        "创业板，近10日有涨停，近3日股价回撤大于5%，今日收盘价没有跌破10日均线",
        "创业板+涨停+回撤>5%+未破MA10",4,"创业板|近10日涨停|近3日回撤|MA10",
        "scoped+pattern+simple+compare_neg","mixed","混合","scoped+pattern+gt+not_break","","standard","medium","pending","4条件负向均线"),
]

a15_ceiling = [
    row("A15-009","combo","ceiling_4cond",
        "非ST，上市超过60天，今日涨幅大于3%，今日成交额大于3亿",
        "非ST+上市>60天+涨>3%+额>3亿",4,"非ST|上市天数|今日涨幅|今日成交额",
        "filter+multi","today","混合","multi","","standard","low","pending","4条件基准线"),
    row("A15-010","combo","ceiling_5cond",
        "非ST，上市超过60天，今日涨幅大于3%，今日成交额大于3亿，今日换手率大于5%",
        "非ST+上市>60天+涨>3%+额>3亿+换手>5%",5,"非ST|上市天数|涨幅|成交额|换手率",
        "filter+multi","today","混合","multi","","standard","low","pending","5条件"),
    row("A15-011","combo","ceiling_6cond",
        "非ST，上市超过60天，今日涨幅大于3%，今日成交额大于3亿，今日换手率大于5%，流通市值在30亿到150亿之间",
        "非ST+上市>60天+涨>3%+额>3亿+换手>5%+市值30~150亿",6,"非ST|上市天数|涨幅|成交额|换手率|流通市值",
        "filter+multi+range","today","混合","multi+between","","standard","low","pending","6条件"),
    row("A15-012","combo","ceiling_7cond",
        "非ST，上市超过60天，今日涨幅大于3%，今日成交额大于3亿，今日换手率大于5%，流通市值在30亿到150亿之间，今日收盘价大于5日均线",
        "非ST+上市>60天+涨>3%+额>3亿+换手>5%+市值30~150亿+收盘>MA5",7,"非ST|上市天数|涨幅|成交额|换手率|流通市值|MA5",
        "filter+multi+compare","today","混合","multi+gt","","standard","low","pending","7条件"),
    row("A15-013","combo","ceiling_8cond",
        "非ST，上市超过60天，今日涨幅大于3%，今日成交额大于3亿，今日换手率大于5%，流通市值在30亿到150亿之间，今日收盘价大于5日均线，今日主力净流入为正",
        "非ST+上市>60天+涨>3%+额>3亿+换手>5%+市值30~150亿+收盘>MA5+主力正",8,"非ST|上市天数|涨幅|成交额|换手率|流通市值|MA5|主力净流入",
        "filter+multi+compare+positive","today","混合","multi+gt+positive","","standard","low","pending","8条件"),
]

# 分隔符测试：语义一致，只改分隔符
a15_sep = [
    row("A15-014","separator","sep_cn_comma",
        "非ST，上市超过60天，今日涨幅大于3%，今日成交额大于3亿",
        "非ST+上市>60天+涨>3%+额>3亿(中文逗号)",4,"非ST|上市天数|涨幅|成交额",
        "filter+multi","today","混合","multi","","standard","low","pending","分隔符：中文逗号（基准）"),
    row("A15-015","separator","sep_pause",
        "非ST、上市超过60天、今日涨幅大于3%、今日成交额大于3亿",
        "非ST+上市>60天+涨>3%+额>3亿(顿号)",4,"非ST|上市天数|涨幅|成交额",
        "filter+multi","today","混合","multi","","standard","low","pending","分隔符：顿号"),
    row("A15-016","separator","sep_space",
        "非ST 上市超过60天 今日涨幅大于3% 今日成交额大于3亿",
        "非ST+上市>60天+涨>3%+额>3亿(空格)",4,"非ST|上市天数|涨幅|成交额",
        "filter+multi","today","混合","multi","","standard","low","pending","分隔符：空格"),
    row("A15-017","separator","sep_en_comma",
        "非ST,上市超过60天,今日涨幅大于3%,今日成交额大于3亿",
        "非ST+上市>60天+涨>3%+额>3亿(英文逗号)",4,"非ST|上市天数|涨幅|成交额",
        "filter+multi","today","混合","multi","","standard","low","pending","分隔符：英文逗号"),
    row("A15-018","separator","sep_slash",
        "非ST/上市超过60天/今日涨幅大于3%/今日成交额大于3亿",
        "非ST+上市>60天+涨>3%+额>3亿(斜杠)",4,"非ST|上市天数|涨幅|成交额",
        "filter+multi","today","混合","multi","","standard","low","pending","分隔符：斜杠"),
]

write_csv("A15_practical_combo_ceiling.csv", a15_combo + a15_ceiling + a15_sep)
print("All done.")
