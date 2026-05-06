# 009 第一阶段综合评估报告

> 作者：Claude 分析员（架构讨论角色）
> 日期：2026-05-06
> 本文基于直接阅读代码，不基于报告转述。证据清单见附录 B。
> 规则：文档结论 ≠ 代码事实；代码优先。

---

## 第一部分：总结论

**第一阶段真实状态：骨架已立，但有至少 5 个代码级缺陷会在真实运营中造成误判。**

V6OP 第一阶段完成了一个可运行的单页操盘台骨架，6 个 live 技能接通，三种执行路径可跑，K线本地数据库机制在位，内容寻址技能结果库已实现。这是第一阶段实打实的成果。

但以下 5 个缺陷不是"风险"，而是**已确认的代码级错误**，在真实运行中会静默产生错误结果：

1. **wencai api_key 不传**：`wencai_source.py` 接收了 key 但从不传给 `pywencai.get()`，问财请求永远以未授权方式发出。
2. **czsc 回看天数硬编码**：`czsc_producer.py` 的 `_analyze_one()` 里固定 `days=365`，用户设置的 days 参数被硅默忽略，但仍影响 mask_cache 指纹，导致缓存永不复用。
3. **fetch_planner 收不到 lookback_days**：`execution_engine.py` 两次调用 `fetch_planner.plan()` 均不传 `lookback_days`，永远检查 `{code}_365d.pkl`，即使用户设置了 `days=730` 也会认为 K 线已足够（实为检查错误文件名）。
4. **SMC 默认模式双轨**：`skill_registry.py` 默认 `soft_filter`，`execution_engine.py` 硬编码 `"strict"`，同一次运行中参数读取方不同，行为不可预期。
5. **ohlcv_provider 写缓存失败静默吞掉**：`_write_cache()` 有 `except Exception: pass`，写入失败不记录、不警告、不上报，数据丢失用户无感知。

V6OP-026 宣布的"15/15 大纲验收条目全部关闭"在技术意义上不成立——上述缺陷让验收条目背后的保证失效。

---

## 第二部分：大纲要求了什么

根据 `v6-op_full_rescue_charter.md`，第一阶段核心要求（15 个验收条目）涵盖：

| 编号 | 核心要求 |
|------|---------|
| 条1 | 页面可用：单页操盘台，来源→参数→启动→结果完整动线 |
| 条2 | 问财真实闭环：问财 key 真实传递，能返回股票池，能驱动后续技能 |
| 条3 | 全A来源：本地A股名单可用，数量与档位对齐 |
| 条4 | 三路径执行：sequential / parallel_and / simple_hybrid 可运行 |
| 条5 | 6 个 live 技能：wencai/czsc/smc/kline/wave/landmine 全部接通 |
| 条6 | 流式状态：运行日志实时反馈，不是阻塞等待 |
| 条7 | 参数面板：主要技能参数可在 UI 设置，不需要改代码 |
| 条8 | K线两阶段隔离：网络取数阶段 / 纯本地分析阶段分离 |
| 条9 | 内容寻址缓存：同一批股票+参数+数据日期，技能结果可复用 |
| 条10 | 排雷负向语义：排雷命中 = 应剔除，不混入最终命中 |
| 条11 | abort 可中止 |
| 条12 | 报告：run_report.json / run_report.md 可生成 |
| 条13 | 密钥不泄露 |
| 条14 | pytest 481+ 通过 |
| 条15 | 前端语法检查通过 |

大纲章程第 8 章（执行路径）要求三路径最终结果必须与报告表达式一致。
大纲第 9 章（数据取数）要求 baostock → akshare → yfinance → 旧K线 的四级降级链路。
大纲第 10 章（内容寻址缓存）要求指纹由 skill_id + 排序后的 codes + params + data_date + algo_version 构成。

---

## 第三部分：报告声称了什么

### V6OP-019（2026-05-05，已被 V6OP-026 取代）

- 声称 12 条全关闭，3 条部分关闭
- 特别声称"内容寻址 Mask 复用**未实现**"

**代码裁定：V6OP-019 关于 mask_cache 未实现的判断是错误的，该报告是过期文档。**

### V6OP-026（最终第一阶段签收报告）

- 声称**15/15 全部关闭**
- pytest 481 passed，node --check 通过
- 300 只预热 smoke PASS（全部 cache_hit，new_fetch=0，耗时 4.1s）
- wencai 主链关闭（run_20260505_200356_9bafd7，final_hit=3）
- 明确注记：图执行统一节点是 Phase 2 任务，Playwright browser_unavailable

