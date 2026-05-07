# Claude 工单：问财选A股返回契约补确认

只在 `F:\v.6\v6-op` 内工作。不要修改 `F:\v.6\v6`、V5、V5.10。

## 目标

只做一件事：确认 `问财选A股` 除了股票代码以外，返回内容里还包含什么。

前期我们默认 `问财选A股` 返回股票代码池，但这是工程假设。现在要用事实补确认：

1. 是否返回股票代码？
2. 是否返回股票中文简称/名称？
3. 是否返回价格字段，例如收盘价、最新价、涨跌幅？
4. 是否返回成交额、换手率、量比、主力净流入等条件相关字段？
5. 是否有纯文本说明、混合表、空字段？
6. 这些返回字段后续能不能展示在策略台/报告中心？

## 边界

不要重跑 A1-A15。
不要跑 sector / 问财选板块。
不要自动 promote。
不要修改正式 canon。

只新增一个小组：

```text
A_return_contract
```

## 新增用例文件

请新建：

```text
query_lab/cases/astock_问财选A股/A_return_contract.csv
```

字段沿用现有 A 股 CSV 格式。若现有 runner 只支持 A1/A2 这类组名，也可以命名为：

```text
A16_return_contract.csv
```

但报告里统一称 `A_return_contract`。

建议测试 8 条，不要多跑：

```text
AR-001 今日涨幅大于3%
AR-002 今日成交额大于5亿
AR-003 今日换手率大于5%
AR-004 今日量比大于1.5
AR-005 今日主力净流入大于1亿
AR-006 流通市值在80亿到300亿之间
AR-007 半导体板块，今日涨幅大于3%
AR-008 今日涨幅大于3%，今日成交额大于5亿，今日主力净流入为正
```

目的不是测语义稳定性，而是覆盖不同字段后看 raw columns。

## 返回分类要求

每条必须记录：

```text
return_object_type:
  stock_code_only       只有股票代码
  stock_code_name       股票代码 + 股票简称/名称
  stock_with_quote      股票代码/名称 + 行情字段
  stock_with_factor     股票代码/名称 + 条件字段/指标字段
  text_explanation      文字说明
  mixed_unknown         混合不清
  empty_or_error        空/错误/超时
```

每条必须记录：

```text
actual_query_backend
raw_columns
extracted_stock_codes
extracted_stock_names
extracted_quote_fields
extracted_factor_fields
result_count
elapsed_ms
next_pipeline_route
```

## 重点观察字段

请明确检查原始结果中是否存在：

```text
股票代码 / code / 股票代码列
股票简称 / 股票名称 / name
最新价 / 收盘价 / 现价
涨跌幅
成交额
换手率
量比
主力净流入 / 主力资金流向
流通市值 / 总市值
所属行业 / 所属概念 / 板块名
```

如果列名不同，请按真实 raw_columns 写。

## 运行纪律

先检查状态：

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action status
```

如有旧进程，先停：

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action stop
```

运行时必须限制取数，不要全量翻页：

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 `
  -Action start -Route astock -Group A_return_contract -Limit 0 `
  -SleepMs 3000 -FetchLimit 100 -QueryTimeoutSec 45
```

如果现有 guard 不接受 `A_return_contract` 组名，请用你创建的实际组名，但最终报告必须写清楚。

FetchLimit=100 足够确认列结构，不需要 300/全量。

## 报告要求

生成：

```text
query_lab/reports/astock_return_contract_report.md
```

并同步复制/更新到人看的双语目录：

```text
query_lab/reports/ASTOCK_问财选A股/ASTOCK_问财选A股__RETURN_CONTRACT_返回契约.md
```

同时更新：

```text
query_lab/reports/ASTOCK_QUERY_CANON_HANDOFF.md
query_lab/reports/ASTOCK_问财选A股/ASTOCK_问财选A股__QUERY_CANON_HANDOFF_法典交接.md
query_lab/reports/REPORT_INDEX__技能报告索引_中英对照.md
```

如果 `ASTOCK_QUERY_CANON_HANDOFF.md` 里已有总结，请追加一节：

```text
问财选A股返回契约补确认
```

## 最终报告必须回答

1. `问财选A股` 返回的是只有股票代码，还是代码 + 中文名称？
2. 是否附带价格、涨跌幅、成交额、换手率、量比、主力净流入等字段？
3. 哪些字段是默认返回，哪些只有 query 中出现对应条件才返回？
4. 返回内容能否用于策略台/报告中心展示？
5. 后续 pipeline 应该提取哪些字段？
6. 是否需要再补测“股票简称查询 / 代码查询 / 板块前缀查询”？

完成后给出简短结果：

```text
1. 修改文件
2. run_id
3. 返回字段结论
4. 更新了哪些总结/索引
5. 是否建议下一轮补测
```
