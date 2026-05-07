# 给 Claude 的执行工单：只完成问财选A股闭环与天花板测试

## 0. 只做一个技能

本工单只针对：

```text
skill_type = astock
skill_name_zh = 问财选A股
```

不要扩展板块，不要扩展日线，不要扩展行情，不要碰 21 个技能。

正式项目只允许修改：

```text
F:\v.6\v6-op
```

禁止修改：

```text
F:\v.6\v6
F:\v.6\v5.10
F:\New.V5.10\Old.V5
```

## 1. 当前问题

QueryLab 第一版已经能读取 A股测试 CSV、中文预检、调用问财、写原始结果、生成 run_summary、写 candidate_changes。

但 `问财选A股` 的落点区闭环还没完成：

```text
query_results.jsonl 只有原始结果，status 仍是 pending
ResultAnalyzer 的 stable/failed/risky 没有单独落盘
stable_dictionary.md 会被最后一次运行覆盖
candidate_changes.jsonl 有重复候选
canon lint 没有检查候选重复和证据合并
failed_replay 没有形成可靠闭环
```

本次任务就是补齐这条链：

```text
cases/astock_问财选A股/*.csv
-> run
-> query_results.jsonl
-> analyzed_results.jsonl
-> failed_replay.jsonl
-> candidate_changes.jsonl
-> cumulative_dictionary
-> canon diff/lint/promote
-> astock 技能说法典
```

## 2. 第一步：先修落点区闭环

先不要跑大量问财。先把程序闭环修好。

### 2.1 每次 run 必须产生这些文件

每次运行必须写入独立目录：

```text
query_lab/results/runs/run_YYYYMMDD_HHMMSS/
  query_results.jsonl           # 原始执行结果
  analyzed_results.jsonl        # 分析分类结果
  failed_replay.jsonl           # 本次失败回放队列
  run_summary.md                # 本次中文报告
  astock_ceiling_report.md      # 本次天花板观察，仅 astock
```

同时更新：

```text
query_lab/results/latest/query_results.jsonl
query_lab/results/latest/analyzed_results.jsonl
query_lab/results/latest/failed_replay.jsonl
```

### 2.2 analyzed_results.jsonl 必须包含

每条分析结果必须包含：

```text
run_id
query_id
skill_type
skill_name_zh
test_group
category
query_text
normalized_intent
condition_count
field_atoms
risk_tags
actual_query_backend
exec_status
analysis_status              # stable / unstable / risky / failed / forbidden / invalid_query / pending
risk_level
recommended_usage
result_count
elapsed_ms
raw_error
failure_type                 # none / api_error / session_error / empty_result / field_extract_error / invalid_query / timeout
failure_reason_zh
notes
```

注意：不要再只把 `status=pending` 留在原始结果里。分析状态必须真实落盘。

### 2.3 stable_dictionary 必须是累计字典

不要让一次失败运行把稳定字典覆盖成 0。

必须区分：

```text
run_summary.md                         单次运行报告
reports/stable_dictionary.md           累计稳定字典
reports/risk_dictionary.md             累计风险字典
reports/forbidden_dictionary.md        累计禁问字典
reports/astock_ceiling_report.md       问财选A股天花板总报告
```

累计字典来源可以是：

```text
results/runs/*/analyzed_results.jsonl
canon/review_queue/candidate_changes.jsonl
canon/skills/astock_问财选A股/canon.csv
```

### 2.4 candidate 必须去重并合并证据

同一技能、同一 `canonical_query_text` 不要重复生成多条候选。

例如：

```text
今日涨幅大于3%
```

如果 A1 和 A2 都测过，应该合并成一条候选，证据字段合并：

```text
evidence_run_ids = run_x|run_y
evidence_query_ids = A1-001|A2-001
success_count
failed_count
result_count_min
result_count_max
result_count_avg
```

### 2.5 canon lint 必须增强

至少检查：

```text
候选重复 query
同一 query 多个 meaning
同一 meaning 多个 strong 候选
strong 与 forbidden 冲突
stable 与 forbidden 冲突
candidate 缺证据
candidate 缺 analyzed_result 来源
```

### 2.6 failed_replay 必须真实可用

失败项必须写入：

```text
query_lab/results/runs/run_*/failed_replay.jsonl
query_lab/results/failed_replay.jsonl
```

失败记录必须包含：

```text
query_id
query_text
skill_type
exec_status
failure_type
failure_reason_zh
raw_error
run_id
created_at
replay_count
next_replay_after
```

### 2.7 长跑测试执行纪律：禁止截断管道卡死

QueryLab 实测问财时，禁止把长时间运行的 Python 命令接到 `Select-Object -First N`、`head`、只读前 N 行的管道，或任何会提前停止读取 stdout 的命令上。

已经踩过的坑：

```text
PowerShell 使用 Select-Object -First 50 读取长跑输出后，管道读端提前结束。
Python 子进程继续写 stdout，stdout 管道被填满，进程被阻塞。
结果表现为：Python 进程还在、run 目录为空、Claude 以为还在等问财，实际没有可验收落盘。
```

长跑实测必须这样做：

```text
1. 输出重定向到 log 文件，不要靠截断管道看前几行。
2. 设置 NODE_NO_WARNINGS=1，避免 pywencai/Node warning 刷屏堵住输出。
3. 每完成一条 Query，立刻追加写入 query_results.jsonl 和 analyzed_results.jsonl。
4. 单条 Query 超时必须记录 failure_type=timeout 或 session_error，然后继续下一条，不允许整批永久卡住。
5. 检查进度时读取 run 目录、jsonl 行数、log tail、文件 LastWriteTime，不要用截断管道等待。
```

