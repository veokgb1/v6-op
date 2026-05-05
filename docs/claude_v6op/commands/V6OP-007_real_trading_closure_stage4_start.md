# V6OP-007 真实操盘闭合与阶段 4 启动包

> 下发角色：v6-op 架构师（Codex）
> 执行对象：Claude
> 任务性质：大阶段推进 + 强验收闸门
> 时间：2026-05-05

---

## 0. 本轮总判断

V6OP-006 + V6OP-006b 已经把主链路和可信运行层拉回 charter。现在不要继续停在小补丁里。

本轮直接推进 V6OP-007：用真实端到端运行闭合阶段 1-3，并启动阶段 4 中最必要的两件事：

1. 问财来源正式进入操盘台主链路；
2. 全 A 扫描加入运行保护。

这是“大步推进”，但不是无边界扩张。

---

## 1. 必读文件

开始前必须阅读：

```text
F:\v.6\v6-op\v6-op_full_rescue_charter.md
F:\v.6\v6-op\docs\claude_v6op\current_status.md
F:\v.6\v6-op\docs\claude_v6op\latest_report.md
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-006_completion_report.md
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-006b_trustworthy_runtime_report.md
```

重点代码先读：

```text
scripts/source_resolver.py
scripts/fetch_planner.py
scripts/data_prefetch.py
scripts/execution_engine.py
scripts/v6op_server.py
scripts/run_report.py
web/index.html
web/app.js
web/styles.css
tests/
```

---

## 2. 本轮必须完成的六件事

### 2.1 真实端到端验收矩阵

必须做真实运行，不准只跑 fixture，不准只写静态测试。

至少完成：

```text
manual 来源：
- 10-30 只真实 A 股；
- parallel_and 路径；
- sequential 路径；
- simple_hybrid 路径；
- 自动预热；
- 本地分析只读缓存；
- run_report.md 中文可读；
- 页面能显示结果并展开单股证据。

wencai 来源：
- 输入自然语言策略；
- limit 5-20；
- 只读当前 v6-op 环境变量或当前 v6-op .env；
- 不复制 V5/V6 .env；
- 不打印、不写入、不泄露 key；
- 成功时必须进入 Fetch Planner → 自动预热 → READ_CACHE_ONLY 分析 → 输出结果；
- 如果 key 缺失、额度不足或接口失败，必须中文透明提示失败原因，不准伪造成成功。
```

要求在报告中列出每个演示：

```text
source_type
query/codes（wencai query 可写，key 不可写）
limit
path_type
skills
run_id
final_hit_count
readiness
prefetch_report 自洽性
run_report.md 路径
页面/接口是否可读
```

---

### 2.2 问财来源正式接入操盘台

当前问财不能只停留在 smoke。它必须成为页面来源区的一种正式来源。

要求：

- 单页操盘台来源区加入“问财条件”输入；
- 用户可输入中文自然语言策略；
- limit 默认 50 或 100，页面允许改小；
- 后端 `/api/run` 能接收 `source.type = "wencai"`、`query`、`limit`；
- 问财结果进入 `scope_codes`，后续必须走同一条 Fetch Planner → data_prefetch → READ_CACHE_ONLY Producer → report 主链路；
- 失败时页面显示清楚中文提示；
- 不要打印 key；
- 不要把问财失败伪造成空结果成功；
- 不新增页面。

如果当前已有问财模块或 smoke 入口，优先复用现有实现，不要另起一套。

---

### 2.3 全 A 扫描保护

全 A 来源不能无提示直接跑重技能。

必须加入保护：

- 超过阈值时前端给中文风险提示；
- 建议阈值：300 只提醒，500 只以上需要用户确认；
- API 层也要保护，不能只靠前端；
- 用户未确认时，`/api/run` 应拒绝或返回需要确认的中文状态；
- 用户确认后才允许继续；
- 报告中记录本次扫描规模、是否触发保护、是否用户确认。

页面提示要轻松可懂，不要写晦涩术语。可以保留小号英文补充，但主文案必须中文。

---

### 2.4 V5 风格可读报告增强

`run_report.md` 不能只是技术 JSON 的 Markdown 版。它必须更像用户能直接复制阅读的操盘报告。

必须包含：

```text
一、本次策略摘要
二、股票来源
三、路径类型与技能组合
四、关键参数
五、数据准备阶段
六、本地分析阶段
七、命中股票列表
八、单股中文证据
九、排除原因 / 负向技能命中
十、失败代码 / 旧缓存 / 未分析代码
十一、风险与边界声明
十二、运行产物路径
```

要求：

- 中文为主；
- 每只命中股票至少有代码、命中技能、中文原因；
- 被排除的股票如能追踪，写出排除原因；
- 数据准备阶段和本地分析阶段继续分开写；
- 不泄露 key；
- 不把失败掩盖成成功。

---

### 2.5 单页操盘台可用性增强

仍然不新增页面，只增强当前单页。

