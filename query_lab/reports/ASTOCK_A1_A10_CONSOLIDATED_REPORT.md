# 问财选A股 A1-A10 整理验收报告

生成时间：2026-05-07 16:12:24

## 1. 纳入范围

只纳入以下已完成 run；未完成、中断、早期调试 run 全部排除。

| 组别 | run_id | RUN_COMPLETE | 行数 | 状态统计 |
|---|---|---:|---:|---|
| A1_basic | run_20260507_150529 | True | 20 | stable=20 |
| A2_synonym | run_20260507_150925 | True | 15 | stable=15 |
| A3_combo | run_20260507_151853 | True | 7 | stable=7 |
| A4_risky | run_20260507_152032 | True | 8 | failed=1, forbidden=5, risky=2 |
| A5_forbidden | run_20260507_152351 | True | 3 | invalid_query=3 |
| A6_time_window | run_20260507_154006 | True | 8 | failed=1, risky=1, stable=6 |
| A7_numeric_relative | run_20260507_154212 | True | 8 | risky=1, stable=7 |
| A8_capital_flow | run_20260507_154454 | True | 8 | stable=8 |
| A9_technical_shape | run_20260507_154831 | True | 8 | risky=4, stable=4 |
| A10_complex_boundary | run_20260507_155054 | True | 8 | forbidden=2, risky=4, stable=2 |

## 2. 清理规则

- 同一句 Query 后续已 `stable` 或 `risky` 的，覆盖早期 `failed/empty_result/api_error`。
- 接口返回 stable 但含 `relative_comparison / consecutive_condition / non_standard_field` 等风险标签的，整理时降为 `weak`。
- 标准矩阵生成默认使用 `大于 / 小于 / 在...之间 / 为正`，同义词如 `超过/高于/以上` 只作为识别能力，不作为默认生成句式。
- 只整理 A1-A10，本报告不新增 A11-A15。
- `strong` 可进入标准矩阵；`weak` 只可人工选择或二次确认；`forbidden` 不得进入 P1-P6；`review` 留给第三阶段复测。

## 3. 总体结论

- 原始纳入记录：93 条
- 去重清理后：82 条
- 被覆盖旧记录：11 条
- strong / 可进标准矩阵：54 条
- weak / 谨慎人工用：17 条
- forbidden / 禁用或非法：10 条
- review / 待第三阶段复测：1 条

清理后状态统计：

| 状态 | 数量 |
|---|---:|
| failed | 1 |
| forbidden | 7 |
| invalid_query | 3 |
| risky | 11 |
| stable | 60 |

## 4. 可进入标准矩阵 strong

这些是当前最适合做字段矩阵、P1-P6 收藏底座的表达。

