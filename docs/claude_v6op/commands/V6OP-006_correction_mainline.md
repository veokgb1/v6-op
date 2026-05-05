# V6OP-006 主链路纠偏返工命令

> 下发角色：v6-op 架构师（Codex）
> 执行对象：Claude
> 任务性质：纠偏返工，不是新增功能
> 时间：2026-05-05

---

## 0. 本轮总要求

本轮不要继续新增功能，不要扩页面，不要接 21 个新技能，不要做 UI 美化，不要引入新架构。

V6OP-005 的中途验收显示：当前骨架已经形成，但有 4 个偏离章程的阻断项，另有 1 个必须同时处理的结果契约问题。V6OP-006 只允许修这些主链路纠偏项。

这次必须把 v6-op 从“看起来像操盘台”拉回“用户点击运行即可真实执行”的主链路。

---

## 1. 必读文件

请先阅读：

```text
F:\v.6\v6-op\v6-op_full_rescue_charter.md
F:\v.6\v6-op\docs\claude_v6op\current_status.md
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-005_codex_review.md
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-005_phase3_acceptance_closure_report.md
```

重点对齐 charter 第五节、第八节、第九节、第十二节、第十三节。

---

## 2. 必须修正的错误签收口径

之前把“正式使用前需手动运行 `data_prefetch.py` 全量预热”作为可接受残余风险，这是错误签收口径。

现在恢复 charter 原始要求：

```text
用户点击 v6-op 页面上的运行按钮后，系统必须自动完成：
股票来源解析 → Fetch Planner → data_prefetch 真实预热 → READ_CACHE_ONLY 本地分析 → 命中结果 → 中文解释。
```

用户不能为了完成一次正常运行而先手动打开命令行跑 `data_prefetch.py`。

---

## 3. 本轮只修 4 个阻断项 + 1 个结果契约问题

### 3.1 阻断项一：运行按钮必须自动触发真实 K 线预热

当前偏差：

`scripts/execution_engine.py` 里写着“本轮 read_cache_only，不实际预热”，缺缓存时只提示用户手动运行 `data_prefetch.py`。

这违反 charter 第十三节第 6 条：

```text
启动运行后，系统先显示“准备数据”进度（真实预热 K 线缓存，非 fixture）。
```

请修正为：

```text
1. resolve source 得到 scope_codes
2. fetch_planner 生成预热计划
3. 如果缺缓存，execution_engine 必须调用 data_prefetch 的程序接口或安全子进程入口执行真实预热
4. 预热完成后重新读取/刷新 prefetch_report
5. 再切换 READ_CACHE_ONLY 运行 Producer
```

要求：

- 不要让 Producer 自己拉网络数据；
- 网络拉取仍集中在 data_prefetch；
- 前端运行按钮触发 `/api/run` 后必须能进入“准备数据”阶段；
- 预热结果必须进入 `execution_result.json`、`run_report.json`、`run_report.md`；
- 如果预热失败率超过阈值，结果应显示 aborted，不得静默继续冒充完整分析；
- 如果用户选择全 A 股且范围很大，必须在报告/日志中明确提示耗时风险；前端可先显示 warning，不要求本轮做复杂弹窗。

验收：

用一个没有完整缓存的小股票池运行 `/api/run`，日志里必须出现真实预热步骤，而不是“请手动运行 data_prefetch.py”。

---

### 3.2 阻断项二：`sequential` 必须是真正顺序漏斗

当前偏差：

`sequential` 实际仍然让所有正向技能吃同一个原始 `scope_codes`，最后再 AND。

这不是真漏斗。

请修正为：

```text
current_scope = 初始 scope_codes
for skill in selected_positive_skills:
    result = producer.run(codes=current_scope, ...)
    current_scope = result.hit_codes
负向技能如排雷，对当前结果执行 EXCLUDE
```

要求：

