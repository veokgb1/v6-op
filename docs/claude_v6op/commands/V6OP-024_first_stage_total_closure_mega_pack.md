# V6OP-024 第一阶段总收口大包

> 指令发出：Codex / V6OP 新架构师  
> 执行对象：Claude / V6OP 新代码师  
> 工作目录：`F:\v.6\v6-op`  
> 报告路径：`F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-024_first_stage_total_closure_mega_pack_report.md`

---

## 一、总目标

本轮把此前拆成多轮的收口任务压缩成一个大包，不再只修 V6OP-023 尾巴。

目标是对齐 `v6-op_full_rescue_charter.md`，完成第一阶段最终收口前的所有结构性缺口：

```text
source -> fetch_plan -> prefetch -> producer -> expression -> report
```

本轮不是新增页面，不是接通全部灰色技能，不是做 DAG 编辑器，也不是复制 V5 Slot 漏斗。

本轮必须一次性处理：

1. 技能资产全量导入与可检测；
2. 内容寻址 Mask 缓存严格化；
3. V6 后台资产继承口径与最小必要接入；
4. 执行图 / 拓扑 / Fetch Planner 架构收敛；
5. 300 预热与真实浏览器验收；
6. 最终签收矩阵预备。

---

## 二、必须完成的 6 个大项

### 大项 1：技能资产全量导入与检测

现状：

- V6 实际技能卡 JSON 是 22 条，不是总纲写的 27 条；
- `scripts/skill_catalog.py` 已出现，`/api/skill_catalog` 已出现，前端也开始动态装载；
- 但尚无 V6OP-024 报告签收；
- 当前 catalog 显示 `v6_total=22, mapped=4, gray=18, live=5`；
- 第一阶段应有 6 个绿色能力：问财、缠论、SMC、K线、波浪、排雷。

要求：

1. 保留并完善 `scripts/skill_catalog.py`，必须以以下 V6 文件为源，不准回到手写灰卡：
   - `F:\v.6\v6\data\skill_connection_cards.json`
   - `F:\v.6\v6\data\raw_skill_sample_cards.json`
2. 输出机器可检测 catalog：
   - `v6_total=22`
   - `declared_total=27`
   - `missing_asset_count=5`
   - `live_count=6`
   - `gray_count` 与实际映射一致
3. 问财必须进入 live 能力口径。建议映射：
   - `hithink-astock-selector -> wencai`
   - 或明确标为 `source_live`，但最终 live 能力必须包含 `wencai`
4. 4 个 V6 技能映射继续保留：
   - `chan-pattern-recognition -> czsc`
   - `smart-money-concepts -> smc`
   - `candlestick-pattern-recognition -> kline`
   - `elliott-wave-engine -> wave`
5. `landmine` 标明是 v6-op 原生 live 能力，不来自 V6 JSON。
6. 缺失的 5 张不能消失，必须进入 `missing_assets` 或等价字段，供最终检测。
7. 前端工具箱：
   - 6 个 live 能力可用；
   - 其余 V6 卡灰色不可勾选；
   - 缺失 5 张可在报告/检测接口中展示，不一定进入主 UI。
8. 测试必须覆盖 catalog 数量、映射、灰卡不可执行、问财 live 口径。

### 大项 2：内容寻址 Mask 缓存严格化

这是总纲第十章的实现原则，本轮必须收口，不再后拖。

现状：

- `scripts/mask_cache.py` 已有雏形；
- 但当前是 SHA1，总纲写 SHA256；
- `data_date` 在不触发 prefetch 时可能为空；
- `algo_version` 集中写在 `mask_cache.py`，总纲要求来自技能算法版本；
- 没有接入 V6 `mask_store.py`。

要求：

1. fingerprint 改为 SHA256。
2. fingerprint 字段必须包含：
   - `skill_id`
   - sorted `scope_codes`
   - sorted serialized `params`
   - `data_date`，来自本轮实际读取的 K 线缓存最大日期，不得只依赖 prefetch_report
   - `algo_version`
3. 每个 live producer 文件内定义算法版本，例如：
   - `ALGO_VERSION = "1.0.0"`
4. `mask_cache.py` 从 producer 模块读取 `ALGO_VERSION`，不要只维护集中硬编码版本。
5. 若能安全适配 V6 `mask_store.py`，用它保存或记录 Mask；如不接，必须在报告中说明第一阶段为什么只读参考，以及后续接入点。
6. 必须新增或调整测试：
   - 同输入同日期 hit；
   - 参数变化 miss；
   - scope 变化 miss；
   - data_date 变化 miss；
   - algo_version 变化 miss；
   - `prefetch_triggered=False` 时 data_date 仍真实有效。

### 大项 3：V6 后台资产继承口径与最小必要接入

总纲不是只要 v6-op 自己跑通，还要求承接 V6 后台能力。

请逐项审计并分类：

| V6 资产 | 本轮要求 |
|---|---|
| `contracts.py` | 已部分接入，确认并补测试 |
| `expression_runner.py` | 已部分接入，确认并补测试 |
| `mask_store.py` | 判断是否本轮最小接入；若不接，说明原因 |
| `io_utils.py` | 判断是否可替换当前 JSON 写入；可小步接入 |
| `universe_provider.py` | 判断 source scope 是否应包装 Universe；可小步接入 |
| `secret_masking.py` | 必须用于日志/报告/异常脱敏，或证明当前等价机制 |
| `live_recapture.py` | 问财/真实 API 调用是否应适配引用；若不接，说明原因 |
| `selection_condition.py` | 第一阶段是否只读参考，说明原因 |
| `mask_expression_executor.py` | 是否替代当前 expression path，说明原因 |
| `report_group_summary.py` | 第一阶段报告只读参考，说明原因 |

