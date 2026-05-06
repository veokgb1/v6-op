# V6OP-P2-002 第二阶段过程正式改建报告

> 执行：Claude / V6OP 代码师  
> 命令文件：`V6OP-P2-002_phase2_process_formal_rebuild.md`  
> 执行日期：2026-05-06  
> 总宗旨：**让用户在操盘时，能知道自己在相信什么**

---

## 1. 修改文件清单

| 文件 | 改建范围 |
|------|----------|
| `scripts/producers/czsc_producer.py` | G1: `_analyze_one` 解除 days=365 硬编码，接受 days 参数 |
| `scripts/execution_engine.py` | G1: max_lookback_days 计算 + fetch_planner 传参；G2: build_global_explanation；G4: Bridge constrained/annotate；G5: data_provenance；G8: pre_exclude_codes 传入生成器 |
| `scripts/expression_auto_generator.py` | G8: 根据 path_type 生成路径准确规格；sequential/simple_hybrid 生成 sequential_chain；parallel_and 生成可执行 AND+EXCLUDE steps |
| `scripts/explanation_builder.py` | G2: 新增 build_global_explanation()，五层解释 + why_zero 归因 |
| `scripts/sources/wencai_source.py` | G3: 新增 query_text / actual_count / api_called / count_note 诊断字段 |
| `scripts/source_resolver.py` | G3/G4-auth: _wencai_diag 传递，auth_note 说明 session 认证机制 |
| `scripts/ohlcv_provider.py` | G5: 为 fetch_ohlcv 所有返回路径附加 is_new_fetch / is_degraded / latest_date / trust_level；写缓存失败不再静默 |
| `scripts/run_report.py` | G1: actual_days_used；G3: source_info；G2/G5: global_explanation / data_provenance |
| `scripts/v6op_server.py` | G7: GET /api/runs；GET /api/runs/:id/params；POST /api/cache/clear/{layer}；GET /api/wencai/status |
| `web/index.html` | G6: 主操盘台 7 项；管理中心 Modal；PRO 5000 语义区分；global-explanation-section；data-provenance-section |
| `web/styles.css` | G6: .mgmt-overlay/.mgmt-modal/.mgmt-tab/.mgmt-panel；.result-details；.cache-layer-card；.prov-stat 等新 class |
| `web/app.js` | G6/G7: initMgmtCenter / loadMgmtHistory / restoreRunParams / clearCacheLayer / checkWencaiAuth；G2: renderGlobalExplanation；G5: renderDataProvenance；clearResult 新增清理 |

---

## 2. G1-G8 逐项完成状态

### G1 参数-数据-缓存全链路一致化 ✅

- `czsc_producer._analyze_one()` 接受 `days` 参数，不再固定 365
- `execution_engine` 计算 `max_lookback_days = max(各技能 days 参数)`
- `fetch_planner.plan()` 和 `compute_scope_data_time_max()` 均接收 `lookback_days=max_lookback_days`
- Mask 缓存指纹包含 `data_date`（由实际 K 线日期驱动），不同 days 不互相命中
- `run_report` 记录 `actual_days_used`

### G2 全局解释层与分层归零诊断 ✅

- `explanation_builder.build_global_explanation()` 实现五层解释
- 五层：source_layer / data_layer / skill_layer / path_layer / report_layer + why_zero
- why_zero 归因优先级：来源层空 → 数据层全失败 → 技能层首先筛空 → 路径层交集为空 → 报告层
- 前端：`<details id="global-explanation-section">` 折叠显示，命中 0 时自动展开 why-zero-badge
- `execution_result.global_explanation` 字段

### G3 来源层语义清晰化 ✅

- 问财 select：`"PRO 5000（最多接收问财返回结果）"` — 不保证返回 5000
- 全 A select：`"PRO 5000（本地名单截取上限）"` — 本地名单最多截取
- wencai_source 新增字段：`query_text` / `actual_count` / `api_called` / `elapsed_s` / `count_note`
- count_note 区分三种量级：0 只（授权/条件问题）/ 少量（<50）/ 接近上限（≥95% limit）
- source_resolver 传递 auth_note：明确说明 pywencai 使用 session 认证，不接受 api_key 参数

### G4-auth 问财授权验证 ✅

- GET /api/wencai/status 端点：检查 pywencai 安装 + IWENCAI_API_KEY 配置
- auth_note 明确说明：pywencai 使用 session cookie 认证，IWENCAI_API_KEY 不传入 pywencai.get()
- 管理中心「问财授权」标签：点击「检查」调用 /api/wencai/status

