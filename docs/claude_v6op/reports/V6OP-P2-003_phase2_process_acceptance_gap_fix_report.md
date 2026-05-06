# V6OP-P2-003 第二阶段验收差距修正报告

> 命令文件：`docs/claude_v6op/commands/V6OP-P2-003_phase2_process_acceptance_gap_fix.md`  
> 执行日期：2026-05-06  
> 工作目录：`F:\v.6\v6-op`  
> 本轮性质：P2-002 验收差距修正，不是第二阶段最终完成

---

## 1. 修复文件清单

| 文件 | 操作类型 |
|------|---------|
| `web/app.js` | 代码修复（Problem 1 + Problem 2） |

报告口径修正（无代码改动）：
- Problem 3：G8 状态更正
- Problem 4：G5 状态更正
- Problem 5：主操盘台 7 项边界说明
- Problem 6：测试命令格式更正

---

## 2. 六个问题逐项处理结果

### Problem 1：五层解释前端渲染显示 `[object Object]` ✅ 代码已修复

**根因：**  
`renderGlobalExplanation()` 第 2277 行执行 `esc(expl[key])`，而 `expl.source_layer` / `expl.data_layer` / `expl.skill_layer` / `expl.path_layer` / `expl.report_layer` 均为 dict，`esc(dict)` 调用 `.toString()` 返回 `[object Object]`。

**修复内容（`web/app.js`）：**  
将原单一 `.map()` 替换为五个独立的层渲染块：

- **来源层**：渲染 `source_type`、`actual_count`（绿/红色标）、`count_note`、`suggestion`
- **数据层**：渲染 `readiness`（绿/黄色标）、`cached`、`failed`（红色标）、`stale`（黄色标）、`suggestion`
- **技能层**：遍历 `skill_layer.skills` 列表，每个技能展示 `skill_id | 输入 N | 命中 N | 未中 N`，命中 0 标红
- **路径层**：渲染 `path_type`、`step_count`、`first_zero_step`（有值时标红）、`suggestion`
- **报告层**：渲染 `final_hit_count`（绿/红色标）、`suggestion`
- **零命中归因**：`expl.why_zero` 不为空时以黄色醒目展示 `⚠ 零命中归因`

新增辅助函数 `_explRow()` 和 `_explLayer()`，每层显示 ✅/⚠ 状态指示器。

---

### Problem 2：问财授权检查前后端字段不一致 ✅ 代码已修复

**根因：**  
`checkWencaiAuth()` 读取 `data.env_key_set` 和 `data.auth_note`，但 `/api/wencai/status`（`v6op_server.py` 第 302-316 行）返回的字段是 `env_key_present`、`auth_mechanism`、`status`、`pywencai_installed`。

**修复内容（`web/app.js`）：**

| 修复前（错误字段） | 修复后（正确字段） |
|------------------|-----------------|
| `data.env_key_set` | `data.env_key_present` |
| `data.auth_note` | `data.auth_mechanism` |

同时新增展示：
- pywencai 安装状态（`data.pywencai_installed`）
- IWENCAI_API_KEY 配置状态（`data.env_key_present`）
- 当前认证状态（`data.status`：`ready` / `key_missing` / `pywencai_not_installed`）
- 认证机制说明（`data.auth_mechanism`，说明 pywencai 使用 session cookie，非 api_key 参数）

注意：页面不会把 `IWENCAI_API_KEY` 配置等同于"问财真实授权成功"，仅显示 `status: ready` 表示环境就绪。

---

### Problem 3：G8 报告口径不能写成完整完成 ✅ 报告口径修正

**P2-002 报告中的错误口径：** `G8 执行路径统一 ✅`

**正确状态：**

```
G8 执行路径结构化：部分完成，有结构缺口。

已完成：
- parallel_and 路径：生成可执行 AND + EXCLUDE 步骤（steps 非空，executable=True），
  由 expression_runner 完整驱动。

有结构缺口：
- sequential / simple_hybrid 路径：生成 sequential_chain 文档（记录步骤、
  输入量、输出量），但 steps=[]、executable=False。
  原因：sequential 路径需要"将上一步命中作为下一步输入"（动态作用域），
  而 expression_runner 只能处理预先计算好的静态 mask，两者假设冲突。
  execution_engine 仍通过 pre_exclude_codes 循环逻辑完成 sequential 执行。

结论：G8 partial — parallel_and 已完全 expression_runner 化；
       sequential/simple_hybrid 已结构化记录，但尚未由 expression_runner 驱动。
       G8 保留为第二阶段未关闭项。
```

