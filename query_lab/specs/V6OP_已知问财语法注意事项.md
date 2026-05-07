# V6OP 已知问财语法注意事项

本文件记录 V6OP 前期实测中已经踩过的问财 Query 坑。Claude 修 QueryLab 或继续实测前必须阅读。

## 1. 不要用英文金融语句请求问财

实际发送给同花顺问财的 `query_text` 必须是中文金融自然语言。

允许：

```text
流通市值在30亿到150亿之间，近30日振幅小于15%的A股
```

禁止：

```text
A-shares with market cap between 3 and 15 billion
```

## 2. A股 Query 优先使用明确字段表达

已实测较稳定的表达风格：

```text
今日涨幅大于3%
今日成交额大于3亿
今日换手率大于5%
今日量比大于1.5
流通市值在30亿到150亿之间
今日主力净流入为正
近5日涨幅大于10%
近20日涨幅大于20%
非ST，非停牌
上市超过60天，非ST，非停牌
今日收盘价大于5日均线
```

这些只能算初步稳定候选，仍需进入 QueryLab 证据链和法典候选。

## 3. 动态比较表达要谨慎

以下表达曾经更容易导致空结果或不稳定，不要直接放进默认 P1-P6：

```text
今日成交量较昨日放大2倍以上
今日成交额大于近5日平均成交额的1.5倍
今日换手率大于近5日平均换手率的1.5倍
今日量比大于近5日平均量比
```

它们可以进入高风险反测组，但默认 `recommended_usage = manual_only` 或 `forbidden`。

## 4. 板块联动语法注意

V6OP 前期发现，多个板块拼接时，下面这种写法更容易失败或含义不清：

```text
属于电池、IT服务、电力板块，且今日涨幅大于3%
```

应优先测试更明确的“或”连接：

```text
属于电池板块或IT服务板块或电力板块，且今日涨幅大于3%
```

如果 QueryLab 要测试“板块 -> A股”的桥接语法，必须把这两类写法分开作为对照组，不要混在同一条结论里。

## 5. 问财选板块和问财选A股不能混测

必须分两路：

```text
astock / 问财选A股 / 返回股票
sector / 问财选板块 / 返回板块
```

板块查询还需要记录底层实际调用：

```text
sector
zhishu
sector+zhishu_fallback
```

因为部分板块数据可能不在普通 `sector` 返回结构里。

## 6. 板块失败要区分原因

板块测试失败时，不能笼统写 `empty_result`。至少要区分：

```text
api_error
session_error
auth_failed
empty_result
field_extract_error
```

只有当问财确实返回了 rows，但无法从 rows 中提取板块名称时，才允许标记为 `field_extract_error`。

## 7. 不要把一次 API/session 故障当成语法失败

如果连续查询出现：

```text
'NoneType' object has no attribute 'get'
```

这更可能是 pywencai/session/API 状态问题，而不一定是中文 Query 语法本身失败。

QueryLab 必须把这种情况记录为 API/session 问题，并进入失败回放，而不是直接判定中文表达 forbidden。

## 8. 进入法典前必须有证据

任何表达进入技能说法典前，必须能追溯：

```text
run_id
query_id
query_text
skill_type
actual_query_backend
exec_status
result_count
analysis_status
```

没有证据链的表达只能是 pending，不能进入 strong/weak 引用。

## 9. 长跑实测不要使用截断管道

问财实测经常是长跑任务，尤其是 A1/A2/A3 批量测试。不要用下面这种方式观察输出：

```powershell
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py --route astock --group A1_basic |
  Select-Object -First 50
```

原因：`Select-Object -First 50` 读满 50 行后会停止读取，Python 进程继续写 stdout 时可能把管道写满，导致进程卡住。此时表面看进程还在，实际 run 目录没有结果文件，等待再久也没有可靠产物。

正确做法：

```text
长跑输出写入 log 文件。
每条 Query 完成后立即落盘 jsonl。
用 run 目录文件数、jsonl 行数、LastWriteTime、log tail 判断进度。
如果超过 10 分钟没有任何 query_results/analyzed_results 落盘，直接中断重跑。
```

V6OP QueryLab 已提供守护脚本，实测优先使用：

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action start -Route astock -Group A1_basic -Limit 5 -Repeat 1 -SleepMs 3000
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action status
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action tail
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action stop
```

这类卡死不能归因于中文 Query 语法失败，也不能进入 forbidden/risky 法典。它只能记录为执行方式错误或 runner 卡死。
