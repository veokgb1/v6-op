# Claude 执行单：问财选A股第二批 A6-A10 边界跑测

## 0. 边界

只操作正式项目：

```powershell
F:\v.6\v6-op
```

只做：

```text
astock / 问财选A股
```

不要修改 V5/V6 参考目录。不要改动第一批 A1-A5 既有用例含义。第二批只能新增 A6-A10 用例、运行、分析、报告。

## 1. 第二批目标

第一批 A1-A5 已经建立基础法典雏形。第二批不要重复第一批，不要做“用户口语压力测试”。本批只测结构化中文金融问法的更深边界：

```text
A6_time_window       时间窗口
A7_numeric_relative  数值边界 / 相对比较
A8_capital_flow      资金字段深测
A9_technical_shape   技术字段 / 图形字段边界
A10_complex_boundary 复杂刁钻组合 / 禁问边界
```

## 2. 新增 cases 目录与文件

在现有目录下新增或补齐这些 CSV：

```powershell
F:\v.6\v6-op\query_lab\cases\astock_问财选A股\A6_time_window.csv
F:\v.6\v6-op\query_lab\cases\astock_问财选A股\A7_numeric_relative.csv
F:\v.6\v6-op\query_lab\cases\astock_问财选A股\A8_capital_flow.csv
F:\v.6\v6-op\query_lab\cases\astock_问财选A股\A9_technical_shape.csv
F:\v.6\v6-op\query_lab\cases\astock_问财选A股\A10_complex_boundary.csv
```

CSV 字段结构必须沿用现有 A1-A5 CSV 表头，不要另起 schema。所有 `query_text` 必须是中文金融语义。

## 3. A6-A10 建议用例

### A6_time_window：时间窗口

至少包含：

```text
近3日涨幅大于5%
近5日涨幅大于10%
近20日涨幅小于10%
最近一个月涨幅大于20%
连续3日主力净流入为正
近5日成交额持续放大
近3日换手率大于10%
近20日成交额大于5亿
```

目的：确认问财对“近N日 / 最近一个月 / 连续N日 / 持续放大”的理解边界。

### A7_numeric_relative：数值边界 / 相对比较

至少包含：

```text
流通市值大于30亿且小于150亿
流通市值在30亿到150亿之间
今日涨幅大于5%，近5日涨幅小于0%
今日量比大于前2日量比
今日成交额大于近5日平均成交额的1.5倍
今日换手率大于近3日平均换手率
今日成交额是昨日成交额的2倍以上
今日涨幅小于5%，今日成交额大于5亿
```

目的：测试“大于 / 小于 / 之间 / 以上 / 倍数 / 平均值 / 前N日比较”的稳定性。  
注意：相对比较类很可能 risky，不要强行判 stable。

### A8_capital_flow：资金字段深测

至少包含：

```text
今日主力净流入大于5000万
今日主力净流入大于1亿
今日主力净流入为正
近3日主力资金连续净流入
今日大单净流入大于3000万
今日超大单净流入为正
今日资金净流入大于5000万
今日主力净流入占成交额比例大于5%
```

目的：测试“主力净流入 / 大单净流入 / 超大单净流入 / 资金净流入 / 占比”哪些能直接问，哪些必须改写。

### A9_technical_shape：技术字段 / 图形字段边界

至少包含：

```text
今日收盘价站上5日均线
今日收盘价大于20日均线
均线多头排列
MACD金叉
KDJ金叉
今日K线为锤子线
今日K线为阳包阴
收盘价站上JMA均线
```

目的：测试“均线 / MACD / KDJ / K线形态 / 非标准 JMA”是否能直接问。  
JMA 属于高风险/非标准字段，必须特别标注。

### A10_complex_boundary：复杂刁钻组合 / 禁问边界

至少包含：

```text
今日量比明显大于前两日，且今日涨幅大于3%
今日成交额放大但股价涨幅不超过5%
主力净流入显著增加，且近5日涨幅小于10%
平台突破且成交额大于近5日平均成交额
今日涨幅大于3%，但近20日涨幅小于0%
今日涨幅大于5%，但主力净流入为负
低位放量突破
图形走得很好
```

目的：测试“明显 / 放大 / 显著 / 平台突破 / 图形”这类词到底是否可问。  
这些不是用户口语测试，而是结构化金融表达边界测试。凡无法结构化的，应进入 risky / forbidden / rewrite_required。

## 4. 跑测方式

仍然只使用 guard，不裸跑 Python：

```powershell
Set-Location F:\v.6\v6-op
```

每组按顺序跑：

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action start -Route astock -Group A6_time_window -Limit 0 -SleepMs 3000 -FetchLimit 100 -QueryTimeoutSec 45
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action start -Route astock -Group A7_numeric_relative -Limit 0 -SleepMs 3000 -FetchLimit 100 -QueryTimeoutSec 45
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action start -Route astock -Group A8_capital_flow -Limit 0 -SleepMs 3000 -FetchLimit 100 -QueryTimeoutSec 45
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action start -Route astock -Group A9_technical_shape -Limit 0 -SleepMs 3000 -FetchLimit 100 -QueryTimeoutSec 45
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action start -Route astock -Group A10_complex_boundary -Limit 0 -SleepMs 3000 -FetchLimit 100 -QueryTimeoutSec 45
```

每次 start 前必须确认没有正在跑的 query_lab 进程：

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action status
```

如果上一组未 `RUN_COMPLETE`，不得继续下一组。

## 5. 验收报告

完成后必须输出：

1. 新增/修改文件列表
2. A6-A10 各自 run_id
3. 每组是否 RUN_COMPLETE
4. 每组 stable / risky / failed / forbidden / invalid_query 数量
5. A6 时间窗口可用清单
6. A7 相对比较可用/风险清单
7. A8 资金字段强可用/弱可用/不可用清单
8. A9 技术字段和图形字段边界清单
9. A10 复杂刁钻表达的改写/禁问建议
10. 哪些可以进入候选法典，哪些必须重跑

不要 promote 到正式法典，先只生成候选和验收报告。