必须完成：

- 来源区支持 manual / wencai / all_a；
- 所有主要面板、按钮、提示、状态文字必须中文优先；
- 中文必须轻松可懂，避免生硬术语堆叠；
- 英文专业词可以作为小字或括号补充；
- 问财输入框在来源区；
- 全 A 风险提示在运行前出现；
- 结果区报告摘要更清楚；
- 命中证据展开更容易读；
- 失败、旧缓存、未分析代码单独显示；
- 参数区保持 V5 左侧面板风格。

不要做营销页，不要做新页面，不要重写前端架构。

---

### 2.6 阶段状态修正

完成后必须明确判断：

```text
阶段 1-3 是否真实验收闭合；
阶段 4 是否已启动；
阶段 4 哪些部分完成，哪些仍未完成。
```

不能只写“测试通过”。必须用真实端到端结果说话。

---

## 3. 本轮禁止事项

禁止：

- 接入 21 个灰色技能；
- 做任意 DAG 编辑器；
- 新增页面；
- 开放全部 12 种表达式操作符；
- 重写系统架构；
- 修改 `F:\v.6\v5.10`；
- 修改 `F:\v.6\v6`；
- 复制 `.env` / `.venv`；
- 打印、写入、泄露任何 API key；
- 用 fixture 冒充真实运行；
- 把 wencai 失败伪造成成功；
- 把 all_a 大扫描无保护直接放行。

---

## 4. 允许修改范围

只允许在 `F:\v.6\v6-op` 内修改。

优先可能涉及：

```text
scripts/source_resolver.py
scripts/execution_engine.py
scripts/v6op_server.py
scripts/run_report.py
web/index.html
web/app.js
web/styles.css
tests/
docs/claude_v6op/
```

如修改其他文件，必须在报告中说明原因。

---

## 5. 必须新增或更新测试

至少覆盖：

1. `/api/run` 支持 `source.type = "wencai"` 的请求结构。
2. wencai key-safe：测试不得打印或写出 key。
3. wencai 失败时返回中文错误，不伪造成成功。
4. all_a 超阈值时 API 层需要确认。
5. all_a 用户确认后才允许继续。
6. `run_report.md` 包含 V5 风格中文报告章节。
7. 前端来源区包含 manual / wencai / all_a。
8. 前端主要按钮和提示中文优先。
9. 命中证据、失败、旧缓存、未分析代码可以独立显示。
10. 三种 path_type 的真实或半真实端到端测试记录不互相污染。

测试可以用 mock 验证失败路径和 key-safe，但最终报告必须包含真实端到端演示。不能用 fixture 冒充最终业务结果。

---

## 6. 必须执行的验收命令

必须执行：

```powershell
cd F:\v.6\v6-op
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts\v6op_server.py --self-test --port 8878
node --check web\app.js
```

必须执行端到端演示：

```text
manual + parallel_and
manual + sequential
manual + simple_hybrid
wencai + 至少一种 path_type（如果 key 可用）
all_a 保护触发演示
```

如果 wencai key 不可用：

- 不得阻塞整个 V6OP-007；
- 但必须把 wencai 标记为“页面/API 已接入，真实源演示因 key/接口失败未通过”；
- 必须写清失败原因；
- 不准写“wencai 真实演示通过”。

---

## 7. 输出要求

完成后必须写唯一总报告：

```text
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-007_real_trading_closure_stage4_start_report.md
```

同时更新：

```text
F:\v.6\v6-op\docs\claude_v6op\latest_report.md
F:\v.6\v6-op\docs\claude_v6op\current_status.md
```

报告必须包含：

1. V6OP-007 完成 / 未完成。
2. 真实 manual 三路径演示结果。
3. 真实 wencai 演示结果，或脱敏失败原因。
4. all_a 保护演示结果。
5. 页面改动说明。
6. V5 风格 `run_report.md` 样例路径。
7. 修改文件清单。
8. 测试命令和结果。
9. 阶段 1-3 是否闭合。
10. 阶段 4 已启动范围。
11. 未完成项和风险。
12. 是否修改 V5.10 / V6：必须明确写“没有”。
13. 是否读取/泄露密钥：必须明确写“没有泄露”；如读取当前 v6-op 环境变量，只能写“读取环境状态”，不能写 key 值。
14. 是否使用 fixture 冒充真实结果：必须明确写清。

---

## 8. 完成后回复格式

```text
V6OP-007 已完成 / 未完成

真实操盘验收：
- manual + parallel_and:
- manual + sequential:
- manual + simple_hybrid:
- wencai:
- all_a 保护:

阶段判断：
- 阶段 1-3:
- 阶段 4:

验收：
- pytest:
- self-test:
- node --check:
- run_report.md 样例:

安全：
- V5.10/V6 是否修改:
- 密钥是否泄露:
- fixture 是否冒充真实结果:

报告路径：
- ...

风险：
- ...
```