| 分组 | query_id | 状态 | 用法 | 条件 | 返回 | Query | 标签/原因 |
|---|---:|---|---|---:|---:|---|---|
| A10_complex_boundary | A10-005 | stable | strong | 2 | 84 | 今日涨幅大于3%，但近20日涨幅小于0% | 返回 84 条，语义稳定 |
| A10_complex_boundary | A10-006 | stable | strong | 2 | 81 | 今日涨幅大于5%，但主力净流入为负 | 返回 81 条，语义稳定 |
| A1_basic | A1-002 | stable | strong | 1 | 100 | 今日涨幅大于5% | 返回 100 条，语义稳定 |
| A1_basic | A1-003 | stable | strong | 2 | 100 | 今日涨幅大于3%，非ST | 返回 100 条，语义稳定 |
| A1_basic | A1-005 | stable | strong | 1 | 100 | 今日成交额大于5亿 | 返回 100 条，语义稳定 |
| A1_basic | A1-006 | stable | strong | 1 | 100 | 今日换手率大于5% | 返回 100 条，语义稳定 |
| A1_basic | A1-007 | stable | strong | 1 | 100 | 今日换手率大于10% | 返回 100 条，语义稳定 |
| A1_basic | A1-008 | stable | strong | 1 | 100 | 今日量比大于1.5 | 返回 100 条，语义稳定 |
| A1_basic | A1-009 | stable | strong | 1 | 100 | 今日量比大于2 | 返回 100 条，语义稳定 |
| A1_basic | A1-011 | stable | strong | 1 | 100 | 流通市值在80亿到300亿之间 | 返回 100 条，语义稳定 |
| A1_basic | A1-012 | stable | strong | 1 | 100 | 总市值在50亿到300亿之间 | 返回 100 条，语义稳定 |
| A1_basic | A1-017 | stable | strong | 1 | 100 | 近20日涨幅大于20% | 返回 100 条，语义稳定 |
| A1_basic | A1-018 | stable | strong | 2 | 100 | 非ST，非停牌 | 返回 100 条，语义稳定 |
| A1_basic | A1-019 | stable | strong | 3 | 100 | 上市超过60天，非ST，非停牌 | 返回 100 条，语义稳定 |
| A1_basic | A1-020 | stable | strong | 1 | 100 | 今日收盘价大于5日均线 | 返回 100 条，语义稳定 |
| A2_synonym | A2-002 | stable | strong | 1 | 100 | 今天涨幅大于3% | 返回 100 条，语义稳定 |
| A2_synonym | A2-003 | stable | strong | 1 | 100 | 涨幅大于3% | 返回 100 条，语义稳定 |
| A2_synonym | A2-004 | stable | strong | 1 | 100 | 涨幅超过3% | 返回 100 条，语义稳定 |
| A2_synonym | A2-005 | stable | strong | 1 | 100 | 涨幅高于3% | 返回 100 条，语义稳定 |
| A2_synonym | A2-006 | stable | strong | 1 | 100 | 今日涨幅超过3% | 返回 100 条，语义稳定 |
| A2_synonym | A2-007 | stable | strong | 1 | 100 | 今日涨幅3%以上 | 返回 100 条，语义稳定 |
| A2_synonym | A2-008 | stable | strong | 1 | 100 | 今天上涨超过3% | 返回 100 条，语义稳定 |
| A2_synonym | A2-009 | stable | strong | 1 | 100 | 今日成交额大于3亿 | 返回 100 条，语义稳定 |
| A2_synonym | A2-010 | stable | strong | 1 | 100 | 今日成交金额大于3亿 | 返回 100 条，语义稳定 |
| A2_synonym | A2-011 | stable | strong | 1 | 100 | 今日成交额超过3亿 | 返回 100 条，语义稳定 |
| A2_synonym | A2-012 | stable | strong | 1 | 100 | 今日成交额3亿以上 | 返回 100 条，语义稳定 |
| A2_synonym | A2-014 | stable | strong | 1 | 100 | 主力资金净流入为正 | 返回 100 条，语义稳定 |
| A2_synonym | A2-015 | stable | strong | 1 | 100 | 今日主力资金流入 | 返回 100 条，语义稳定 |
| A3_combo | A3-001 | stable | strong | 1 | 100 | 今日涨幅大于3% | 返回 100 条，语义稳定 |
| A3_combo | A3-002 | stable | strong | 2 | 100 | 非ST，今日涨幅大于3% | 返回 100 条，语义稳定 |
| A3_combo | A3-003 | stable | strong | 3 | 100 | 非ST，非停牌，今日涨幅大于3% | 返回 100 条，语义稳定 |
| A3_combo | A3-004 | stable | strong | 4 | 100 | 非ST，非停牌，今日涨幅大于3%，今日成交额大于3亿 | 返回 100 条，语义稳定 |
| A3_combo | A3-005 | stable | strong | 5 | 100 | 非ST，非停牌，今日涨幅大于3%，今日成交额大于3亿，今日换手率大于5% | 返回 100 条，语义稳定 |
| A3_combo | A3-006 | stable | strong | 6 | 100 | 非ST，非停牌，今日涨幅大于3%，今日成交额大于3亿，今日换手率大于5%，流通市值在30亿到150亿之间 | 返回 100 条，语义稳定 |
| A3_combo | A3-007 | stable | strong | 7 | 100 | 非ST，非停牌，非新股，今日涨幅大于3%，今日成交额大于3亿，今日换手率大于5%，流通市值在30亿到150亿之间 | 返回 100 条，语义稳定 |
| A6_time_window | A6-001 | stable | strong | 1 | 100 | 近3日涨幅大于5% | 返回 100 条，语义稳定 |
| A6_time_window | A6-002 | stable | strong | 1 | 100 | 近5日涨幅大于10% | 返回 100 条，语义稳定 |
| A6_time_window | A6-003 | stable | strong | 1 | 100 | 近20日涨幅小于10% | 返回 100 条，语义稳定 |
| A6_time_window | A6-004 | stable | strong | 1 | 100 | 最近一个月涨幅大于20% | 返回 100 条，语义稳定 |
| A6_time_window | A6-007 | stable | strong | 1 | 100 | 近3日换手率大于10% | 返回 100 条，语义稳定 |
| A7_numeric_relative | A7-001 | stable | strong | 1 | 100 | 流通市值大于30亿且小于150亿 | 返回 100 条，语义稳定 |
| A7_numeric_relative | A7-002 | stable | strong | 1 | 100 | 流通市值在30亿到150亿之间 | 返回 100 条，语义稳定 |
| A7_numeric_relative | A7-003 | stable | strong | 2 | 28 | 今日涨幅大于5%，近5日涨幅小于0% | 返回 28 条，语义稳定 |
| A7_numeric_relative | A7-008 | stable | strong | 2 | 100 | 今日涨幅小于5%，今日成交额大于5亿 | 返回 100 条，语义稳定 |
| A8_capital_flow | A8-001 | stable | strong | 1 | 100 | 今日主力净流入大于5000万 | 返回 100 条，语义稳定 |
| A8_capital_flow | A8-002 | stable | strong | 1 | 100 | 今日主力净流入大于1亿 | 返回 100 条，语义稳定 |
| A8_capital_flow | A8-003 | stable | strong | 1 | 100 | 今日主力净流入为正 | 返回 100 条，语义稳定 |
| A8_capital_flow | A8-005 | stable | strong | 1 | 100 | 今日大单净流入大于3000万 | 返回 100 条，语义稳定 |
| A8_capital_flow | A8-006 | stable | strong | 1 | 100 | 今日超大单净流入为正 | 返回 100 条，语义稳定 |
| A8_capital_flow | A8-007 | stable | strong | 1 | 100 | 今日资金净流入大于5000万 | 返回 100 条，语义稳定 |
| A9_technical_shape | A9-001 | stable | strong | 1 | 100 | 今日收盘价站上5日均线 | 返回 100 条，语义稳定 |
| A9_technical_shape | A9-002 | stable | strong | 1 | 100 | 今日收盘价大于20日均线 | 返回 100 条，语义稳定 |
| A9_technical_shape | A9-004 | stable | strong | 1 | 100 | MACD金叉 | 返回 100 条，语义稳定 |
| A9_technical_shape | A9-005 | stable | strong | 1 | 100 | KDJ金叉 | 返回 100 条，语义稳定 |

