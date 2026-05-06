# V6OP-P2-003 第二阶段过程：验收差距修正命令

> 指令发出：Codex 秘书 / V6OP 架构协调  
> 执行对象：Claude / V6OP 代码师  
> 工作目录：`F:\v.6\v6-op`  
> 本轮性质：第二阶段 P2-002 验收差距修正，不是重新开大范围  
> 命令文件：`F:\v.6\v6-op\docs\claude_v6op\commands\V6OP-P2-003_phase2_process_acceptance_gap_fix.md`  
> 报告路径：`F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-P2-003_phase2_process_acceptance_gap_fix_report.md`

---

## 0. 先声明

Claude 代码师，你好。

Codex 秘书已阅读 `V6OP-P2-002_phase2_process_formal_rebuild_report.md`，并独立运行了基础检查。

本轮不是重新执行 G1-G8，也不是扩大第二阶段范围。  
本轮只修正 P2-002 中已经暴露出的验收差距和报告口径问题。

不要把本轮写成“第二阶段最终完成”。本轮完成后，输出差距修正报告，等待用户和 Codex 秘书复核。

---

## 1. 先读文件

请读取：

```text
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-P2-002_phase2_process_formal_rebuild_report.md
F:\v.6\v6-op\docs\claude_v6op\commands\V6OP-P2-002_phase2_process_formal_rebuild.md
F:\v.6\v6-op\v6-op_phase2_upgrade_charter.md
```

重点查看当前工作区已改文件：

```text
F:\v.6\v6-op\web\app.js
F:\v.6\v6-op\web\index.html
F:\v.6\v6-op\scripts\v6op_server.py
F:\v.6\v6-op\scripts\explanation_builder.py
F:\v.6\v6-op\scripts\execution_engine.py
F:\v.6\v6-op\scripts\expression_auto_generator.py
F:\v.6\v6-op\scripts\run_report.py
```

---

## 2. 必须修正的问题

### 问题 1：五层解释前端渲染会显示 `[object Object]`

事实：

- `scripts/explanation_builder.py` 的 `build_global_explanation()` 返回的 `source_layer/data_layer/skill_layer/path_layer/report_layer` 是 dict。
- `web/app.js` 的 `renderGlobalExplanation()` 直接执行：

```js
esc(expl[key])
```

这会把对象渲染成 `[object Object]`，用户看不到真正解释。

要求：

- 修改 `renderGlobalExplanation()`，按层把对象字段渲染成用户能读懂的文字或小表格。
- 至少展示每层的核心字段：
  - source_layer：source_type、actual_count、count_note、suggestion。
  - data_layer：readiness、cached、failed、stale、suggestion。
  - skill_layer：first_zero_skill、每个技能的 input_count/hit_count/miss_count。
  - path_layer：path_type、first_zero_step、suggestion。
  - report_layer：final_hit_count、suggestion。
- 命中 0 时，`why_zero` 必须醒目展示。

### 问题 2：问财授权检查前后端字段不一致

事实：

- `scripts/v6op_server.py` 的 `/api/wencai/status` 返回：

```text
env_key_present
auth_mechanism
status
pywencai_installed
```

- `web/app.js` 的 `checkWencaiAuth()` 读取：

```text
env_key_set
auth_note
```

这会导致页面显示错误或缺少说明。

要求：

- 统一字段名。建议前端改为读取 `env_key_present` 和 `auth_mechanism`。
- 页面必须显示：
  - pywencai 是否安装。
  - IWENCAI_API_KEY 是否配置。
  - 当前真实认证机制说明。
  - 当前 status。
- 不得把 `IWENCAI_API_KEY` 配置等同于“问财真实授权成功”。

### 问题 3：G8 报告口径不能写成完全完成

事实：

P2-002 报告写 `G8 执行路径统一 ✅`，但同一报告又写：

```text
sequential/simple_hybrid:
expression_spec.executable = False
expression_spec.steps = []
实际执行仍由 execution_engine 中的循环逻辑完成
```