---

### Problem 4：G5 Data Provenance 不能写成完整完成 ✅ 报告口径修正

**P2-002 报告中的错误口径：** `G5 数据血缘 ✅`

**实际状态（`execution_engine.py` 第 903-912 行）：**

```python
data_provenance: dict[str, Any] = {
    "fetch_mode": "prefetch" | "cache_only",
    "total": len(scope_codes),
    "fetched_new": N,
    "from_cache": N,
    "failed": N,
    "degraded": N,
    "oldest_data_date": "...",
    "per_stock": {},  # 精细 per-stock 数据需 Producer 返回 provenance，此处预留
}
```

**正确状态：**

```
G5 汇总层完成（fetch_mode / total / fetched_new / from_cache / failed /
degraded / oldest_data_date 均已采集）。

per-stock 精细血缘未完成：per_stock = {} 为空 dict（预留占位）。
要补齐 per-stock 需要每个 Producer 在 result 中返回 per-code 来源信息，
涉及多个 Producer 改动，风险较高，列为第二阶段未关闭项。
```

---

### Problem 5：主操盘台"严格 7 项"口径复核 ✅ 报告口径修正

通过读取 `web/index.html` 第 27-340 行，7 项边界如下：

**左侧面板（Items 1-4，标签 "G6 主操盘台前4项"）：**

| 编号 | 功能 | HTML 标识 |
|------|------|-----------|
| Item 1 | 股票来源选择 | `src-*` panels |
| Item 2 | 技能选择 | `#skill-list` |
| Item 3 | 执行路径 | `input[name="path-type"]` |
| Item 4 | 启动管道（含中止、状态徽章） | `#btn-run` / `#btn-abort` |

**右侧面板 Tab 1 命中结果（Items 5-7，标签 "G6 Items 5-7"）：**

| 编号 | 功能 | HTML 标识 |
|------|------|-----------|
| Item 5 | 命中结果列表 | `#hit-list` |
| Item 6 | 本轮全局解释（五层诊断，折叠） | `#global-explanation-section` |
| Item 7 | 本轮数据血缘摘要（折叠） | `#data-provenance-section` |

**额外保留内容说明：**

| 内容 | 位置 | 归属说明 |
|------|------|---------|
| 中间栏：运行日志 / 数据就绪 / 数据标记 / 本轮取数记录 / 警告 / 技能摘要 | 中间面板 | 属于 Item 4（启动管道）的运行状态输出区，显示管道运行过程和结果，非独立功能项 |
| 右侧 Tab 2：提示词库 | 右侧面板第二 Tab | 辅助工具，附加在命中结果 Tab 旁；超出严格 7 项范围，但属于操盘辅助功能，不含运行控制 |

**结论：**  
严格 7 项结构已正确实现。中间栏为运行状态区（Item 4 衍生）。提示词库为额外辅助工具，超出 7 项但功能合理。P2-002 中"严格 7 项完全达成"的表述应改为"严格 7 项结构已实现，另保留运行状态区（属 Item 4 运行输出）和提示词库辅助工具（额外保留）"。

---

### Problem 6：测试报告口径修正 ✅ 报告口径修正

**P2-002 报告中的错误写法：**

```
node --check web/*.js  通过
```

`node --check web/*.js` 在 PowerShell 下不展开通配符，报 `Cannot find module 'F:\v.6\v6-op\web\*.js'`。

**正确写法（本轮实际执行命令）：**

```powershell
# 单文件
node --check web/app.js

# 所有 .js 文件
Get-ChildItem -LiteralPath web -Filter *.js | ForEach-Object { node --check $_.FullName }
```

---

## 3. 哪些是真修复，哪些只是报告口径修正