## 5. weak / risky：可问，但不要默认生成

这些表达能返回或部分返回，但含相对比较、模糊词、非标准技术字段或图形字段。建议作为人工高级选项，不自动进标准 P。

| 分组 | query_id | 状态 | 用法 | 条件 | 返回 | Query | 标签/原因 |
|---|---:|---|---|---:|---:|---|---|
| A10_complex_boundary | A10-001 | risky | weak | 2 | 100 | 今日量比明显大于前两日，且今日涨幅大于3% | vague_condition｜relative_comparison |
| A10_complex_boundary | A10-002 | risky | weak | 2 | 100 | 今日成交额放大但股价涨幅不超过5% | vague_condition |
| A10_complex_boundary | A10-003 | risky | weak | 2 | 100 | 主力净流入显著增加，且近5日涨幅小于10% | vague_condition |
| A10_complex_boundary | A10-004 | risky | weak | 2 | 90 | 平台突破且成交额大于近5日平均成交额 | vague_condition｜relative_comparison｜non_standard_field |
| A4_risky | A4-001 | risky | weak | 1 | 100 | 今日换手率大于近5日平均换手率的1.5倍 | vague_condition |
| A6_time_window | A6-005 | stable | weak | 1 | 100 | 连续3日主力净流入为正 | consecutive_condition |
| A6_time_window | A6-006 | risky | weak | 1 | 17 | 近5日成交额持续放大 | vague_condition｜consecutive_condition |
| A7_numeric_relative | A7-004 | stable | weak | 1 | 100 | 今日量比大于前2日量比 | relative_comparison |
| A7_numeric_relative | A7-005 | risky | weak | 1 | 100 | 今日成交额大于近5日平均成交额的1.5倍 | relative_comparison｜vague_condition |
| A7_numeric_relative | A7-006 | stable | weak | 1 | 100 | 今日换手率大于近3日平均换手率 | relative_comparison |
| A7_numeric_relative | A7-007 | stable | weak | 1 | 100 | 今日成交额是昨日成交额的2倍以上 | relative_comparison |
| A8_capital_flow | A8-004 | stable | weak | 1 | 100 | 近3日主力资金连续净流入 | consecutive_condition |
| A8_capital_flow | A8-008 | stable | weak | 1 | 100 | 今日主力净流入占成交额比例大于5% | relative_comparison |
| A9_technical_shape | A9-003 | risky | weak | 1 | 100 | 均线多头排列 | non_standard_field |
| A9_technical_shape | A9-006 | risky | weak | 1 | 6 | 今日K线为锤子线 | non_standard_field｜candlestick |
| A9_technical_shape | A9-007 | risky | weak | 1 | 100 | 今日K线为阳包阴 | non_standard_field｜candlestick |
| A9_technical_shape | A9-008 | risky | weak | 1 | 100 | 收盘价站上JMA均线 | jma_unverified｜non_standard_field |

