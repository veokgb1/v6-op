# V6OP-P2-005 第二阶段最终收口判断报告

> 执行人：Codex 秘书  
> 工作目录：`F:\v.6\v6-op`  
> 对账依据：`v6-op_phase2_upgrade_charter.md`、`V6OP-P2-002_phase2_process_formal_rebuild_report.md`、`V6OP-P2-003_phase2_process_acceptance_gap_fix_report.md`、当前代码与测试结果  
> 本报告性质：第二阶段收口判断，不新增开发命令

> 重要更新：本报告是 P2-006 继续补齐前的中间判断，最终口径已被  
> `F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-P2-006_phase2_final_completion_report.md`  
> 覆盖。P2-006 后，第二阶段按 G1-G8 收口完成。

---

## 1. 总判断

P2 不能写成“严格全项 100% 完成”。

P2 当前真实状态是：

```text
第二阶段主体改建已经完成，核心可用链路已经建立；
但按第二阶段正式大纲逐条验收，仍有 4 个未关闭项。
```

如果按用户目标“最好一步完成”来推进，建议只剩 **一步**：

```text
P2-005 收口：确认当前主体完成，记录未关闭项，决定进入提交/推送，或把未关闭项转入下一阶段专项。
```

这一步不应该再交给 Claude 继续自由扩展。现在最重要的是防止第二阶段继续失控滚动。

---

## 2. 对应第二阶段 G1-G8 状态

| 目标 | 当前判断 | 说明 |
|---|---|---|
| G1 参数-数据-缓存全链路一致化 | 已完成 | `days` 已进入 K 线准备、技能分析、报告字段；`actual_days_used` 已写入报告；测试已覆盖。 |
| G2 全局解释层与分层归零诊断 | 已完成 | 已有五层解释对象，前端 `[object Object]` 渲染问题已在 P2-003 修复。 |
| G3 来源层语义清晰化与诊断字段保留 | 已完成 | 问财/全A 的 5000 语义已区分；问财诊断字段保留到来源信息。 |
| G4 问财授权验证 | 已完成 | `/api/wencai/status` 与前端字段已对齐；状态表达不再把 key 配置等同于真实授权成功。 |
| G4 Bridge 双角色定义 | 后端已完成，前端入口未完成 | `strategy.bridge` 后端支持 constrained / annotate；但用户还不能从主操盘台直接配置 Bridge。 |
| G5 数据血缘层 | 汇总层完成，逐股层未完成 | `data_provenance` 汇总字段已存在；`per_stock` 仍为空占位。 |
| G6 主操盘台与管理中心分流 | 主体完成 | 管理中心已承接历史、缓存、问财授权、设置、帮助；主操盘台结构基本到位。提示词库归属仍可后续整理。 |
| G7 运行管理语义正式化 | 已完成 | abort、三层缓存清理、历史参数恢复语义已建立；Codex 追加修复了历史参数恢复接口契约。 |
| G8 执行路径统一 | 部分完成，未关闭 | `parallel_and` 已 expression_runner 化；`sequential` / `simple_hybrid` 仍是结构化记录，不是真正由 expression_runner 驱动。 |

---

## 3. 原 Claude 计划与实际执行对账

### Pass 1：G1 -> G3 -> G4-auth -> G2 -> G5

实际结果：基本完成。

已经做成：

- 参数天数链路修正。
- PRO 5000 语义拆分。
- 问财诊断字段保留。
- 问财授权状态接口与页面展示。
- 五层解释器。
- 数据血缘汇总层。

未完全关闭：

- G5 的逐股 `per_stock` 血缘没有填实。

### Pass 2：G6 -> G7 -> G4-Bridge -> G8

实际结果：主体完成，但 G8 和 Bridge UI 未完全关闭。

已经做成：

- 管理中心基本成型。
- abort、缓存清理、历史恢复语义成型。
- Bridge 后端两种模式成型。
- `parallel_and` 可执行表达式链路成型。

未完全关闭：

- Bridge 没有前端配置入口。
- `sequential` / `simple_hybrid` 没有真正走 expression_runner。
- 提示词库是否移入管理中心，需要后续产品边界决定。

### Pass 3：验收补漏

实际结果：完成了两类补漏。

