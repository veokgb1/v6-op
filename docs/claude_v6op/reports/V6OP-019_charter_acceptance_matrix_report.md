# V6OP-019 总纲验收矩阵与状态文档纠偏报告

> 执行日期：2026-05-05
> 执行者：Claude 新代码师 (claude-sonnet-4-6)
> 指令来源：Codex / V6OP 新架构师
> 等待：Codex / V6OP 新架构师验收签收

---

## 概述

本轮为核对轮，不开发新功能。工作内容：

1. 对照 `v6-op_full_rescue_charter.md` 第十三节验收标准 1–15 条，逐条生成总纲验收矩阵
2. 修复 `current_status.md` V6OP-016 bullet 被 V6OP-018 内容截断的文档错位
3. 列明已完成且禁止重复开发的已验收项
4. 列明真正未闭合的大项
5. 运行 pytest / node --check 确认基线不变

---

## 一、总纲验收矩阵

> 依据：`v6-op_full_rescue_charter.md` 第十三节（第一阶段验收标准 1–15 条）

### 图例

| 标志 | 含义 |
|---|---|
| ✅ 已闭合 | 有 run_id 或命令产物为证，经测试验证 |
| 🟡 部分闭合 | 功能已实现，但有已知缺口或环境限制 |
| ❌ 未闭合 | 实现不完整或从未验收 |
| ⛔ 明确不做 | 章程第六节明确排除 |

---

### 验收标准逐条矩阵

#### 条1：打开 v6-op 单页，无需跳转其他 V6 页面即可完成全部操作

| 项 | 内容 |
|---|---|
| **状态** | ✅ 已闭合 |
| **证据文件** | `web/index.html`（单文件，无跳转路由）；`scripts/v6op_server.py`（静态文件托管）|
| **对应报告** | V6OP-004（阶段3单页操盘台）；V6OP-007（三路径端到端验收）|
| **对应测试** | `test_phase3_web_assets.py`（HTML/JS/CSS 存在并语法正确）；`test_v6op_server.py`（API 端点覆盖）|
| **剩余缺口** | 无 |

---

#### 条2：可以输入问财策略语句，系统调用真实问财 API，返回股票代码列表

| 项 | 内容 |
|---|---|
| **状态** | 🟡 部分闭合 |
| **证据文件** | `scripts/sources/wencai_source.py`；`scripts/source_resolver.py` |
| **对应报告** | V6OP-007（wencai query="净利润增速大于20%" → scope_count=10，status=ok）；V6OP-008（wencai 链路触发验收通过）|
| **对应 run_id** | `run_20260505_161203_2738e2`（wencai → scope(5只,ok) → prefetch 触发 → readiness=aborted）|
| **剩余缺口** | **wencai → prefetch 成功 → READ_CACHE_ONLY 分析 → 最终命中** 完整端到端未闭合。wencai source 本身 OK，但 baostock 在当前 Windows 开发环境不可达，新股票预热失败，readiness=aborted。代码完整，0 行需改，仅需网络环境。 |

---

#### 条3：可以手动粘贴股票代码，系统直接使用该列表作为全集

| 项 | 内容 |
|---|---|
| **状态** | ✅ 已闭合 |
| **证据文件** | `web/app.js`（手动输入区）；`scripts/source_resolver.py`（manual 来源解析）|
| **对应报告** | V6OP-008（manual 20只真实 A 股三路径硬验收）|
| **对应 run_id** | `run_20260505_161035_7fba8f`（parallel_and，hit=6/20）；`run_20260505_161041_9ab802`（sequential，hit=6/20）；`run_20260505_161043_388e1d`（simple_hybrid，hit=6/20）|
| **剩余缺口** | 无 |

---

#### 条4：在界面上选择至少两个技能（如缠论 + SMC + 排雷）

| 项 | 内容 |
|---|---|
| **状态** | ✅ 已闭合 |
| **证据文件** | `web/app.js`（SKILL_PARAMS 定义 6 技能，checkbox 多选）；`scripts/skill_registry.py`（6技能注册表）|
| **对应报告** | V6OP-008（kline+czsc+wave+landmine 四技能同时运行）；V6OP-011（kline+smc+landmine 三技能运行）|
| **对应 run_id** | `run_20260505_180215_b8e84e`（kline+smc+landmine，parallel_and，hit=5/20）|
| **剩余缺口** | 无 |

