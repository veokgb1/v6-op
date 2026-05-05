# V6OP-004 阶段 3 单页操盘台前端

> 下发角色：v6-op 架构师（Codex）
> 执行角色：Claude
> 状态：ready
> 日期：2026-05-05

## 1. 目标

在 `F:\v.6\v6-op` 内完成 charter 阶段 3：

```text
单页操盘台：股票来源 + 技能选择 + 参数 + 路径选择 + 运行进度 + 命中结果 + 中文解释 + 报告摘要
```

本轮目标是让用户打开一个页面，就能完成完整 V6OP 操盘流。

不要做 landing page，不要做多页面 workbench，不要新增概念页。

## 2. 当前基础

V6OP-003 已完成后端：

- `POST /api/run`
- `GET /api/result`
- `GET /api/stream`（JSON 轮询，非 true SSE）
- `GET /api/health`
- `execution_engine.py`
- `run_report.json`
- `run_report.md`

请先读：

```text
F:\v.6\v6-op\docs\claude_v6op\latest_report.md
F:\v.6\v6-op\docs\claude_v6op\current_status.md
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-003_phase2_fetch_planner_execution_api_report.md
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-003_codex_review.md
F:\v.6\v6-op\scripts\v6op_server.py
F:\v.6\v6-op\scripts\execution_engine.py
F:\v.6\v6-op\output\current\execution_result.json
F:\v.6\v6-op\output\current\run_report.json
```

## 3. 允许修改

只允许修改 / 新增：

```text
F:\v.6\v6-op\*
```

建议新增：

```text
web\index.html
web\app.js
web\styles.css
tests\test_phase3_web_assets.py
```

可以修改：

```text
scripts\v6op_server.py
```

用于静态文件服务或前端自测，但不要重写后端主逻辑。

## 4. 禁止事项

禁止：

- 新建多页面 workbench
- 新建 explain/report/closure/debug 等独立页面
- 做 DAG 编辑器
- 做 landing page
- 写营销式介绍页
- 修改 V5.10 / V6
- 在页面或日志显示真实 key
- 把问财设成唯一入口
- 隐藏 readiness=aborted 风险
- 隐藏 SMC soft_filter / Wave weak_signal 标注

## 5. 页面布局要求

一个页面，三栏或等价响应式布局：

```text
左侧：来源 + 技能 + 参数 + 路径 + 启动
中间：运行进度日志 / readiness / 数据覆盖
右侧：命中结果 + 解释 + 失败摘要 + 报告入口
```

移动端可以上下堆叠，但仍是一个页面。

## 6. 必须支持的用户操作

### 6.1 股票来源

至少支持：

- 手动输入代码
- 全 A 股，带 limit 输入，默认不要全量扫 5000 只
- 问财输入框可以显示，但问财失败不能阻断其他来源

默认示例使用 manual：

```text
000001.SZ, 000002.SZ, 000063.SZ
```

### 6.2 技能选择

显示 6 个核心能力：

- 问财
- 缠论
- SMC
- K线形态
- 波浪
- 排雷

默认建议勾选：

- K线形态
- 排雷

可选：

- 缠论
- SMC strict
- 波浪弱信号

SMC soft_filter 必须标成调试/软过滤。

Wave 必须标成弱信号/辅助参考。

### 6.3 路径选择

支持三种：

- 顺序漏斗 `sequential`
- 并行取交集 `parallel_and`
- 简单混合 `simple_hybrid`

不要做任意 DAG 编辑器。

### 6.4 运行

点击运行后：

- `POST /api/run`
- 轮询 `GET /api/stream`
- 完成后拉取 `GET /api/result`

显示：

- run_id
- status
- 当前阶段
- final_hit_count
- warnings
- readiness

### 6.5 结果

必须显示：

- 命中股票列表
- 每只股票中文解释
- 失败 / 未分析 / stale 单独区域
- 本次参数
- 数据覆盖
- 运行报告摘要

不要把失败股票混进命中列表。

## 7. 后端服务要求

如果 `v6op_server.py` 当前不能直接服务 `web/index.html`，可以补静态服务。

建议：

```text
http://127.0.0.1:8876/
```

如果端口占用，自动尝试 8877 / 8878，并写报告。

## 8. 测试与验收

必须执行：

```powershell
cd F:\v.6\v6-op
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts\v6op_server.py --self-test --port 8878
```

如果新增 JS 文件，必须做语法检查。

如果没有 Node，可用 Python 或浏览器打开检查替代，但报告要说明。

建议补充轻量前端资产测试：

- `web/index.html` 存在
- 引用 `app.js` / `styles.css`
- 页面包含来源、技能、路径、运行、结果、报告关键词

## 9. 报告落点

必须更新：

```text
docs\claude_v6op\latest_report.md
docs\claude_v6op\current_status.md
```

必须新增：

```text
docs\claude_v6op\reports\V6OP-004_phase3_single_page_console_report.md
```

`latest_report.md` 顶部给用户看的最终回复，必须和聊天窗口最终回复一致或等价。

## 10. 报告必须说明

- 改了哪些文件
- 页面访问 URL
- 是否启动服务验证
- 是否访问真实外部接口
- 是否读取 `.env`
- 是否修改 V5.10 / V6
- API 是否仍通过 self-test
- 前端是否能提交 manual 策略并显示结果
- stream 使用轮询还是 SSE
- 需要 v6-op 架构师审阅的 3-5 点

## 11. 完成后回复

Claude 聊天窗口短回复：

```text
Claude 已完成 V6OP-004 阶段 3 单页操盘台前端。

报告已写入：
- docs/claude_v6op/latest_report.md
- docs/claude_v6op/current_status.md
- docs/claude_v6op/reports/V6OP-004_phase3_single_page_console_report.md

访问地址：
- http://127.0.0.1:<port>/

测试：
- <命令>：<结果>

真实外部接口：
- 问财：是/否
- 行情源：是/否

是否修改 V5.10 / V6：否

需要 v6-op 架构师审阅：
- ...
```