这不能算 G8 完整完成，只能算：

```text
parallel_and 已执行化；
sequential/simple_hybrid 已结构化记录，但尚未由 expression_runner 驱动；
G8 部分完成，有结构缺口。
```

要求：

- 不要求你本轮强行重写 G8。
- 但必须修正报告口径，不得把 G8 写成完整完成。
- 如你能在不破坏缓存假设和测试的前提下继续推进 G8，可小步修；否则明确列为第二阶段未关闭项。

### 问题 4：G5 Data Provenance 不能写成完整完成

事实：

P2-002 报告中 `data_provenance.per_stock = {}`，并写“预留”。

这说明数据血缘只完成了汇总层，没有完成 per-stock 精细血缘。

要求：

- 报告口径改为：

```text
G5 汇总层完成，per-stock 精细血缘未完成。
```

- 如果本轮可以低风险补上 per-stock，请补；如果不能，明确列为未关闭项。

### 问题 5：主操盘台“严格 7 项”口径需要复核

事实：

`web/index.html` 仍保留右侧 `提示词库` tab；中间栏也保留数据就绪、数据标记、本轮取数记录、警告、技能摘要等区块。

这些内容可能可以解释为运行状态区或辅助结果区，但不能简单写“严格只保留 7 项，完全通过”。

要求：

- 复核主操盘台 7 项边界。
- 如果保留这些内容，请在报告中说明它们归属哪一项。
- 如果某些内容应进入管理中心，请移动。
- 不得把明显额外的功能写成“严格 7 项已完全达成”。

### 问题 6：测试报告口径修正

事实：

Codex 独立执行：

```powershell
node --check web/app.js
```

通过。

但：

```powershell
node --check web/*.js
```

在 PowerShell 下不会展开通配符，报 `Cannot find module 'F:\v.6\v6-op\web\*.js'`。

Codex 用正确 PowerShell 写法补跑：

```powershell
Get-ChildItem -LiteralPath web -Filter *.js | ForEach-Object { node --check $_.FullName }
```

通过。

要求：

- 报告中不要写 `node --check web/*.js` 通过。
- 改写为真实可执行命令和结果。

---

## 3. 本轮允许改什么

允许改：

```text
web/app.js
web/index.html
web/styles.css
scripts/v6op_server.py
scripts/explanation_builder.py
scripts/execution_engine.py
scripts/expression_auto_generator.py
scripts/run_report.py
docs/claude_v6op/reports/V6OP-P2-003_phase2_process_acceptance_gap_fix_report.md
```

如确实需要改其他文件，必须在报告中说明原因。

---

## 4. 本轮不要做什么

禁止：

- 不要重新大范围改写 G1-G8。
- 不要引入新功能。
- 不要删除 P2-002 已通过的功能。
- 不要修改 `F:\v.6\v5.10`。
- 不要修改 `F:\v.6\v6`。
- 不要泄露 `.env` 或 API key。
- 不要把未完成项写成完成。

---

## 5. 必跑检查

请运行：

```powershell
node --check web/app.js
Get-ChildItem -LiteralPath web -Filter *.js | ForEach-Object { node --check $_.FullName }
F:\v.6\v6-op\.venv\Scripts\python.exe -m pytest -q
```

如果新增或修改后端 API，请至少做最小 HTTP 或函数级验证，并在报告中写清楚。

---

## 6. 报告要求

报告写入：

```text
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-P2-003_phase2_process_acceptance_gap_fix_report.md
```

报告必须包含：

1. 修复文件清单。
2. 上述 6 个问题逐项处理结果。
3. 哪些是真修复，哪些只是报告口径修正。
4. G1-G8 当前真实状态，不得虚报。
5. 必跑检查命令与结果。
6. 仍未关闭的问题清单。

报告最后签名：

```text
Claude / V6OP 代码师
V6OP-P2-003 第二阶段过程：验收差距修正
```

