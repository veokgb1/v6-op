# Claude 工单：问财选板块 S9 返回增强补测

只在 `F:\v.6\v6-op` 内工作。不要修改 `F:\v.6\v6`、V5、V5.10。

## 目标

在已完成的 `问财选板块` S1-S8 基础上，只补测一层：S9 返回增强。

这次不是重新摸地板/天花板，而是回答三个问题：

1. `问财选板块` 能不能返回“上涨原因 / 板块上涨原因 / 走强原因”？
2. `问财选板块` 能不能稳定返回“板块指数代码 / 指数简称 / 指数行情字段”？
3. `问财选板块` 能不能返回“板块内龙头股 / 领涨股 / 前排股”？如果不能，应该怎么拆到 `问财选A股`？

## 背景结论

S1-S8 已确认：

- 成功结果主要是 `sector_only`。
- 成功 backend 实际是 `zhishu`。
- 原始列已出现 `指数代码`、`指数简称`、涨跌幅、成交额、上涨家数、涨停家数等指数字段。
- `X板块中今日涨幅排名前10的股票` 在 sector 路由下失败。
- `龙头股 / 最强 / 值得关注 / 原因是什么` 类表达有忽略语义或空结果风险。

本次 S9 要把这些结论再补清楚，而不是重复跑 S1-S8。

## 新增用例文件

请新建：

```text
query_lab/cases/sector_问财选板块/S9_return_enrichment.csv
```

字段沿用现有 sector CSV 格式。

建议用例如下，可根据现有表头补齐字段：

```text
S9-001 今日涨幅排名前10的板块，上涨原因是什么
S9-002 今日涨停家数排名前10的板块，原因是什么
S9-003 今日主力净流入排名前10的板块，资金流入原因是什么
S9-004 今日涨幅排名前10的板块，返回板块指数代码
S9-005 今日成交额排名前10的板块，返回指数代码和指数简称
S9-006 今日涨停家数排名前10的板块，返回涨停家数和上涨家数
S9-007 今日涨幅排名前5的板块及其领涨股
S9-008 今日涨停家数排名前5的板块及其龙头股
S9-009 军工板块领涨股
S9-010 军工板块中今日涨幅排名前10的股票
S9-011 今日涨幅排名前5的板块，然后查询每个板块中的今日涨幅排名前3股票
```

## 分类要求

每条必须分类：

```text
return_object_type:
  sector_only
  sector_with_reason
  sector_with_index_fields
  stock_only
  mixed_sector_stock
  text_explanation
  empty_or_error
```

每条必须记录：

```text
actual_query_backend
raw_columns
extracted_sector_names
extracted_index_codes
extracted_index_names
extracted_stock_codes
extracted_stock_names
extracted_reason_text
result_count
elapsed_ms
next_pipeline_route
```

## 判断规则

### 上涨原因

如果 query 写了“原因是什么”，但返回列仍只是指数简称、涨跌幅、成交额等普通表格，没有原因文本，则结论必须写：

```text
reason_query_ignored
```

不要把普通板块列表误判成“原因返回成功”。

### 板块指数

如果原始列里有：

```text
指数代码
指数简称
指数@涨跌幅
指数@成交额
指数@上涨家数
指数@涨停家数
```

则说明 `问财选板块` 可以返回板块指数类字段。

注意：

- `指数代码` 是 88xxxx/884xxx 这类指数代码，不是 A 股代码。
- `指数简称` 才是板块名。

### 龙头股 / 领涨股 / 前排股

如果返回的是板块列表，而不是股票列表，必须标为：

```text
leader_query_not_supported_by_sector
```

推荐拆法：

```text
Step 1 sector:
  今日涨幅排名前5的板块

Step 2 astock:
  {板块名}中今日涨幅排名前3的股票
```

如果 sector 直接返回股票，才标 `stock_only` 或 `mixed_sector_stock`。不要预设会返回股票。

## 运行纪律

不要跑 S1-S8。
不要跑 astock 全量。
不要自动 promote。
不要裸跑长任务。

先检查状态：

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action status
```

如果有旧进程，先停：

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action stop
```

运行 S9：

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 `
  -Action start -Route sector -Group S9_return_enrichment -Limit 0 `
  -SleepMs 3000 -FetchLimit 20 -QueryTimeoutSec 45
```

如果某条超时或空结果，记录后继续，不要反复重跑。

## 报告要求

生成：

```text
query_lab/reports/sector_s9_return_enrichment_report.md
```

并更新：

```text
query_lab/reports/SECTOR_QUERY_CANON_HANDOFF.md
query_lab/reports/sector_return_contract_report.md
```

报告必须直接回答：

1. 上涨原因能不能返回？
2. 板块指数代码/指数简称/指数行情字段能不能返回？
3. 龙头股/领涨股能不能在 sector 路由直接返回？
4. 如果不能，标准拆分链路是什么？
5. 哪些写法要禁止自动生成？
6. 哪些字段可展示给策略台/输入工坊？

完成后给出：

```text
1. 修改文件
2. S9 run_id
3. 每类结论
4. 是否需要后续 astock 接力测试
```
