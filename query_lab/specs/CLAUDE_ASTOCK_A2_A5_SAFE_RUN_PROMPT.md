# Claude 执行单：问财选A股 A2-A5 安全跑测与法典候选更新

## 0. 绝对边界

本任务只允许操作正式项目：

```powershell
F:\v.6\v6-op
```

不要修改、不要运行、不要写入这些参考目录：

```powershell
F:\v.6\v6
F:\v.6\v5.10
F:\New.V5.10\Old.V5
```

本轮只做一个技能：

```text
astock / 问财选A股
```

不要扩展到板块、日线、行情、其他 21 个技能。

## 1. 本轮目标

从 A2 开始复核，然后继续跑 A3/A4/A5：

```text
A2_synonym    同义说法复核
A3_combo      组合复杂度测试
A4_risky      风险/边界表达测试
A5_forbidden  禁问/不推荐表达测试
```

目标不是单纯跑完，而是形成可验收的“问财选A股说法典候选”：

- 哪些中文说法稳定可用
- 哪些说法只是弱可用，需要谨慎
- 哪些说法容易空结果、超时、误解
- 哪些说法必须禁用或必须改写
- 每条 Query 的返回数量、耗时、状态、失败原因必须落盘

## 2. 必须使用的安全跑法

所有实测必须通过 guard 脚本，不要裸跑 Python，不要用 `Select-Object -First` 截断输出，不要用管道消费长输出。

进入目录：

```powershell
Set-Location F:\v.6\v6-op
```

先查状态：

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action status
```

如果已有 query_lab 进程，先不要启动新任务，先报告当前进程和 current/run 状态。

通用启动格式：

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 `
  -Action start `
  -Route astock `
  -Group <GROUP_NAME> `
  -Limit 0 `
  -SleepMs 3000 `
  -FetchLimit 100 `
  -QueryTimeoutSec 45
```

参数含义必须保持清楚：

- `-Limit 0`：跑该组全部 CSV 用例，不是取股数量
- `-FetchLimit 100`：每条 Query 最多取 100 只股票，只验证问法能否稳定返回，不翻很多页
- `-QueryTimeoutSec 45`：单条 Query 最多等 45 秒，超时后记录失败并进入下一条
- `-SleepMs 3000`：每条之间间隔 3 秒，降低 session 被耗尽概率

## 3. 执行顺序

### Step 1：先复核 A2

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 `
  -Action start `
  -Route astock `
  -Group A2_synonym `
  -Limit 0 `
  -SleepMs 3000 `
  -FetchLimit 100 `
  -QueryTimeoutSec 45
```

A2 完成后必须检查：

- 是否存在 `RUN_COMPLETE`
- `analyzed_results.jsonl` 是否有完整行数
- stable / failed / risky / invalid_query 数量
- 是否出现 `empty_result_retry` 记录
- 是否有超时、空结果、乱码污染关键字段

如果 A2 不是 clean pass，不要继续 A3；先诊断并报告。

### Step 2：A2 clean pass 后跑 A3

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 `
  -Action start `
  -Route astock `
  -Group A3_combo `
  -Limit 0 `
  -SleepMs 3000 `
  -FetchLimit 100 `
  -QueryTimeoutSec 45
```

A3 是摸“组合复杂度天花板”的核心。重点看：

- 2 条件、3 条件、4 条件、5 条件是否还能稳定返回
- 哪个复杂度开始明显变慢、空结果、超时
- 是否存在某个字段组合导致问财误解

### Step 3：A3 完成后跑 A4

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 `
  -Action start `
  -Route astock `
  -Group A4_risky `
  -Limit 0 `
  -SleepMs 3000 `
  -FetchLimit 100 `
  -QueryTimeoutSec 45
```

A4 是风险表达测试。重点看：

- 口语化、模糊化、过度复杂表达是否会误解
- 是否能给出“弱引用 / 需要改写 / 禁用”的判断
- 不能因为偶发空结果直接判死，必须参考 retry 和可重复性

### Step 4：A4 完成后跑 A5

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 `
  -Action start `
  -Route astock `
  -Group A5_forbidden `
  -Limit 0 `
  -SleepMs 3000 `
  -FetchLimit 100 `
  -QueryTimeoutSec 45
```

A5 是禁问测试。重点看：

- 英文整句、无中文金融字段、无法结构化的表达，应该被 validator 拦截或被标记 forbidden/invalid
- 不要把 A5 当成“要返回股票”的成功测试
- A5 的成功标准是：该禁的禁、该拦的拦、原因清楚

## 4. 监控与异常处理

每组启动后，用以下命令监控：

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action status
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action tail -TailLines 120
```

如果 2 到 3 分钟没有新增 query 行：

1. 不要继续傻等。
2. 先查看 `current_query.json`，确认卡在哪个 query_id / query_text。
3. 查看 stdout/stderr log。
4. 如果确实无增长，再用 guard 停止：

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action stop
```

5. 停止后只保留已经 `RUN_COMPLETE` 的 run 作为正式可用结果；未完成 run 只能作为诊断材料，不得进入候选法典。

## 5. 已知经验，必须遵守

1. `case_limit` 和 `fetch_limit` 不能混。
   - `Limit` 是跑多少条测试用例。
   - `FetchLimit` 是每条 Query 最多取多少只股票。

2. 本轮法典测试默认 `FetchLimit=100`。
   - 这是为了验证问法是否能返回、是否可解析、是否稳定。
   - 不要默认翻十几页、几十页取全量股票。

3. 如果需要测“真实数量级天花板”，另开专项 run，用 `FetchLimit=300/500/2000`。
   - 不要和本轮 A2-A5 稳定性测试混在一起。

4. 问财接口可能抖动。
   - 单次 `empty_result` 不能直接污染法典。
   - 当前 QueryRunner 已有 empty_result retry 保护；请确认日志里是否触发。

5. 所有提问必须是中文金融语义。
   - 代码字段可以英文。
   - Query 文本必须中文。

## 6. 验收报告必须包含

完成后请输出一份清楚报告，至少包含：

1. 本轮新增/修改了哪些文件
2. A2/A3/A4/A5 各自 run_id
3. 每组是否有 `RUN_COMPLETE`
4. 每组 stable / risky / failed / forbidden / invalid_query 数量
5. A3 的组合复杂度天花板判断
6. A4 的风险表达清单
7. A5 的禁问/拦截清单
8. 哪些条目建议进入候选法典
9. 哪些条目必须重跑或人工复核
10. 是否可以进入下一步：从候选法典整理为正式 `astock / 问财选A股` 法典

不要只说“完成了”。必须给出可验收路径和文件位置。

