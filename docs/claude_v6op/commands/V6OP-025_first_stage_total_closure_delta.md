# V6OP-025 第一阶段总纲收口 Delta 包

> 指令发出：Codex / V6OP 新架构师  
> 执行对象：Claude / V6OP 新代码师  
> 工作目录：`F:\v.6\v6-op`  
> 报告路径：`F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-025_first_stage_total_closure_delta_report.md`

---

## 一、执行背景

V6OP-024 已按当时下发的五项验收偏差命令完成，详见 Codex 复核。V6OP-025 不是纠正 Claude 上轮跑偏，而是在 V6OP-024 之后继续推进总纲结构缺口。

请先读取：

```text
F:\v.6\v6-op\v6-op_full_rescue_charter.md
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-024_codex_architect_review.md
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-024_v6op023_acceptance_fixes_report.md
```

本轮不是写报告，不是新增页面，不是接通全部灰卡，不是复制 V5.10 漏斗。

本轮目标：把 V6OP-024 命令范围之外、但总纲第一阶段仍要求闭合的结构缺口压缩为一个 delta 包完成。

---

## 二、必须完成的 6 个开发大项

### 大项 1：技能 catalog 总纲口径闭合

当前问题：

- `scripts/skill_catalog.py` 输出 `live_count=5`；
- `hithink-astock-selector` 仍是灰卡；
- 缺失 5 张技能资产没有机器可检测口径。

要求：

1. `scripts/skill_catalog.py` 继续以 V6 JSON 为源：
   - `F:\v.6\v6\data\skill_connection_cards.json`
   - `F:\v.6\v6\data\raw_skill_sample_cards.json`
2. 映射并输出 6 个 live 能力：
   - `hithink-astock-selector -> wencai`
   - `chan-pattern-recognition -> czsc`
   - `smart-money-concepts -> smc`
   - `candlestick-pattern-recognition -> kline`
   - `elliott-wave-engine -> wave`
   - `landmine` 标记为 v6-op 原生能力。
3. 输出字段必须包含：
   - `v6_total=22`
   - `declared_total=27`
   - `missing_asset_count=5`
   - `missing_assets` 列表或等价字段
   - `live_count=6`
   - `gray_count` 与实际一致
4. 前端 6 个 live 能力可用，其余 V6 卡灰色 disabled；缺失 5 张不一定进入主 UI，但必须能被报告/检测接口看到。
5. 测试覆盖：wencai live、22/27、missing 5、灰卡不可执行。

### 大项 2：内容寻址 Mask cache 严格闭合

当前问题：

- `mask_cache.py` 仍是 SHA1；
- `ALGO_VERSIONS` 集中写在 `mask_cache.py`；
- producer 文件没有 `ALGO_VERSION`；
- 300 统计公式把 recovered 重复加进 total。

要求：

1. fingerprint 改为 SHA256。
2. fingerprint 字段保持包含：
   - `skill_id`
   - sorted `scope_codes`
   - sorted serialized `params`
   - 当前 K 线缓存真实 `data_date`
   - `algo_version`
3. 在 5 个 live producer 文件中定义 `ALGO_VERSION = "1.0.0"`：
   - `scripts/producers/czsc_producer.py`
   - `scripts/producers/smc_producer.py`
   - `scripts/producers/kline_producer.py`
   - `scripts/producers/wave_producer.py`
   - `scripts/producers/landmine_producer.py`
4. `mask_cache.py` 从 producer 模块读取 `ALGO_VERSION`，不要再只维护集中硬编码版本。
5. 审计 V6 `mask_store.py`：
   - 能安全接入则接入；
   - 若不接，必须报告第一阶段不接的原因和后续接入点。
6. 修正 `scripts/verify_prefetch_300.py` 的统计口径：`recovered_count` 只能作为说明字段，不能在已加回 `fetched_ok` 后再次计入 total/failure_rate。
7. 测试覆盖：同输入 hit、参数变化 miss、scope 变化 miss、data_date 变化 miss、algo_version 变化 miss、prefetch_triggered=False data_date 有效、300 统计不重复。

### 大项 3：V6 后台资产继承矩阵与最小接入

要求新增或完善 `scripts/v6_asset_alignment.py`，逐项输出：

```text
used_in_mainline
adapted
read_only_reference
deferred_phase
evidence
```

必须审计这些 V6 文件：

