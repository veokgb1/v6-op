# V6OP-028 板块联动只读审计报告

**审计时间：** 2026-05-05  
**审计类型：** 只读审计，无代码修改  
**审计范围：** V5 板块联动逻辑 vs V6OP 当前来源解析 + 执行链路  
**命令来源：** `docs/claude_v6op/commands/V6OP-028_v5_presets_favorites_wave_slot_parity.md`

---

## 一、已读文件清单

| 文件 | 用途 |
|------|------|
| `F:\v.6\v5.10\web\index.html` lines 710–820 | V5 Phase A HTML结构（板块联动 UI） |
| `F:\v.6\v5.10\web\index.html` lines 1118–1182 | V5 PRESET_QUERIES(P1-P6)、SLOT_OPTIONS、init() |
| `F:\v.6\v5.10\web\index.html` lines 1329–1473 | V5 `_slot1Mode`/`_confirmedSectors`、`scanSectors()`、`confirmAndRun()` |
| `F:\v.6\v5.10\web\index.html` lines 1478–1571 | V5 `buildRunConfig()`、`startPipeline()` |
| `F:\v.6\v5.10\web\index.html` lines 2199–2388 | V5 收藏 CRUD（`FAV_KEY`/`FAV_SECTOR_KEY`） |
| `scripts/source_resolver.py` | V6OP 来源解析（仅支持 manual/all_a/wencai） |
| `scripts/v6op_server.py` | V6OP 后端路由清单 |
| `scripts/execution_engine.py` | V6OP 执行链路（step 1 调 source_resolver） |
| `web/app.js` | V6OP 前端 buildStrategy()、saveParams()、SKILL_META |
| `web/index.html` | V6OP 当前 UI（三种来源 radio） |

---

## 二、V5 板块联动架构还原

### 2.1 数据流（两阶段）

```
Phase A — 板块扫描
  前端 UI: 板块模式 textarea + sector-top-n + scan 按钮 + checklist
  → scanSectors()
  → POST /api/scan_sectors { query, top_n }
  → 返回 sector 候选列表
  → 用户勾选 → confirmAndRun()
  → _confirmedSectors = checked sectors (存入内存变量)
  → 调用 startPipeline()

Phase B — 个股选股
  buildRunConfig()
  → Slot 1 type = BUILTIN-WENCAI
  → params.slot1_mode  = "sector"
  → params.confirmed_sectors = _confirmedSectors
  → params.sector_query = <textarea value>
  → params.sector_top_n = <select value>
  → POST /api/run { strategy, slots: [{slot_n:1, skill_id:"BUILTIN-WENCAI", params:{...}}] }
```

### 2.2 V5 的 slots 格式（与 V6OP 不兼容）

```json
{
  "strategy": "...",
  "slots": [
    {
      "slot_n": 1,
      "skill_id": "BUILTIN-WENCAI",
      "params": {
        "slot1_mode": "sector",
        "confirmed_sectors": ["银行", "半导体"],
        "sector_query": "净利润增速大于20%",
        "sector_top_n": 10
      }
    }
  ]
}
```

### 2.3 V5 收藏键名

| localStorage Key | 用途 |
|-----------------|------|
| `openclaw_v5_favorites` | Phase B 个股收藏（问财 query） |
| `openclaw_v5_sector_favorites` | Phase A 板块扫描收藏（sector query） |

---

## 三、V6OP 当前执行链路审计

### 3.1 来源层（source_resolver.py）

支持的 `source_type`：

| type | 行为 |
|------|------|
| `manual` | 直接返回 codes 列表 |
| `all_a` | 从 A股数据库取 codes（limit 参数） |
| `wencai` | 调用问财 API，返回问财筛选后 codes |

**第136行**：任何其他 `source_type` → 立即返回 error，执行链在此终止（readiness=aborted）。

### 3.2 执行链顺序

```
POST /api/run
  → execution_engine.execute()
    [Step 1] source_resolver.resolve(source_type, ...)   ← 来源层
    [Step 2] fetch_planner.build_plan(codes, ...)        ← 数据计划层
    [Step 3] data_prefetch.run_prefetch(plan, ...)       ← 预热层
    [Step 4] producers × N                               ← 技能产出层
    [Step 5] expression_engine                           ← 表达式聚合层
    [Step 6] report_writer                               ← 报告层
```

### 3.3 前端 buildStrategy() 格式（V6OP）