**代码裁定：**
- pytest 481 passed：无法从外部验证，但测试覆盖率和测试质量未见证据
- 300 只预热 PASS：**smoke 在 cache_hit=300 下跑**，等于没有测试真实 baostock 取数路径
- wencai 主链：code review 发现 api_key 不传给 pywencai，成功的 run_20260505_200356 可能是 pywencai 用了其他机制（如 cookie/session 持久化）而非 key 注入
- 条9（内容寻址缓存）：`mask_cache.py` 已实现，V6OP-026 的声称正确
- 条4（三路径）：sequential/hybrid 最终结果绕过 expression_runner，报告表达式和执行代码不在同一路径

---

## 第四部分：代码实际显示什么

以下均为直接读取代码所得，附文件和行号。

### 4.1 wencai api_key 不传（已确认缺陷）

- `wencai_source.py:121`：`_query_wencai(query, api_key, limit)` 函数签名接收 `api_key`
- `wencai_source.py:147-152`：`pywencai.get(...)` 调用体中**没有 api_key 参数**
- `wencai_source.py:252-258`：`run()` 从 .env 读取 key，判断是否空，然后调用 `_query_wencai`，但 key 在 `pywencai.get()` 层被丢弃
- 分类完整（auth_failed/network_error/api_error/empty_result）：正确
- `source_resolver.py:114-146`：调用 `_wencai_source.run()` 后只提取 `scope_codes` 和 `status`，丢弃 `query_hash`、`elapsed_s`、`api_called` 诊断字段

### 4.2 czsc 回看天数硬编码（已确认缺陷）

- `czsc_producer.py:294`：`run()` 接收 `days: int = 365` 参数
- `czsc_producer.py:324`：调用 `_analyze_one(code, signal_bars, buy_type)`——`days` 未传入
- `czsc_producer.py:184`：`_analyze_one()` 签名无 `days` 参数
- `czsc_producer.py:199`：`df = fetch_ohlcv(code, days=365, verbose=False)`——**硬编码 365**
- 对比：`smc_producer.py:244`：`df = fetch_ohlcv(code, days=days, ...)` — 正确传递
- 对比：`kline_producer.py:262`：`df = fetch_ohlcv(code, days=days, ...)` — 正确传递
- 影响：czsc days 参数进入 `mask_cache` 指纹（hash 不同），但实际取的 K 线永远是 365 天，导致指纹变化但数据不变，缓存永不命中

### 4.3 fetch_planner 永不收到 lookback_days（已确认缺陷）

- `fetch_planner.py:64`：`plan()` 有 `lookback_days: int = 365` 默认参数
- `fetch_planner.py:141`：`cache_file = cache_dir / _cache_fname(code, lookback_days)` — 用 lookback_days 查文件
- `execution_engine.py:359-363`：第一次调用 `fetch_planner.plan()` — **不传 lookback_days**
- `execution_engine.py:449-453`：第二次调用 `fetch_planner.plan()` — **不传 lookback_days**
- 结果：用户在 UI 设 `days=730`，prefetch 写 `{code}_730d.pkl`，但 fetch_planner 检查 `{code}_365d.pkl`，永远"够用"假象

### 4.4 SMC 默认模式双轨（已确认缺陷）

- `skill_registry.py:56`：SMC `mode` 默认值 `"soft_filter"`
- `execution_engine.py:553`：`smc_params.get("mode", "strict")` — 默认 `"strict"`
- 结果：`soft_filter` 模式会让 SMC 透传所有股票（命中 = 输入量），`strict` 模式只保留有 BOS/ChoCH 信号的股票；两个默认值不一致，同一次运行行为取决于哪边覆盖了哪边

### 4.5 写缓存失败静默（已确认缺陷）

- `ohlcv_provider.py:195-200`：`_write_cache()` 的 `except Exception: pass` — 任何写失败静默吞掉
- 影响：磁盘满、路径错误、权限问题时 K 线缓存写失败，系统继续运行，但下次会重取，与"本地已有"假设不符

### 4.6 execution_engine sequential/hybrid 绕过 expression_runner（架构问题）

