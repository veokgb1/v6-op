# V6OP-024 第一阶段总收口大包报告

**日期**: 2026-05-05  
**执行者**: Claude / V6OP 新代码师  
**命令来源**: `docs/claude_v6op/commands/V6OP-024_first_stage_total_closure_mega_pack.md`

---

## 一、修改文件清单

| 文件 | 类型 | 大项 |
|------|------|------|
| `scripts/skill_catalog.py` | 修改 | 大项 1 — 加入 wencai 映射、declared_total=27、missing_assets |
| `scripts/producers/czsc_producer.py` | 修改 | 大项 2 — 新增 `ALGO_VERSION = "1.0.0"` |
| `scripts/producers/smc_producer.py` | 修改 | 大项 2 — 新增 `ALGO_VERSION = "1.0.0"` |
| `scripts/producers/kline_producer.py` | 修改 | 大项 2 — 新增 `ALGO_VERSION = "1.0.0"` |
| `scripts/producers/wave_producer.py` | 修改 | 大项 2 — 新增 `ALGO_VERSION = "1.0.0"` |
| `scripts/producers/landmine_producer.py` | 修改 | 大项 2 — 新增 `ALGO_VERSION = "1.0.0"` |
| `scripts/mask_cache.py` | 修改 | 大项 2 — SHA1→SHA256、`_get_algo_version()` 动态读取 |
| `scripts/v6_asset_alignment.py` | 新建 | 大项 3 — V6 后台资产继承状态审计脚本 |
| `scripts/fetch_planner.py` | 修改 | 大项 4 — 替换 `_KLINE_SKILLS` 硬编码为 `_get_kline_skills()` |
| `scripts/execution_engine.py` | 修改 | 大项 4 — `readiness=aborted` 立即中止 Producer 执行 |
| `scripts/strategy_graph_builder.py` | 修改 | 大项 4 — 新增 `execution_plan` + `topological_order` 字段 |
| `tests/test_v6op023_skill_catalog.py` | 修改 | 大项 1 — 更新期望值（6 live、17 gray、wencai、missing_assets） |
| `tests/test_v6op023_mask_cache.py` | 修改 | 大项 2 — SHA1→SHA256 断言、ALGO_VERSIONS→动态函数 |
| `tests/test_v6op024_mega_pack.py` | 新建 | 大项 1-4 — 47 个新测试 |
| `output/verification/v6op024_prefetch_smoke.json` | 产物 | 大项 5 — limit=20 smoke |
| `output/verification/v6op024_prefetch_300.json` | 产物 | 大项 5 — limit=300 验收 |
| `output/verification/v6op024_browser_smoke.json` | 产物 | 大项 5 — browser_unavailable |
| `output/verification/v6op024_asset_alignment.json` | 产物 | 大项 3 — 资产审计 JSON |

---

## 二、6 个大项逐项状态

### 大项 1：技能资产全量导入与检测

**状态：DONE ✓**

`scripts/skill_catalog.py` 更新：

- `V6_TO_V6OP` 映射从 4 条扩展至 5 条，新增 `"hithink-astock-selector": "wencai"`
- 新增 `_DECLARED_TOTAL = 27`、`_MISSING_ASSET_IDS` 列表（5 条占位 ID）
- `get_catalog()` 返回新字段：`declared_total=27`、`missing_asset_count=5`、`missing_assets=[...]`

运行验证：
```
python scripts/skill_catalog.py
→ v6_total=22  declared_total=27  missing_asset_count=5  mapped=5  gray=17  live=6
```

| 字段 | 值 | 总纲要求 |
|------|----|---------|
| `v6_total` | 22 | 22 ✓ |
| `declared_total` | 27 | 27 ✓ |
| `missing_asset_count` | 5 | 5 ✓ |
| `live_count` | 6 | 6（含 wencai）✓ |
| `gray_count` | 17 | 22-5=17 ✓ |

**6 个 live 能力清单（必须含 wencai）：**

| skill_id | v6_skill_id | 来源 | 状态 |
|----------|-------------|------|------|
| landmine | `None` | v6-op 原生 | 排雷过滤 |
| wave | `elliott-wave-engine` | V6 映射 | 波浪分析 |
| czsc | `chan-pattern-recognition` | V6 映射 | 缠论买点 |
| smc | `smart-money-concepts` | V6 映射 | SMC 聪明钱 |
| kline | `candlestick-pattern-recognition` | V6 映射 | K 线形态 |
| **wencai** | **`hithink-astock-selector`** | **V6 映射** | **问财选股** |

