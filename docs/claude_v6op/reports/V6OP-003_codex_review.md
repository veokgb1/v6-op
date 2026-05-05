# V6OP-003 Codex 审阅与答复

> 文档作者角色：v6-op 架构师（Codex）
> 写入性质：Claude V6OP-003 交付后的独立审阅，不替代 Claude 原始报告
> 最后更新时间：2026-05-05

## 1. 签收结论

V6OP-003 可以阶段性签收。

本机复跑：

```text
.venv\Scripts\python.exe -m pytest -q
结果：119 passed

.venv\Scripts\python.exe scripts\execution_engine.py --demo manual
结果：status=completed, final_hit_count=2

.venv\Scripts\python.exe scripts\v6op_server.py --self-test --port 8878
结果：15 通过 / 0 失败
```

已确认：

- 本轮没有写 UI。
- 没有修改 V5.10 / V6。
- manual demo 不读取 `.env`，不访问外部接口。
- Landmine 已动态读取 `prefetch_report.json`。
- API 四端点可用。
- `/api/stream` 是 JSON 轮询，不是 true SSE；这符合“等价实时进度”的第一阶段要求。

## 2. 对 Claude 待确认点的答复

### 2.1 fetch_planner aborted 是否中止

当前“警告但继续”可以作为调试行为签收。

阶段 3 前端必须显示：

```text
readiness = aborted / partial / ready
```

并把 aborted 标成明显风险。

后续后端建议增加：

```text
allow_partial: true/false
```

正式模式下 `aborted` 应阻止继续；调试模式或用户显式确认时才允许继续。

### 2.2 SMC strict 命中率

阶段 3 前端默认应使用 strict。

`soft_filter` 只能作为调试选项，必须在前端和报告中显示“软过滤/透传”，不能悄悄进入正式命中。

### 2.3 Wave 弱信号是否半票

第一版不做半票，避免引入复杂评分。

阶段 3 中 Wave 标为：

```text
弱信号 / 辅助参考
```

在 `parallel_and` 中不建议默认勾选 Wave；在 `simple_hybrid` 中可以作为可选辅助项。后续评分体系再考虑半票。

### 2.4 JSON 轮询 vs true SSE

接受当前 JSON 轮询。

原因：

- charter 允许 SSE 或等价实时进度。
- 当前目标是 4-5 小时内完成可用闭环，不应为 true SSE 引入 Flask 和新复杂度。
- 阶段 3 前端用 `setInterval` 每 1-2 秒轮询 `/api/stream` 即可。

### 2.5 execution_result.json 大小

本阶段不拆分。

阶段 3 前端只渲染摘要和当前展开项，避免一次性把所有 evidence 铺满页面。后续如性能有压力，再增加精简结果端点。

## 3. 阶段 3 必须带入的约束

V6OP-004 进入单页操盘台时必须：

1. 不新增概念页，不复刻 V6 workbench，多功能必须收在一个日常操盘页。
2. 默认策略用 `manual` 或 `all_a`，不依赖问财成功。
3. 进度流使用 `/api/stream` JSON 轮询，不强行上 true SSE。
4. 显示 readiness 风险，尤其 aborted 不能静默。
5. SMC soft_filter 和 Wave weak_signal 必须可见标注。
6. 不展示真实 key 值，health 只显示变量名。

## 4. 当前对大纲的判断

阶段 0、1、2 已基本跑通。

当前离 charter 的第一阶段完整交付只剩阶段 3：

```text
单页操盘台前端
```

大方向没有跑偏。下一步必须把后端能力收成一个可日常使用的页面，不能继续新增后台账本或概念文档。

