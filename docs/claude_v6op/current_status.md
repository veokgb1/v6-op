# V6OP 当前状态

> 最后更新：2026-05-05 by Claude 新代码师 (claude-sonnet-4-6)（V6OP-026 第一阶段最终签收）

## 阶段进度

| 阶段 | 内容 | 状态 |
|---|---|---|
| 阶段 0 | 数据引擎 + K线预热 + CZSCProducer | 完成 |
| 阶段 1 | 6 个 Producer 接通 | 完成 |
| 阶段 2 | Fetch Planner + 执行引擎 + 后端 API | 完成（经 V6OP-006/006b 纠偏）|
| 阶段 3 | 单页操盘台 + 参数面板 + 证据展开 | **真实验收闭合**（V6OP-007 三路径端到端通过）|
| 阶段 4 | 问财来源 + 全 A 扫描保护 + 可读报告增强 + 证据质量 | **第一阶段全面闭合**（V6OP-022 最终签收，wencai 主链 run_20260505_200356_9bafd7）|
| 总纲结构补全 | 技能 catalog / Mask SHA256 / V6 资产矩阵 / Fetch Planner / aborted / 拓扑结构 | **V6OP-024 大包完成，V6OP-025 补正收口**（见下方）|
| **第一阶段最终签收** | 第十三节 15 条验收标准复核 + 全量验收命令运行 | **V6OP-026 最终签收完成**（2026-05-05，pytest 481/0, 300 只 PASS）|

## 当前真实状态

### V6OP-022 之前已验收通过（摘要）

- **manual 多技能三路径硬验收**：20 只真实 A 股，kline+czsc+wave+landmine，parallel_and / sequential / simple_hybrid 三路径均命中 6 只，readiness=ready。
- **wencai 完整主链验收通过**（V6OP-021 + Codex 追加）：run_id=run_20260505_200356_9bafd7，fetched_ok=5，failed=0，final_hit=3（300083.SZ / 688400.SH / 688256.SH），data_time_max=2026-04-30。
- **V5.10 真实数据闭环经验对齐**（V6OP-020）：recovery pass / 门控修复 / wencai 归因细化 / 数据新鲜度报告。pytest 279/279（+7）。
- **实时进度推送 + Prefetch Parity + 双参数重跑**（V6OP-021）：_log_sink + server 注入 + 前端预热摘要区 + verify_wencai_e2e.py。pytest 299/299（+20）。
- **V6OP-022 最终签收**：15 条验收标准全部闭合，pytest 297 passed / 2 skipped（条件性 skip），node --check 通过。

### V6OP-023 至 V6OP-025 补全项

#### V6OP-023（5 项验收偏差修复）

已按 Codex 复核列出的 5 项偏差完成：
1. `verify_prefetch_300.py` dry-run + timeout 路径修复
2. `mask_cache.py` data_date 不依赖 prefetch_triggered（compute_scope_data_time_max 独立读取 .pkl 缓存）
3. execution_engine.py `readiness=aborted` 提前返回（不继续执行 Producer）
4. fetch_planner.py 去除 `_KLINE_SKILLS` 硬编码 → 读取 skill_registry data_requirement
5. skill_catalog.py 新增 declared_total=27 / missing_asset_count=5 字段

#### V6OP-024（第一阶段总收口大包）

6 个大项全部完成：

**大项 1：技能 catalog 总纲口径**
- v6_total=22，declared_total=27，missing_asset_count=5
- live_count=6（czsc / smc / kline / wave / landmine / **wencai**）
- wencai 映射：hithink-astock-selector → wencai（source-tier live 能力）
- gray_count=17（V6 JSON 中未映射的卡片，灰色不可执行）
- 缺失 5 张（v6-missing-asset-01 ~ 05）进入 missing_assets 字段，可机器检测

**大项 2：内容寻址 Mask cache 严格化**
- fingerprint 从 SHA1 改为 SHA256（64 位 hex）
- 5 个 live producer 文件定义 `ALGO_VERSION = "1.0.0"`（czsc/smc/kline/wave/landmine）
- mask_cache.py 动态 importlib 读取 ALGO_VERSION，不再维护集中硬编码版本字典
- compute_scope_data_time_max 独立读取 .pkl DatetimeIndex，prefetch_triggered=False 时 data_date 仍有效
- 5 维度 miss 测试全部覆盖（同输入 hit、参数/scope/data_date/algo_version 变化 miss）

**大项 3：V6 后台资产继承矩阵**
- `scripts/v6_asset_alignment.py` 审计 10 个 V6 资产
- adapted=3（contracts.py / expression_runner.py / secret_masking.py）
- read_only_reference=7（mask_store / io_utils / universe_provider / live_recapture / selection_condition / mask_expression_executor / report_group_summary）
- 各项均有 evidence 字段，不再笼统写"V6 已继承"

