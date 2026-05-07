# Claude 工单：问财选板块地板/天花板与返回契约实测

只在 `F:\v.6\v6-op` 内工作。不要修改 `F:\v.6\v6`、V5、V5.10。

本任务是 V6-OP 的重要事项：摸清 `问财选板块` 的中文问法边界、返回内容类型、以及后续 pipeline 应该怎么接。不要把它当成普通搜索框测试。

## 一句话目标

建立 `问财选板块` 的“文财学 / 说法典 / 返回契约”初版：知道怎么问、不能怎么问、返回的到底是板块还是股票还是文本，以及返回后应该接到哪里。

## 绝对边界

这次只做 `sector / 问财选板块`。

不要跑：

- `astock / 问财选A股` 的新一轮全量测试
- `daily_kline`
- `quote`
- 官方 OpenAPI 数据源治理
- `canon promote`

可以参考 A 股法典，但不要生硬套板。板块和 A 股是两种对象。

## 最重要的新要求：返回内容分类

`问财选板块` 和 `问财选A股` 的返回不一样。每条 Query 都必须记录返回对象类型，不允许只写 success/failed。

请在 analyzer / report 中明确记录：

```text
return_object_type:
  sector_only          只返回板块、行业、概念、指数简称等板块对象
  stock_only           返回 A 股股票代码/简称为主
  mixed_sector_stock   同时返回板块和股票
  text_explanation     主要是文本说明、理由、摘要
  table_unknown        有表格但对象类型不清
  empty_or_error       空、None、异常、无法解析
```

每条结果还要记录：

```text
actual_query_backend   sector / zhishu / fallback / unknown
raw_columns            原始列名摘要
extracted_sector_names 提取出的板块名样例
extracted_stock_codes  提取出的股票代码样例
extracted_stock_names  提取出的股票简称样例
result_count           返回数量
latency_ms             耗时
next_pipeline_route    下一步建议接法
```

### next_pipeline_route 规则

```text
sector_only:
  可以接入 Phase B / 问财选A股。
  例：sector 返回“军工板块”，后续可生成“军工板块，今日收盘价站上5日均线的股票”。

stock_only:
  不要再送回问财选A股做代码池复问。
  A12 已确认：问财选A股不支持稳定代码池复问。
  应该直接进入本地技能，如 kline / smc / wave / landmine。

mixed_sector_stock:
  拆开记录。板块部分可进入 Phase B，股票部分可进入本地技能。
  标记为 review，不要直接自动跑完整 pipeline。

text_explanation:
  只能作为解释或人工参考，不可直接进入 pipeline。

table_unknown:
  先修 extractor 或人工确认列含义。

empty_or_error:
  failed，记录原因。
```

这块是本次验收核心。最终报告必须回答：

1. 问财选板块返回的主对象是什么？
2. 哪些问法返回板块？
3. 哪些问法会跳到股票？
4. 哪些问法只返回文本/理由？
5. sector 返回板块后，怎么接 Phase B？
6. sector 返回股票后，为什么不能再接问财选A股？

## 文财学分层：从地板到天花板

请把 `C:\Users\devic\Downloads\问财选板块_文财学_由浅入深提问体系V1.md` 作为参考素材，但不要机械全量照抄。当前阶段要快、稳、可验收。

### 第一批必须跑：S1-S4

现有用例目录：

```text
F:\v.6\v6-op\query_lab\cases\sector_问财选板块\
```

已有分组：

```text
S1_basic.csv      地板测试，最短稳定路径
S2_synonym.csv    同义表达测试
S3_combo.csv      组合阶梯，摸复杂度天花板
S4_risky.csv      模糊词、预测词、禁问测试
```

含义：

| 组别 | 要测什么 |
|---|---|
| S1 | 板块基础字段：今日涨幅、成交额、主力净流入、近5日涨幅、近20日涨幅、换手率、量比 |
| S2 | 同义词：今日/今天、板块前置、超过/大于、主力资金/主力净流入、流入最多 |
| S3 | 条件叠加：1 条到 5 条组合，判断板块 Query 的组合天花板 |
| S4 | 风险/禁问：热门板块、强势板块、主线板块、可能爆发的板块 |

