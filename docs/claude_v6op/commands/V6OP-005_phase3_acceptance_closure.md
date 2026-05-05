# V6OP-005 阶段 3 验收闭合：参数面板 + 运行归档 + 问财 smoke

> 下发角色：v6-op 架构师（Codex）  
> 执行角色：Claude  
> 状态：ready  
> 日期：2026-05-05

## 1. 目标

本轮不是 Phase 4，不扩张新功能，不新建页面。

目标只有一个：把 V6OP-004 已完成的单页操盘台，对齐 charter 阶段 3 和第十三节验收标准中尚未闭合的点。

重点闭合：

```text
技能参数面板 -> 策略 JSON -> Producer 参数生效 -> 报告记录
每次运行归档 -> output/runs/<run_id>/...
问财真实入口 smoke -> key-safe 验证或给出清楚失败原因
```

## 2. 必读文件

请先读：

```text
F:\v.6\v6-op\v6-op_full_rescue_charter.md
F:\v.6\v6-op\docs\claude_v6op\latest_report.md
F:\v.6\v6-op\docs\claude_v6op\current_status.md
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-004_phase3_single_page_console_report.md
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-004_codex_review.md
F:\v.6\v6-op\scripts\skill_registry.py
F:\v.6\v6-op\scripts\execution_engine.py
F:\v.6\v6-op\scripts\run_report.py
F:\v.6\v6-op\scripts\v6op_server.py
F:\v.6\v6-op\web\index.html
F:\v.6\v6-op\web\app.js
F:\v.6\v6-op\web\styles.css
```

重点对照 charter：

- 第十一节：参数面板必须写进验收标准。
- 第十二节：报告输出。
- 第十三节：第一阶段验收标准。
- 阶段 3：单页操盘台前端。

## 3. 允许修改

只允许修改 / 新增：

```text
F:\v.6\v6-op\*
```

建议涉及：

```text
web\index.html
web\app.js
web\styles.css
scripts\v6op_server.py
scripts\execution_engine.py
scripts\run_report.py
tests\test_phase3_web_assets.py
tests\test_phase2_execution.py
tests\test_v6op_server.py
```

禁止修改：

```text
F:\v.6\v5.10\*
F:\v.6\v6\*
```

## 4. 必做任务

### 4.1 参数面板闭合

当前问题：前端只暴露了 SMC mode，没有完整展示 6 个核心技能参数。

中文表达硬要求：

- 参数面板、按钮、标签、提示、告警、空状态必须以中文为主。
- 中文必须轻松、直接、可理解，不要把内部工程术语直接甩给用户。
- 英文技术名可以保留，但只作为小字、括号、等宽补充或 tooltip，例如 `parallel_and`、`strict`、`soft_filter`。
- 专业英文名如果不适合翻译，可以保留，但附近必须有中文解释。
- 不要让用户在界面上必须理解 Mask、ScopeRef、ExecutionDraft 等 V6 内部术语。

请实现：

1. 6 个核心技能的参数面板。
2. 默认值来自或对齐 `scripts\skill_registry.py`。
3. 参数只在对应技能被勾选时进入策略 JSON。
4. 前端提交的参数必须能进入 `execution_engine.py`，并传给对应 Producer。
5. 不要继续使用一个全局 `signal_bars` 覆盖所有技能；需要支持每个技能自己的参数。
6. 参数值必须写入 `execution_result.json` / `run_report.json` / `run_report.md`。

推荐策略 JSON 结构：

```json
{
  "source": {"type": "manual", "codes": ["000001.SZ"]},
  "skills": ["czsc", "smc", "kline", "landmine"],
  "path_type": "parallel_and",
  "params": {
    "skills": {
      "czsc": {"signal_bars": 5, "buy_type": "all", "days": 365},
      "smc": {"signal_bars": 15, "mode": "strict", "days": 365},
      "kline": {"signal_bars": 5, "body_pct": 0.1, "shadow_ratio": 2.0, "days": 365},
      "wave": {"signal_bars": 20, "days": 365},
      "landmine": {"min_bars": 60, "days": 365}
    }
  }
}
```

可以兼容旧的 flat params，但新 UI 必须发 skill-scoped params。

### 4.2 运行归档闭合

当前问题：只写 `output/current/*`，没有每次运行独立归档。

请实现：

```text
output/current/execution_result.json
output/current/run_report.json
output/current/run_report.md

output/runs/<run_id>/execution_result.json
output/runs/<run_id>/run_report.json
output/runs/<run_id>/run_report.md
```

要求：

- `output/current/*` 仍保留，作为最新结果。
- `output/runs/<run_id>/...` 作为历史归档。
- `.gitignore` 可以继续忽略 `output/current` 和 `output/runs` 的生成结果。
- 报告必须说明 run archive 路径。

