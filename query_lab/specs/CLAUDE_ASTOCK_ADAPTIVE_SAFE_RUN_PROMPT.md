# 给 Claude 的命令：问财选A股自适应安全跑测

你现在只处理 V6OP QueryLab 的一个技能：

```text
skill_type = astock
skill_name_zh = 问财选A股
workspace = F:\v.6\v6-op
```

禁止修改或运行旧版本目录：

```text
F:\v.6\v6
F:\v.6\v5.10
F:\New.V5.10\Old.V5
```

## 目标

把 `问财选A股` 的 QueryLab 跑测链路跑通，并形成可验收证据：

```text
cases/astock_问财选A股/*.csv
-> 安全实测
-> query_results.jsonl
-> analyzed_results.jsonl
-> failed_replay.jsonl
-> run_summary.md
-> astock_ceiling_report.md
-> stable/risk/forbidden dictionary
```

必须记住：**没有 `RUN_COMPLETE` 的 run 不能进入法典、累计字典、诊断依据。**

## 先读这些文件

```text
query_lab/specs/CLAUDE_ASTOCK_CLOSURE_AND_TEST_PROMPT.md
query_lab/specs/V6OP_已知问财语法注意事项.md
query_lab/scripts/query_lab_guard.ps1
query_lab/scripts/run_query_lab.py
query_lab/scripts/query_runner.py
```

## 执行纪律

不要再裸跑长命令，不要用 `Select-Object -First N`、`head`、截断管道观察长跑输出。

实测必须优先使用守护脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action status
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action start -Route astock -Group A1_basic -Limit 5 -Repeat 1 -SleepMs 3000
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action tail
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action stop
```

这些只是起点，不是死命令。你必须根据状态自适应调整。

## 自适应规则

1. 如果 `status` 显示已有 QueryLab 进程在跑，不要再启动第二个。先判断它是否有新文件落盘。
2. 如果 run 超过 10 分钟没有 `query_results.jsonl` 或 `analyzed_results.jsonl` 增长，立刻 `stop`，不要继续等。
3. 如果问财 session/API 连续失败，不要把中文语句判成 forbidden。先降低 `Limit`，增大 `SleepMs`，必要时暂停几分钟后重跑。
4. 如果 `Limit 5` 能完整生成 `RUN_COMPLETE`，再扩大到 `Limit 10` 或完整分组。
5. 如果扩大后失败，保留已完成 run 的证据，失败 run 不进法典；回退到上一个稳定规模继续。
6. 如果某条 Query 超时或 API 返回异常，要进入 `failed_replay.jsonl`，不能污染 stable dictionary。
7. 每次完成后必须检查：

```text
run_dir 是否有 RUN_COMPLETE
query_results.jsonl 行数
analyzed_results.jsonl 行数
run_summary.md
astock_ceiling_report.md
stable_dictionary.md / risk_dictionary.md / forbidden_dictionary.md
```

## 建议测试顺序

只测 `astock / 问财选A股`，不要扩展板块、日线、行情、21个技能。

按这个顺序由小到大：

```text
A1_basic      地板测试，最短稳定路径
A2_synonym    同义表达测试
A3_combo      组合阶梯，摸复杂度天花板
A4_risky      高风险表达
A5_forbidden  禁问测试
```

每组都先小批量，再扩大：

```text
Limit 1 -> Limit 5 -> Limit 10 -> full group
```

不要为了“跑完”硬等。判断标准是：有落盘、有完成标记、有报告、有可解释结果。

## 必须输出的验收报告

完成后请明确报告：

```text
1. 问财选A股闭环是否完成
2. 新增/修改了哪些文件
3. 离线测试结果
4. 实测 run_id 列表，只列 RUN_COMPLETE 的有效 run
5. A1/A2/A3/A4/A5 各自完成到什么规模
6. 哪些 query 稳定，返回多少，耗时多少
7. 哪些 query 是 API/session 问题，不算语法失败
8. 哪些 query 是 forbidden / invalid_query
9. 当前最短稳定问法
10. 当前复杂度天花板
11. 下一步是否可以投喂更大的检测稿
```

不要自动 promote。等用户和 Codex 验收后再发布法典。
