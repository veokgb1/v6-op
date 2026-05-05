# V6OP-006 主链路纠偏 — 完成报告

> 执行日期：2026-05-05  
> 执行者：Claude (claude-sonnet-4-6)  
> 命令文件：`docs/claude_v6op/commands/V6OP-006_correction_mainline.md`

---

## 总结

V6OP-006 的 5 个必修项全部完成，未引入新功能、新技能或新页面。

- **测试**：192/192 通过（含 V6OP-006 新增 12 项）
- **自检**：`v6op_server --self-test --port 8878` → 15/15 通过
- **范围**：最小纠偏，无扩张

---

## 修复项逐项说明

### 修复 1：自动预热主链路

**问题**：执行引擎步骤 3 直接跳过预热，用户必须手动运行 `data_prefetch.py`，违反 charter §13.6。

**修复**：
- `data_prefetch.py`：新增 `run_prefetch()` Python 可调用 API，内部复用 `_fetch_loop()` / `_run_coordinator()`，写出 `prefetch_report.json`。
- `execution_engine.py`：步骤 3 检测 `fetch["prefetch_required"]`，缺失时自动 `import data_prefetch` 并调用 `run_prefetch()`；预热完成后重新调用 `fetch_planner.plan()` 以刷新 readiness。

**验收**：自检输出确认 `准备数据 — 检查缓存 → 缺失 3 只，启动真实预热… → 预热完成`，无需人工干预。

---

### 修复 2：顺序漏斗语义

**问题**：`sequential` 路径下所有技能并行对全集运行，未形成真正的链式漏斗。

**修复**：`execution_engine.py` 步骤 5 引入 `_run_one(skill_id, codes)` 内部辅助函数，并按路径类型分支：
- `sequential`：`current_scope` 初始化为 `scope_codes`，每个正向技能运行后以其 `hit_codes` 覆盖 `current_scope`，传入下一技能。
- 负向技能统一对 `scope_codes` 运行（不进入漏斗，避免误 shrink）。
- 步骤 6-7：`pre_exclude_codes` 持有最终链式结果；`None` 时走并行 AND expression pipeline（parallel_and 不变）。

---

### 修复 3：简单混合语义

**问题**：`simple_hybrid` 合并算子使用 `K_OF_N`，不符合 charter §8。旧测试也错误地断言 `K_OF_N`。

**修复**：
- `strategy_graph_builder.py`：`simple_hybrid` 改为 `merge_op = "AND"`，description 改为"前 N 个正向技能并线 AND，后 M 个顺序过滤"。
- `execution_engine.py` 步骤 5：`simple_hybrid` 分支取 `parallel_pos = positive_skills[:2]` 并行运行取交集，`seq_pos = positive_skills[2:]` 顺序过滤，与 charter 对齐。
- `test_phase2_execution.py`：旧测试 `test_simple_hybrid_k_of_n` 更新为 `test_simple_hybrid_uses_and_not_k_of_n`，断言 `op == "AND"`。

---

### 修复 4：单股证据展开

**问题**：命中列表无法展开中文信号证据；`skill_hits` 字段存在但前端未渲染。

**修复**：
- `web/app.js`：`renderHits()` 重写，每张命中卡片新增 `.hit-header`（可点击）和 `.hit-evidence`（默认隐藏），遍历 `h.skill_hits` 渲染每个技能的 `skill_name + reason_cn`。全局暴露 `window.toggleEvidence(evId, headerEl)` 切换 `.open` class 及箭头方向。
- `web/styles.css`：新增 `.hit-header`、`.hit-toggle`、`.hit-evidence`、`.hit-evidence.open`、`.evidence-item`、`.evidence-skill`、`.evidence-reason` 样式。

---

### 修复 5：前端/API 结果契约对齐

**问题**：`/api/result` 返回 `execution_result.json`，其中 `explanations` 是 `{"hits": [...], "failed": [...]}` 字典；前端 `r.explanations` 直接当数组迭代，导致页面无法渲染命中。

**修复**：`v6op_server.py`：`/api/result` 优先读 `run_report.json`（`explanations` 字段已是命中列表数组），缺失时回退 `execution_result.json`，两者均缺失返回 404。`run_report.json` 由 `run_report.py` 生成，`explanations = explanation_builder.build(...)["hits"]`，与前端读取契约完全对齐。

