# 问财选A股说法典交接笔记

日期：2026-05-07
范围：只适用于 `F:\v.6\v6-op`。`F:\v.6\v6` 和 V5/V5.10 只允许作为参考，不是本次正式修改对象。

## 1. 当前结论

本轮“问财选A股”测试已经收口，可以作为 V6-OP 后续 P1-P6、输入工坊、策略台 Query 矩阵的第一版依据。

本轮完成的核心事情：

- 建立了 `query_lab` 实验体系，用 CSV 用例驱动问财实测。
- 完成 A1-A15 和 A12R 代码池修复测试。
- 完成 A_return_contract（A16）返回契约补确认：问财不只返回代码，还附带股票简称、最新价、条件相关字段。
- 形成稳定表达、风险表达、禁问表达和自然语言改写规则。
- 明确了代码池复问不能交给问财，必须由 V6-OP 应用层做交集。
- 明确了以后新增问法必须先进入待测表，再跑测，再候选，再人工确认，不能直接写进正式法典。

当前最重要的两句话：

```text
问财选A股负责生成候选股票池；已有股票池、手动代码池、上一步结果池，只能在 V6-OP 应用层做 intersection，不能让问财二次按代码池复问。

问财选A股返回内容不止股票代码：每次都附带股票简称、最新价、条件触发字段；pipeline 应直接提取，无需额外 quote API 调用。
```

---

## 1.5 返回契约补确认结论（2026-05-07）

**AR-001 至 AR-008 全部返回 `stock_with_quote`（8/8）。**

| 字段 | 出现规律 |
|------|---------|
| `股票代码` | 必返回 |
| `股票简称` | 必返回（中文名称始终存在） |
| `最新价` | 必返回 |
| `今日涨跌幅` | 必返回（视 query 写法为 `今日涨跌幅` 或 `涨跌幅:前复权[date]`） |
| 成交额、换手率、量比、主力净流入、市值 | 条件触发（query 包含该字段时出现） |
| OHLC 四价（前复权） | 条件触发（含涨幅或多条件时出现） |
| 行业字段（同花顺行业、所属行业） | 条件触发（含板块名时出现） |

完整报告：`query_lab/reports/astock_return_contract_report.md`

## 2. 数据入口边界

当前 QueryLab 的问财选A股实测，实际走的是：

```text
pywencai -> www.iwencai.com 网页接口
```

不是官方截图里的：

```text
openapi.iwencai.com SkillHub / OpenAPI
```

这不是本文件要修的内容，但必须明确记录。数据源入口治理另见：

```text
F:\v.6\v6-op\docs\02_data_source_entry_governance.md
```

后续如果把问财入口改成官方 OpenAPI，需要重新做一轮入口验证，不要默认沿用本轮网页接口的所有耗时和返回特征。

## 3. 文件地图

### 3.1 先看这些正式报告

```text
F:\v.6\v6-op\query_lab\reports\ASTOCK_QUERY_CANON_HANDOFF.md
F:\v.6\v6-op\query_lab\reports\astock_ceiling_report.md
F:\v.6\v6-op\query_lab\reports\stable_dictionary.md
F:\v.6\v6-op\query_lab\reports\risk_dictionary.md
F:\v.6\v6-op\query_lab\reports\forbidden_dictionary.md
F:\v.6\v6-op\query_lab\reports\query_normalizer_rules.md
```

其中本文件是交接入口。其他 5 个文件是机器生成或半自动整理后的当前法典材料。

### 3.2 A1-A10 旧整理报告

```text
F:\v.6\v6-op\query_lab\reports\ASTOCK_A1_A10_CONSOLIDATED_REPORT.md
F:\v.6\v6-op\query_lab\reports\astock_a1_a10_clean_dictionary.csv
F:\v.6\v6-op\query_lab\reports\astock_a1_a10_clean_dictionary.json
```

注意：这些只覆盖 A1-A10。A11-A15 和 A12R 以后，以 `astock_ceiling_report.md` 及本交接笔记为准。

### 3.3 测试用例位置

```text
F:\v.6\v6-op\query_lab\cases\astock_问财选A股\
```

当前用例：

```text
A1_basic.csv
A2_synonym.csv
A3_combo.csv
A4_risky.csv
A5_forbidden.csv
A6_time_window.csv
A7_numeric_relative.csv
A8_capital_flow.csv
A9_technical_shape.csv
A10_complex_boundary.csv
A11_relative_amount_scoped.csv
A12_code_pool_requery.csv
A12R_code_pool_repair.csv
A13_limitup_pullback.csv
A14_ma_pullback_boundary.csv
A15_practical_combo_ceiling.csv
```