- 第一个正向技能吃全集；
- 第二个正向技能吃第一个技能的 `hit_codes`；
- 第三个正向技能吃第二个技能的 `hit_codes`；
- 如果中间结果为空，后续正向技能可跳过或对空集运行，但报告必须说明“上游已为空”；
- `producer_summary` 必须能看出每一步输入数量和输出数量；
- 用户仍然不需要理解 MaskExpression。

验收：

构造一个测试或 demo，证明 `sequential` 中第二个技能收到的代码数量等于第一个技能的 `hit_count`，不是原始全集数量。

---

### 3.3 阻断项三：`simple_hybrid` 必须回到 charter 定义

当前偏差：

`simple_hybrid` 被实现成了 `K_OF_N`。

这不是 charter 定义。第一阶段不做 K_OF_N。

请修正为：

```text
simple_hybrid = 前 N 个正向技能对同一全集并线运行 → AND 交集 → 后续正向技能按顺序继续过滤 → 最后 EXCLUDE 负向技能
```

本轮建议采用一个明确、简单的第一阶段规则：

```text
如果正向技能数量 >= 3：
    前 2 个正向技能并线取交集
    第 3 个及之后的正向技能顺序过滤
如果正向技能数量 <= 2：
    simple_hybrid 等价于 parallel_and
负向技能始终最后 EXCLUDE
```

要求：

- 删除或隐藏第一阶段 UI/报告中的 `K_OF_N` 语义；
- 不再讨论 Wave 半票；
- 不开放任意 DAG；
- 报告里用中文说明：“简单混合：前两个技能并线交集，后续技能顺序过滤”。

验收：

选择 `czsc + smc + kline + landmine` 且 path_type=`simple_hybrid` 时，执行语义必须是：

```text
AND(czsc(scope), smc(scope)) → 中间结果 → kline(中间结果) → EXCLUDE(landmine)
```

而不是 `K_OF_N(czsc, smc, kline)`。

---

### 3.4 阻断项四：前端必须支持单股证据展开

当前偏差：

`execution_result.json` 里已有 evidence，但 `web/index.html/app.js` 的命中列表没有单股展开。

这不满足 charter 第五节、第十二节：

```text
点开单只股票展开完整证据，不跳转 explain 页面。
```

请修正为：

- 命中列表每只股票可以展开/折叠；
- 展开后显示：
  - 股票代码和名称（如有）；
  - 命中哪些技能；
  - 每个技能的中文信号说明；
  - 本次相关参数摘要；
  - 是否使用旧缓存/是否有数据风险；
- 不跳转新页面；
- 不新增独立 explain 页面。

验收：

打开页面完成一次运行后，点击任意命中股票，浏览器里能看到中文证据说明，而不是只能在 JSON 文件里看到。

---

### 3.5 必须同时修：前端/API 结果契约对齐

当前风险：

`/api/result` 当前返回的是 `execution_result.json`。但前端 `web/app.js` 的部分渲染逻辑更像是在按 `run_report.json` 的扁平字段读取，例如把 `r.explanations` 当数组使用，而 `execution_result.json` 中 `explanations` 是对象，真正命中列表在 `explanations.hits`。

这会造成一种危险状态：

```text
后端文件里有结果
但页面显示不完整、证据无法展开、覆盖摘要字段对不上
```

请修正为明确稳定的前端结果契约。可以二选一：

方案 A（推荐）：

```text
GET /api/result 返回前端专用结果对象，结构对齐 run_report.json：
- final_hit_codes
- final_hit_count
- explanations: list
- failed_codes
- stale_codes
- data_coverage
- producer_summary
- expression
- run_id
```

方案 B：

```text
保持 /api/result 返回 execution_result.json，但前端必须严格按 execution_result.json 的真实结构读取：
- explanations.hits
- explanations.failed
- fetch_plan.failed_codes
- fetch_plan.stale_codes
- producer_results
```

要求：