判断是否该中断的标准：

```text
如果 run 已经运行超过 10 分钟，但 run_*/query_results.jsonl、analyzed_results.jsonl、run_summary.md 都不存在，
或者文件 LastWriteTime 长时间不变，
则认为本次长跑没有可靠落盘，应中断并用日志重定向方式重跑。
```

中断时只能停止 QueryLab 当前测试进程，不要停止 V6OP 网页服务：

```powershell
Get-CimInstance Win32_Process -Filter "name='python.exe'" |
  Where-Object { $_.CommandLine -like '*query_lab*run_query_lab.py*--route astock*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

不要误杀：

```text
scripts\v6op_server.py --bind 127.0.0.1 --port 8876
```

## 3. 第二步：修完闭环后，开始念 A股检测稿

闭环修好并通过离线测试后，才开始小批量实测。

只跑：

```text
cases/astock_问财选A股/
```

不要跑 sector。

## 4. A股检测顺序

按由简到难跑：

### 4.1 地板测试：最短路径

目标：确认问财选A股最简单、最稳定的问法。

先跑：

```text
A1_basic
```

重点观察：

```text
单字段是否稳定
返回数量是否正常
耗时是否正常
是否出现 api/session 错误
```

### 4.2 同义表达测试

再跑：

```text
A2_synonym
```

目标：同一语义下，哪种中文说法最稳。

例如：

```text
今日涨幅大于3%
今天涨幅大于3%
涨幅超过3%
今日涨幅3%以上
```

必须输出：

```text
推荐标准说法
可接受变体
风险变体
不推荐变体
```

### 4.3 组合阶梯测试：摸天花板

再跑：

```text
A3_combo
```

目标：找出问财选A股能承受的条件复杂度。

必须输出：

```text
最短稳定路径
2条件稳定性
3条件稳定性
4条件稳定性
5条件开始是否变慢/失败/吞条件
最高建议条件数
不建议自动生成的条件数
```

### 4.4 高风险表达测试

再跑：

```text
A4_risky
```

目标：找出可以手动问、但不适合自动生成的表达。

例如：

```text
强势股
低位强势股
资金关注股
JMA均线向上
今日成交额较昨日放大一倍
```

必须输出：

```text
risky / manual_only 清单
能不能被改写
建议改写成什么
```

### 4.5 禁问测试

最后跑：

```text
A5_forbidden
```

目标：确认英文 Query、空 Query、预测性表达等会被拦截或标记禁用。

必须输出：

```text
forbidden_dictionary.md
invalid_query 规则
禁止自动生成清单
```

## 5. 目标报告

完成后必须生成：

```text
query_lab/reports/astock_ceiling_report.md
query_lab/reports/stable_dictionary.md
query_lab/reports/risk_dictionary.md
query_lab/reports/forbidden_dictionary.md
query_lab/reports/query_normalizer_rules.md
query_lab/canon/review_queue/candidate_changes.jsonl
query_lab/canon/conflicts/conflict_report.md
```

其中 `astock_ceiling_report.md` 必须回答：

```text
问财选A股的最短稳定问法是什么？
问财选A股的推荐标准表达是什么？
问财选A股最多建议几个条件？
从几个条件开始明显不稳定？
哪些字段最稳定？
哪些字段高风险？
哪些表达禁止问？
哪些用户自然语言需要改写？
```

## 6. 诊断功能

增加一个只针对 A股的诊断入口：

```powershell
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py diagnose --route astock --query "低位强势、资金关注、KDJ金叉、JMA向上的小盘股"
```

诊断功能不需要请求问财，它只查法典和字典。

输出必须说明：

```text
可直接使用的片段
需要改写的片段
高风险片段
禁用片段
未知/待测片段
建议改写后的中文 Query
引用证据 canon_id / run_id
```

目标是：以后用户随便说一句复杂话，系统能告诉他：

```text
哪段能问
哪段不能问
为什么不能问
应该改写成什么
```

## 7. 建议运行命令

先跑离线：

```powershell
Set-Location F:\v.6\v6-op
.\.venv\Scripts\python.exe -m pytest query_lab\tests\test_query_lab.py -q
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py --dry-run --route astock --limit 20
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py canon lint
```

离线通过后，小批量实测必须用守护脚本启动，不要直接裸跑长命令：

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action start -Route astock -Group A1_basic -Limit 5 -Repeat 1 -SleepMs 3000
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action status
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action tail
```

如需停止：

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action stop
```

确认落点区正常后，再逐组跑。每组先小批量 `-Limit 5`，确认有逐条落盘后才放大：

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action start -Route astock -Group A1_basic -Limit 5 -Repeat 1 -SleepMs 3000
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action start -Route astock -Group A2_synonym -Limit 5 -Repeat 1 -SleepMs 3000
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action start -Route astock -Group A3_combo -Limit 5 -Repeat 1 -SleepMs 3000
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action start -Route astock -Group A4_risky -Limit 5 -Repeat 1 -SleepMs 3000
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action start -Route astock -Group A5_forbidden -Limit 5 -Repeat 1 -SleepMs 3000
```

最后：

```powershell
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py canon lint
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py canon diff
```

不要自动 promote。等用户和 Codex 验收后再发布。

## 8. 最终交付说明

完成后请明确报告：

```text
问财选A股闭环是否完成
哪些文件新增/修改
离线测试结果
实测运行 run_id
A1/A2/A3/A4/A5 各自结果
最短稳定路径
复杂度天花板
禁问清单
风险表达
建议标准问法
是否可以进入下一步投喂更大的检测稿
```