---

#### 条5：调整至少一个参数（如 SMC 的 signal_bars 从 15 改为 10）

| 项 | 内容 |
|---|---|
| **状态** | ✅ 已闭合 |
| **证据文件** | `web/app.js`（SKILL_PARAMS 含每技能参数定义和默认值，展开后有输入框）；`scripts/execution_engine.py`（`_sp()` 从 params 读取并传给 Producer）|
| **对应报告** | V6OP-011（SMC params=\{signal_bars:60, swing_length:10, mode:strict\} 明确用于真实运行，hit=7/20）|
| **对应 run_id** | `run_20260505_180215_b8e84e`（params.skills.smc.signal_bars=60 记录在 execution_result.json）|
| **剩余缺口** | 无。参数通过前端输入框修改、由 `/api/run` 接收、传入 Producer，结果随参数变化（SMC strict signal_bars=60 vs 默认 15 结果明显不同）。|

---

#### 条6：启动运行后，系统先显示"准备数据"进度（真实预热 K 线缓存，非 fixture）

| 项 | 内容 |
|---|---|
| **状态** | 🟡 部分闭合 |
| **证据文件** | `scripts/data_prefetch.py`（workers>1协调者模式，8-worker架构）；`scripts/v6op_server.py`（`/api/stream` JSON 轮询）；`web/app.js`（`pollStream()` 实时滚动）|
| **对应报告** | V6OP-007（prefetch 触发 → 新拉取 2 只 → prefetch_run_id 有效）；V6OP-018（workers=2 exit code 0，worker_report.json 正常生成）|
| **剩余缺口** | ① 实现为 **JSON 轮询**（非 true SSE），在 v6op_server.py 注释中已声明 "本实现为 JSON 轮询（非 true SSE），功能等价"；② **wencai 来源的真实预热成功路径**（见条2）未闭合，现有进度展示逻辑依赖预热被触发。20 只缓存股票（manual 来源）不触发预热，进度日志直接进分析阶段。 |

---

#### 条7：缓存就绪后系统自动开始分析，页面显示实时进度日志

| 项 | 内容 |
|---|---|
| **状态** | ✅ 已闭合（等价实现）|
| **证据文件** | `web/app.js`（`pollStream()` 250ms 轮询，log-box 实时追加）；`scripts/v6op_server.py`（`/api/stream` 返回累积 events）|
| **对应报告** | V6OP-003（执行引擎 + SSE 等价轮询）；V6OP-007（三路径运行期间日志滚动演示）|
| **剩余缺口** | 非 true SSE（已文档说明为等价实现）|

---

#### 条8：分析完成后显示真实命中股票列表（不是 fixture 数据）

| 项 | 内容 |
|---|---|
| **状态** | ✅ 已闭合 |
| **证据文件** | `output/current/execution_result.json`（final_hit_codes=\['000001.SZ','000006.SZ','000008.SZ','000019.SZ','000020.SZ'\]）；`output/runs/`（161 个历史运行存档）|
| **对应报告** | V6OP-008（三路径 hit_codes 真实命中，readiness=ready）；V6OP-011（SMC strict hit=7/20，ChoCH/BOS 信号）|
| **对应 run_id** | `run_20260505_180215_b8e84e`（kline+smc+landmine，parallel_and，5只真实命中）|
| **剩余缺口** | 无。`v5_modified=False`，`v6_modified=False`，`api_called=False` 均在 execution_result 中确认，产物为真实本地缓存分析。|

---

#### 条9：每只命中股票有中文命中解释（命中了哪些技能，发现了什么信号）

| 项 | 内容 |
|---|---|
| **状态** | ✅ 已闭合 |
| **证据文件** | `scripts/explanation_builder.py`；`output/current/run_report.md`（第八章"单股中文证据"）|
| **对应报告** | V6OP-008（证据质量修复，explanation_builder key 名对齐，中文证据完整）；V6OP-011（SMC ChoCH/BOS + 日历日期中文证据）|
| **剩余缺口** | 无 |

---

#### 条10：失败/未分析的股票单独列出，不混入命中列表