```json
{
  "source": { "type": "wencai", "query": "净利润增速大于20%", "limit": 50 },
  "skills": ["czsc", "smc"],
  "path_type": "parallel_and",
  "params": { "skills": { "czsc": {}, "smc": {} } }
}
```

**无 slots，无 slot1_mode，无 confirmed_sectors。**

### 3.4 后端路由清单（v6op_server.py）

| Method | Route | 存在 |
|--------|-------|------|
| GET | /api/health | ✅ |
| GET | /api/result | ✅ |
| GET | /api/stream | ✅ |
| GET | /api/skill_catalog | ✅ |
| POST | /api/run | ✅ |
| POST | /api/scan_sectors | ❌ 不存在 |

---

## 四、审计结论（逐问作答）

### Q1：板块联动接入 V6OP 哪一层？

**结论：必须接入 source 层，通过 wencai source_type 进行。**

V5 的 Phase B 最终产物是一个「由板块筛选后确定的问财 query」。板块联动的职责是：帮助用户从"板块维度"精炼问财 query，而不是绕过问财接口。

因此在 V6OP 中，Phase A 板块扫描的结果，应当转化为 Phase B 的 wencai query，送入已有的 `wencai` source_type。V6OP 的 source 层无需感知"sector"概念。

---

### Q2：是否会绕开现有 source_resolver？

**否。正确实现不会绕开 source_resolver。**

错误路径（禁止）：
- 新增 `sector` source_type → source_resolver 内部直接处理板块扫描 → 破坏单一职责，且 source_resolver 不应调用外部问财两次
- 在 execution_engine 里直接注入 codes 绕过 source_resolver → 破坏链路一致性，readiness/缓存/report 均依赖 source_resolver 的输出格式

正确路径（推荐）：
- Phase A 在**前端**完成（或新增独立后端接口 `/api/scan_sectors`，仅供前端查询）
- Phase A 结果（板块名列表）由前端转化为 wencai query（如 `所属板块:银行 OR 所属板块:半导体，净利润增速大于20%`）
- Phase B 以普通 `wencai` source_type 调用 POST /api/run
- source_resolver 完全感知不到"板块"概念

---

### Q3：是否会破坏 readiness / 缓存 / report？

**只要通过 wencai source_type 接入，不会破坏任何现有机制。**

- **readiness**：source_resolver 的 wencai 分支已有完整就绪判断逻辑，无需改动
- **Mask 缓存**：缓存 key = skill_id + scope_codes + params + data_date + algo_version；codes 由 wencai 返回后正常进入 fetch_planner，缓存逻辑不变
- **report_writer**：report 依赖 `producer_results`，不关心 codes 来源，无影响

**风险点**（仅当实现错误时发生）：
- 若 Phase A 结果直接变成 codes 列表注入 execution_engine（绕过 source_resolver），则 readiness 状态将不准确，source_type 字段在 report 中会显示错误
- 若新增 `sector` source_type 但未处理 readiness 的 aborted 分支，可能导致链路在无数据时继续运行

---

### Q4：是否应新增 source_type，还是转换成普通 wencai source？

**结论：最终必须转换成普通 wencai source，不应新增 sector source_type。**

原因：
1. V6OP source 层的设计原则是"来源类型 = 数据获取方式"，而非"来源类型 = 选股策略"
2. `sector` 实质上是一个问财 query 的构建辅助，不是一种新的数据获取方式
3. 新增 source_type 会导致 source_resolver 扩张、readiness 分支增加、report 字段增加，成本高且无必要
4. V5 的 Phase B 最终也是通过 BUILTIN-WENCAI 接口送出，与此结论一致

---

### Q5：/api/scan_sectors 是否已有等价能力？若没有，最小安全实现是什么？

**V6OP 当前不存在 `/api/scan_sectors`。**

V5 的 `/api/scan_sectors` 做的事情：接收 `{ query, top_n }`，返回板块候选列表（sector names），供前端勾选。

V6OP 的**最小安全实现方案**（审计建议，不实现代码）：

```
新增后端路由：GET 或 POST /api/scan_sectors
  输入：{ query: str, top_n: int }
  行为：调用问财 API 的板块接口（或 wencai sector 查询）
  输出：{ sectors: ["银行", "半导体", ...], count: N, source: "wencai" }
  约束：
    - 此接口只查询，不触发 execution_engine
    - 不写入任何缓存（scan 结果是临时的）
    - 不影响 /api/run 链路
    - 错误时返回 { sectors: [], error: "..." }，前端降级
```

