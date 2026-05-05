# V6OP-003 阶段 2 Fetch Planner + 执行引擎 + 后端 API

> 下发角色：v6-op 架构师（Codex）
> 执行角色：Claude
> 状态：ready
> 日期：2026-05-05

## 1. 目标

在 `F:\v.6\v6-op` 内完成 charter 阶段 2：

```text
scope 解析 -> 数据需求合并 -> 预热 -> Producer 执行 -> MaskExpression 自动生成 -> 最终命中 -> 中文解释 -> JSON 报告 -> API / SSE
```

本轮要让 V6OP 后端可以通过 API 跑一条完整策略链路。

本轮仍不做 UI。

## 2. 当前基础

V6OP-001 已完成数据预热和 `CZSCProducer`。

V6OP-002 已完成 6 个核心能力：

- `WencaiSource`
- `CZSCProducer`
- `SMCProducer`
- `KlineProducer`
- `WaveProducer`
- `LandmineProducer`
- `skill_registry.py`
- `run_core_producers.py`

请先阅读：

```text
F:\v.6\v6-op\docs\claude_v6op\latest_report.md
F:\v.6\v6-op\docs\claude_v6op\current_status.md
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-002_phase1_core_producers_report.md
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-002_codex_review.md
```

Codex 对 V6OP-002 的关键约束必须带入本轮：

1. Fetch Planner 不得依赖问财成功；必须支持全 A 股、手动代码、已解析 scope。
2. Landmine 必须动态读取 `output/current/prefetch_report.json` 的 failed/stale 代码，不再硬编码 V6OP-001 失败列表。
3. SMC `soft_filter` 只能作为调试模式；正式路径默认 `strict`，或必须在结果中清楚标注软过滤。
4. WaveProducer 当前是轻量可运行版；不能把 `no_top -> 放行` 当作强正向命中，阶段 2 中应标为 `weak_signal` 或辅助信号。
5. 报告目录不能被 `.gitignore` 忽略；Claude 报告必须能进 Git。

## 3. 必读文件

```text
F:\v.6\v6-op\v6-op_full_rescue_charter.md
F:\v.6\v6-op\docs\00_v6op_supervision_rules.md
F:\v.6\v6-op\docs\01_asset_audit_and_phase0_plan.md
F:\v.6\v6-op\scripts\skill_registry.py
F:\v.6\v6-op\scripts\run_core_producers.py
F:\v.6\v6-op\scripts\data_prefetch.py
F:\v.6\v6-op\scripts\sources\wencai_source.py
F:\v.6\v6-op\scripts\producers\czsc_producer.py
F:\v.6\v6-op\scripts\producers\smc_producer.py
F:\v.6\v6-op\scripts\producers\kline_producer.py
F:\v.6\v6-op\scripts\producers\wave_producer.py
F:\v.6\v6-op\scripts\producers\landmine_producer.py
F:\v.6\v6\scripts\v6\contracts.py
F:\v.6\v6\scripts\v6\expression_runner.py
F:\v.6\v6\scripts\v6\mask_expression_executor.py
F:\v.6\v6\scripts\v6\mask_store.py
```

V6 文件只能引用或适配，不允许修改。

V5 文件本轮原则上不再需要读；除非确有必要，只读参考，禁止修改。

## 4. 允许修改

只允许修改 / 新增：

```text
F:\v.6\v6-op\*
```

建议新增：

```text
scripts\source_resolver.py
scripts\fetch_planner.py
scripts\strategy_graph_builder.py
scripts\expression_auto_generator.py
scripts\execution_engine.py
scripts\explanation_builder.py
scripts\run_report.py
scripts\v6op_server.py
tests\test_phase2_execution.py
tests\test_v6op_server.py
output\current\execution_result.json
output\current\run_report.json
output\current\run_report.md
```

可以修改阶段 1 Producer 以提供统一 `run()` 接口或补充元数据。

可以修改 `.gitignore`，但必须继续忽略：

```text
.env
.venv/
var/cache/
output/current/*.json
output/current/*.md
```

不得忽略：

```text
docs/claude_v6op/reports/*.md
```

## 5. `.env` 与真实接口规则

V6OP 自己的 `.env` 已可存在。

本轮允许读取：

```text
F:\v.6\v6-op\.env
```

但规则如下：

1. 只有 `source_type=wencai` 时才允许读取问财 key 和访问问财接口。
2. `source_type=manual` / `source_type=all_a` / `source_type=existing_scope` 不得读取或依赖真实 key。
3. 本轮 API 默认示例应使用 `manual` 或 `all_a`，确保无问财也能跑通。
4. 任何 key 值不得进入日志、JSON、Markdown、报告、测试输出。
5. 报告只写变量名，不写变量值。

## 6. 禁止修改

禁止修改：

```text
F:\v.6\v5.10\*
F:\v.6\v6\*
```

禁止：

- 写 UI
- 扩张 V6 workbench
- 做任意 DAG 编辑器
- 将问财设为唯一来源
- 在真实 key 缺失或问财失败时伪造 scope
- 将 SMC soft_filter 作为无标注的生产正向结果
- 将 Wave no_top 放行作为无标注的强正向结果
- 将真实 key 写入 Git 可追踪文件

## 7. 具体任务

### 7.1 `source_resolver.py`

统一处理三类股票来源：

```text
all_a      -> 读取 data/ashare_codes.txt
manual     -> 接收用户代码列表
wencai     -> 调用 WencaiSource，失败时返回 blocked/error，不伪造
```