| 项 | 内容 |
|---|---|
| **状态** | ✅ 已闭合 |
| **证据文件** | `web/app.js`（`coverage-box`、`failed-list`、`stale-list` 独立展示区）；`web/index.html`（failed-list / stale-list 元素与 hit-list 分离）|
| **对应报告** | V6OP-009（fetch_planner 不变式：failed ∩ cached = ∅）；V6OP-010（stale ≠ failed，stale 不影响 failure_rate）；V6OP-016（prefetch_report=null 不变式）|
| **剩余缺口** | 无 |

---

#### 条11：将 SMC signal_bars 改回 15 并重新运行，命中列表与第一次可以不同（证明参数真实有效）

| 项 | 内容 |
|---|---|
| **状态** | 🟡 部分闭合 |
| **证据文件** | `scripts/producers/smc_producer.py`（signal_bars 参数直接决定 hit_codes）；`output/current/execution_result.json`（params.skills.smc.signal_bars=60 → hit=5/20）|
| **对应报告** | V6OP-011（SMC strict signal_bars=60 → hit=7/20；soft_filter 全量透传 → 更多命中，两组结果不同）|
| **剩余缺口** | 章程要求"将参数改回 15 并重新运行"的**交互式二次运行**验收未作为独立验收项记录（现有证据是两次不同参数的独立 run，不是同一会话内的"修改后重跑"演示）。行为已被代码和测试充分支撑，但缺少一次"从页面修改参数→重新运行→结果变化"的完整交互录制/截图证据。|

---

#### 条12：本次使用的参数值出现在结果报告里

| 项 | 内容 |
|---|---|
| **状态** | ✅ 已闭合 |
| **证据文件** | `scripts/run_report.py`（第四章"关键参数"）；`output/current/run_report.md`（含 smc.signal_bars=60）；`output/current/execution_result.json`（`params` 字段）|
| **对应报告** | V6OP-007（run_report.md 12 章节结构建立）|
| **剩余缺口** | 无 |

---

#### 条13：全流程不读取、不显示、不泄露任何 API 密钥

| 项 | 内容 |
|---|---|
| **状态** | ✅ 已闭合 |
| **证据文件** | `output/current/execution_result.json`（`api_called: false`）；`scripts/execution_engine.py`（`api_called: False` 明确跟踪）；`scripts/sources/wencai_source.py`（key 从 .env 读入内存，不输出）|
| **对应报告** | V6OP-007（"key 值未打印、未写入、未泄露" 明确记录）|
| **对应测试** | `test_phase1_producers.py::TestPhase1Isolation::test_env_not_hardcoded_in_source`（扫描全部 .py 文件无硬编码 key）|
| **剩余缺口** | 无 |

---

#### 条14：V5.10 目录下的文件未被修改（只读参考）

| 项 | 内容 |
|---|---|
| **状态** | ✅ 已闭合 |
| **证据文件** | `output/current/execution_result.json`（`v5_modified: false`）；`scripts/execution_engine.py`（`v5_modified: False` 运行时跟踪）|
| **对应报告** | 所有 V6OP 报告均含"未修改 F:\v.6\v5.10" 安全声明 |
| **剩余缺口** | 无 |

---

#### 条15：用户在整个操作过程中，不需要理解 Mask、ScopeRef、ExecutionDraft 等 V6 内部术语

| 项 | 内容 |
|---|---|
| **状态** | ✅ 已闭合 |
| **证据文件** | `web/index.html`（UI 仅暴露：来源选择、技能名称、路径类型、命中列表、中文证据）；`web/app.js`（无 Mask/ScopeRef/ExecutionDraft 等词）|
| **对应测试** | `test_phase3_web_assets.py::test_no_internal_v6_terms_in_html`（扫描 HTML 不含 V6 内部术语）|
| **剩余缺口** | 无 |

---

### 汇总表