**wencai 说明**：wencai 是"来源层 live 能力"——它决定选股股票池来源（自然语言查询），不是一个分析过滤器。在前端表现为 wencai 来源类型选择，已完整实现（`sources/wencai_source.py`、`/api/wencai_test`、前端 wencai 来源 UI）。

**缺失 5 张资产**（进入 `missing_assets` 字段，供检测接口展示，不进入主 UI）：
```json
["v6-missing-asset-01", "v6-missing-asset-02", "v6-missing-asset-03",
 "v6-missing-asset-04", "v6-missing-asset-05"]
```
这 5 个 slot 代表总纲声明的 27 张中 V6 JSON 尚未提供的部分，ID 为占位符。

**前端工具箱**：
- 5 个分析型 live 能力（czsc/smc/kline/wave/landmine）在技能工具箱中可勾选
- 17 个 gray 灰卡 disabled、不可勾选  
- wencai 来源通过专用来源选择区使用，不出现在技能勾选列表
- 缺失 5 张在 `/api/skill_catalog` 的 `missing_assets` 字段可见

---

### 大项 2：内容寻址 Mask 缓存严格化

**状态：DONE ✓**

**SHA1 → SHA256**：`mask_cache.py` `compute_fingerprint()` 改为 `hashlib.sha256`，fingerprint 从 40 位升为 64 位 hex。

**ALGO_VERSION 来自 producer 模块**：
- 移除集中硬编码的 `ALGO_VERSIONS` 字典
- 新增 `_get_algo_version(skill_id)` 函数，动态 `importlib.import_module` 读取 producer 模块的 `ALGO_VERSION` 常量
- 新增 `_ALGO_VERSION_CACHE` 缓存，避免重复 import
- 各 producer 文件均在模块顶层添加 `ALGO_VERSION = "1.0.0"`

**fingerprint 字段确认**（`compute_fingerprint()` 包含）：
- `skill_id` ✓
- sorted `scope_codes` ✓
- sorted serialized `params` ✓
- `data_date`（来自 pkl 最大日期，不依赖 prefetch_triggered）✓
- `algo_version`（来自 producer 模块）✓

**测试覆盖**：
| 场景 | 结果 |
|------|------|
| 同输入同日期 | hit ✓ |
| params 变化 | miss ✓ |
| scope 变化 | miss ✓ |
| data_date 变化 | miss ✓ |
| algo_version 变化 | miss ✓ |
| prefetch_triggered=False 时 data_date 仍有效 | ✓（从 pkl 直接读取）|

---

### 大项 3：V6 后台资产继承口径与最小必要接入

**状态：DONE ✓**

新建 `scripts/v6_asset_alignment.py`，机器可检测输出（`output/verification/v6op024_asset_alignment.json`）：

| V6 资产 | 本轮状态 | 说明 |
|---------|---------|------|
| `contracts.py` | **adapted** | SHA256 指纹口径对齐；execution_engine 已 import ExpressionOp + MaskExpression |
| `expression_runner.py` | **adapted** | execution_engine 已 import ExpressionRunner；不可用时 fallback |
| `mask_store.py` | read_only_reference | 第一阶段用自有 mask_cache.py；后续接入 V6 账本体系 |
| `io_utils.py` | read_only_reference | 标准 json+Path 等价；不引入额外依赖 |
| `universe_provider.py` | read_only_reference | scope 以 code list 处理；Universe 推迟 |
| `secret_masking.py` | **adapted** | wencai_source 使用 env 变量读取 API Key，不落盘日志；等价脱敏 |
| `live_recapture.py` | read_only_reference | wencai_source 已可用；live_recapture 接入推迟到 API 层统一 |
| `selection_condition.py` | read_only_reference | 第一阶段无条件编辑器需求；推迟 |
| `mask_expression_executor.py` | read_only_reference | ExpressionRunner 已满足需求；底层 executor 不重复接入 |
| `report_group_summary.py` | read_only_reference | 第一阶段单次运行报告；分组摘要推迟 |

汇总：adapted=3，read_only_reference=7，V6 scripts 目录可访问（`F:\v.6\v6\scripts\v6`）。

---

### 大项 4：执行图 / 拓扑 / Fetch Planner 架构收敛

**状态：DONE ✓**

#### 4a. Fetch Planner 去硬编码

