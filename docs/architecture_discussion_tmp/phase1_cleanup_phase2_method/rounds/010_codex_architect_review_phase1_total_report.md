# Round 003: Codex 秘书对 Claude 009 技术审计报告的复核意见

本文件复核：

```text
F:\v.6\v6-op\docs\architecture_discussion_tmp\phase1_cleanup_phase2_method\rounds\009_claude_analyst_response_phase1_total_report.md
```

## 1. 总体判断

Codex 秘书判断：

```text
Claude 009 可以纳入第二阶段改造的技术证据库。
但不能逐字照单全收，需要带三处口径修正。
```

它的主要价值是：把第一阶段从“文档签收状态”拉回到“当前代码真实状态”，列出了若干可以直接进入第二阶段候选任务池的代码级缺陷。

它的不足是：有几处措辞过重，容易把“待验证/授权机制不透明”写成“必然错误”，或把“局部验收需要重开”写成“15 条验收整体不成立”。

## 2. 可以接收的技术结论

以下结论经 Codex 抽查代码后，可以接收：

### 2.1 问财 api_key 没有传入 `pywencai.get()`

代码证据：

```text
F:\v.6\v6-op\scripts\sources\wencai_source.py
```

事实：

- `_query_wencai(query, api_key, limit)` 接收 `api_key`。
- `run()` 会读取 `IWENCAI_API_KEY`。
- 但 `pywencai.get(...)` 调用体里没有传入 `api_key`。

接收结论：

```text
api_key 参数目前没有参与 pywencai.get 调用。
问财授权机制不透明，需要第二阶段优先验证。
```

### 2.2 `czsc_producer.py` 回看天数硬编码 365

代码证据：

```text
F:\v.6\v6-op\scripts\producers\czsc_producer.py
```

事实：

```python
df = fetch_ohlcv(code, days=365, verbose=False)
```

接收结论：

```text
czsc 的 days 参数没有端到端影响实际 K 线读取。
这会破坏“参数修改后结果可变化”的验收口径。
```

### 2.3 `fetch_planner.plan()` 未接收真实 lookback_days

代码证据：

```text
F:\v.6\v6-op\scripts\fetch_planner.py
F:\v.6\v6-op\scripts\execution_engine.py
```

事实：

- `fetch_planner.plan()` 支持 `lookback_days` 参数。
- `execution_engine.py` 两处调用 `fetch_planner.plan()` 时未传入真实最大 days。
- `compute_scope_data_time_max()` 也未传入真实 days。

接收结论：

```text
K线准备判断、数据日期计算和技能实际读取可能不一致。
这是第二阶段 P0/P1 级链路一致性问题。
```

### 2.4 SMC 默认模式双轨

代码证据：

```text
F:\v.6\v6-op\scripts\skill_registry.py
F:\v.6\v6-op\scripts\execution_engine.py
```

事实：

- `skill_registry.py` 里 SMC 默认值是 `soft_filter`。
- `execution_engine.py` 里 SMC 默认回退是 `strict`。

接收结论：

```text
SMC 默认模式口径不一致，第二阶段需要统一。
```

### 2.5 `_write_cache()` 写缓存失败静默吞掉

代码证据：

```text
F:\v.6\v6-op\scripts\ohlcv_provider.py
```

事实：

- `_write_cache()` 中存在 `except Exception: pass`。

接收结论：

```text
K线缓存写入失败缺少日志/告警/报告字段。
这会影响运行可诊断性，应纳入第二阶段数据链路稳定化。
```

### 2.6 sequential / simple_hybrid 与 expression_runner 双轨

代码证据：

```text
F:\v.6\v6-op\scripts\execution_engine.py
F:\v.6\v6-op\scripts\strategy_graph_builder.py
```

事实：

- `parallel_and` 使用 expression runner 或表达式路径。
- `sequential` / `simple_hybrid` 在 `execution_engine.py` 内部用手写分支和集合结果计算。
- `strategy_graph_builder.py` 目前主要生成可检查的 plan，不驱动 producer 执行。

接收结论：

```text
三路径当前可运行，但不是统一图执行器。
报告表达式和真实执行路径存在双轨风险。
```

### 2.7 FAST_FULL_SCAN 下没有三源降级

代码证据：

```text
F:\v.6\v6-op\scripts\ohlcv_provider.py
F:\v.6\v6-op\scripts\data_prefetch.py
```

事实：

- `FAST_FULL_SCAN=true` 时路径是“新鲜缓存 -> baostock -> None”。
- worker 预取路径设置了 `FAST_FULL_SCAN=true`。

接收结论：

```text
预热主路径不符合章程里 baostock -> akshare -> yfinance -> 旧K线 的完整降级描述。
```