- `execution_engine.py:663`：sequential 路径分支
- `execution_engine.py:703`：simple_hybrid 路径分支
- `execution_engine.py:752`：parallel_and 路径分支
- `execution_engine.py:780-790`：sequential/hybrid 最终结果用 `pre_exclude_codes` 集合操作，**不经过 expression_runner**
- `execution_engine.py:792-811`：parallel_and 使用 expression_runner（或降级）
- `strategy_graph_builder.py:149`（注释）：execution_plan "不执行 producer，用于报告可检查性"
- 结果：报告中的 `expression_spec`（如 `czsc AND kline MINUS landmine`）和 sequential/hybrid 的实际执行逻辑不在同一代码路径，报告表达式是文档性的，不是驱动性的

### 4.7 FAST_FULL_SCAN 下无三源降级（设计选择，但文档不透明）

- `ohlcv_provider.py:317`（docstring）：FAST_FULL_SCAN = `新鲜缓存 → baostock → None`
- `ohlcv_provider.py:342-356`：FAST_FULL_SCAN 下 baostock 失败直接返回 `None`，无 akshare/yfinance 降级
- `ohlcv_provider.py:358-385`：标准模式有完整四级链路
- `data_prefetch.py:91`：`os.environ["FAST_FULL_SCAN"] = "true"` — worker 线程全部走 FAST_FULL_SCAN
- V6OP-026 预热 smoke 是 cache_hit=300 跑的，等于未测试 FAST_FULL_SCAN 下 baostock 失败时的行为

### 4.8 scope_id 截断（轻微，但影响缓存正确性）

- `source_resolver.py:47-49`：`_make_scope_id()` 用 `codes[:30]` 做 hash
- 影响：30 只以上的股票池，scope_id 仅由前 30 只决定，不同大池可能得到相同 scope_id

### 4.9 compute_scope_data_time_max 无 days 参数（衍生缺陷）

- `mask_cache.py:130`：`compute_scope_data_time_max(codes, cache_dir, days=365)` 有参数
- `execution_engine.py:472-478`：调用时**不传 days**，永远读 `{code}_365d.pkl`
- 影响：数据新鲜度检测基于错误文件，`data_time_max` 字段可能显示错误的最新 K 线日期

### 4.10 内容寻址 mask_cache 已实现（确认文档一致）

- `mask_cache.py`：`compute_fingerprint()`、`cache_get()`、`cache_put()`、`compute_scope_data_time_max()` 全部实现
- 指纹构成：skill_id + sorted_codes + params + data_date + algo_version
- V6OP-019 的"未实现"判断错误，V6OP-026 的"已实现"判断正确

### 4.11 前端三层数据标记已对齐（确认文档一致）

- `app.js:29-62`：`HELP_TEXT` 已包含 `data-markers`、`source-snapshot`、`kline-db`、`skill-result-store` 四组帮助文字
- 用语：★ 来源快照 / ★★ K线数据库 / ★★★ 技能结果库 — 与 V6OP-032 规范对齐

---

## 第五部分：仅结构完成项

以下项目存在代码骨架，但因上述缺陷而承诺无法兑现：

| 项目 | 骨架状态 | 实际缺陷 |
|------|---------|---------|
| 问财真实取数 | 代码路径存在 | api_key 从不传给 pywencai |
| K线回看天数端到端 | 参数从 UI 传到 engine | czsc 硬编码 / fetch_planner 收不到 |
| 内容寻址缓存 | mask_cache.py 完整实现 | czsc 指纹不稳定，data_time_max 读错文件 |
| expression_runner 统一驱动 | parallel_and 用了 | sequential/hybrid 绕过 |
| V5 三源降级 | 标准模式有完整链路 | FAST_FULL_SCAN（预热主路径）无降级 |

---

## 第六部分：重大问题与风险

### 级别 P0（静默产生错误结果）

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| P0-1 | wencai api_key 不传 | `wencai_source.py:147` | 问财请求以未授权方式发出，有时靠 session 持久化成功；key 设置无效 |
| P0-2 | czsc days 硬编码 365 | `czsc_producer.py:199` | 用户设置 days 参数被忽略，但 mask_cache 指纹变化，缓存永不命中 |
| P0-3 | fetch_planner 不收 lookback_days | `execution_engine.py:359,449` | K线"够用"判断永远基于 `{code}_365d.pkl`，days!=365 时判断错误 |