### G4-Bridge 双模式 ✅

**constrained mode（已有池与问财结果取交集）：**
- 触发方式：`strategy.bridge = {"mode": "constrained", "wencai_query": "...", "wencai_limit": 300}`
- 执行位置：来源解析后、fetch_planner 前
- 逻辑：`scope_codes = original_pool ∩ wencai_result`
- 结果记录：`execution_result.bridge_result` 包含 pool_before / pool_after / wencai_returned / description

**second-pass annotate mode（对命中股票附加问财标签）：**
- 触发方式：`strategy.bridge = {"mode": "annotate", "wencai_query": "...", "wencai_limit": 300}`
- 执行位置：final_hit_codes 计算后
- 逻辑：查询问财，为每个命中股票标注 `{"in_wencai": bool}`
- 不改变命中列表，只在 bridge_result.annotations 中记录

**架构说明：** Bridge 是主操盘台来源/参数能力，通过 `strategy.bridge` 字段触发，不是独立分析页面。前端 UI 扩展（在源选择区增加 bridge 控件）属于后续 Pass 3+ 工作。

### G5 数据血缘层 ✅

- `execution_result.data_provenance` 包含：fetch_mode / total / fetched_new / from_cache / failed / degraded / oldest_data_date / per_stock（预留）
- `ohlcv_provider` 为所有返回路径附加属性：`is_new_fetch` / `is_degraded` / `latest_date` / `trust_level`
- 写缓存失败不再静默，改为 logging.error
- 前端：`<details id="data-provenance-section">` 折叠显示，renderDataProvenance() 渲染统计气泡

### G6 主操盘台与管理中心分流 ✅

**主操盘台保留 7 项（满足命令要求）：**
1. 股票来源选择（来源类型 + 各来源具体参数）
2. 技能开关与参数调节（含技能顺序调整）
3. 执行路径选择（sequential / parallel_and / simple_hybrid）
4. 启动按钮 + 实时进度状态区（含 abort 按钮）
5. 命中结果列表（命中数 + 命中卡片 + 证据折叠）
6. 本轮全局解释（五层诊断，折叠）
7. 本轮数据血缘摘要（来源/缓存/降级统计，折叠）

**管理中心（⚙ 管理中心按钮 → Modal）：**
- 历史记录：列出 /api/runs 最近 20 条，「↩ 恢复参数」填回主操盘台但不启动
- 缓存管理：三层缓存分别清理（来源快照 / K线数据库 / 技能结果库）
- 问财授权：调用 /api/wencai/status 检查
- 系统设置：默认路径、默认 days
- 帮助文档：压力测试指南 + 五层解释说明

管理中心不含启动运行按钮，不是第二套操盘台。

### G7 运行管理语义正式化 ✅

- abort：步骤边界停止（AbortRequested 在每个技能前检查）
- 三层缓存清理 API：`POST /api/cache/clear/source|kline|skill`（互不误伤）
- 历史参数恢复 API：`GET /api/runs/:run_id/params`，前端填回参数不自动启动
- 历史列表 API：`GET /api/runs`（最多 20 条）
- 前端管理中心实现完整 JS：loadMgmtHistory / restoreRunParams / clearCacheLayer / saveMgmtSettings

### G8 执行路径统一 ✅（含剩余缺口说明）

**parallel_and：已完全使用 expression_runner ✓**
- `expression_auto_generator` 生成 AND + EXCLUDE 可执行 steps
- `_run_expression_steps()` 执行这些 steps
- 结果：`expression_spec.executable = True`，`expression_spec.steps` 有效

**sequential / simple_hybrid：expression_spec 已准确，执行路径剩余缺口 ⚠**
- `expression_auto_generator` 现在为 sequential/simple_hybrid 生成 `sequential_chain` 文档字段，准确记录每步的输入/输出规模
- `expression_spec.steps` 为 `[]`，`expression_spec.executable = False`
- 实际执行仍由 execution_engine 中的循环逻辑完成（pre_exclude_codes 路径）

**剩余缺口原因（G8 结构说明）：**
sequential/simple_hybrid 无法完全迁移到 expression_runner，原因：
1. expression_runner 处理预先计算好的静态 mask（固定输入集合）
2. sequential 路径要求「上一步命中作为下一步输入」，每个技能看到不同输入规模
3. 要通过 expression_runner 实现 sequential，需要 Producer 对不同输入集合多次运行，破坏 Mask 缓存假设（缓存指纹基于固定 scope_codes）
4. 不回归证据：561 个测试全部通过，sequential/simple_hybrid 结果与预期一致

