# Claude 执行单：问财选 A 股第三批 A11-A15 深测

## 0. 边界

只操作正式项目：

```powershell
F:\v.6\v6-op
```

只做 `astock / 问财选A股`。不要改 V5/V6 参考目录。不要改 A1-A10 的既有语义，只能新增 A11-A15 用例、运行、分析、报告。

这批不是“用户口语改写测试”，不要写成闲聊句。所有 `query_text` 必须是中文金融语义，目标是摸清问财 A 股查询在以下几类复杂条件下的地板、天花板、禁问边界。

## 1. 总目标

这批只围绕五个问题：

```text
A11_relative_amount_scoped      相对成交额 + 缩圈查询
A12_code_pool_requery           指定股票代码池复问
A13_limitup_pullback            涨停后回撤 / 缩量 / 均线约束
A14_ma_pullback_boundary        回撤幅度与均线未跌破边界
A15_practical_combo_ceiling     实战组合天花板 / 关键词叠加与分隔符
```

核心问题来自这句：

```text
今日成交额大于近5日平均成交额1.5倍
```

不要一上来全市场无限翻页。默认用：

```text
FetchLimit=100
QueryTimeoutSec=45
SleepMs=3000
```

如果某条明显慢或超时，不要死等，不要无限翻页。记录为 `timeout / risky / rewrite_required`，继续下一条。

## 2. 必须先确认运行安全

每次运行前先检查：

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action status
```

运行必须走 guard，不要裸跑 Python：

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action start -Route astock -Group <GROUP_NAME> -Limit 0 -SleepMs 3000 -FetchLimit 100 -QueryTimeoutSec 45
```

如果某组超过 10 分钟没有文件增长，先诊断原因，再决定是否停止。必须保留已完成且合规的单条结果，不能因为一条卡住导致整组有效结果丢失。

## 3. 新增 CSV

在现有目录新增：

```text
F:\v.6\v6-op\query_lab\cases\astock_问财选A股\A11_relative_amount_scoped.csv
F:\v.6\v6-op\query_lab\cases\astock_问财选A股\A12_code_pool_requery.csv
F:\v.6\v6-op\query_lab\cases\astock_问财选A股\A13_limitup_pullback.csv
F:\v.6\v6-op\query_lab\cases\astock_问财选A股\A14_ma_pullback_boundary.csv
F:\v.6\v6-op\query_lab\cases\astock_问财选A股\A15_practical_combo_ceiling.csv
```

CSV 表头沿用 A1-A10，不要另起 schema。CSV 必须使用 UTF-8 with BOM，方便 Excel 打开中文不乱码。

## 4. A11：相对成交额 + 缩圈查询

目的：确认“今日成交额大于近5日平均成交额1.5倍”是否能被问财稳定识别；同时确认缩小范围后是否明显更快、更稳定。

至少 8 条，必须包含：

```text
创业板，今日成交额大于近5日平均成交额1.5倍
科创板，今日成交额大于近5日平均成交额1.5倍
军工板块，今日成交额大于近5日平均成交额1.5倍
半导体板块，今日成交额大于近5日平均成交额1.5倍
非ST，今日成交额大于近5日平均成交额1.5倍
流通市值在30亿到150亿之间，今日成交额大于近5日平均成交额1.5倍
今日成交额大于近5日平均成交额1.5倍，今日收盘价站上5日均线
今日成交额大于近5日平均成交额1.5倍，近3日涨幅小于10%
```

判定重点：

- 能不能返回 A 股代码。
- 延迟是否明显超过普通字段。
- 是否因为全量过大导致 timeout。
- “近5日平均成交额”是否被稳定识别。
- 缩圈条件是否能显著改善稳定性。

## 5. A12：指定股票代码池复问

目的：验证“先由问财返回一批股票，再拿股票代码池复问局部条件”是否可行。这是后续 pipeline 很关键的一环。

运行方式必须分两步：

1. 从 A11 成功结果里取 2 个明确满足条件的股票代码。
2. 再混入 8 个无关 A 股代码，组成约 10 个代码的代码池。

然后构造至少 6 条查询。不要硬编码未知代码，必须从 A11 的实测结果中抽样生成。