## 3. 需要修正口径的地方

### 3.1 “wencai 请求永远以未授权方式发出”口径过重

Claude 009 原话倾向于说：请求永远以未授权方式发出。

Codex 修正：

```text
代码只能证明 api_key 没有传给 pywencai.get。
不能仅凭代码证明 pywencai 没有通过 cookie/session/内部状态授权。
```

建议正式口径：

```text
问财 key 参数没有进入 pywencai.get 调用，授权机制不透明。需要在清洁环境下验证：无 session/cookie 时，仅配置 IWENCAI_API_KEY 是否能成功取数。
```

### 3.2 “czsc 缓存永不复用”口径过重

Claude 009 说 days 进入指纹但不影响实际取数，导致缓存永不复用。

Codex 修正：

```text
如果用户一直使用默认 days=365，同参数重复运行仍可能命中缓存。
问题不是绝对“永不复用”，而是用户改变 days 时，指纹变化但实际计算仍用 365，造成缓存语义错误和重复计算。
```

建议正式口径：

```text
czsc days 参数参与 mask_cache 指纹，但没有参与实际 K线读取；当 days 不同于 365 或用户调整 days 时，缓存语义不可信。
```

### 3.3 “V6OP-026 15/15 技术意义不成立”口径需要降级

Claude 009 对 V6OP-026 的批评方向成立，但措辞过重。

Codex 修正：

```text
V6OP-026 不是假报告。
它记录了当时验收口径下的通过状态，也明确写了 browser_unavailable 和若干限制。
问题是验收口径过窄，不能代表真实运营稳定完成。
```

建议正式口径：

```text
V6OP-026 的“15/15闭合”应重新解释为：按当时局部验收口径通过；其中若干条需要在代码审计后重开、降级为部分关闭或标记待验证。
```

## 4. 建议纳入第二阶段候选改造池的条目

以下条目可以进入第二阶段候选改造池，但还不是正式施工命令。

### P0：结果可信度 / 数据链路一致性

1. 修复 `czsc_producer.py` days 硬编码，使 UI days 真正影响 K线读取。
2. 在 `execution_engine.py` 中统一计算 max lookback days，并传给：
   - `fetch_planner.plan()`
   - `data_prefetch.run_prefetch()`
   - `compute_scope_data_time_max()`
   - 各 producer 参数。
3. 验证并修正问财授权机制：
   - `IWENCAI_API_KEY` 是否被 pywencai 使用；
   - 无 session/cookie 的清洁环境是否能靠 key 成功；
   - 如 pywencai 不支持 key 参数，则文档和 UI 必须明确授权实际机制。

### P1：解释可信度 / 行为一致性

4. 统一 SMC 默认模式，避免 registry 与 engine 双轨。
5. 修正 FAST_FULL_SCAN 取数路径与三源降级口径：
   - 要么恢复降级；
   - 要么明确快速扫描只用 baostock，并在报告中标注风险。
6. 让 run_report 保留更多来源诊断字段：
   - query 原文；
   - query_hash；
   - limit；
   - actual_count；
   - api_called；
   - status；
   - elapsed；
   - 分页信息。
7. 设计全局解释层：说明来源为空、K线不足、技能过严、路径交集过严分别导致什么结果。

### P2：架构收敛 / 可维护性

8. 逐步统一三路径执行：
   - 不再让 sequential / hybrid 长期绕过 expression_runner；
   - 让 report expression 与真实执行逻辑一致。
9. 修复 `_write_cache()` 静默吞错，至少进入日志和报告。
10. 修复 `scope_id` 只取前 30 只的 hash 风险。

### P3：运行管理与体验

11. 补真实浏览器验收。
12. 明确 abort 是“步骤边界中止”还是“强中止”。
13. 后续再讨论历史报告、清缓存、续跑、管理中心分流。

## 5. 是否需要反驳 Claude 009

不建议反驳整份报告。

建议处理方式：

```text
整体接收，作为技术审计材料纳入第二阶段讨论。
但在后续正式报告或开发计划里，采用 Codex 修正后的口径：
  - 问财授权机制不透明，不写死“永远未授权”；
  - czsc 缓存语义错误，不写死“永不复用”；
  - V6OP-026 需要重解释，不写成“完全无效”。
```

## 6. 下一步建议

下一步不应马上生成施工命令。

建议先形成一个正式中间产物：

```text
第二阶段候选改造池 v0
```

内容包括：

- 问题编号；
- 问题层级；
- 风险等级；
- 证据文件；
- 是否需运行验证；
- 是否可直接施工；
- 是否需架构讨论；
- 与用户体验痛点的关系。

这个候选池整理完后，再由人类决定哪些进入第二阶段第一批开发。