### 级别 P1（影响结果可信度）

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| P1-1 | SMC 默认模式双轨 | `skill_registry.py:56`, `execution_engine.py:553` | 行为取决于调用路径，soft_filter vs strict 结果差异巨大 |
| P1-2 | sequential/hybrid 绕过 expression_runner | `execution_engine.py:780-790` | 报告表达式 ≠ 执行逻辑，不可信赖报告表达式还原实际命中条件 |
| P1-3 | FAST_FULL_SCAN 无三源降级 | `ohlcv_provider.py:342-356` | baostock 失败时直接 None，无 akshare/yfinance 兜底 |
| P1-4 | compute_scope_data_time_max 不传 days | `execution_engine.py:472` | 数据新鲜度日期读错文件，显示可能有误 |

### 级别 P2（运行质量）

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| P2-1 | 写缓存失败静默 | `ohlcv_provider.py:195` | 磁盘满等故障无提示 |
| P2-2 | source_resolver 丢弃诊断字段 | `source_resolver.py:114` | query_hash/elapsed_s/api_called 不进报告，无法排查"为什么返回 0" |
| P2-3 | scope_id 截断 30 | `source_resolver.py:47` | 大池 scope_id 非唯一 |

---

## 第七部分：大纲需要重新解释的地方

### 7.1 条2（问财真实闭环）

大纲措辞是"问财 key 真实传递，能返回股票池"。V6OP-026 用一次成功运行（final_hit=3）宣布关闭。但这次成功可能依赖 pywencai 自己的 session 持久化，不是 key 驱动的。

**建议重新解释**：条2 验收要求加入"能在 key 全新环境（清空 session）下通过 key 参数成功授权并取回结果"。仅凭一次有结果不足以关闭。

### 7.2 条9（内容寻址缓存）

大纲要求指纹由 skill_id + 排序 codes + params + data_date + algo_version 构成。`mask_cache.py` 已实现，但 `czsc_producer` 的 days 参数进了指纹却不影响实际取数，产生了"指纹变化但数据不变"的悖论。

**建议重新解释**：条9 验收需加入"指纹中的 days 参数与实际 fetch_ohlcv(days=) 的参数一致"的测试用例。

### 7.3 条4（三路径执行结果与表达式一致）

大纲第 8 章明确要求三路径最终结果和报告表达式一致。当前代码 sequential/hybrid 用集合操作，parallel_and 用 expression_runner，不在同一路径。

**建议重新解释**：在 graph execution 统一节点完成之前，条4 应该标记为"结构可运行，但报告表达式与执行代码存在双轨，后续 Phase 2 统一"，而不是已关闭。

### 7.4 V5 三源降级（大纲第 9 章）

大纲要求 baostock → akshare → yfinance → 旧K线。代码中标准模式有完整链路，FAST_FULL_SCAN 无降级。但预热阶段（data_prefetch.py）强制 FAST_FULL_SCAN。

**建议重新解释**：大纲对三源降级的要求适用于"真实数据缺失时的兜底"，而不仅限于标准模式。应明确哪些场景允许跳过降级，哪些不允许。

---

## 第八部分：修订后的验收结论

| 条目 | V6OP-026 声称 | 代码裁定 | 修订状态 |
|------|------------|---------|---------|
| 条1：页面可用 | 关闭 | 代码证实 | ✅ 关闭 |
| 条2：问财真实闭环 | 关闭 | api_key 不传，一次成功不足以关闭 | ⚠️ **重新开启** |
| 条3：全A来源 | 关闭 | 代码结构在位 | ✅ 关闭 |
| 条4：三路径执行 | 关闭 | 可运行，但 sequential/hybrid 绕过 expression_runner | ⚠️ **降为部分关闭** |
| 条5：6 live 技能 | 关闭 | 代码证实 6 个接通 | ✅ 关闭 |
| 条6：流式状态 | 关闭（JSON 轮询，非 SSE） | 代码确认是 JSON 轮询，主动标注可接受 | ✅ 关闭（已标注） |
| 条7：参数面板 | 关闭 | 代码证实参数在 UI 可设置 | ✅ 关闭 |
| 条8：K线两阶段隔离 | 关闭 | producers 均设 READ_CACHE_ONLY=true | ✅ 关闭 |
| 条9：内容寻址缓存 | 关闭 | mask_cache.py 已实现，但 czsc 悖论存在 | ⚠️ **降为部分关闭** |
| 条10：排雷负向语义 | 关闭 | landmine hit_semantics=negative 代码证实 | ✅ 关闭 |
| 条11：abort 可中止 | 关闭 | 结构在位，未深度验证 | ✅ 接受（标注待核实） |
| 条12：报告生成 | 关闭 | run_report.py 代码证实 | ✅ 关闭 |
| 条13：密钥不泄露 | 关闭 | 报告生成中未见明文 key | ✅ 关闭 |
| 条14：pytest 481+ | 关闭 | 无法从代码层核实，接受历史声称 | ✅ 接受 |
| 条15：前端语法检查 | 关闭 | 无法从代码层核实，接受历史声称 | ✅ 接受 |