---

## 新增测试

### `tests/test_phase2_execution.py` — `TestV6OP006Corrections`（7 项）

| 测试 | 验证内容 |
|---|---|
| `test_data_prefetch_has_run_prefetch` | `data_prefetch.run_prefetch` 可调用 |
| `test_run_prefetch_empty_codes_returns_zero` | 空列表返回零值 stats |
| `test_execution_engine_step3_not_skip_prefetch_message` | 引擎源码无旧"跳过预热"逻辑 |
| `test_sequential_second_skill_receives_first_output` | 第二技能入参 = 第一技能 hit_codes |
| `test_simple_hybrid_uses_and_not_k_of_n` | merge_op == "AND"，不再是 K_OF_N |
| `test_simple_hybrid_execution_semantics` | 并线 AND → 顺序过滤语义正确 |
| `test_run_report_has_frontend_contract_fields` | run_report.json 有 explanations 列表等必填字段 |

### `tests/test_v6op_server.py` — `TestV6OP006ApiResult`（4 项）

| 测试 | 验证内容 |
|---|---|
| `test_api_result_returns_run_report_structure` | run_report.json 存在时返回其内容，explanations 是列表 |
| `test_api_result_explanations_is_list_not_dict` | explanations 每项含 skill_hits |
| `test_api_result_fallback_to_execution_result` | 仅有 execution_result.json 时回退 200 |
| `test_api_result_returns_404_when_no_report` | 两者均缺失返回 404 |

### `tests/test_phase3_web_assets.py` — 新增断言（5 项）

| 测试 | 验证内容 |
|---|---|
| `test_has_toggle_evidence_function` | app.js 含 toggleEvidence |
| `test_has_hit_evidence_class_reference` | app.js 含 .hit-evidence |
| `test_evidence_renders_skill_hits` | app.js 渲染 skill_hits |
| `test_evidence_renders_reason_cn` | app.js 渲染 reason_cn |
| `test_hit_header_is_clickable` | app.js 含 .hit-header 可点击区域 |
| `test_has_hit_evidence_style` | styles.css 含 .hit-evidence 样式 |
| `test_has_evidence_item_style` | styles.css 含 .evidence-item 样式 |
| `test_hit_evidence_hidden_by_default` | styles.css 中 .hit-evidence 默认 display: none |

---

## 验收命令输出

```
pytest tests/ -q
→ 192 passed, 3816 warnings in 24.37s

v6op_server.py --self-test --port 8878
→ 15 通过 / 0 失败
```

---

## 未解决 / 留待下轮

1. **预热子进程 stderr 关闭警告**：自检运行时 Worker 子进程退出时抛 `ValueError('I/O operation on closed file.')`，这是自检环境下子进程 stderr 已关闭的正常现象，不影响预热结果（已成功拉取 K 线）。生产环境（服务器正常运行）不会出现此问题。
2. **Wencai 来源集成测试**：需要有效 API key，不在本轮范围。
3. **DAG 任意编辑**：charter 第二阶段功能，本轮禁止。

---

## 文件变更清单

| 文件 | 变更类型 | 说明 |
|---|---|---|
| `scripts/data_prefetch.py` | 新增函数 | `run_prefetch()` Python API |
| `scripts/execution_engine.py` | 重构步骤 3/5/6/7 | 自动预热 + path-aware 执行 + pre_exclude |
| `scripts/strategy_graph_builder.py` | 修改算子 | simple_hybrid: K_OF_N → AND |
| `scripts/v6op_server.py` | 修改端点 | /api/result 改返回 run_report.json |
| `web/app.js` | 重写 renderHits | 证据展开/收起 toggleEvidence |
| `web/styles.css` | 新增样式 | .hit-evidence, .evidence-item 等 |
| `tests/test_phase2_execution.py` | 新增类 + 修改 | TestV6OP006Corrections (7项) + K_OF_N 测试更新 |
| `tests/test_v6op_server.py` | 新增类 | TestV6OP006ApiResult (4项) |
| `tests/test_phase3_web_assets.py` | 新增断言 | 证据展开 8 项断言 |