## 6. forbidden / invalid：不得进入 P1-P6

| 分组 | query_id | 状态 | 用法 | 条件 | 返回 | Query | 标签/原因 |
|---|---:|---|---|---:|---:|---|---|
| A10_complex_boundary | A10-007 | forbidden | forbidden | 0 | 73 | 低位放量突破 | vague_word｜sentiment_word |
| A10_complex_boundary | A10-008 | forbidden | forbidden | 0 | 10 | 图形走得很好 | vague_word｜sentiment_word｜natural_language |
| A4_risky | A4-003 | forbidden | forbidden | 0 | 14 | 强势股 | vague_word｜sentiment_word |
| A4_risky | A4-004 | forbidden | forbidden | 0 | 100 | 放量上涨股票 | vague_word |
| A4_risky | A4-005 | forbidden | forbidden | 0 | 100 | 短线龙头股 | vague_word｜sentiment_word |
| A4_risky | A4-006 | forbidden | forbidden | 0 | 19 | 明天可能上涨的股票 | prediction_word |
| A4_risky | A4-007 | forbidden | forbidden | 0 | 0 | 有可能涨停的股票 | prediction_word |
| A5_forbidden | A5-001 | invalid_query | forbidden | 0 | 0 | A-shares with market cap between 3 and 15 billion | english_query |
| A5_forbidden | A5-002 | invalid_query | forbidden | 0 | 0 | stocks with volume ratio greater than 2 | english_query |
| A5_forbidden | A5-003 | invalid_query | forbidden | 0 | 0 |  | empty_query |

## 7. review：第三阶段优先复测

| 分组 | query_id | 状态 | 用法 | 条件 | 返回 | Query | 标签/原因 |
|---|---:|---|---|---:|---:|---|---|
| A6_time_window | A6-008 | failed | review | 1 | 0 | 近20日成交额大于5亿 | 问财 API 接口异常（session 耗尽 / 网络 / 认证失败） |

## 8. 字段稳定性快照