输出统一：

```text
scope_id
source_type
scope_codes
scope_count
status
error
generated_at
```

### 7.2 `fetch_planner.py`

输入：

```text
scope_codes
selected_skills
skill_registry
```

输出：

```text
prefetch_required
prefetch_plan
prefetch_report
readiness
```

要求：

- 合并 K 线类 Producer 的需求，只预热一次。
- 默认 `lookback_days=365`。
- 如果已有缓存且 limit=50，可复用缓存。
- 读取 `output/current/prefetch_report.json`，并将 failed/stale 情况传给后续结果层。
- 失败率 > 20% 时 `readiness=aborted`；否则 `ready` 或 `partial`。

### 7.3 `strategy_graph_builder.py`

支持 charter 第一阶段固定三种路径：

```text
sequential
parallel_and
simple_hybrid
```

本轮不要做任意 DAG 编辑器。

图节点类型：

- producer
- merge
- exclude

### 7.4 `expression_auto_generator.py`

根据路径和 Producer `hit_semantics` 自动生成 MaskExpression。

要求：

- positive 技能默认 AND / SEQUENCE 组合。
- negative 技能接入 EXCLUDE。
- SMC soft_filter 结果如果被选中，必须在 expression metadata 中标注 `mode=soft_filter`。
- Wave weak signal 如果被选中，必须标注 `signal_strength=weak`。

不要让用户手写表达式。

### 7.5 `execution_engine.py`

输入策略 JSON，完成：

1. resolve source
2. plan fetch
3. prefetch if needed
4. run selected producers
5. build expression
6. run expression
7. build explanations
8. write run report

必须支持一个最小策略：

```json
{
  "source": {"type": "manual", "codes": ["000001.SZ", "000002.SZ", "000063.SZ"]},
  "skills": ["czsc", "kline", "landmine"],
  "path_type": "parallel_and",
  "params": {}
}
```

输出：

```text
output/current/execution_result.json
output/current/run_report.json
output/current/run_report.md
```

### 7.6 `explanation_builder.py`

为最终命中生成中文解释。

每只股票至少包含：

- 命中哪些技能
- 每个技能的中文理由
- 是否用了后复权数据
- 是否受 SMC soft_filter / Wave weak_signal 影响
- 是否有数据缺失或 stale 风险

失败 / 未分析股票必须单列，不混进命中列表。

### 7.7 `run_report.py`

生成前端可渲染 JSON 和中文 Markdown。

必须包含：

- source 摘要
- selected_skills
- path_type
- params
- prefetch_report
- producer_summary
- expression
- final_hit_codes
- explanations
- failed_codes
- stale_codes
- data_coverage
- warnings

### 7.8 `v6op_server.py`

实现本地后端 API。

可以用 Flask，也可以用标准库 HTTP server；优先简单稳定。

必须支持：

```text
POST /api/run
GET  /api/result
GET  /api/stream
GET  /api/health
```

`POST /api/run`：

- 接收策略 JSON
- 启动一次同步或后台执行
- 返回 run_id 和初步状态

`GET /api/result`：

- 返回最近一次 `execution_result.json`

`GET /api/stream`：

- SSE 或等价实时日志
- 如果实现困难，可以先提供可轮询事件列表，但报告必须说明

`GET /api/health`：

- 返回 Python 版本、V6OP 路径、关键文件是否存在、是否存在 `.env` 但不返回变量值

## 8. 验收命令

优先执行：

```powershell
cd F:\v.6\v6-op
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts\execution_engine.py --demo manual
.venv\Scripts\python.exe scripts\v6op_server.py --self-test
```

如果 server 需要单独启动，请报告可用命令和本地 URL。

建议本地 URL：

```text
http://127.0.0.1:8876
```

如果端口占用，自动换 8877 / 8878，并写入报告。

## 9. 输出要求

必须更新：

```text
docs\claude_v6op\latest_report.md
docs\claude_v6op\current_status.md
```

必须新增：

```text
docs\claude_v6op\reports\V6OP-003_phase2_fetch_planner_execution_api_report.md
```

注意：

`latest_report.md` 顶部给用户看的最终回复，必须和聊天窗口最终回复一致或等价。若本轮只有一个总报告，就以 `latest_report.md` 为唯一总报告入口。

## 10. 报告必须说明

- 改了哪些文件
- 是否读取 `.env`
- 是否真实访问问财接口
- 是否访问 baostock / akshare / yfinance
- 是否修改 V5.10 / V6
- API 是否可启动
- `POST /api/run` 是否跑通
- SSE 是否真实实现；如果没有，实现了什么等价能力
- 测试命令和结果
- 需要 v6-op 架构师审阅的 3-5 点
- 下一步建议

## 11. 完成后回复

Claude 聊天窗口短回复：

```text
Claude 已完成 V6OP-003 阶段 2 Fetch Planner + 执行引擎 + 后端 API。

报告已写入：
- docs/claude_v6op/latest_report.md
- docs/claude_v6op/current_status.md
- docs/claude_v6op/reports/V6OP-003_phase2_fetch_planner_execution_api_report.md

测试：
- <命令>：<结果>

API：
- health：可用/不可用
- run：可用/不可用
- stream：SSE/轮询/未实现

真实外部接口：
- 问财：是/否
- 行情源：是/否

是否修改 V5.10 / V6：否

需要 v6-op 架构师审阅：
- ...
```