要求：

1. 形成 `scripts/v6_asset_alignment.py` 或等价检测脚本，输出每项状态：
   - `used_in_mainline`
   - `adapted`
   - `read_only_reference`
   - `deferred_phase`
2. 至少把安全脱敏和 JSON/Mask 存储中容易低风险接入的部分接入或明确拒绝。
3. 报告不能再笼统写"V6 已继承"，必须逐项写证据。

### 大项 4：执行图、拓扑排序、Fetch Planner 架构收敛

总纲第八、第九、第十章要求三路径共用策略依赖图和拓扑执行，不为三路径写三套逻辑。

现状：

- `strategy_graph_builder.py` 有图规格；
- `execution_engine.py` 仍对 `sequential / simple_hybrid / parallel_and` 写了明显分支；
- `fetch_planner.py` 有 `_KLINE_SKILLS` 硬编码；
- `readiness=aborted` 当前只是 warning 后继续跑。

要求：

1. 在不大改 UI 的前提下，把三路径统一为图节点执行，至少做到：
   - 构建统一 execution plan；
   - 节点按依赖顺序执行；
   - 并线节点、顺序节点、EXCLUDE 节点都在 plan 里表达；
   - `execution_engine.py` 不再有三套业务逻辑大分支，最多保留 path -> graph 构建差异。
2. 实现最小拓扑排序或等价稳定排序，并在报告中解释。
3. Fetch Planner 从 skill metadata / data_requirement 推导需求，不再依赖 `_KLINE_SKILLS` 硬编码集合。
4. `readiness=aborted` 按总纲处理：
   - 失败率 >20% 时本批不得继续冒充完整分析；
   - 可以返回 aborted 结果和报告，但不要继续跑 Producer 当作完成。
5. 测试覆盖：
   - 三路径最终语义不回退；
   - graph/topological plan 可检查；
   - Fetch Planner 新增技能 metadata 后能自动识别数据需求；
   - aborted 不继续执行 Producer。

### 大项 5：300 预热、真实浏览器、GBK warning

要求：

1. `verify_prefetch_300.py` 必须支持 timeout 后写 partial JSON，并清理 worker。
2. 必须运行：

```powershell
python scripts\verify_prefetch_300.py --limit 20 --workers 2 --json-out output\verification\v6op024_prefetch_smoke.json
python scripts\verify_prefetch_300.py --limit 300 --workers 8 --timeout 240 --json-out output\verification\v6op024_prefetch_300.json
```

300 结果只能是三种之一：

- `pass`
- `timeout`
- `fail`

不能含糊，不能把脚本就绪写成通过。

3. 新增真实浏览器 smoke。若 Playwright 可用，真实打开页面验证：
   - live/gray 技能真实 DOM；
   - 灰卡 disabled；
   - 参数修改、本地保存、刷新回显；
   - manual 小股票池运行；
   - 日志、预热摘要、结果区、失败/stale 区。
4. 若 Playwright 不可用，输出 `browser_unavailable` JSON，HTTP smoke 只能叫 HTTP smoke，不得冒充浏览器通过。
5. 清理 pytest 中 Windows GBK 子进程解码 warning。

### 大项 6：第一阶段最终签收预备矩阵

本轮最后必须输出两张矩阵：

1. 第十三节 15 条验收矩阵；
2. 总纲实现原则矩阵，至少包含：
   - V6 后台资产继承；
   - V5 真实数据闭环继承；
   - 技能卡 22/27/缺失 5 的检测口径；
   - 内容寻址；
   - 拓扑执行；
   - Fetch Planner 数据需求；
   - 参数回显；
   - 300 预热；
   - 浏览器验收。

这不是最终签收报告，但必须为下一轮最终签收扫清事实矛盾。

---

## 三、本轮禁止

禁止：

- 不接通全部灰色技能的真实执行；
- 不新增页面；
- 不做任意 DAG 编辑器；
- 不修改 `F:\v.6\v5.10`；
- 不修改 `F:\v.6\v6`；
- 不复制 V5 Slot 漏斗；
- 不伪造 wencai、300 预热、浏览器验收；
- 不把 HTTP smoke 写成真实浏览器验收。

---

## 四、必须运行的验收命令

至少运行：

```powershell
pytest -q
node --check web/app.js
python scripts\skill_catalog.py
python scripts\verify_prefetch_300.py --limit 20 --workers 2 --json-out output\verification\v6op024_prefetch_smoke.json
python scripts\verify_prefetch_300.py --limit 300 --workers 8 --timeout 240 --json-out output\verification\v6op024_prefetch_300.json
```

真实浏览器脚本按实际命名运行，并写出 JSON。若不可用，也必须写出 `browser_unavailable` JSON。

如新增 V6 资产检测脚本，也必须运行并报告输出。

---

## 五、报告要求

报告必须写入：

```text
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-024_first_stage_total_closure_mega_pack_report.md
```

报告必须包含：

1. 修改文件清单；
2. 6 个大项逐项状态；
3. 22/27 技能资产导入检测结论；
4. 6 个 live 能力清单，必须含 wencai；
5. 内容寻址是否严格闭合；
6. V6 资产逐项继承矩阵；
7. 拓扑执行 / Fetch Planner / aborted 语义修正证据；
8. 300 预热结果；
9. 真实浏览器结果或 browser_unavailable；
10. pytest 是否还有 GBK warning；
11. 哪些内容仍属于后续阶段，不得混入第一阶段。

签名：

```text
Claude / V6OP 新代码师
V6OP-024 第一阶段总收口大包
```