### 第二批只做抽样扩展：S5-S8

如果 S1-S4 跑通，再从文财学文件中补 4 个抽样 CSV。不要一口气把 L1-L12 全量铺满。

```text
S5_emotion_style.csv     情绪/涨停/上涨家数/游资风格抽样
S6_two_step.csv          必须拆成 sector -> astock 的问题
S7_low_reversal.csv      低位/回流/预期差结构化问法
S8_return_contract.csv   专门测返回对象类型
```

每组先 6-10 条即可。重点是边界，不是数量。

建议样例：

S5：

- 今日上涨家数排名前10的板块
- 今日涨停家数排名前10的板块
- 涨停家数大于3的板块
- 今日换手率排名前10且涨停家数排名前10的板块
- 今日龙虎榜上榜股票最多的板块
- 连板股最多的板块

S6：

- 人工智能板块龙头股
- 今日涨幅最大的板块中的龙头股
- 今日主力净流入最多的板块中的龙头股
- 人工智能板块中今日涨幅排名前10的股票
- 人工智能板块中今日成交额排名前10的股票
- 人工智能板块中今日主力净流入排名前10的股票

S7：

- 近60日涨幅小于20%，今日涨幅大于3%的板块
- 近60日涨幅小于20%，今日主力净流入排名前10的板块
- 近20日涨幅小于5%，今日成交额排名前10的板块
- 近5日主力净流入小于0，今日主力净流入大于0的板块
- 近5日涨幅小于5%，今日成交额排名前10，今日涨幅大于3%的板块

S8：

- 今日涨幅排名前10的板块
- 今日成交额排名前10的板块
- 今日涨停家数排名前10的板块
- 今日最强板块
- 军工板块龙头股
- 军工板块中今日涨幅排名前10的股票
- 今日主力净流入最多的板块有哪些，原因是什么
- 哪些板块值得关注

S8 的目的不是找稳定问法，而是确认返回对象：板块、股票、混合、文本。

## 文财学核心规则

板块问财的成熟流程不是“一句话找牛股”，而是：

```text
板块扫描
-> 板块分层
-> 板块交叉验证
-> 板块内个股拆解
-> 个股再进入 A 股筛选/本地技能
```

稳定方向优先：

- 当前最热方向：涨幅、成交额、主力净流入、涨停家数
- 资金主线：今日/近5日主力净流入、持续流入
- 情绪主线：涨停家数、上涨家数、换手率
- 趋势主线：近20日/近60日涨幅
- 低位回流：近60日涨幅小于阈值 + 今日涨幅/资金流入

高风险自然语言：

- 热门板块
- 强势板块
- 主线板块
- 可能爆发的板块
- 捡漏板块
- 低位启动板块
- 未来爆发板块
- 游资关注板块
- 机构抱团板块

这些可以测试，但不要作为标准生成格式。

## 必须拆成两步的问题

以下问题不能强行要求 sector 一步完成：

1. 某板块里的龙头股
2. 游资最活跃板块里的股票
3. 今日最强板块里的前排股
4. 涨停最多板块里的连板股
5. 某板块中资金流入最多的股票

推荐流程：

```text
第一步 sector:
  今日涨停家数最多的板块

第二步 astock:
  某板块中今日涨停的股票
  某板块中今日成交额排名前10的股票
  某板块中今日主力净流入排名前10的股票
```

但注意：如果 sector 已经返回 stock_only，不要再送回 astock 做代码池复问；直接走本地技能。

## 运行纪律：不要再卡死

不要裸跑长任务，必须用 guard。

先检查状态：

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action status
```

如果有旧进程，先停掉：

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action stop
```

推荐参数：

```text
SleepMs=3000
FetchLimit=20
QueryTimeoutSec=45
```

板块测试不是拉全市场股票，不要无限翻页。目标是语义、字段、对象类型，不是抓全量。

如果某条 Query 超过 45 秒或返回 None：

- 记录为 timeout/api_error/empty_result。
- 继续下一条。
- 不要反复重跑同一条。
- 不要把输出 pipe 到 `Select-Object -First N` 这类可能堵 stdout 的命令。
- 后台运行必须输出到文件，且每条写 `current_query.json`。