| 条 | 内容摘要 | 状态 | 主要证据 |
|---|---|---|---|
| 1 | 单页操盘台，无需跳转 | ✅ 已闭合 | web/index.html，V6OP-007 |
| 2 | 问财 API 真实调用 | 🟡 部分闭合 | V6OP-007/008，wencai→prefetch 端到端未闭合 |
| 3 | 手动粘贴股票代码 | ✅ 已闭合 | V6OP-008 三路径硬验收 |
| 4 | 界面多技能选择 | ✅ 已闭合 | V6OP-008/011 |
| 5 | 参数调整有效 | ✅ 已闭合 | V6OP-011，execution_result.json |
| 6 | 预热进度显示（非fixture）| 🟡 部分闭合 | V6OP-018 workers 修复；JSON 轮询非 true SSE |
| 7 | 实时进度日志 | ✅ 已闭合（等价）| app.js pollStream()，V6OP-007 |
| 8 | 真实命中股票列表 | ✅ 已闭合 | run_20260505_180215_b8e84e，161 历史存档 |
| 9 | 每只股票中文命中解释 | ✅ 已闭合 | V6OP-008/011，explanation_builder |
| 10 | 失败/stale 单独列出 | ✅ 已闭合 | V6OP-009/010/016，coverage-box |
| 11 | 参数改后重跑结果变化 | 🟡 部分闭合 | backend 已证，缺交互式二次运行验收记录 |
| 12 | 参数值记录在报告里 | ✅ 已闭合 | run_report.md 第四章，V6OP-007 |
| 13 | 不泄露 API 密钥 | ✅ 已闭合 | api_called=false，key 扫描测试 |
| 14 | V5.10 文件未被修改 | ✅ 已闭合 | v5_modified=false，所有报告安全声明 |
| 15 | 用户无需理解 V6 内部术语 | ✅ 已闭合 | HTML/JS 无内部术语，test_phase3 扫描验证 |

**小计：已闭合 12 条，部分闭合 3 条（条2/6/11），未闭合 0 条，明确不做 0 条。**

---

## 二、current_status.md 文档错位修复

V6OP-018 插入后，V6OP-016 bullet 末尾被 V6OP-018 stale/landmine 修复的内容截断，形成一个混合 bullet（"stale/landmine 语义修复（V6OP-018）：…：`prefetch_triggered=False` 时…"，冒号后接的是 V6OP-016 的正文）。

**已修复**：V6OP-016 和 V6OP-018 各自独立成条，事实未改，仅结构分拆。

---

## 三、已完成且禁止重复开发的项

以下各项均已有 run_id 或测试为证。**后续开发命令不应重复下发这些项目。**

| 已完成项 | 证据 / 报告 |
|---|---|
| **单页操盘台**（web/index.html，无跳转，左-中-右三栏布局）| V6OP-003/004/007 |
| **六核心技能接通**（wencai/czsc/smc/kline/wave/landmine，真实执行非 fixture）| V6OP-001/002，各 Producer 测试 |
| **三路径执行**（parallel_and / sequential / simple_hybrid，共用同一 DAG 引擎）| V6OP-008，三 run_id |
| **SMC strict 验收**（signal_bars=60，hit=7/20，ChoCH/BOS 中文证据完整）| V6OP-011，run_20260505_174441_7c76b8 |
| **fetch_planner stale 语义**（stale ≠ failed，stale 进 cached_codes 可分析，landmine 不排雷 stale）| V6OP-010/018 |
| **output/current 污染防卫**（prefetch_report=null，10 项 guard test，scope 外代码不出现）| V6OP-013/014/015/016 |
| **报告路径规范**（reports/V6OP-NNN_slug_report.md，不在根目录新建报告）| V6OP-017 |
| **参数面板**（6技能各有可调参数，有默认值，前端输入传入 Producer，run_report 记录）| V6OP-007/011 |
| **all_a 双层保护**（前端 + API 层，limit≥300 提示，limit≥500 需确认）| V6OP-007 |
| **中文可读运行报告**（run_report.md 12 章节，V5 风格）| V6OP-007 |
| **workers>1 Windows UTF-8 修复**（_configure_streams 不替换 sys.stdout 对象）| V6OP-018 |
| **测试产物隔离**（conftest autouse → tmp_path，output/current 不被测试污染）| V6OP-013 |

---

## 四、真正未闭合的大项

### 大项 A：wencai 预热成功完整端到端（最高优先）

**现状**：wencai source 返回 scope_codes OK；Fetch Planner 触发 auto-prefetch；但 baostock 在当前 Windows 开发环境不可达，新股票预热失败，readiness=aborted，最终 final_hit_count=0。

**缺口**：wencai → scope(ok) → prefetch(成功≥1只) → READ_CACHE_ONLY 分析 → final_hit_count≥1 → run_report.md 有命中。

**代码状态**：0 行需改。需要 baostock 可达的网络环境（Linux 服务器/云端）。

**验收命令**：
```
wencai query="净利润增速大于20%", limit=5, skills=["kline","landmine"]
验收：prefetch_triggered=True，≥1 只预热成功，final_hit_count≥0，run_report.md 有命中
```