注意：若问财无板块级接口，可用"行业板块归属"字段的 distinct 值近似替代。  
**此接口须与 execution_engine 完全隔离，是独立的查询端点。**

---

### Q6：P1-P6、问财收藏、板块收藏哪些可以先做纯前端，哪些必须联调后端？

| 功能 | 层次 | 能否纯前端 | 说明 |
|------|------|-----------|------|
| **P1-P6 预设** | 纯前端 | ✅ 可以 | 硬编码 query 字符串填入问财输入框，不需要后端 |
| **问财收藏（个股 query）** | 纯前端 | ✅ 可以 | localStorage 存取，key = `v6op_wencai_favorites`；完全不涉及后端 |
| **板块扫描收藏（sector query）** | 纯前端 | ✅ 可以 | localStorage 存取，key = `v6op_sector_favorites`；仅存 query 字符串，不存 scan 结果 |
| **Phase A 板块 scan 执行** | 前端+后端 | ❌ 必须联调 | 需要 `/api/scan_sectors` 才能返回候选板块列表 |
| **Phase B 转化为 wencai run** | 前端逻辑+现有后端 | ✅ 可以 | confirmed_sectors → 构造 wencai query → POST /api/run（现有接口） |
| **波浪标签清理（去"辅助"/"弱信号"）** | 纯前端 | ✅ 可以 | 修改 `web/app.js` 中 `SKILL_META.wave.isWeak` 逻辑，前端 CSS/label 即可 |

**优先级建议（与命令文件 V6OP-028 一致）：**

```
优先级 1：P1-P6 预设        → 纯前端，可立即做，风险为零
优先级 2：问财收藏           → 纯前端，可立即做
优先级 3：板块收藏（query）  → 纯前端，可立即做（不依赖 scan 接口）
优先级 4：Phase A 板块 scan  → 需新增 /api/scan_sectors（后端最小实现）
优先级 5：方案保存（strategy favorites）→ 纯前端 + 确认 buildStrategy() 格式稳定
优先级 6：波浪标签清理       → 纯前端，1-2行改动
```

---

## 五、集成风险总结

| 风险项 | 级别 | 说明 |
|--------|------|------|
| 误新增 `sector` source_type | 高 | 会导致 source_resolver 扩张、readiness 逻辑分叉，应禁止 |
| scan_sectors 旁路 execution_engine | 高 | 必须是独立查询端点，绝不能触发 execute() |
| V5 slots 格式直接复用 | 高 | V6OP 不接受 slots 格式，前端不能复制 V5 buildRunConfig() |
| Phase A 结果未转化就送 run | 中 | 需要前端明确做 confirmed_sectors → wencai query 转化步骤 |
| localStorage key 冲突 | 低 | V6OP 应使用新 key（`v6op_*`），避免与 V5 `openclaw_v5_*` 混用 |

---

## 六、下一步建议（供 Codex 架构师决策）

1. **立即可做（纯前端，无后端变更）**：
   - 在 `web/index.html` / `web/app.js` 中实现 P1-P6 预设按钮
   - 实现问财收藏 CRUD（key = `v6op_wencai_favorites`）
   - 实现板块 query 收藏 CRUD（key = `v6op_sector_favorites`，仅存 query 字符串）
   - 去掉 wave 的"辅助"/"弱信号"标签（`SKILL_META.wave.isWeak = false` 或移除该 flag）

2. **需后端最小实现（新增独立接口，不改 execution_engine）**：
   - 实现 `GET /api/scan_sectors?query=...&top_n=10` 或等价 POST
   - 与 execution_engine 完全隔离

3. **禁止事项（本轮及后续）**：
   - 不新增 `sector` source_type
   - 不改动 execution_engine 的 step 1（source_resolver 调用）
   - 不将 V5 的 slots 格式引入 V6OP 前端

---

## 七、审计签收

| 项目 | 结果 |
|------|------|
| 有无代码修改 | 无 |
| 有无新增接口 | 无 |
| 有无改动 source_resolver | 无 |
| 有无改动 execution_engine | 无 |
| 有无改动 web/app.js | 无 |
| 审计报告已写 | ✅ 本文件 |

**审计结论：V5 板块联动可以安全接入 V6OP，核心路径是 Phase A 独立查询 + Phase B 转换为 wencai source。现有 source_resolver / execution_engine / report 链路无需改动。**

---

*V6OP-028 只读审计，Claude 代码师执行，2026-05-05*