## 执行步骤

### Step 0：先确认返回契约能力

如果现有 analyzer 还不能记录 `return_object_type / extracted_sector_names / extracted_stock_codes / extracted_stock_names / next_pipeline_route`，先最小修复。

优先修：

```text
query_lab/scripts/adapters/wencai_sector_adapter.py
query_lab/scripts/query_runner.py
query_lab/scripts/diagnose_sector.py
```

不要改 A 股逻辑。

### Step 1：S1 前 3 条小测

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 `
  -Action start -Route sector -Group S1_basic -Limit 3 `
  -SleepMs 3000 -FetchLimit 20 -QueryTimeoutSec 45
```

检查：

- `RUN_COMPLETE`
- `query_results.jsonl`
- `analyzed_results.jsonl`
- 返回对象是否为板块
- `actual_query_backend` 是 `sector` 还是 `zhishu`
- 是否能提取板块名样例

Step 1 不通过，不要继续。

### Step 2：跑 S1-S4

逐组跑，不要并发：

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 `
  -Action start -Route sector -Group S1_basic -Limit 0 `
  -SleepMs 3000 -FetchLimit 20 -QueryTimeoutSec 45
```

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 `
  -Action start -Route sector -Group S2_synonym -Limit 0 `
  -SleepMs 3000 -FetchLimit 20 -QueryTimeoutSec 45
```

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 `
  -Action start -Route sector -Group S3_combo -Limit 0 `
  -SleepMs 3000 -FetchLimit 20 -QueryTimeoutSec 45
```

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 `
  -Action start -Route sector -Group S4_risky -Limit 0 `
  -SleepMs 3000 -FetchLimit 20 -QueryTimeoutSec 45
```

### Step 3：补 S5-S8 抽样扩展

只有 S1-S4 通过后才创建并跑 S5-S8。每组 6-10 条，不要贪多。

如果发现 S5-S8 中某类明显不适合 sector，一定要写 `should_split=true`，并给出推荐拆法。

## 报告文件

完成后生成或更新：

```text
query_lab/reports/sector_ceiling_report.md
query_lab/reports/sector_return_contract_report.md
query_lab/reports/sector_stable_dictionary.md
query_lab/reports/sector_risk_dictionary.md
query_lab/reports/sector_forbidden_dictionary.md
query_lab/reports/SECTOR_QUERY_CANON_HANDOFF.md
```

`SECTOR_QUERY_CANON_HANDOFF.md` 必须写清楚：

1. 实测日期和纳入 run_id。
2. S1-S4 每组结论，若跑了 S5-S8，也写入。
3. 最短稳定问法。
4. stable / risky / forbidden 清单摘要。
5. `sector` 与 `zhishu` backend 的实际表现。
6. 返回内容分类统计：sector_only / stock_only / mixed_sector_stock / text_explanation / table_unknown / empty_or_error。
7. 每种返回类型的下一步 pipeline 接法。
8. 推荐给策略台 / 输入工坊的标准板块 Query 生成格式。
9. 不建议自动生成的板块说法。
10. 后续新增板块问法应该修改哪个 CSV、用什么命令跑、先看哪个报告。

## 验收标准

本任务完成必须满足：

- S1-S4 都有完整 run，或者明确记录为什么某组不能完成。
- Step 0 的返回契约字段已经能落盘。
- 每条结果有耗时、返回数量、backend、板块名样例、股票代码样例、返回对象类型。
- 明确区分“返回板块”和“返回股票”。
- 明确写出：sector_only 接 Phase B，stock_only 接本地技能，mixed 需要拆分审阅。
- 不把 A 股字段误判成板块字段。
- 不自动 promote。
- 最终报告能让用户直接知道：以后板块扫描提示词该怎么写、哪些不要写、返回后接哪里。

完成后请给出简明报告：

```text
1. 修改了哪些文件
2. S1-S4/S5-S8 对应 run_id
3. 地板问法
4. 天花板结论
5. 返回内容分类结论
6. sector -> astock / local skill 的 pipeline 接法
7. 禁问/风险表达
8. 是否需要下一轮补测
```