### 3.4 关键运行结果

```text
F:\v.6\v6-op\query_lab\results\runs\
```

已纳入本轮结论的 run：

| 组别 | run_id | 用途 |
|---|---|---|
| A1 | `run_20260507_150529` | 基础字段 |
| A2 | `run_20260507_150925` | 同义表达 |
| A3 | `run_20260507_151853` | 条件叠加 |
| A4 | `run_20260507_152032` | 高风险表达 |
| A5 | `run_20260507_152351` | 禁问和非法表达 |
| A6 | `run_20260507_154006` | 时间窗口 |
| A7 | `run_20260507_154212` | 数值边界和相对比较 |
| A8 | `run_20260507_154454` | 资金字段 |
| A9 | `run_20260507_154831` | 技术形态 |
| A10 | `run_20260507_155054` | 复杂边界 |
| A11 | `run_20260507_163158` | 相对成交额缩圈 |
| A12 | `run_20260507_163617` | 原始代码池复问 |
| A13 | `run_20260507_163810` | 涨停后回撤 |
| A14 | `run_20260507_163932` | 均线和回撤边界 |
| A15 | `run_20260507_164051` | 实战组合和分隔符 |
| A12R | `run_20260507_173035` | 代码池复问修复确认 |

早期卡住、中断、调试 run 不作为正式证据。尤其不要把 `running=False` 不明确、没有 `RUN_COMPLETE` 或无完整 `analyzed_results.jsonl` 的目录拿来升级法典。

### 3.5 A12R 代码池复问证据

```text
F:\v.6\v6-op\query_lab\results\code_pool_repair\find_test_report.md
F:\v.6\v6-op\query_lab\results\code_pool_repair\find_test_results.jsonl
F:\v.6\v6-op\query_lab\results\runs\run_20260507_173035\
```

这是后续改 pipeline 时必须看的证据。

## 4. A1-A15 各组含义

| 组别 | 中文定位 | 目的 |
|---|---|---|
| A1_basic | 地板测试，最短稳定路径 | 验证最基础字段能不能问 |
| A2_synonym | 同义表达测试 | 验证“超过、高于、以上”等是否可识别 |
| A3_combo | 条件叠加阶梯 | 验证 1 到多条件组合能力 |
| A4_risky | 高风险表达 | 找出模糊、非标准、容易误判的说法 |
| A5_forbidden | 禁问测试 | 确定英文、空句、预测性语句不进入系统 |
| A6_time_window | 时间窗口 | 近3日、近5日、近20日、最近一个月 |
| A7_numeric_relative | 数值边界和相对比较 | 大于、小于、之间、倍数、平均值 |
| A8_capital_flow | 资金字段 | 主力、大单、超大单、资金净流入 |
| A9_technical_shape | 技术字段 | 均线、MACD、KDJ、K线形态 |
| A10_complex_boundary | 复杂边界 | 冲突条件、模糊词、边界组合 |
| A11_relative_amount_scoped | 相对成交额缩圈 | 解决“今日成交额 > 近5日均值 1.5 倍”全市场过重问题 |
| A12_code_pool_requery | 原始代码池复问 | 验证把代码塞进中文 Query 是否可行 |
| A12R_code_pool_repair | 代码池复问修复确认 | 验证中文写法和 pywencai find 是否可行 |
| A13_limitup_pullback | 涨停后回撤 | 近10日涨停、回撤、缩量 |
| A14_ma_pullback_boundary | 均线和回撤边界 | 跌幅、回撤、没有跌破均线 |
| A15_practical_combo_ceiling | 实战组合和分隔符 | 组合条件上限、分隔符、实用策略句 |

## 5. 当前可用规则

### 5.1 标准字段优先

默认生成 Query 时，优先使用这些稳定字段：

```text
非ST
非停牌
上市超过60天
今日涨幅
近3日涨幅
近5日涨幅
近20日涨幅
今日成交额
今日换手率
今日量比
流通市值
总市值
今日主力净流入
今日大单净流入
今日超大单净流入
今日收盘价大于5日均线
今日收盘价大于10日均线
今日收盘价大于20日均线
MACD金叉
KDJ金叉
近10日有涨停
```

### 5.2 标准操作符

矩阵生成、P1-P6、输入工坊推荐时，优先使用：

```text
大于
小于
在...到...之间
为正
非ST
非停牌
上市超过N天
今日收盘价大于N日均线
```

同义词如 `超过`、`高于`、`以上` 可识别，但不作为默认生成格式。默认格式要稳，不要耍花样。