示例问法：

```text
在以下股票代码中，哪些今日成交额大于近5日平均成交额1.5倍：<代码列表>
在以下股票代码中，哪些今日成交额大于近5日平均成交额1.5倍，且今日收盘价站上5日均线：<代码列表>
在以下股票代码中，哪些近3日股价回撤大于3%：<代码列表>
在以下股票代码中，哪些近10日有涨停：<代码列表>
在以下股票代码中，哪些近3日缩量：<代码列表>
在以下股票代码中，哪些没有跌破10日均线：<代码列表>
```

判定重点：

- 问财是否尊重“以下股票代码中”的范围。
- 是否能正确返回 A11 中已知命中的 2 个代码。
- 是否会越界返回不在代码池中的股票。
- 如果不能精确返回，是否需要改写成“股票代码为 ... 且 ...”。

## 6. A13：涨停后回撤 / 缩量

目的：测试“过去 10 天有涨停”与后续回撤、缩量条件能否组合。

至少 8 条：

```text
近10日有涨停
近10日有涨停，近3日股价回撤大于3%
近10日有涨停，近3日股价回撤大于5%
近10日有涨停，近3日缩量
近10日有涨停，近3日成交量逐日缩小
近10日有涨停，近3日股价回撤大于3%，近3日缩量
近10日有涨停，今日收盘价没有跌破5日均线
近10日有涨停，今日收盘价没有跌破10日均线
```

判定重点：

- “近10日有涨停”能不能稳定返回。
- “回撤大于3% / 5%”是否能被识别，还是需要改写成“近3日跌幅大于3%”。
- “缩量 / 成交量逐日缩小”是否为标准字段。
- “没有跌破均线”是否稳定。

## 7. A14：回撤幅度与均线未跌破边界

目的：把“回撤”和“均线不破”的表达拆开测，找出可用标准语。

至少 8 条：

```text
近3日跌幅大于3%
近3日跌幅大于5%
近3日股价回撤大于3%
近3日股价回撤大于5%
今日收盘价大于5日均线
今日收盘价大于10日均线
今日收盘价没有跌破5日均线
今日收盘价没有跌破10日均线
```

判定重点：

- “跌幅”与“回撤”哪个更标准。
- “大于均线”与“没有跌破均线”哪个更标准。
- 如果“没有跌破”可用，是否作为弱引用；如果不稳定，则推荐统一改写为“收盘价大于 N 日均线”。

## 8. A15：实战组合天花板 / 关键词叠加与分隔符

目的：用实战组合测试问财 A 股单句查询的复杂度上限。这里不是为了追求全稳定，而是为了知道复杂句什么时候该拆。

本组还必须补测两个关键问题：

1. 基础关键词最多能稳定叠加几个：4、5、6、7、8 个条件分别是否还能返回，延迟是否明显变长，是否开始 timeout / 空结果 / 误解析。
2. 关键词之间用什么分隔最稳：中文逗号 `，`、顿号 `、`、空格、英文逗号 `,`、斜杠 `/` 是否都能被问财识别；最终要推荐一个标准分隔符。

至少 8 条：

```text
创业板，今日成交额大于近5日平均成交额1.5倍，今日收盘价站上5日均线
军工板块，近10日有涨停，近3日股价回撤大于3%
半导体板块，近10日有涨停，近3日缩量，今日收盘价大于10日均线
非ST，流通市值在30亿到150亿之间，今日成交额大于近5日平均成交额1.5倍
近10日有涨停，近3日股价回撤大于3%，今日收盘价大于5日均线
近10日有涨停，近3日成交量逐日缩小，今日收盘价大于10日均线
今日成交额大于近5日平均成交额1.5倍，近3日涨幅小于10%，今日收盘价大于5日均线
创业板，近10日有涨停，近3日股价回撤大于5%，今日收盘价没有跌破10日均线
```

另增“基础关键词叠加上限”至少 5 条，必须从短到长递增：