### 4.3 问财真实入口 smoke

本轮需要验证问财真实入口，但必须 key-safe：

1. 只在 `source_type=wencai` 时读取 `.env`。
2. 不允许打印或写入任何 key 值。
3. 使用很小 limit，例如 5 或 10。
4. 如果真实接口成功，报告写“成功返回 N 只代码”。
5. 如果真实接口失败，报告写清楚已脱敏错误类型、状态和可复现命令，不要伪造 scope。

建议命令或等价 Python 调用：

```powershell
cd F:\v.6\v6-op
.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'scripts'); import source_resolver; print(source_resolver.resolve('wencai', wencai_query='净利润增长', wencai_limit=5)['status'])"
```

如果你需要用更可靠的测试方式，可以调整，但报告不能泄露 key。

### 4.4 `/api/stream?since=N` 可选但建议

Codex 发现当前前端用 `_lastEventCount` 对最近 50 条数组做 slice，长日志可能跳过中间事件。

如果实现成本小，请补：

```text
GET /api/stream?since=<event_index>
```

并让返回体包含：

```json
{
  "event_count": 123,
  "events": [...]
}
```

前端使用服务器的 `event_count` 更新游标。

如果本轮时间紧，可以不做，但必须在报告里说明仍为后续项。

### 4.5 浏览器/静态验证

必须补足：

```powershell
node --check web\app.js
```

并启动服务验证：

```text
GET /
GET /styles.css
GET /app.js
GET /api/health
```

如果能做移动宽度 smoke，请做；如果不能，报告写清楚未做真实移动设备验证。

还必须检查中文界面表达：

- 按钮文案是否为中文，例如“运行”“停止/重试”“查看报告”等，而不是只显示英文动词。
- 参数说明是否能让非工程用户理解。
- 英文枚举值旁边是否有中文解释。
- tooltip 或小字说明是否覆盖了保留英文技术名。

## 5. 禁止事项

禁止：

- 新建 workbench 多页面。
- 新建 explain/report/closure/debug 独立页面。
- 做 DAG 编辑器。
- 开 Phase 4 的 21 张技能扩张。
- 开 12 种表达式操作符 UI。
- 把真实 key 写进日志、JSON、Markdown、测试输出或 Git 可追踪文件。
- 修改 V5.10 / V6。
- 用 mock 假装问财成功。

## 6. 验收命令

必须执行：

```powershell
cd F:\v.6\v6-op
node --check web\app.js
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts\execution_engine.py --demo manual
.venv\Scripts\python.exe scripts\v6op_server.py --self-test --port 8878
```

还需要补一个参数生效验证，方式不限，但报告必须说明：

```text
修改某个技能参数后，execution_result/run_report 中能看到该参数；
对应 Producer 的 params 也反映该参数。
```

## 7. 报告落点

必须更新：

```text
docs\claude_v6op\latest_report.md
docs\claude_v6op\current_status.md
```

必须新增：

```text
docs\claude_v6op\reports\V6OP-005_phase3_acceptance_closure_report.md
```

`latest_report.md` 顶部给用户看的最终回复，必须和聊天窗口最终回复一致或等价。

## 8. 报告必须说明

- 改了哪些文件。
- 参数面板支持了哪些技能、哪些参数。
- 参数是否进入策略 JSON、Producer、报告。
- `output/runs/<run_id>/` 是否生成。
- 是否真实访问问财接口；成功/失败原因是什么。
- 是否读取 `.env`；必须只报告变量名或是否存在，不报告值。
- 是否修改 V5.10 / V6。
- `node --check`、pytest、execution demo、server self-test 结果。
- 前端中文表达是否符合要求；如仍保留英文，说明对应中文解释在哪里。
- `/api/stream?since=N` 是否实现。
- 仍未闭合的风险点，不超过 5 条。

## 9. 完成后回复

Claude 聊天窗口短回复：

```text
Claude 已完成 V6OP-005 阶段 3 验收闭合。

报告已写入：
- docs/claude_v6op/latest_report.md
- docs/claude_v6op/current_status.md
- docs/claude_v6op/reports/V6OP-005_phase3_acceptance_closure_report.md

参数面板：
- <已支持内容>

运行归档：
- <output/runs 路径>

问财 smoke：
- 成功/失败（脱敏说明）

测试：
- node --check web/app.js：<结果>
- pytest -q：<结果>
- execution_engine.py --demo manual：<结果>
- v6op_server.py --self-test --port 8878：<结果>

是否修改 V5.10 / V6：否

需要 v6-op 架构师审阅：
- ...
```