- 不要让前端猜字段；
- 不要同时混用两个结构；
- 报告里必须写清 `/api/result` 的最终契约；
- 测试必须覆盖前端读取字段或 API 返回字段；
- 证据展开必须基于这个契约实现。

验收：

一次 `/api/run` 完成后，页面能正常显示命中列表、失败列表、数据覆盖、Producer 摘要，并能展开单股证据。

---

## 4. 本轮禁止事项

本轮禁止：

- 新增页面；
- 接入 21 个灰色技能；
- 做任意 DAG 编辑器；
- 开放全部 12 种表达式操作符；
- 做新的报告组体系；
- 引入 Airflow / Dagster / Prefect / Bazel 等框架；
- 修改 `F:\v.6\v5.10`；
- 复制 `.env` / `.venv`；
- 打印、写入、泄露任何 API key；
- 用 fixture 冒充真实运行。

---

## 5. 允许修改范围

只允许在 `F:\v.6\v6-op` 内修改。

优先可能涉及：

```text
scripts/execution_engine.py
scripts/fetch_planner.py
scripts/data_prefetch.py
scripts/strategy_graph_builder.py
scripts/expression_auto_generator.py
scripts/run_report.py
scripts/v6op_server.py
web/app.js
web/index.html
web/styles.css
tests/
docs/claude_v6op/
```

如果需要修改其他文件，必须在报告中说明原因。

---

## 6. 必须新增或更新的测试

请至少补以下测试：

1. `execution_engine` 在缺缓存时会触发预热，而不是只提示手动预热。
2. `sequential` 第二个正向技能的输入 scope 来自第一个技能的 `hit_codes`。
3. `simple_hybrid` 不再生成或执行 `K_OF_N`，而是“前 2 个并线 AND + 后续顺序”。
4. `/api/result` 与前端读取字段契约一致，不再混用 `execution_result` 和 `run_report` 的结构。
5. 前端 JS/HTML 中存在单股证据展开逻辑，并能渲染 evidence 字段。

测试可以使用小样本和 mock/stub 来验证语义，但最终报告必须说明真实预热演练情况。不要用 fixture 冒充最终业务结果。

---

## 7. 验收命令

必须执行：

```powershell
cd F:\v.6\v6-op
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts\v6op_server.py --self-test --port 8878
```

还必须执行至少一次小股票池端到端运行，证明：

```text
POST /api/run
→ 自动预热
→ READ_CACHE_ONLY 分析
→ 输出命中/失败/旧缓存摘要
→ 页面可展开单股证据
```

如果真实网络或数据源阻断，必须写清阻断原因、失败阶段、是否安全降级，不允许把阻断说成通过。

---

## 8. 输出要求

完成后必须更新：

```text
docs/claude_v6op/reports/V6OP-006_correction_mainline_report.md
docs/claude_v6op/latest_report.md
docs/claude_v6op/current_status.md
```

报告格式：

1. 阶段编号：V6OP-006
2. 完成内容
3. 修改文件清单
4. 四个阻断项逐条修复说明
5. `/api/result` 前端结果契约说明
6. 执行语义说明：
   - sequential 当前如何跑；
   - simple_hybrid 当前如何跑；
   - prefetch 当前如何触发。
7. 验收命令和结果
8. 端到端运行样例
9. 未完成项
10. 是否修改 V5.10：必须明确写“没有”
11. 是否读取/泄露密钥：必须明确写“没有泄露”
12. 是否使用 fixture 冒充真实结果：必须明确写清

---

## 9. 完成后回复格式

请回复：

```text
V6OP-006 已完成 / 未完成

五项纠偏：
1. 自动预热：完成情况
2. 顺序漏斗：完成情况
3. 简单混合：完成情况
4. 单股证据展开：完成情况
5. 前端/API 结果契约：完成情况

验收：
- pytest:
- self-test:
- 端到端运行:

报告路径：
- ...

风险：
- ...
```