---

## 3. Pass 执行情况

### Pass 1（G1 → G3 → G4-auth → G2 → G5）

全部完成（前一会话）。关键修复：
- czsc_producer days 硬编码
- execution_engine max_lookback_days 传参链
- ohlcv_provider 属性附加
- explanation_builder 五层诊断
- wencai_source 诊断字段
- source_resolver auth_note

### Pass 2（G6 → G7 → G4-Bridge → G8）

全部完成（本会话）。执行顺序：
1. styles.css + app.js：管理中心 CSS/JS（基于已完成的 index.html HTML）
2. G4-Bridge：execution_engine 两种模式
3. G8：expression_auto_generator 路径准确规格
4. Pass 3：node --check + pytest 561 全过，补 stress-guide 按钮修复测试回归

### Pass 3（验收补漏）

- `node --check web/app.js` ✓（无语法错误）
- `python -m pytest -q` → **561 passed, 0 failed** ✓
- 回归修复：test_has_stress_guide 缺少 data-help="stress-guide" → 在管理中心帮助文档标签的压力测试 summary 中补回

---

## 4. 新增字段与前端显示位置

| 字段 | 位置 | 前端显示 |
|------|------|----------|
| `actual_days_used` | execution_result / run_report | 无直接 UI（供调试用，run_report 包含） |
| `global_explanation.{source,data,skill,path,report}_layer` | execution_result | #global-explanation-section 折叠 |
| `global_explanation.why_zero` | execution_result | #why-zero-badge + global-explanation-body |
| `global_explanation.final_hit_count` | execution_result | badge 显示逻辑 |
| `data_provenance.{fetch_mode,total,fetched_new,...}` | execution_result | #data-provenance-section 折叠 |
| `source_info.{query_text,api_called,elapsed_s,count_note,auth_note}` | run_report | 管理中心问财授权检查页 |
| `bridge_result.{mode,applied,description,annotations,...}` | execution_result | 无直接 UI（供 API 消费） |
| `expression_spec.sequential_chain` | execution_result | 无直接 UI（报告层文档） |
| `expression_spec.executable` | execution_result | 无直接 UI（运行时路由判断） |

---

## 5. Data Provenance 示例

```json
{
  "fetch_mode": "prefetch",
  "total": 300,
  "fetched_new": 12,
  "from_cache": 288,
  "failed": 0,
  "degraded": 3,
  "oldest_data_date": "2025-04-25",
  "per_stock": {}
}
```

（per_stock 精细字段预留，需 Producer 返回 provenance metadata 后填充）

---

## 6. 五层解释器示例

命中 0 时（技能层筛空场景）：

```json
{
  "source_layer": "问财来源: 返回 45 只股票（少量，已记录）",
  "data_layer": "数据层: 43/45 只K线本地可用，2 只获取失败",
  "skill_layer": "技能层: czsc 输入 43，命中 0；后续技能已跳过",
  "path_layer": "路径层: sequential 第1层 czsc 筛空，后续技能跳过",
  "report_layer": "报告层: 本轮 0 命中，可尝试放宽买点窗口或更换技能",
  "why_zero": "技能层归零: czsc 在 43 只股票中命中 0（最先筛空的技能）",
  "final_hit_count": 0
}
```

---

## 7. Bridge 两种模式实现与验收

### constrained mode

**触发**：
```json
{
  "source": {"type": "manual", "codes": ["000001.SZ", "000002.SZ", "600000.SH"]},
  "bridge": {"mode": "constrained", "wencai_query": "今日涨停", "wencai_limit": 300},
  "skills": ["kline"],
  "path_type": "parallel_and"
}
```

**逻辑**：manual 池（3 只）∩ wencai 结果（假设返回 ["000001.SZ", "300750.SZ"]）= ["000001.SZ"]（1 只）

**bridge_result**：
```json
{
  "mode": "constrained",
  "applied": true,
  "wencai_returned": 2,
  "pool_before": 3,
  "pool_after": 1,
  "description": "constrained mode: 原始池 3 只 ∩ 问财 2 只 = 1 只"
}
```

### second-pass annotate mode

**触发**：
```json
{
  "source": {"type": "all_a", "limit": 100},
  "bridge": {"mode": "annotate", "wencai_query": "机构重仓股"},
  "skills": ["kline", "landmine"],
  "path_type": "parallel_and"
}
```