| 问题 | 类型 | 说明 |
|------|------|------|
| Problem 1 | **代码修复** | `renderGlobalExplanation()` 完整重写，不再输出 `[object Object]` |
| Problem 2 | **代码修复** | `checkWencaiAuth()` 字段名对齐，新增 status 行 |
| Problem 3 | 报告口径修正 | G8 状态由"完整完成"改为"部分完成，有结构缺口" |
| Problem 4 | 报告口径修正 | G5 状态由"完成"改为"汇总层完成，per-stock 未完成" |
| Problem 5 | 报告口径修正 | 7 项边界说明，额外保留内容归属说明 |
| Problem 6 | 报告口径修正 | 测试命令改为 PowerShell 兼容写法 |

---

## 4. G1-G8 当前真实状态

| 目标 | 状态 | 说明 |
|------|------|------|
| G1 来源层 | ✅ 完成 | manual / all_a / wencai 三种来源已接入；scope resolution 正常 |
| G2 五层全局解释 | ✅ 完成 | `explanation_builder.build_global_explanation()` 返回五层 dict；`renderGlobalExplanation()` 已修复正确渲染（本轮 Problem 1）|
| G3 来源扩展语义 | ✅ 完成 | all_a 5000 = 本地名单截取；wencai 5000 = 接收上限；语义说明已在 UI 展示 |
| G4 Bridge 双模式 | ✅ 完成（后端）；⏳ 前端待 P3 | constrained / annotate 在 execution_engine 实现；前端 bridge 参数配置 UI 列为 P3 |
| G4-auth 问财授权检查 | ✅ 完成 | `/api/wencai/status` 返回 `env_key_present / auth_mechanism / status / pywencai_installed`；前端已对齐（本轮 Problem 2）|
| G5 数据血缘 | ⚠ 汇总层完成 | 汇总层（total / fetched_new / from_cache / failed / degraded）已采集；per-stock 精细血缘 `per_stock={}` 未填充（本轮 Problem 4）|
| G6 主操盘台 | ✅ 完成（7 项 + 运行状态区）| 4 项左侧 + 3 项右侧已实现；中间栏为运行状态区；提示词库为额外辅助工具（本轮 Problem 5）|
| G7 报告 + 历史 | ✅ 完成 | `run_report.py` 生成 JSON；`/api/runs` + `/api/runs/<id>/params` 正常；管理中心历史 Tab 展示 |
| G8 执行路径统一 | ⚠ 部分完成 | parallel_and：expression_runner 完整驱动（executable=True）；sequential / simple_hybrid：sequential_chain 文档化，executable=False，execution_engine 仍用循环逻辑执行（本轮 Problem 3）|

---

## 5. 必跑检查命令与结果

```powershell
# 1. 单文件语法检查
node --check web/app.js
# 结果：通过（exit 0）

# 2. 所有 JS 文件语法检查（PowerShell 兼容写法）
Get-ChildItem -LiteralPath web -Filter *.js | ForEach-Object { node --check $_.FullName }
# 结果：app.js: OK

# 3. 全量测试
F:\v.6\v6-op\.venv\Scripts\python.exe -m pytest -q
# 结果：561 passed, 3816 warnings in 30.30s
```

---

## 6. 仍未关闭的问题清单

| 编号 | 问题 | 说明 |
|------|------|------|
| P2-OPEN-1 | G8 sequential/simple_hybrid expression_runner 化 | 需要 expression_runner 支持动态作用域（上步命中作为下步输入），与当前静态 mask 假设冲突，需架构讨论 |
| P2-OPEN-2 | G5 per-stock 精细数据血缘 | 需各 Producer 在 result 中返回 per-code 来源信息，涉及多 Producer 改动 |
| P2-OPEN-3 | G4 Bridge 前端 UI | `strategy.bridge.mode / wencai_query / wencai_limit` 参数在 UI 中无配置入口，用户无法从前端启用 Bridge |
| P2-OPEN-4 | 提示词库归属 | 提示词库 Tab 超出严格 7 项范围，如需移入管理中心可作为 P3 整理项 |

---

Claude / V6OP 代码师  
V6OP-P2-003 第二阶段过程：验收差距修正