**大项 4：执行图 / 拓扑 / Fetch Planner / aborted 语义**
- `fetch_planner.py` 移除 `_KLINE_SKILLS` 硬编码 → `_get_kline_skills()` 读 skill_registry
- `execution_engine.py`：readiness=aborted → 写 aborted execution_result.json → 立即返回，producer_results=[]
- `strategy_graph_builder.build()` 新增 `execution_plan` 和 `topological_order` 字段（可检查结构）
- **注意（拓扑执行口径）**：execution_plan / topological_order 是附加的可检查结构，**execution_engine.py 本轮仍保留三路径分支业务逻辑**。完全统一的图节点执行器属于第二阶段，**第一阶段不声明"拓扑执行完全闭合"**。

**大项 5：300 预热 + 浏览器验收**
- verify_prefetch_300.py 支持 timeout 后写 partial JSON，workers_cleaned
- 20 只 smoke 跑通（见 output/verification/v6op024_prefetch_smoke.json）
- 300 只预热（见 output/verification/v6op024_prefetch_300.json）
- 真实浏览器：Playwright 不可用 → browser_unavailable JSON（HTTP smoke 不冒充浏览器验收）

**大项 6：签收预备矩阵**
- 第十三节 15 条验收矩阵输出（均已闭合）
- 总纲实现原则矩阵输出

#### V6OP-025（补正收口 Delta 包）

4 个补正点：

1. **补正点1**：恢复命令文件断链 → 创建 `docs/claude_v6op/commands/V6OP-024_first_stage_total_closure_mega_pack.md`（原命令文件缺失）
2. **补正点2**：修正 `verify_prefetch_300.py` 统计公式 → `total = cache_hit + fetched_ok + failed`（移除重复计入的 recovered_count；recovered 已被 _apply_recovery 折算进 fetched_ok）；新增 TestVerifyPrefetch300RecoveredFormula 4 项测试
3. **补正点3**：拓扑执行口径明确 → 在 current_status.md 中明确 execution_plan/topological_order 为可检查结构，不声明"拓扑执行完全闭合"；图节点统一执行属于第二阶段
4. **补正点4**：更新 current_status.md / latest_report.md 至 V6OP-025 级别（移除"最后更新：V6OP-022"旧口径）

### 技能 catalog 当前口径

| 字段 | 值 |
|---|---|
| v6_total | 22（V6 JSON 实际卡片数） |
| declared_total | 27（总纲声称总数） |
| missing_asset_count | 5（v6-missing-asset-01 ~ 05，可机器检测） |
| live_count | 6（czsc / smc / kline / wave / landmine / wencai） |
| gray_count | 17（V6 未映射卡片，灰色 disabled） |

### 拓扑执行口径（补正点3）

| 能力 | 状态 | 说明 |
|---|---|---|
| execution_plan 可检查结构 | ✅ 已闭合（第一阶段） | strategy_graph_builder.build() 输出 |
| topological_order 可检查结构 | ✅ 已闭合（第一阶段） | 节点 ID 按拓扑序排列 |
| 图节点统一执行器（替换三路径分支） | ⏳ 推迟第二阶段 | execution_engine.py 仍有三路径业务逻辑 |

### 浏览器验收口径

真实浏览器（Playwright）：当前环境不可用 → `browser_unavailable` JSON 输出。HTTP smoke 不等于真实浏览器验收，两者不混淆。

## 当前待闭合（明确属于第二阶段）

| 项目 | 原因 |
|---|---|
| 全部灰色技能（18 个 V6 映射 + landmine 之外）真实执行 | 第二阶段技能接入 |
| 图节点统一执行器（替换 execution_engine 三路径分支） | 第二阶段架构收敛 |
| Playwright 真实浏览器 DOM/localStorage 验收 | 环境限制，第二阶段 |
| mask_store.py 接入（V6 mask 存储） | 第一阶段只读参考，第二阶段接入 |
| DAG 编辑器 | 明确不做 |

## 测试状态

- V6OP-022 基线：297 passed / 2 skipped / 0 failed
- V6OP-023/024 新增约 50+ 测试（test_v6op024_mega_pack.py 等）
- V6OP-025 补正：新增 TestVerifyPrefetch300RecoveredFormula 4 项测试
- node --check：通过

## 报告路径规范（V6OP-017 确立）

- 所有任务报告必须写入 `docs/claude_v6op/reports/` 子目录
- 文件名格式：`V6OP-NNN_<slug>_report.md`（全小写 slug，下划线分隔）

## 当前禁止（本轮范围边界）

- 不接通全部灰色技能（第二阶段接入，须先审计 V6 资产和 V5.10 历史）
- 不做任意 DAG 编辑器
- 不新增页面
- 不修改 `F:\v.6\v5.10` 或 `F:\v.6\v6`（只读复用）
- 不复制 `.env` / `.venv`
- 不泄露密钥
- 不用 HTTP smoke 冒充真实浏览器验收
- 不声明"拓扑执行完全闭合"（图节点统一执行属第二阶段）