**逻辑**：技能执行后，对 final_hit_codes（如 8 只）逐一标注是否出现在问财结果中。不改变命中列表。

**bridge_result**：
```json
{
  "mode": "annotate",
  "applied": true,
  "wencai_returned": 450,
  "annotated_count": 3,
  "annotations": {
    "000001.SZ": {"in_wencai": true},
    "000002.SZ": {"in_wencai": false},
    ...
  },
  "description": "annotate mode: 8 只命中中 3 只也在问财结果中"
}
```

---

## 8. 主操盘台 7 项与管理中心边界验收

| 验收项 | 结果 |
|--------|------|
| 主操盘台只保留 7 项操盘内容 | ✅ (详见 G6 节) |
| 管理中心无启动运行入口 | ✅ Modal 无任何 btn-run 或启动功能 |
| 历史恢复参数但不启动 | ✅ restoreRunParams 填回参数后关闭 Modal，不触发 run |
| 管理中心5个标签（历史/缓存/问财授权/设置/帮助）| ✅ |
| 缓存清理三层独立 | ✅ /api/cache/clear/source|kline|skill 互不影响 |

---

## 9. 三层缓存、abort、历史参数恢复验收

### 三层缓存清理

| 层 | API 路径 | 清理目标 | 不影响 |
|----|---------|---------|--------|
| ★ 来源快照 | POST /api/cache/clear/source | output/current/*_scope.json + prefetch_report.json | K线、技能 |
| ★★ K线数据库 | POST /api/cache/clear/kline | var/cache/kline_daily/*.pkl | 来源、技能 |
| ★★★ 技能结果库 | POST /api/cache/clear/skill | output/mask_cache/*.json | 来源、K线 |

### abort

- 实现位置：`AbortRequested` 在每个技能前 `_check_abort()`
- 触发：`POST /api/abort` → `request_abort()`
- 结果：返回 `status="aborted"`，资源正确释放

### 历史参数恢复

- `GET /api/runs` → 列出 output/runs/ 最近 20 条
- `GET /api/runs/:run_id/params` → 返回 `{params: strategy}` 供前端填表
- 前端 `_applyRestoredParams()` 填充来源/路径/技能/技能参数，不触发运行

---

## 10. G8 三路径验收

### parallel_and 验收

- expression_spec.executable = True
- expression_spec.steps 有效（AND 合并 → EXCLUDE 排雷）
- _run_expression_steps 执行这些 steps
- 所有 parallel_and 相关测试通过（test_phase2_execution.py）

### sequential 验收

- execution_engine 按顺序漏斗执行（每步 → current_scope 缩小）
- expression_spec.sequential_chain 准确记录每步 input_count / output_count
- expression_spec.executable = False（文档性，不可执行）
- expression_spec.steps = [] → execution_engine 走 pre_exclude_codes 路径
- 不回归：测试全部通过

### simple_hybrid 验收

- execution_engine 先并线 AND（前2个正向技能）→ 顺序过滤（后续技能）
- expression_spec.sequential_chain 区分 phase="parallel" 和 phase="sequential"
- expression_spec.executable = False
- 不回归：测试全部通过

---

## 11. 必跑命令输出摘要

```
node --check web/app.js
→ 通过（无输出 = 语法正确）

python -m pytest -q
→ 561 passed, 3816 warnings in ~32s
   (warnings: czsc DeprecationWarning，不影响功能，来自第三方库)
```

---

## 12. 未完成项

| 项目 | 状态 | 说明 |
|------|------|------|
| Bridge 前端 UI 控件 | 未完成 | 后端 strategy.bridge 触发机制已实现；主操盘台来源区的 bridge 参数输入控件属后续 Pass |
| G5 per_stock 精细血缘 | 预留 | execution_result.data_provenance.per_stock = {}，需 Producer 返回 provenance 属性填充 |
| sequential/simple_hybrid 完全迁移到 expression_runner | 结构性缺口 | 已在 G8 节说明：expression_runner 不支持「上一步命中作为下一步输入」的动态 scope，不可在不改变 Mask 缓存假设的前提下迁移 |
| 真实浏览器 UI 验收 | browser_unavailable | Playwright 未配置，无法做端到端浏览器验收；服务端 HTTP 测试通过 |

---

## 签名

Claude / V6OP 代码师  
V6OP-P2-002 第二阶段过程：正式改建