```text
非ST，上市超过60天，今日涨幅大于3%，今日成交额大于3亿
非ST，上市超过60天，今日涨幅大于3%，今日成交额大于3亿，今日换手率大于5%
非ST，上市超过60天，今日涨幅大于3%，今日成交额大于3亿，今日换手率大于5%，流通市值在30亿到150亿之间
非ST，上市超过60天，今日涨幅大于3%，今日成交额大于3亿，今日换手率大于5%，流通市值在30亿到150亿之间，今日收盘价大于5日均线
非ST，上市超过60天，今日涨幅大于3%，今日成交额大于3亿，今日换手率大于5%，流通市值在30亿到150亿之间，今日收盘价大于5日均线，今日主力净流入为正
```

另增“分隔符稳定性”至少 5 条，语义保持一致，只改变分隔符：

```text
非ST，上市超过60天，今日涨幅大于3%，今日成交额大于3亿
非ST、上市超过60天、今日涨幅大于3%、今日成交额大于3亿
非ST 上市超过60天 今日涨幅大于3% 今日成交额大于3亿
非ST,上市超过60天,今日涨幅大于3%,今日成交额大于3亿
非ST/上市超过60天/今日涨幅大于3%/今日成交额大于3亿
```

判定重点：

- 2 条件、3 条件、4 条件分别是否稳定。
- 4、5、6、7、8 个基础条件是否还能稳定返回。
- 条件变多后，是返回变少、延迟变长，还是直接误解析/超时。
- 中文逗号、顿号、空格、英文逗号、斜杠哪个最稳定。
- 最终推荐给矩阵生成器的标准分隔符是什么。
- “板块/市场范围 + 相对成交额 + 均线”是否可用。
- “涨停 + 回撤 + 缩量 + 均线”是否需要拆成两段。
- 推荐最终标准：单句最多容纳几类条件。

## 9. 分析规则

每条必须记录：

```text
query_id
query_text
result_count
elapsed_ms
analysis_status
risk_level
recommended_usage
rewrite_suggestion
failure_reason
```

特别要分清：

```text
stable      可以强引用，适合后续矩阵生成
weak        可识别但不建议默认生成
risky       可偶发返回，但不稳定
forbidden   语义不该问或问财不支持
timeout     因接口/翻页/会话导致超时，不能直接判语义错
review      需要人工复核
```

## 10. 跑法

按顺序跑：

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action start -Route astock -Group A11_relative_amount_scoped -Limit 0 -SleepMs 3000 -FetchLimit 100 -QueryTimeoutSec 45
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action start -Route astock -Group A12_code_pool_requery -Limit 0 -SleepMs 3000 -FetchLimit 100 -QueryTimeoutSec 45
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action start -Route astock -Group A13_limitup_pullback -Limit 0 -SleepMs 3000 -FetchLimit 100 -QueryTimeoutSec 45
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action start -Route astock -Group A14_ma_pullback_boundary -Limit 0 -SleepMs 3000 -FetchLimit 100 -QueryTimeoutSec 45
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action start -Route astock -Group A15_practical_combo_ceiling -Limit 0 -SleepMs 3000 -FetchLimit 100 -QueryTimeoutSec 45
```

如果 A12 需要 A11 的实测代码池，必须先完成 A11，再生成 A12 的具体 CSV，不允许凭空写代码池。

## 11. 最终交付

完成后明确报告：

1. 新增/修改了哪些文件。
2. A11-A15 每组 run_id。
3. 每组 stable / weak / risky / forbidden / timeout 数量。
4. “今日成交额大于近5日平均成交额1.5倍”最终判定：
   - 全市场是否可问。
   - 缩圈是否可问。
   - 代码池复问是否可问。
   - 推荐标准问法是什么。
5. “近10日有涨停 + 近3日回撤/缩量 + 均线不破”最终判定：
   - 哪些表达可强引用。
   - 哪些表达只能弱引用。
   - 哪些必须改写。
6. 关键词叠加上限：
   - 4、5、6、7、8 个条件分别是否稳定。
   - 超过几个条件后建议拆问。
7. 分隔符结论：
   - 推荐标准分隔符。
   - 哪些分隔符可识别但不推荐。
   - 哪些分隔符禁止用于矩阵生成。
8. 是否可以进入下一步法典整理。

不要自动 promote 到正式法典。先只产出候选结果和报告，等用户确认后再入法典。