### 5.3 条件叠加

测试中 4 到 8 个条件可以返回，但生产生成不要盲目堆满。

建议：

```text
普通自动生成：2 到 4 个条件
高级人工模板：最多 5 到 6 个条件
超过 6 个条件：建议拆成两段，或先问财缩圈，再应用层/本地技能过滤
```

推荐分隔符：

```text
中文逗号：，
```

其他分隔符如空格、英文逗号、顿号、斜杠在测试中有识别能力，但默认不要用它们做矩阵生成。

## 6. 关键专项结论

### 6.1 相对成交额

以下表达可用：

```text
今日成交额大于近5日平均成交额1.5倍
```

但最好缩圈使用：

```text
创业板，今日成交额大于近5日平均成交额1.5倍
科创板，今日成交额大于近5日平均成交额1.5倍
军工板块，今日成交额大于近5日平均成交额1.5倍
非ST，今日成交额大于近5日平均成交额1.5倍
流通市值在30亿到150亿之间，今日成交额大于近5日平均成交额1.5倍
```

测试器运行这类 Query 时，必须限制抓取量：

```text
FetchLimit=100
QueryTimeoutSec=45 或 60
```

不要让一条 Query 无限翻页，否则容易耗尽 session 或卡死。

### 6.2 涨停后回撤

稳定或可用表达：

```text
近10日有涨停
近10日有涨停，近3日股价回撤大于3%
近10日有涨停，近3日股价回撤大于5%
近10日有涨停，今日收盘价没有跌破5日均线
近10日有涨停，今日收盘价没有跌破10日均线
```

生产矩阵更推荐标准化成：

```text
近10日有涨停，近3日跌幅大于3%，今日收盘价大于5日均线
```

`回撤` 可识别但解释不够透明，`跌幅` 更适合自动生成。

### 6.3 技术指标

可用：

```text
MACD金叉
KDJ金叉
今日收盘价大于5日均线
今日收盘价大于10日均线
今日收盘价大于20日均线
```

谨慎：

```text
均线多头排列
今日K线为锤子线
今日K线为阳包阴
收盘价站上JMA均线
```

本轮 A12R 中，`军工板块，今日成交额大于近5日平均成交额1.5倍，MACD金叉` 和类似 KDJ/零轴组合返回空。结论不是 MACD/KDJ 不能问，而是“板块缩圈 + 相对成交额 + 技术指标”组合不应一次性强塞，建议拆问或应用层过滤。

### 6.4 禁止和弱表达

不得自动进入 P1-P6：

```text
强势股
放量上涨股票
短线龙头股
明天可能上涨的股票
有可能涨停的股票
低位放量突破
图形走得很好
英文整句 Query
空 Query
```

这些可以进入反例库，不能作为自动生成模板。

## 7. A12 代码池复问最终结论

本轮专门做了 A12 和 A12R。结论非常明确：

```text
中文 Query 代码池复问：不可行
pywencai find 参数代码池复问：不可用
V6-OP 应用层 intersection：必须采用
```

失败例：

```text
股票代码为000060或603399，今日成交额大于近5日平均成交额1.5倍
证券代码为000060或603399，今日成交额大于近5日平均成交额1.5倍
000060或603399，今日成交额大于近5日平均成交额1.5倍
股票简称为中金岭南或抚顺特钢，今日成交额大于近5日平均成交额1.5倍
```

`pywencai.get(..., find=codes)` 虽然能返回数据，但测试发现返回结果不受代码池约束，会返回池外股票，因此不能用于生产代码池过滤。

生产规则：

```text
问财 Query -> 候选集合 A
已有股票池 / 手动代码 / Phase A 或前序结果 -> 集合 B
V6-OP 应用层执行 A ∩ B
后续 K线技能只处理交集后的股票
```

这条规则以后不要再争论，除非换成官方 OpenAPI 后重新实测证明支持代码池参数。

## 8. 测试执行纪律

### 8.1 不要裸跑长任务

不要直接裸跑 Python 做大批量问财实测。必须用 guard：

```text
F:\v.6\v6-op\query_lab\scripts\query_lab_guard.ps1
```

推荐参数：

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 `
  -Action start -Route astock -Group A1_basic -Limit 20 `
  -SleepMs 3000 -FetchLimit 100 -QueryTimeoutSec 45