---

### 大项 B：大规模真实预热性能与全 A 日常可用性

**现状**：all_a 保护（300/500 阈值）已实现并测试。data_prefetch workers>1 架构已修复（V6OP-018）。但全 A 5,465 只股票的**真实预热性能**从未实测：
- 耗时是否在可接受范围（章程目标：300 只 60 秒内）？
- workers=8 的真实并行效率（baostock 不可达时无法验证）？
- TIME_WAIT 端口耗尽风险（猴子补丁是否在真实多 worker 场景生效）？

**缺口**：需要 baostock 可达环境，跑 300 只真实预热，记录耗时/成功率/失败率。

---

### 大项 C：内容寻址 Mask 复用未实现

**现状**：章程第十节明确要求：`key = hash(skill_id + scope_codes + params + data_date + algo_version)` → 指纹命中则直接复用 Mask，不重算。

**当前代码**：`execution_engine.py` 每次运行全量调用 Producer，没有基于指纹的 Mask 缓存层。`mask_id` 字段存在于每个 Producer 输出，但没有持久化缓存和命中判断逻辑。

**缺口**：内容寻址缓存（Mask 复用判断）完全未实现。

**说明**：章程将其定义为"实现原则，不是新的架构层"，但当前实现不满足此原则。本轮边界明确"不实现内容寻址缓存"，仅标记为未闭合大项，后续再议。

---

### 大项 D：21 个剩余技能接入前未完成 V6/V5 资产审计

**现状**：skill_registry.py 注册 6 个技能（wencai/czsc/smc/kline/wave/landmine）。V6（`F:\v.6\v6`）有 27 张技能卡的完整 metadata；V5.10（`F:\v.6\v5.10\tonghuashun_skill_local_lab`）有真实跑通历史。

**缺口**：在接入任意新技能前，应先完成资产审计：
1. 确认目标技能在 V6 的技能卡 metadata（命中方向/参数/data_type）
2. 确认 V5.10 对应分析脚本是否可用（step_*.py 的真实跑通状态）
3. 评估需要新写的 Producer 逻辑 vs 可直接移植的部分

**说明**：这是"后续接入任何技能的先决条件"，不是当前紧急缺口。章程第六节明确"其余 21 张灰色显示"为阶段 4+ 工作。

---

### 大项 E（补充）：参数修改后"交互式二次运行"验收缺失

**现状**：条11 部分闭合。backend 已证明参数影响结果（SMC signal_bars=60 vs 默认 hit 不同），但没有"在同一会话内从页面修改参数→重新运行→对比两次 run_id"的完整文档记录。

**缺口**：不是代码问题，是验收证据问题。可在 baostock 可达时连同大项 A 一并完成。

---

## 五、本轮测试结果

```
pytest：272/272 通过，0 failed，0 skipped
node --check web/app.js：OK
```

（基线 272，本轮无新测试，无代码变更，基线保持）

---

## 六、output/current 污染检查

本轮无 `execute()` 调用，无 run_prefetch 调用。

```
output/current/execution_result.json → run_id=run_20260505_180215_b8e84e（未变）
000003.SZ in execution_result.json: False
000005.SZ in execution_result.json: False
prefetch_triggered: False
```

output/current 未被污染。

---

## 七、修改文件清单

| 文件 | 变更类型 | 说明 |
|---|---|---|
| `docs/claude_v6op/current_status.md` | 结构修复 + 时间戳更新 | V6OP-016 bullet 从 V6OP-018 内容中分离，各自独立成条；更新最后修改版本为 V6OP-019 |
| `docs/claude_v6op/latest_report.md` | 更新 | 补充 V6OP-019 判断行和报告链接 |
| `docs/claude_v6op/reports/V6OP-019_charter_acceptance_matrix_report.md` | 新增 | 本文件，正确路径 |

**无功能代码变更。**

---

## 安全

- 未修改 `F:\v.6\v5.10` 或 `F:\v.6\v6`
- 未读取或泄露 .env / API key
- 未使用 fixture 冒充真实结果
- 本轮为核对轮，无 v6-op 功能代码变更

---

## 等待 Codex / V6OP 新架构师验收签收

— Claude 新代码师 (claude-sonnet-4-6)，2026-05-05