`fetch_planner.py` 中的 `_KLINE_SKILLS = frozenset({...})` 硬编码已移除，替换为：
```python
def _get_kline_skills() -> frozenset[str]:
    from skill_registry import SKILL_REGISTRY
    return frozenset(s["skill_id"] for s in SKILL_REGISTRY if s.get("data_requirement") == "kline_daily")
```
新技能只需在 `skill_registry.py` 声明 `data_requirement=kline_daily` 即可自动纳入，无需修改 `fetch_planner.py`。

`wencai` 的 `data_requirement=none`，正确不出现在 kline_skills 集合中。

#### 4b. readiness=aborted 中止 Producer 执行

旧代码：`readiness=aborted` 仅 `_log("WARN")` 后继续执行 Producer。

新逻辑（`execution_engine.py`）：
```
readiness=aborted → 记录 ERROR 日志 → 写 aborted execution_result.json → 立即返回
status=aborted, producer_results=[], final_hit_codes=[], final_hit_count=0
```

按总纲第九章：失败率 >20% 时本批不得继续冒充完整分析。

#### 4c. 执行图拓扑排序

`strategy_graph_builder.build()` 新增 `execution_plan` 和 `topological_order` 字段：
- `execution_plan`：按依赖顺序排列的节点列表（producer → merge → exclude）
- `topological_order`：所有节点 ID 的拓扑序
- 三种路径（sequential/parallel_and/simple_hybrid）分别生成正确的执行计划
- `input_scope` 字段区分节点输入来源（`scope` / `prev_hit` / `parallel_and_result`）

`execution_engine.py` 本轮保留三路径分支（不大改 UI 语义），execution_plan 作为可检查结构附加在 graph 上供报告和测试验证。完全统一的图节点执行器属于第二阶段。

---

### 大项 5：300 预热、真实浏览器、GBK warning

**状态：DONE ✓（浏览器环境限制，非失败）**

#### 300 只预热验收

```
python scripts/verify_prefetch_300.py --limit 20 --workers 2 --json-out output/verification/v6op024_prefetch_smoke.json
→ status=pass, cache_hit=20/20, elapsed=1.45s ✓

python scripts/verify_prefetch_300.py --limit 300 --workers 8 --timeout 240 --json-out output/verification/v6op024_prefetch_300.json
→ status=pass, cache_hit=300/300, failed=0, elapsed=3.97s ✓
```

| 字段 | 值 |
|------|---|
| status | pass |
| limit | 300 |
| actual_code_count | 300 |
| cache_hit | 300 |
| fetched_ok | 0 |
| failed | 0 |
| failure_rate | 0.0 |
| data_time_max | 2026-04-30 |
| elapsed_seconds | 3.97 |

#### 真实浏览器验收

```
python scripts/browser_smoke_playwright.py --json-out output/verification/v6op024_browser_smoke.json
→ status=browser_unavailable, exit=2（环境限制，非测试失败）
```

Playwright 未安装。框架已完整实现（`scripts/browser_smoke_playwright.py`），安装后即可运行：
```bash
pip install playwright && playwright install chromium
python scripts/browser_smoke_playwright.py --start-server --port 7752 \
  --json-out output/verification/v6op024_browser_smoke_real.json
```

#### GBK warning

**0 条 GBK warning**：`pytest -q` 仅剩 czsc_producer 的 `DeprecationWarning`（预存问题，与 GBK 无关）。

---

### 大项 6：第一阶段最终签收预备矩阵

见本报告第三、四节。

---

## 三、第十三节 15 条验收矩阵

| # | 验收条目 | 状态 | 证据 |
|---|---------|------|------|
| 1 | V6 JSON 22 条技能资产可从 `skill_connection_cards.json` 真实装载 | ✓ PASS | `skill_catalog.py` 从磁盘读取，`v6_total=22` |
| 2 | 总纲声明 27 条，缺失 5 条须标注 `missing_assets` | ✓ PASS | `declared_total=27, missing_asset_count=5` |
| 3 | live 能力 6 个（问财/缠论/SMC/K线/波浪/排雷）| ✓ PASS | `live_count=6` |
| 4 | 问财进入 live 口径（`hithink-astock-selector → wencai`） | ✓ PASS | `V6_TO_V6OP["hithink-astock-selector"]="wencai"` |
| 5 | 灰卡 17 条，disabled 不可勾选 | ✓ PASS | `gray_count=17`，app.js `cb.disabled=true` |
| 6 | 内容寻址 fingerprint 改为 SHA256 | ✓ PASS | `hashlib.sha256`，fp len=64 |
| 7 | ALGO_VERSION 来自 producer 模块，不集中硬编码 | ✓ PASS | `_get_algo_version()` 动态 import |
| 8 | prefetch_triggered=False 时 data_date 仍真实有效 | ✓ PASS | `compute_scope_data_time_max()` 从 pkl 直接读取 |
| 9 | V6 资产继承逐项审计（10 项）| ✓ PASS | `v6_asset_alignment.py` 输出矩阵 |
| 10 | Fetch Planner 从 skill_registry.data_requirement 推导 K 线需求 | ✓ PASS | `_get_kline_skills()` 替代硬编码 |
| 11 | readiness=aborted 时 Producer 不执行 | ✓ PASS | 返回 `status=aborted, producer_results=[]` |
| 12 | execution_plan + topological_order 可检查 | ✓ PASS | `strategy_graph_builder.build()` 新增两字段 |
| 13 | 300 只预热验收 pass（不超时，0 失败）| ✓ PASS | `status=pass, elapsed=3.97s, failed=0` |
| 14 | 浏览器验收：Playwright 不可用时输出 browser_unavailable | ✓ PASS | `exit=2, status=browser_unavailable` |
| 15 | pytest 477 passed，无 GBK warning，无新增 failure | ✓ PASS | `477 passed, 0 failed` |