```text
F:\v.6\v6\scripts\v6\contracts.py
F:\v.6\v6\scripts\v6\expression_runner.py
F:\v.6\v6\scripts\v6\mask_store.py
F:\v.6\v6\scripts\v6\io_utils.py
F:\v.6\v6\scripts\v6\universe_provider.py
F:\v.6\v6\scripts\v6\secret_masking.py
F:\v.6\v6\scripts\v6\live_recapture.py
F:\v.6\v6\scripts\v6\selection_condition.py
F:\v.6\v6\scripts\v6\mask_expression_executor.py
F:\v.6\v6\scripts\v6\report_group_summary.py
```

至少低风险处理：

- 安全脱敏：接入或证明当前日志/报告/异常已有等价脱敏；
- JSON/Mask 存储：接入或明确第一阶段只读参考；
- 不能再笼统写“V6 已继承”，必须逐项给证据。

### 大项 4：执行图、拓扑排序、Fetch Planner、aborted 语义收敛

当前问题：

- `execution_engine.py` 仍有三路径业务大分支；
- `fetch_planner.py` 仍有 `_KLINE_SKILLS` 硬编码；
- `readiness=aborted` 仍是警告后继续执行。

要求：

1. 形成统一 execution plan：
   - path 只负责构建 graph/plan；
   - producer 执行按 plan 节点顺序走；
   - sequential、simple_hybrid、parallel_and 都表达为节点和依赖；
   - EXCLUDE/landmine 也在 plan 中表达。
2. 实现最小拓扑排序或等价稳定排序，输出可测试 plan。
3. `execution_engine.py` 不再保留三套 producer 业务执行大分支，最多保留 path -> graph/plan 构建差异。
4. `fetch_planner.py` 从 `skill_registry.py` 的 `data_requirement` 或等价 metadata 推导需求，不再依赖 `_KLINE_SKILLS`。
5. `readiness=aborted` 时返回 aborted 结果和报告，不继续运行 producer 冒充完整分析。
6. 测试覆盖三路径语义不回退、拓扑 plan 可检查、metadata 新增技能能自动触发/不触发预热、aborted 不执行 producer。

### 大项 5：验收脚本与真实验收

必须运行：

```powershell
pytest -q
node --check web/app.js
python scripts\skill_catalog.py
python scripts\v6_asset_alignment.py --json-out output\verification\v6op025_v6_asset_alignment.json
python scripts\verify_prefetch_300.py --limit 20 --workers 2 --json-out output\verification\v6op025_prefetch_smoke.json
python scripts\verify_prefetch_300.py --limit 300 --workers 8 --timeout 240 --json-out output\verification\v6op025_prefetch_300.json
python scripts\browser_smoke_playwright.py --json-out output\verification\v6op025_browser_smoke.json
```

浏览器验收口径：

- 如果 Playwright 可用，必须真实 DOM/localStorage/运行区验收；
- 如果不可用，输出 `browser_unavailable`，不得写真实浏览器通过；
- HTTP smoke 只能叫 HTTP smoke。

### 大项 6：状态文档与最终签收预备

更新：

```text
docs/claude_v6op/current_status.md
docs/claude_v6op/latest_report.md
```

要求：

1. 不再停留在 V6OP-022 “最终签收”旧口径；
2. 记录 V6OP-023、V6OP-024、V6OP-025 的真实进度；
3. 输出两张矩阵：
   - 第十三节 15 条验收矩阵；
   - 总纲实现原则矩阵。
4. 明确哪些是第一阶段已闭合，哪些属于后续阶段，不要混淆。

---

## 三、禁止事项

禁止：

- 新增页面；
- 做任意 DAG 编辑器；
- 接通全部灰色技能真实执行；
- 修改 `F:\v.6\v5.10` 或 `F:\v.6\v6`；
- 复制 V5.10 Slot 漏斗；
- 伪造 wencai、300、浏览器验收；
- 把 HTTP smoke 写成真实浏览器；
- 只写报告不改代码。

---

## 四、报告要求

写入：

```text
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-025_first_stage_total_closure_delta_report.md
```

报告必须包含：

1. 修改文件清单；
2. 6 个大项逐项状态；
3. 6 个 live 能力清单，必须含 wencai；
4. 22/27/缺失 5 的机器检测结果；
5. Mask cache SHA256 / ALGO_VERSION / V6 mask_store 结论；
6. V6 资产继承矩阵；
7. execution plan / topological sort / Fetch Planner / aborted 的代码证据；
8. 300 预热 JSON 摘要，且统计不得重复计数；
9. 浏览器 JSON 摘要；
10. pytest/node 结果；
11. current_status/latest_report 更新摘要；
12. 明确下一轮是否可进入最终签收。

签名：

```text
Claude / V6OP 新代码师
V6OP-025 第一阶段总纲收口 Delta 包
```