```

含义：

- `Limit`：跑多少条 CSV 用例。
- `FetchLimit`：每条 Query 最多抓多少只股票，避免无限翻页。
- `QueryTimeoutSec`：单条 Query 超时后记录失败并继续下一条。

### 8.2 为什么必须有 FetchLimit

问财默认可能每页 100 只股票，一条宽条件 Query 会翻十几页甚至几十页。

例如：

```text
流通市值在30亿到150亿之间
```

这类条件可能返回上千只股票。如果不限制抓取量，就会不断翻页，导致：

- 耗时极长。
- session 耗尽。
- pywencai 阻塞。
- 后续 Query 被拖死。
- 误以为语法有问题。

所以测试法典时，目标不是拿全市场完整名单，而是判断“这句能不能被问财稳定识别”。默认 `FetchLimit=100` 足够。

### 8.3 失败不要立刻进法典

以下情况不能自动 promote：

- `api_error`
- `timeout`
- `empty_result`
- `RUN_COMPLETE` 缺失
- `analyzed_results.jsonl` 不完整
- `find` 返回池外股票
- 语义被吞，返回内容和预期不一致

测试器只能写候选，正式法典必须人工确认。

## 9. 后续怎么新增和修改

### 9.1 新增一个问法

先写到对应 CSV：

```text
F:\v.6\v6-op\query_lab\cases\astock_问财选A股\Axx_xxx.csv
```

字段风格参考已有 A1-A15，不要另起一套格式。

然后用 guard 小批量跑：

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 `
  -Action start -Route astock -Group Axx_xxx -Limit 3 `
  -SleepMs 3000 -FetchLimit 100 -QueryTimeoutSec 45
```

小批量稳定后再全组跑。不要一上来跑大批量。

### 9.2 修改已有问法

修改顺序：

1. 先看本文件。
2. 再看 `astock_ceiling_report.md`。
3. 再看对应组 CSV。
4. 再看对应 run 的 `run_summary.md` 和 `analyzed_results.jsonl`。
5. 如果是代码池问题，先看 A12R 报告。
6. 修改 CSV 或 runner。
7. 用 guard 小批量复测。
8. 生成候选变更。
9. 人工确认后再 promote。

### 9.3 不要直接改生产 UI

输入工坊、P1-P6、策略台矩阵后续要引用法典，但不要在法典没验收时直接把一条新说法写进 UI 默认项。

正确链路：

```text
用户新说法
-> pending / CSV
-> QueryLab 实测
-> stable / risky / forbidden
-> 候选变更
-> 人工确认
-> 输入工坊 / P1-P6 / 策略台引用
```

## 10. 后续生产设计建议

### 10.1 P1-P6 不应再只是文本框

后续输入工坊应改成“字段矩阵”：

```text
字段：涨幅 / 成交额 / 换手率 / 量比 / 流通市值 / 主力净流入 / 均线 / MACD / KDJ
关系：大于 / 小于 / 在...之间 / 为正
数值：用户填写
时间：今日 / 近3日 / 近5日 / 近10日 / 近20日
风险级别：strong / weak / forbidden
```

系统生成标准 Query，而不是让用户每次手打长句。

### 10.2 自然语言转换应让 AI 看法典

程序本身没有真正理解自然语言的能力。后续如果用户输入一句口语，推荐流程是：

```text
用户口语
-> AI 读取法典和风险规则
-> AI 改写成标准 Query
-> 系统展示可编辑预览
-> 用户确认
-> 保存为模板或直接运行
```

当前 `query_normalizer_rules.md` 只有少量规则，不能当成熟自然语言系统使用。

## 11. 当前遗留事项

本轮“问财选A股”收口，但还有这些后续事项：

- 数据源入口治理：把 `pywencai/www.iwencai.com` 与官方 `openapi.iwencai.com` 对齐。
- 问财选板块：需要单独做 sector/zhishu 法典。
- 正式 canon 发布：当前报告和字典是候选基础，promote 仍需人工确认。
- 输入工坊矩阵：后续要基于 strong/weak/forbidden 做 UI。
- 应用层 intersection：需要接入策略台 pipeline，解决代码池复问不可行的问题。

## 12. 一句话交接

如果后来者只读一段，就读这一段：

```text
问财选A股已经完成 A1-A15 + A12R 实测。稳定表达看 stable_dictionary.md，风险表达看 risk_dictionary.md，禁问看 forbidden_dictionary.md。代码池复问已经确认不可交给问财，中文 Query 和 pywencai find 都不可靠，V6-OP 必须在应用层做 intersection。以后新增说法先写 cases，再用 query_lab_guard.ps1 小批量跑，FetchLimit 默认 100，QueryTimeoutSec 默认 45，测试器只生成候选，人工确认后才能进入正式法典。
```