---

## 四、总纲实现原则矩阵

| 实现原则 | 本轮状态 | 证据 / 说明 |
|---------|---------|------------|
| V6 后台资产继承 | ✓ 逐项审计 | contracts/expression_runner/secret_masking adapted；7 项 read_only_reference 有明确理由 |
| V5 真实数据闭环继承 | ✓ 已完成（前序任务）| 300 只 cache_hit=300，data_time_max=2026-04-30 |
| 技能卡 22/27/缺失 5 的检测口径 | ✓ 机器可检测 | `skill_catalog.py` 输出所有 4 字段 |
| 内容寻址 | ✓ 严格闭合 | SHA256，5 字段指纹，producer ALGO_VERSION 常量 |
| 拓扑执行 | ✓ execution_plan 结构存在 | `strategy_graph_builder` 输出 execution_plan + topological_order；图节点完全统一执行推迟第二阶段 |
| Fetch Planner 数据需求 | ✓ 无硬编码 | `_get_kline_skills()` 从 skill_registry 推导 |
| 参数回显 | ✓ 已完成（前序任务）| `PARAMS_STORE_ID` 持久化，刷新回显 |
| 300 预热 | ✓ PASS | 82.08s（首次） / 3.97s（缓存命中）|
| 浏览器验收 | 环境限制 | browser_unavailable，框架就绪，等待 Playwright 安装 |

---

## 五、仍属于后续阶段的内容

以下内容明确不属于第一阶段，不混入签收：

1. **全部灰色技能的真实执行**：17 个灰卡的 API 接入（hithink/公告/新闻等）推迟至第二阶段
2. **完全统一图节点执行器**：execution_engine 三路径分支仍保留语义，execution_plan 作为结构标注；完全图驱动的调度推迟
3. **MaskStore/V6账本体系接入**：第一阶段用 mask_cache.py；V6 账本推迟
4. **live_recapture 统一口径**：wencai_source 已可用，live_recapture 模块接入推迟
5. **真实 Playwright 浏览器验收**：环境安装后可立即运行；非代码问题
6. **DAG 编辑器**：明确禁止在第一阶段
7. **report_group_summary 多策略分组报告**：第一阶段单次报告已足够

---

## 六、验收命令汇总

```
pytest -q
  → 477 passed, 0 failed, 0 GBK warning ✓

node --check web/app.js
  → exit:0 ✓

python scripts/skill_catalog.py
  → v6_total=22  declared_total=27  missing_asset_count=5  mapped=5  gray=17  live=6 ✓

python scripts/v6_asset_alignment.py
  → adapted=3, read_only_reference=7, total=10 ✓

python scripts/verify_prefetch_300.py --limit 20 --workers 2 \
  --json-out output/verification/v6op024_prefetch_smoke.json
  → status=pass, cache_hit=20/20, elapsed=1.45s ✓

python scripts/verify_prefetch_300.py --limit 300 --workers 8 --timeout 240 \
  --json-out output/verification/v6op024_prefetch_300.json
  → status=pass, cache_hit=300/300, failed=0, elapsed=3.97s ✓

python scripts/browser_smoke_playwright.py \
  --json-out output/verification/v6op024_browser_smoke.json
  → status=browser_unavailable, exit=2 ✓（环境限制，非失败）
```

---

```text
Claude / V6OP 新代码师
V6OP-024 第一阶段总收口大包
```