| 字段 | stable | risky | failed | forbidden | invalid_query |
|---|---:|---:|---:|---:|---:|
| 今日涨幅 | 20 | 2 | 0 | 0 | 0 |
| 今日成交额 | 12 | 3 | 0 | 0 | 0 |
| 非ST | 9 | 0 | 0 | 0 | 0 |
| 今日主力净流入 | 7 | 0 | 0 | 0 | 0 |
| 非停牌 | 7 | 0 | 0 | 0 | 0 |
| 今日换手率 | 6 | 1 | 0 | 0 | 0 |
| 流通市值 | 5 | 0 | 0 | 0 | 0 |
| 今日量比 | 3 | 1 | 0 | 0 | 0 |
| 收盘价 | 3 | 1 | 0 | 0 | 0 |
| 近20日涨幅 | 3 | 0 | 0 | 0 | 0 |
| 5日均线 | 2 | 0 | 0 | 0 | 0 |
| 近5日涨幅 | 2 | 1 | 0 | 0 | 0 |
| 20日均线 | 1 | 0 | 0 | 0 | 0 |
| KDJ | 1 | 0 | 0 | 0 | 0 |
| MACD | 1 | 0 | 0 | 0 | 0 |
| 上市超过60天 | 1 | 0 | 0 | 0 | 0 |
| 主力净流入 | 1 | 1 | 0 | 0 | 0 |
| 今日大单净流入 | 1 | 0 | 0 | 0 | 0 |
| 今日资金净流入 | 1 | 0 | 0 | 0 | 0 |
| 今日超大单净流入 | 1 | 0 | 0 | 0 | 0 |
| 前2日量比 | 1 | 1 | 0 | 0 | 0 |
| 总市值 | 1 | 0 | 0 | 0 | 0 |
| 昨日成交额 | 1 | 0 | 0 | 0 | 0 |
| 近1月涨幅 | 1 | 0 | 0 | 0 | 0 |
| 近3日主力净流入 | 1 | 0 | 0 | 0 | 0 |
| 近3日平均换手率 | 1 | 0 | 0 | 0 | 0 |
| 近3日换手率 | 1 | 0 | 0 | 0 | 0 |
| 近3日涨幅 | 1 | 0 | 0 | 0 | 0 |
| 非新股 | 1 | 0 | 0 | 0 | 0 |
| INVALID | 0 | 0 | 0 | 0 | 3 |
| JMA均线 | 0 | 1 | 0 | 0 | 0 |
| K线形态 | 0 | 2 | 0 | 0 | 0 |
| 低位 | 0 | 0 | 0 | 1 | 0 |
| 可能上涨 | 0 | 0 | 0 | 1 | 0 |
| 可能涨停 | 0 | 0 | 0 | 1 | 0 |
| 图形走势 | 0 | 0 | 0 | 1 | 0 |
| 均线多头 | 0 | 1 | 0 | 0 | 0 |
| 平台突破 | 0 | 1 | 0 | 0 | 0 |
| 强势股 | 0 | 0 | 0 | 1 | 0 |
| 放量 | 0 | 0 | 0 | 1 | 0 |
| 放量上涨 | 0 | 0 | 0 | 1 | 0 |
| 明天 | 0 | 0 | 0 | 1 | 0 |
| 突破 | 0 | 0 | 0 | 1 | 0 |
| 近20日成交额 | 0 | 0 | 1 | 0 | 0 |
| 近5日平均成交额 | 0 | 2 | 0 | 0 | 0 |
| 近5日平均换手率 | 0 | 1 | 0 | 0 | 0 |
| 近5日成交额 | 0 | 1 | 0 | 0 | 0 |
| 龙头 | 0 | 0 | 0 | 1 | 0 |

## 9. 第三阶段建议

- 先做 A11：给定股票池 / Bridge 二次验证。重点测“在这些代码中筛选/验证”。
- 再做 A12：重型相对比较降载测试。比如先主题/板块/均线缩小股票池，再问平均成交额、量比、缩量。
- 再做 A13：K线/形态字段专项。锤子线、阳包阴、平台突破、跌破/不跌破均线。
- 再做 A14：涨停/回撤/缩量组合。比如十日内涨停、三日缩量、回撤 3%、未跌破 5 日均线。
- 最后做 A15：矩阵生成验证。用法典字段+关系+数值自动拼标准 Query，再跑小批量验证。

## 10. 产物

- `query_lab/reports/astock_a1_a10_clean_dictionary.csv`：Excel 友好 UTF-8 BOM 表。
- `query_lab/reports/astock_a1_a10_clean_dictionary.json`：后续页面/矩阵可读取的干净字典。
- `query_lab/reports/ASTOCK_A1_A10_CONSOLIDATED_REPORT.md`：本整理报告。
