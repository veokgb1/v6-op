# V6OP-004 Codex 架构审阅报告

> 审阅角色：v6-op 架构师（Codex）  
> 审阅时间：2026-05-05  
> 对象：Claude `V6OP-004_phase3_single_page_console_report.md`

## 1. 结论

V6OP-004 的“单页操盘台”主体可以通过：页面入口、三栏布局、手动策略提交、API 轮询、结果渲染、readiness/SMC/Wave 风险标注都已经形成第一版可用闭环。

但它还不能算 charter 阶段 3 的完整验收闭合。当前缺口主要不是页面能不能打开，而是：

1. 技能参数面板未完整实现：目前前端只暴露 SMC mode，未按 `skill_registry.py` 展开 6 个核心技能的默认参数与可修改输入。
2. 运行归档未闭合：当前只写 `output/current/*`，未按 charter 对象接力要求把每次运行写入 `output/runs/<run_id>/`。
3. 问财真实链路未在 Phase 3 验证：报告明确本轮只跑 manual demo，问财 UI 有入口，但真实 API 路径需要下一轮做 key-safe smoke。
4. `/api/stream` 继续采用 JSON 轮询，本阶段可接受；但前端按数组长度追踪事件，长日志下可能跳过中间事件，建议后续加 `?since=N`。
5. 移动端只做了 CSS 折叠，未做真实浏览器/移动视口验证。

## 2. Codex 已执行验证

```powershell
cd F:\v.6\v6-op
node --check web\app.js
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts\v6op_server.py --self-test --port 8878
```

结果：

- `node --check web\app.js`：通过。本机实际有 Node.js，Claude 报告里的“无 Node.js”不再成立。
- `pytest -q`：162 passed，1696 warnings。warnings 来自 CZSC 第三方 deprecated 函数，不阻断本阶段。
- `v6op_server.py --self-test --port 8878`：15 通过 / 0 失败。

## 3. Codex 已做的小修补

文件：

- `scripts/v6op_server.py`
- `tests/test_phase3_web_assets.py`

修补内容：

- 将 `_serve_static()` 的路径边界判断从字符串 `startswith()` 改为 `Path.relative_to()`。
- 对 URL path 做 `unquote()` 和反斜杠归一化，避免 Windows 路径形态绕过。
- 增加 `web2` 前缀兄弟目录绕过测试，防止 `/../web2/...` 被误认为仍在 `web/` 下。

修补后新增 1 条测试，前端资产测试从 42 条变为 43 条，全量测试从 161 条变为 162 条。

## 4. 对 Claude 报告中 5 个问题的回答

1. 路径穿越防护：已由 Codex 小修补解决，并加测试。
2. JS 语法验证：本机有 Node.js，已用 `node --check web\app.js` 通过。
3. `/api/stream` 事件截断：保留为下一轮验收闭合项，建议实现 `?since=N`，但不作为 V6OP-004 阻断项。
4. self-test 依赖已有缓存：接受为当前 demo 约束；正式验收仍应补一个“空 current 目录首次运行”的边界说明或测试。
5. 移动端布局验证：保留为下一轮浏览器 smoke，不作为当前阻断。

## 5. 对照大纲的进度判断

已完成：

- 阶段 0：数据引擎 + K 线预热 + CZSCProducer。
- 阶段 1：6 个核心 Producer 接通。
- 阶段 2：Fetch Planner + 执行引擎 + 后端 API。
- 阶段 3：单页操盘台第一版可用。

仍需闭合后才能宣布“第一阶段完成”：

- 参数面板：每个核心技能有默认参数、可修改、会进入策略 JSON、会影响 Producer、会写入报告。
- 运行归档：每次 run 保留独立记录，不只覆盖 `output/current`。
- 问财真实入口：在不泄露 key 的前提下做一次小规模真实 smoke 或给出可复现的失败原因。

## 6. 下一步建议

下一条 Claude 指令不进入 Phase 4，不加新能力，命名为：

```text
V6OP-005 阶段 3 验收闭合：参数面板 + 运行归档 + 问财 smoke
```

目标是补齐 charter 阶段 3/第十三节验收缺口，然后再做最终总验收。