- Claude P2-003 修复了全局解释前端渲染、问财授权字段不一致。
- Codex 追加修复了历史参数恢复：报告保存 `strategy_snapshot`，后端 `/api/runs/:id/params` 返回前端可恢复的 `params`，前端兼容 `params / strategy_snapshot / strategy`。

---

## 4. 当前已知未关闭项

| 编号 | 未关闭项 | 性质 | 建议归属 |
|---|---|---|---|
| P2-OPEN-1 | G8 sequential/simple_hybrid 真正 expression_runner 化 | 架构级 | 不建议继续临时补丁；转专项设计或下一阶段。 |
| P2-OPEN-2 | G5 per-stock 数据血缘填实 | 中型开发 | 可作为下一阶段第一批数据透明度增强。 |
| P2-OPEN-3 | Bridge 前端 UI 配置入口 | 中小型开发 | 可作为下一阶段操盘台入口增强。 |
| P2-OPEN-4 | 提示词库归属 | 产品边界 | 若坚持主操盘台只保留 7 项，应迁入管理中心。 |
| P2-OPEN-5 | 真实浏览器端到端验收 | 环境/验收 | 当前只有 node 语法、后端测试、静态/单元测试；缺 Playwright 真实 UI 验收。 |

---

## 5. Codex 追加小修记录

本次 Codex 直接处理了一个小问题，不再发给 Claude：

```text
G7 历史参数恢复接口契约不完整。
```

修复内容：

- `scripts/run_report.py`：新增 `strategy_snapshot`，保存原始完整策略。
- `scripts/v6op_server.py`：`/api/runs/:id/params` 返回 `params`，优先使用 `strategy_snapshot`，无快照时从旧 summary 兜底重建。
- `web/app.js`：历史恢复兼容 `params / strategy_snapshot / strategy`，并兼容 `skills / selected_skills`。
- `tests/test_phase2_execution.py`：补充 `strategy_snapshot` 报告字段断言。
- `tests/test_v6op_server.py`：新增历史参数恢复接口契约测试。

这属于小修，不是新一轮大开发命令。

---

## 6. 测试结果

已执行并通过：

```powershell
node --check web/app.js
Get-ChildItem -LiteralPath web -Filter *.js | ForEach-Object { node --check $_.FullName }
F:\v.6\v6-op\.venv\Scripts\python.exe -m pytest -q
```

结果：

```text
node 检查通过。
pytest：562 passed，0 failed，2544 warnings。
```

pytest warnings 来自 `czsc_producer.py` 调用的 `czsc` 弃用提示，不作为本轮失败项。

---

## 7. 还需要几步

如果目标是“第二阶段严格全项完成”，还需要至少 3 个开发动作：

```text
1. G8 sequential/simple_hybrid 真正 expression_runner 化。
2. G5 per-stock 数据血缘填实。
3. Bridge 前端 UI + 提示词库归属整理。
```

这不是最稳妥路线，因为会重新打开执行引擎、数据血缘、前端操盘入口三条线。

如果目标是“第二阶段主体完成并受控收口”，只剩 1 步：

```text
确认 P2-005 收口判断，提交/推送当前可用成果，把 4 个未关闭结构项转入后续专项。
```

---

## 8. 建议

Codex 建议采用第二种：

```text
P2 主体完成，允许收口；
但不得宣称 G1-G8 全部 100% 完成；
必须带着 P2-OPEN-1 到 P2-OPEN-5 进入后续阶段。
```

原因：

- 当前核心痛点已经被覆盖：为什么为 0、5000 语义、数据来源透明、问财授权口径、管理中心、历史恢复。
- 未关闭项都不是几行小修，尤其 G8 会牵动执行模型和缓存假设。
- 继续在 P2 里滚动追加，会重复第一阶段“纲领有了但开发计划失控”的风险。

---

## 9. 收口结论

```text
P2 现在可以进入收口和提交阶段；
但 P2 不是严格全项完成，而是“主体完成 + 明确未关闭项”。
```

下一步建议：

```text
1. 用户确认是否接受这个收口口径。
2. 若接受，Codex 整理最终 git diff、提交信息和推送。
3. 若不接受，则不能说 P2 完成，需要新开一轮 G8/G5/Bridge 专项开发。
```
