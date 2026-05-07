# Codex 复核报告：QueryLab 第一版

复核时间：2026-05-07

## 结论

Claude 第一版已经把 QueryLab 的目录、程序入口、中文 Query 预检、离线测试、候选法典队列搭起来了。

但它还不能算“完整生产完成”。这里必须区分两类问题：

1. **程序闭环问题**：这是第一步骨架本身需要修的，例如分析结果没有落盘、长期字典被覆盖、候选去重不足、错误分类不细。
2. **金融语句覆盖问题**：这是第二步计划内的工作。完整中文金融字段和复杂 Query 还没有全面投喂、分层实测，因此不能拿“覆盖不足”去责怪 Claude 第一版。

当前状态更准确地说是：

```text
第一步程序骨架：基本完成
离线测试：通过
A股基础实测：有 20 条候选证据
板块实测：未通过
法典闭环：未完全打通
长期字典报告：存在覆盖问题
```

所以本报告的修复重点是：**先修程序闭环，不是要求 Claude 立刻完成全部金融问法实测。**

## 我已执行的验证

```powershell
.\.venv\Scripts\python.exe -m pytest query_lab\tests\test_query_lab.py -q
```

结果：

```text
49 passed
```

```powershell
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py --dry-run --route all --limit 20
```

结果：能列出中文 Query。

```powershell
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py --dry-run --route astock --group A5_forbidden --limit 10
```

结果：英文 Query 被拦截为 NG，不会发送问财。

```powershell
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py canon lint
```

结果：

```text
errors=0 warnings=0
```

```powershell
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py canon diff
```

结果：当前有 21 条 astock 候选变更。

## 已确认可用的部分

1. `query_lab/` 位于正式 V6OP 目录下。
2. 没有修改旧 `F:\v.6\v6` 或 V5 目录。
3. 中文 Query 预检有效。
4. A股和板块目录分开。
5. 技能注册表存在，已包含：
   - `astock / 问财选A股`
   - `sector / 问财选板块`
   - `daily_kline / 日线`
   - `quote / 行情`
   - `technical_indicator / 技术指标`
   - `capital_flow / 资金`
6. `cases/extensions/pending_queries.csv` 已放入 KDJ、MACD、JMA、BOLL、均线等待测项。

## 必须修复的问题（程序闭环）

### 1. 原始结果没有回填分析状态

`query_lab/results/runs/*/query_results.jsonl` 中，所有记录的 `status` 仍是：

```text
pending
```

但 `run_summary.md` 中已经显示 stable/failed。

这说明：

```text
QueryRunner 写了 raw result
ResultAnalyzer 生成了分析结果
但分析结果没有写回 normalized_results.jsonl 或 analyzed_results.jsonl
```

要求修复：

```text
每次 run 必须同时写：
query_results.jsonl          原始执行结果
analyzed_results.jsonl       分类后的结果
run_summary.md               本次中文报告
```

`latest/` 也要同时保存这两类文件。

### 2. 长期稳定字典被最后一次运行覆盖

当前：

```text
query_lab/reports/stable_dictionary.md
```

显示 0 条稳定表达。

但 A1_basic 明明有 20 条 stable 候选。原因是最后一次 sector 运行失败，覆盖了全局 stable_dictionary。

要求修复：

```text
run_summary.md 是单次运行报告
reports/stable_dictionary.md 必须是累计字典或候选汇总
不能被一次失败运行覆盖成 0
```

可以从以下来源重建：

```text
canon/review_queue/candidate_changes.jsonl
canon/skills/*/canon.csv
results/runs/*/analyzed_results.jsonl
```

### 3. 板块测试没有通过，不能宣布板块法典完成

当前板块实测：

```text
S1_basic 10 条全部 failed/empty_result
```

Claude 报告里说“可能是字段提取失败”，但 Codex 复核时直接调用 pywencai，当前 stock 和 sector 都出现：

```text
AttributeError: 'NoneType' object has no attribute 'get'
```

因此现在不能断言只是字段名问题。

注意：板块未通过不等于“全部金融语句设计失败”。它只是说明当前板块适配器、问财 session/API 状态、字段提取 debug 还没有形成可验证闭环。

要求修复：

1. 增加原始返回 debug 保存，但不要污染普通 output。
2. 区分：
   - `api_error`
   - `auth_failed`
   - `session_error`
   - `empty_result`
   - `field_extract_error`
3. 只有确认问财返回了 rows 但提取不到名称时，才标记 `field_extract_error`。
4. 板块必须重新小批量验证。

### 4. 候选法典存在重复候选

`canon diff` 显示：

```text
今日涨幅大于3%
```

出现了两次候选，来自不同测试组。

这不应该直接变成两条法典项。

要求修复：

```text
canon propose / canon promote 必须按 skill_key + canonical_query_text 去重
重复候选要合并 evidence_run_ids 和 evidence_query_ids
```

### 5. `canon lint` 对候选队列检查偏弱

当前 lint 没报错，但它没有发现重复候选。

要求增强：

1. 检查 candidate 重复 query。
2. 检查同一 query 对应多个 meaning。
3. 检查同一 meaning 有多个 candidate strong 候选。
4. 检查 astock/sector 路由混用。

## 下一步建议

请 Claude 先做程序闭环修复，不要急着跑大量问财：

1. 写 `analyzed_results.jsonl`。
2. 修复累计字典报告。
3. 增强候选去重和 lint。
4. 增强 API/session/field 提取错误分类。
5. 增加板块 raw debug。
6. 明确读取已知问财语法注意事项：

```text
query_lab/specs/V6OP_已知问财语法注意事项.md
```

7. 重新跑：

```powershell
.\.venv\Scripts\python.exe -m pytest query_lab\tests\test_query_lab.py -q
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py --dry-run --route all --limit 20
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py canon lint
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py canon diff
```

通过后再跑小批量实测：

```powershell
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py --route astock --group A1_basic --limit 5 --repeat 1 --sleep-ms 3000
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py --route sector --group S1_basic --limit 3 --repeat 1 --sleep-ms 3000
```

## 验收口径

这版不能说“全部完成”，只能说：

```text
QueryLab 第一版骨架已完成，但生产闭环还需修复。
```

真正可验收需要满足：

1. 原始结果和分析结果都落盘。
2. 长期字典不会被单次失败运行覆盖。
3. candidate 能去重并合并证据。
4. 板块至少有基础查询能稳定返回。
5. API/session 错误和字段提取错误能区分。
6. canon promote 前能看到干净 diff。

## 不应归责的问题

以下内容属于第二阶段，不应算作第一版程序骨架失败：

1. 中文金融字段库还没全面扩展到 21 个技能。
2. A2/A3/复杂组合/排斥组合还没全部跑完。
3. KD、KDJ、MACD、JMA、BOLL 等技术指标还没完成系统反测。
4. P1-P6 还没根据完整法典重新生成。

这些要在程序闭环修好后，按中文 Query 种子清单和长期扩展协议逐步实测。