**修订结论：15 条中 11 条可确认关闭，2 条需要重新开启（条2/条9部分），1 条降为部分关闭（条4）。**

---

## 第九部分：第二阶段优先级

### 9.1 必须先修的代码缺陷（第二阶段入场前）

优先级排序基于：影响正确性 > 影响可信度 > 影响质量。

**P0 级，必须先修：**

1. **修复 czsc_producer 硬编码 days=365**
   - `czsc_producer.py:184`：`_analyze_one` 加 `days` 参数
   - `czsc_producer.py:199`：`fetch_ohlcv(code, days=days, ...)`
   - `czsc_producer.py:324`：传入 days

2. **修复 execution_engine 传 lookback_days 给 fetch_planner**
   - `execution_engine.py:359,449`：计算实际 max_days，传入 `fetch_planner.plan(lookback_days=max_days)`
   - `execution_engine.py:472`：`compute_scope_data_time_max(codes, cache_dir, days=max_days)`

3. **确认或修复 wencai api_key 传递路径**
   - 先测试：在清空 pywencai session 后，只靠 .env key 是否能成功取回结果
   - 如果不能：`wencai_source.py` 的 `pywencai.get()` 调用需补 key 参数

**P1 级，第二阶段早期：**

4. **统一 SMC 默认模式**：`execution_engine.py:553` 改为 `smc_params.get("mode", "soft_filter")`，与 skill_registry 对齐

5. **修复写缓存静默失败**：`ohlcv_provider.py:195` 的 `except` 改为至少 `warnings.warn()` 或写 error log

6. **source_resolver 保留诊断字段**：`source_resolver.py:114` 传递 `query_hash`、`api_called` 进入 run_context

### 9.2 第二阶段架构方向

以下是基于本轮代码阅读的架构建议，供讨论，不是施工命令：

**方向 A：expression_runner 统一三路径**（V6OP-026 明确列为 Phase 2）
- 当前 sequential/hybrid 用集合操作绕过 expression_runner
- 完成 strategy_graph_builder.py 的"执行节点"功能
- 让报告 expression_spec 与执行代码真正对齐

**方向 B：Data Provider Adapter 层**（架构讨论中提出）
- 当前 `_FETCHERS = [("baostock", ...), ("akshare", ...), ("yfinance", ...)]` 是 proto-adapter
- 将其正式化为 `DataProviderAdapter`，统一接口
- 好处：FAST_FULL_SCAN 的"仅 baostock"可以成为一个配置而非 if/else 分支

**方向 C：解释层（中文 bridge）**
- `explanation_builder.py` 已有每只股票的中文解释骨架
- 缺少的是"全局解释"：为什么总命中数为 0？哪一层在哪里截断了？下一步怎么办？
- 建议后端生成结构化解释字段（source_explain / kline_explain / skill_explain），前端展示

**方向 D：问财 Bridge Capability 定位**（架构讨论中提出）
- 当前 wencai 既是来源层，也有潜力作为下游筛选器
- 代码上已有分离：wencai_source.py 只做取池，execution_engine 负责路径
- 是否将 wencai 正式设计为可复用的 Bridge Capability，取决于是否有"先跑技能再回问财验证"的真实需求

---

## 附录 A：文档-代码对齐表

| 大纲/验收条目 | 文档声称 | 代码证据 | 判断 | 状态 |
|-------------|--------|---------|------|------|
| 条2 问财真实闭环 | V6OP-026: 关闭，run_20260505 final_hit=3 | `wencai_source.py:147` api_key 不传 pywencai | 成功可能靠 session 而非 key | ⚠️ 重新开启 |
| 条4 三路径执行 | V6OP-026: 关闭 | `execution_engine.py:780-790` sequential 不走 expression_runner | 可运行，但报告表达式与执行双轨 | ⚠️ 部分关闭 |
| 条8 K线两阶段隔离 | V6OP-026: 关闭 | producers 均 `os.environ["READ_CACHE_ONLY"]="true"` | 代码证实 | ✅ 关闭 |
| 条9 内容寻址缓存 | V6OP-026: 关闭（V6OP-019: 未实现）| `mask_cache.py` 完整实现；czsc days 不传导致指纹悖论 | 实现存在，但 czsc 缓存无效 | ⚠️ 部分关闭 |
| czsc days 端到端 | V6OP-030: 高风险 | `czsc_producer.py:199` 硬编码 365 | 确认缺陷 | ❌ 未修复 |
| fetch_planner lookback | V6OP-030: 高风险 | `execution_engine.py:359` 不传 lookback_days | 确认缺陷 | ❌ 未修复 |
| SMC 默认模式 | V6OP-032: 需对齐 | `skill_registry:soft_filter` vs `engine:strict` | 确认双轨 | ❌ 未修复 |
| V5 三源降级 | V6OP-030: 高风险 | `data_prefetch.py:91` FAST_FULL_SCAN 无降级 | 标准模式有，预热无 | ⚠️ 部分关闭 |
| 写缓存失败 | V6OP-030: 高风险 | `ohlcv_provider.py:195` except: pass | 确认静默 | ❌ 未修复 |
| 三层数据标记 | V6OP-032: 规范 | `app.js:29-62` HELP_TEXT 已对齐 | 前端已对齐 | ✅ 关闭 |
| mask_cache 实现 | V6OP-019: 未实现; V6OP-026: 已实现 | `mask_cache.py` 完整 | V6OP-019 是过期文档 | ✅ V6OP-026 正确 |

---

## 附录 B：实际读取的证据文件

本报告基于以下文件的直接阅读，不依赖报告转述：

**文档类：**
- `v6-op_full_rescue_charter.md`
- `V6OP-019_charter_acceptance_matrix_report.md`
- `V6OP-026_final_first_stage_signoff_report.md`
- `V6OP-030_full_logic_risk_audit.md`
- `V6OP-031_phase1_work_summary_report.md`
- `V6OP-032_code_alignment_guidelines_report.md`

**代码类：**
- `scripts/source_resolver.py`（完整读取）
- `scripts/sources/wencai_source.py`（完整读取）
- `scripts/execution_engine.py`（关键段落，含 line 359-363, 425-553, 663-811）
- `scripts/ohlcv_provider.py`（关键段落，含 line 195-385）
- `scripts/fetch_planner.py`（关键段落，含 line 64-141）
- `scripts/data_prefetch.py`（前 100 行，含 line 91）
- `scripts/mask_cache.py`（完整读取）
- `scripts/skill_registry.py`（完整读取）
- `scripts/strategy_graph_builder.py`（完整读取）
- `scripts/run_report.py`（前 80 行）
- `scripts/v6op_server.py`（前 80 行）
- `scripts/explanation_builder.py`（前 120 行）
- `scripts/producers/czsc_producer.py`（关键段落，含 line 184-324）
- `scripts/producers/smc_producer.py`（关键段落，含 line 192-280）
- `scripts/producers/kline_producer.py`（关键段落，含 line 235-268）
- `scripts/producers/wave_producer.py`（关键段落，含 line 1-198）
- `scripts/producers/landmine_producer.py`（前 120 行）
- `web/app.js`（前 80 行）

---

## 附录 C：待核实列表

以下结论基于部分阅读或间接推断，需要进一步核实才能确定：

1. **pytest 481 passed**：未读取测试文件，无法判断测试是否覆盖了关键边界条件（尤其 days 参数端到端、wencai key 传递）
2. **abort 可靠性**：`v6op_server.py` 有 `/api/abort` 端点，未读取 abort 完整逻辑
3. **run_report 字段完整性**：只读了前 80 行，未验证报告是否包含 query_hash / api_called 等字段
4. **wencai 真实授权机制**：api_key 不传给 pywencai，但 pywencai 可能有其他持久化机制（session cookie），需要在清洁环境测试
5. **scope_id 截断的实际碰撞率**：理论上 30 只截断可能导致大池 scope_id 碰撞，但实际发生概率取决于使用场景
6. **wave_producer days 传递**：读取前 198 行，`run()` 函数未在此范围内，需确认是否也正确传 days

---

*报告结束。本文档是讨论材料，不是施工命令。结论更改建议先讨论，再决定是否提交为施工任务。*
