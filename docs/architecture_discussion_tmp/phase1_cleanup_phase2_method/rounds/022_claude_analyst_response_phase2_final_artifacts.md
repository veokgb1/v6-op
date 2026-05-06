# V6OP 第二阶段最终交付物

> 作者：Claude 分析员（架构讨论角色）
> 日期：2026-05-06
> 本文件是第二阶段架构讨论的收口交付物，包含三类最终产出。
> 基于：012 架构总评 / 015 目标对齐 / 020 完整开发计划 / 016 Codex 审核意见。

---

# 第一部分：《V6OP 第二阶段升级大纲》

---

## 一、第二阶段总宗旨

**让用户在操盘时，能知道自己在相信什么。**

更具体地说：当系统说"K线已够用"，K线真的是按用户设置的天数准备好的；当用户改了参数，结果确实基于新参数计算；当问财返回 45 只，报告能说清楚为什么是 45；当命中数为 0，系统能告诉用户是哪一层把结果变成了 0，以及下一步应该调什么。

在此之上，第二阶段还要建立页面动线纪律：主操盘台只保留操盘必需内容，管理诊断功能集中于独立的管理中心，两者的边界不可模糊。

---

## 二、第二阶段为什么存在

第一阶段的结论是："可运行骨架 + 关键链路待稳定化"。

骨架已经立住：单页操盘台、六个技能、三条路径、两阶段数据隔离、内容寻址技能结果库、三层报告体系，这些都是真实建立的能力。

但以下问题没有解决，让用户无法真正相信系统给出的结果：

1. 用户设了 days=730，系统内部仍用默认 365 天计算，改了参数没有任何实际效果。
2. 问财返回 45 只，用户不知道为什么是 45，不知道是否是问财限制还是查询结果。
3. 命中数为 0，用户不知道是来源为空、K线不足、技能过严、还是路径交集太严，无法判断下一步。
4. "K线已够用"的判断基于 365d.pkl 是否存在，不是基于用户实际设置的天数。
5. 问财授权机制不透明，不知道清洁环境下是否能成功取数。
6. 页面过重，操盘必需内容与管理诊断内容混在同一视野里。
7. abort / 清缓存 / 续跑没有明确的后端语义，用户不知道操作后系统处于什么状态。
8. 三条执行路径的实际代码逻辑与报告表达式不在同一路上，调试时无法追溯。

第二阶段存在的理由就是解决这八类问题，让第一阶段建立的骨架真正"可信"。

---

## 三、第二阶段要解决的用户问题

用户在真实使用中碰到的混乱，集中在以下六个场景：

**来源层混乱**：问财返回的数字无法解释，PRO 5000 在两种来源下含义完全不同，用一个标签覆盖两种语义。

**K线层混乱**：系统说"K线已够用"，但这个判断不基于用户实际设置的天数，用户设 730 天，系统其实用 365 天的缓存就判定够用了。

**参数层混乱**：用户改了参数，运行了，结果有时没变。用户不知道是技能本来就不会命中，还是参数根本没有真正影响计算。

**结果解释混乱**：命中 0 只，用户无从判断是哪一层造成的，系统没有分层解释，无法决定下一步该调什么。

**"缓存"概念混乱**：用户听到"缓存"这个词，不知道说的是问财返回的股票名单、还是本机存的K线数据、还是上次技能算出的结果。这三种东西性质完全不同，当前没有清晰区分。

**页面信息密度混乱**：主操盘台承载了太多内容，操盘必需的动作信息被历史报告、帮助折叠、缓存管理入口稀释，重要的不突出，不重要的占据太多视野。

---

## 四、第二阶段不是什么

**不是新增功能阶段。** 打分制、反压测试模型、新技能接入、更复杂的路径组合——这些都不是第二阶段的目标。第二阶段的目标是让现有功能真正可信，而不是在不可信的基础上堆更多功能。

**不是纯粹修 bug 阶段。** 第二阶段不只是把第一阶段的点状问题逐个修补，而是建立三套可持续的基础设施：透明度机制（解释为什么这样）、分类机制（操盘内容与管理内容分流）、Bridge 能力（问财双角色）。这三套机制建好之后，第三阶段才有稳固的地基。

**不是把单页操盘台做成博物馆。** Data Provenance、Bridge Capability、分层解释器这些概念，都必须以"在当前运行结果内折叠展示"的方式落地，不能为任何一个新概念创建独立的管理页面或可浏览数据库。

**不是长期路线图。** 第二阶段有明确的边界：8 个目标，最多 2 次主体开发 + 1 次验收修正，完成后关闭，进入第三阶段讨论。

---

## 五、第二阶段 8 个大目标

**G1 参数-数据-缓存全链路一致化**
让用户设置的 days 参数真正从"参数 → K线取数 → 分析 → 缓存指纹"走到底。每一个环节使用相同的 days 值，K线"够用"的判断也基于用户实际设置的天数，而非固定 365d.pkl 文件。

**G2 全局解释层与分层归零诊断**
建立五层解释契约（来源层、数据层、技能层、路径层、报告层），每层输出：输入数量、产出数量、失败原因、建议操作。命中 0 时，系统能精确告诉用户是哪一层导致了清零，以及下一步该调什么。

**G3 来源层语义清晰化与诊断字段保留**
PRO 5000 在问财模式和全A模式下分别展示对应的语义说明。问财 0/45/接近上限三种边界情况各有对应提示文案。问财返回的诊断字段（query_text、actual_count、api_called、elapsed_s）不在 source_resolver 层丢弃，保留进报告。

**G4 问财授权验证与 Bridge 双角色定义**
在清洁环境下验证问财授权机制，明确 api_key 的实际作用路径。同时建立 Bridge Capability 的两种模式：Constrained mode（问财在已有池内约束检索）和 Second-pass mode（技能筛选后问财对命中股票做外部标签/验证）。Bridge 是来源选项，不是新页面。

**G5 数据血缘层定义与取数透明化**
定义 Data Provider Adapter 统一接口，每次取数都携带来源（baostock/akshare/yfinance/旧缓存）、是否降级、数据最新日期等血缘字段。FAST_FULL_SCAN 与完整取数模式的行为差异在报告和日志中明确标注。写缓存失败不再静默，有日志记录。

**G6 主操盘台与管理中心分流**
主操盘台只保留 7 项操盘必需内容（见第七节）。历史报告、分层缓存清理、系统设置、帮助文档、问财授权状态检查，全部迁入管理中心。管理中心没有"启动运行"入口，不具备分析能力。

**G7 运行管理语义正式化**
abort 定义为步骤边界停止，不是强中止。清缓存分为三层（★来源快照 / ★★K线数据库 / ★★★技能结果库），三层独立清理。每条历史运行记录关联到参数快照，点击可恢复参数到主操盘台，不自动启动。续跑有明确的前提条件检查。

**G8 执行路径统一（图执行器）**
sequential 和 simple_hybrid 路径改为走 expression_runner，与 parallel_and 对齐。报告中的 expression_spec 字段从描述性字符串升级为真正驱动执行的结构化规格。此目标在所有其他目标稳定后最后完成，G8 引入回归时允许进入 Pass 3 修复，但不允许永久后置。

---

## 六、Pass 1 / Pass 2 / Pass 3 的关系

三次开发合为一个完整的第二阶段，不是三个独立阶段，也不是削减范围。

**Pass 1（信任基础主链）**
覆盖目标：G1、G3、G4-auth、G2、G5
执行顺序：G1 → G3 → G4-auth → G2 → G5
完成后用户能感受到：改参数有效、问财 45 只有解释、命中 0 时分层定位、报告有数据血缘摘要。
Pass 1 是后续所有工作的可信基础，Pass 2 依赖 Pass 1 的透明度框架已成形。

**Pass 2（结构与架构）**
覆盖目标：G6、G7、G4-Bridge、G8（G8 必须最后做）
执行顺序：G6 → G7 → G4-Bridge → G8
完成后用户能感受到：页面清晰、管理功能独立、Bridge 两种模式可用、三条路径表达式统一。
G8 完成后立即运行三路径对比验收，如有严重回归，还原 G8 变更，其余成果保留。

**Pass 3（验收补漏）**
不新增目标，只修补：文案、边界字段、漏测场景、G8 如果在 Pass 2 末尾有轻微回归则在 Pass 3 修正。
如 G8 在 Pass 2 产生严重回归并已还原，Pass 3 单独处理 G8，在 G8 完成前在报告中明确标注"expression_spec 为描述性字段，暂未驱动执行"。
Pass 3 是验收修正，不是新功能批次。

---

## 七、主操盘台动线原则

**主操盘台严格只保留以下 7 项内容，不多不少：**

1. 股票来源选择（含 PRO 5000 语义提示、Bridge 模式选项）
2. 技能开关与参数调节
3. 执行路径选择（顺序/并行/混合）
4. 启动按钮 + 实时进度状态区
5. 命中结果列表
6. 本轮全局解释（五层诊断，折叠展开，位于结果区内）
7. 本轮数据血缘摘要（折叠展开，位于结果区内）

**主操盘台禁止出现的内容：**
- 历史运行列表（迁入管理中心）
- 分层缓存清理按钮（迁入管理中心）
- 完整帮助文档（迁入管理中心）
- 技能资产说明（迁入管理中心）
- 任何独立的"数据管理"或"诊断中心"页面

**动线纪律**：用户进入主操盘台，完成一次完整运行（选来源 → 选技能 → 选路径 → 启动 → 看结果 + 解释），全程不需要离开当前视野，不需要跳页，不需要阅读管理文档。

---

## 八、管理中心边界

管理中心是主操盘台右上角的独立入口（单一按钮，不是侧边导航栏），承接以下功能：

**允许的内容：**
- 历史运行记录（时间序列列表，含参数快照、命中数、来源类型）
- 分层缓存清理（★来源快照 / ★★K线数据库 / ★★★技能结果库，三层独立）
- 系统设置（wencai key 配置、取数模式选择、默认参数）
- 帮助文档（技能说明、操盘指南，只读）
- 问财授权状态检查（只读状态显示，不是分析入口）

**禁止的内容：**
- "启动运行"按钮
- 技能参数调节
- 任何分析动作入口
- 数据血缘的可浏览历史数据库（只能看当次运行的血缘摘要，不能浏览所有历史K线来源）

**设计纪律**：管理中心存在的理由是让用户能做配置和查历史，不是让用户能在里面做第二套分析。如果某个功能让用户在管理中心里产生"分析意图"，那它不应该在管理中心。

---

## 九、Bridge Capability 定义

Bridge Capability 是问财的第二种工作模式，是主操盘台来源选择区里的一个参数选项，不是独立页面。

**模式一：Constrained mode（约束模式）**

含义：问财查询在已有股票池范围内执行，返回该池中符合问财语句的子集。
语义等价：`result = wencai_query ∩ existing_pool`
触发方式：用户先用技能/全A/手动生成一个池，再勾选"问财约束"并输入查询语句。
使用场景：已经有一批候选股票，想用自然语言进一步缩小范围（如"只保留有机构评级上调的"）。
报告字段：`bridge_mode.mode = "constrained"`，记录输入池大小、约束后结果大小、问财查询语句。

**模式二：Second-pass mode（二次验证模式）**

含义：先用缠论/K线/SMC/排雷等技能筛选，对最终命中的股票列表发起问财查询，获取概念、公告、资金、行业等标签信息。问财在此模式下不做进一步筛选，命中列表不变，只是附加标签。
语义等价：`final_list = skill_filtered → wencai_annotate(hit_list)`
触发方式：用户在路径执行完成后，选择"问财二次标注"。
使用场景：技术面筛完后，想知道命中股票有没有特定基本面支撑，用于辅助判断。
报告字段：`bridge_mode.mode = "second_pass"`，每只命中股票附有问财返回的标签字段。

**Bridge 的不变约束**：两种模式都必须作为主操盘台里的参数选项，不能为 Bridge 创建独立的操盘流程或独立页面。问财在 Bridge 模式下的行为受制于主操盘台已有的来源参数和执行结果，不是独立启动的查询入口。

---

## 十、Data Provenance 定义

Data Provenance（数据血缘）是一套随每次运行记录的元信息，说明"本轮的数据从哪里来"。它展示在主操盘台结果区的折叠摘要里，也保存进 run_report.json 的 `data_provenance` 节。

**per-stock 血缘字段（每只股票）：**

```
source: "baostock" | "akshare" | "yfinance" | "old_cache" | "manual"
is_new_fetch: bool           # 本次新拉，还是使用了本地缓存
is_degraded: bool            # 是否从非首选 provider 取的（降级）
latest_date: "YYYY-MM-DD"   # 本地数据最新日期
trust_level: "fresh" | "stale" | "missing"  # 给用户看的简化状态
```

**本轮汇总字段（run_report.json 的 data_provenance 节）：**

```
fetch_mode: "FAST_FULL_SCAN" | "FULL_WITH_DEGRADATION"
total: N                   # 本轮股票池大小
fetched_new: N             # 新拉数量
from_cache: N              # 使用缓存数量
failed: N                  # 失败数量
degraded: N                # 降级（非首选 provider）数量
oldest_data_date: "YYYY-MM-DD"
```

**Data Provenance 的边界**：它是"每次运行的数据来源说明"，不是"历史所有K线的来源数据库"。用户看到的是本轮的血缘摘要，不是一个可以浏览历史数据来源的数据管理界面。

---

## 十一、分层问题定位解释器定义

分层问题定位解释器是在命中数为 0（或极少）时，向用户解释"是哪一层造成的"的组件，展示在主操盘台结果区的折叠诊断 section，命中为 0 时自动展开。

**五层解释契约：**

| 层 | 说明 | 必须输出的字段 | 对应的"建议操作" |
|----|------|--------------|---------------|
| 来源层 | 股票池从哪里来、来了多少只 | 来源类型、实际数量、是否截断 | 修改查询语句 / 降低档位 / 检查授权 |
| 数据层 | K线覆盖了多少只、有多少失败 | covered、failed、has_old_data | 重新预取 / 接受旧数据 |
| 技能层 | 每个技能命中多少、失败多少 | per-skill hit/miss/error | 放宽参数 / 关闭过严技能 |
| 路径层 | 合并后剩多少，每步剩多少 | after_each_step、final | 换路径模式 / 关闭某技能 |
| 报告层 | 最终命中，有无解释缺失 | final_hit、explanation_missing | 检查 explanation_builder |

**why_zero 字段**：当 final_hit=0 时，解释器自动填写 `why_zero`，指出是哪一层首先将结果降为 0，给出简短的中文原因和建议。

**展示规则**：
- 命中 0：诊断 section 自动展开，不需要用户手动打开
- 命中少量（如 1-5 只）：诊断 section 折叠但有视觉提示，用户可展开
- 命中正常：诊断 section 折叠，不强制用户查看

---

## 十二、第二阶段完成后，第三阶段才能接什么

第二阶段完成后，以下基础设施已经就位：
- 参数端到端可信（用户设的参数真的影响结果）
- 结果可解释（命中数可以分层追溯原因）
- 数据血缘透明（每次运行能看到数据从哪里来）
- Bridge 双角色可用（问财可以做来源，也可以做验证）
- 管理动线清晰（操盘与管理不再混淆）
- 三条路径统一（执行逻辑与报告表达式对齐）

**第三阶段才能接的方向（当前仅方向，不展开）：**
- 打分制与排序：在可信的命中结果上增加多维打分，按信心度排序
- 抗压测试模型：对命中股票做历史回测，评估策略稳健性
- 新技能接入：把 V6/V5 技能资产库中待接入的技能（波浪更精细化、量化排列等）接入主操盘线
- 多策略协调：允许用户保存和切换多套参数配置，而不是每次都手动调
- 自动报告推送：定时运行 + 推送报告，而不是每次手动启动

**第三阶段的前提硬性条件**：第三阶段的任何方向都不能在第二阶段 G1-G8 未完成的情况下启动。在一个参数不可信、结果不可解释的系统上加打分制，得到的是可信的打分制分数，还是不可信的打分制分数？答案是后者。

---

# 第二部分：给代码执行 Claude 的第二阶段升级提示词

---

```
给代码执行 Claude 的第二阶段升级提示词

你现在接手的是 V6OP 第二阶段的完整升级开发任务。本任务不允许砍目标、不允许缩范围。
你的任务是把 8 个大目标全部完成，按照 Pass 1 → Pass 2 → Pass 3 的检查点推进，
每个 Pass 完成后请自行验收，再进入下一个 Pass。

本任务包含后端 Python 修改、前端 HTML/CSS/JS 修改、报告字段新增，
以及针对每个目标的验收测试。不要在所有目标都完成前就宣布任务完成。

========== 项目基础信息 ==========

工作目录：F:\v.6\v6-op\
后端入口：scripts/execution_engine.py
数据取数：scripts/ohlcv_provider.py
技能生产者：scripts/producers/（czsc_producer.py / smc_producer.py / kline_producer.py 等）
来源解析：scripts/source_resolver.py / scripts/sources/wencai_source.py
解释生成：scripts/explanation_builder.py
缓存：scripts/mask_cache.py / scripts/ohlcv_provider.py（写缓存处）
图执行：scripts/expression_runner.py / scripts/strategy_graph_builder.py
前端：web/index.html / web/styles.css / web/app.js
接口层：web/app.py（Flask）

========== 第二阶段总宗旨 ==========

让用户在操盘时，能知道自己在相信什么。

改参数必须真的有效。命中 0 时必须能分层解释原因。数据来源必须透明。
页面操盘动线必须清晰，管理功能必须独立。问财双角色必须可用。
三条执行路径必须真正统一在 expression_runner 下。

========== 8 个大目标 ==========

G1：参数-数据-缓存全链路一致化
G2：全局解释层与分层归零诊断
G3：来源层语义清晰化与诊断字段保留
G4：问财授权验证与 Bridge 双角色定义
G5：数据血缘层定义与取数透明化
G6：主操盘台与管理中心分流
G7：运行管理语义正式化
G8：执行路径统一（图执行器）

以上 8 个目标全部必须完成，没有例外。

========== Pass 1：信任基础主链 ==========

覆盖目标：G1、G3、G4-auth、G2、G5
执行顺序：G1 → G3 → G4-auth → G2 → G5
完成后必须验收，才能进入 Pass 2。

--- G1：参数-数据-缓存全链路一致化 ---

需要改的文件：

1. scripts/producers/czsc_producer.py:199
   现状：days=365 硬编码
   修改：从传入的 params 字典读取 days 值，传给 _fetch_ohlcv() 或等效取数函数
   目的：用户设 days=730，czsc 使用 730 天K线

2. scripts/execution_engine.py:359 和 :449
   现状：fetch_planner 调用时未传入 lookback_days
   修改：把用户设置的 days 参数传入 fetch_planner 的 lookback_days 参数

3. scripts/execution_engine.py:472（或等效行）
   现状：compute_scope_data_time_max 调用未传入 days
   修改：传入用户设置的 days

4. scripts/ohlcv_provider.py
   现状：K线"够用"判断基于 {code}_365d.pkl 是否存在
   修改：判断基于用户实际设置的 days 值，验证对应时间范围内的数据是否充足
   注意：如果文件命名有 _365d 后缀，需要同步评估是否要改命名策略

报告字段新增（run_report.json）：
  actual_days_used: int    # 本次实际传入取数的 days 值

G1 验收：
  设置 days=730，运行，确认 run_report.json 中 actual_days_used=730
  日志中出现 "days=730 传入取数"
  连续两次运行分别 days=365 和 days=730，mask_cache 给出不同的缓存 key（不互命中）

--- G3：来源层语义清晰化与诊断字段保留 ---

需要改的文件：

1. scripts/source_resolver.py:114-146
   现状：wencai 返回的 query_hash、actual_count、api_called、elapsed_s 被丢弃
   修改：保留这四个字段，放入 source_result dict，传递给 execution_engine 和报告层

2. web/app.js 和 web/index.html（来源区）
   新增：PRO 5000 提示文案按来源模式动态变化
   - 问财模式：显示"最多取 N 条（本次实际返回 M 条）"，运行后更新 M
   - 全A模式：显示"从本地A股名单截取最多 N 只"
   新增：问财三种边界情况提示文案
   - 返回 0：显示"wencai 返回 0 只，请检查查询语句或授权"
   - 返回 1-4999：显示"wencai 返回 M 只"
   - 返回接近 5000：显示"wencai 返回 M 只，可能已触发返回上限，实际结果可能更多"

报告字段新增（run_report.json 的 source_info 节）：
  query_text: str           # 问财查询原文
  actual_count: int         # 实际返回数量
  api_called: bool          # 是否真正发起了 API 调用
  elapsed_s: float          # 查询耗时

G3 验收：
  构造问财返回 0 的场景（查询词无结果），页面来源区显示对应提示
  构造问财返回 45 的场景，页面来源区显示"wencai 返回 45 只"
  全A模式选 5000 档位，来源区文案与问财模式明显不同
  run_report.json 中 source_info 包含以上四个字段

--- G4-auth：问财授权验证 ---

任务：
1. 在清洁环境下（删除或清空已有 pywencai session/cookie）运行问财取数，
   观察 wencai_source.py:147-152 处的 api_key 是否被传入 pywencai.get() 调用。
2. 如果 api_key 没有被传入：修复传入路径
3. 如果 pywencai 依赖自维护的 session/cookie 机制（而非 api_key 参数）：
   在代码注释、帮助文档、管理中心的"问财授权状态"区域明确说明
   - 说明 session 的维护方式（如需要定期登录刷新）
   - 说明清洁环境下问财是否可用的条件

管理中心（Pass 2 实现后）要有一个"问财授权状态"显示区，只读，告诉用户当前问财是否可用。

G4-auth 验收：
  清洁环境下能成功取数，或者能看到明确的失败提示和操作指引
  代码注释或文档中明确说明了授权机制

--- G2：全局解释层与分层归零诊断 ---

需要改的文件：

1. scripts/explanation_builder.py
   新增函数：build_global_explanation(run_result) -> GlobalExplanation
   GlobalExplanation 包含五层诊断（见下方字段定义）

2. scripts/execution_engine.py
   在执行结束时汇总：每个技能的 input_count、hit_count、miss_count、error_count
   把这些数据传给 explanation_builder

报告字段新增（run_report.json 的 global_explanation 节）：
  source_layer:
    source_type: str
    count: int
    note: str           # 问财返回 45 只 / 全A截取 / 等原因说明
  data_layer:
    input: int
    covered: int
    failed: int
    has_old_data: bool
  skill_layer: list of
    skill: str
    input: int
    hit: int
    miss: int
    error: int
  path_layer:
    mode: str
    after_each_step: list[int]    # 每步结束后的命中数
    final: int
  report_layer:
    final_hit: int
    explanation_missing: int
  why_zero: str | null            # 命中 0 时说明哪层导致清零

前端新增区域（结果区内，折叠 section）：
  区域名：本轮运行诊断
  位置：命中结果列表上方或下方，结果区内，不是独立页面
  行为：final_hit=0 时自动展开；final_hit>0 时折叠但可手动展开
  内容：每层用一行文字 + 数字摘要

G2 验收：
  场景 1：问财查询无结果（来源层清零）→ why_zero 指向来源层，诊断区显示"来源层返回 0 只"
  场景 2：K线取数全部失败（数据层清零）→ why_zero 指向数据层
  场景 3：技能参数过严（技能层筛空）→ why_zero 指向技能层，显示各技能命中数
  场景 4：并行交集为空（路径层清零）→ why_zero 指向路径层，显示交集步骤数字
  命中 0 时诊断 section 自动展开，无需用户手动点击

--- G5：数据血缘层定义与取数透明化 ---

需要改的文件：

1. scripts/ohlcv_provider.py:195
   现状：except Exception: pass（写缓存失败静默）
   修改：捕获异常后记录日志 logger.error(...)，不静默

2. scripts/ohlcv_provider.py:342-356
   现状：FAST_FULL_SCAN 模式，baostock 失败直接 return None，无降级
   修改：在日志中明确标注"FAST_FULL_SCAN 模式，baostock 失败不降级"
   同时在 run_report.json 的 data_provenance.fetch_mode 字段标注模式名称

3. 每次 ohlcv 取数返回时，附带以下元信息（可扩充现有 return dict 或新建专用结构）：
   source: "baostock" | "akshare" | "yfinance" | "old_cache"
   is_new_fetch: bool
   is_degraded: bool
   latest_date: "YYYY-MM-DD"
   trust_level: "fresh" | "stale" | "missing"

4. scripts/execution_engine.py（或新增 run_provenance.py）
   汇总本轮所有股票的 provenance 元信息，生成 data_provenance 节

报告字段新增（run_report.json 的 data_provenance 节）：
  fetch_mode: str
  total: int
  fetched_new: int
  from_cache: int
  failed: int
  degraded: int
  oldest_data_date: str
  per_stock: dict[code, {source, is_new_fetch, is_degraded, latest_date, trust_level}]

前端新增区域（结果区内，折叠 section）：
  区域名：本轮数据来源
  位置：全局解释诊断区旁边或下方，折叠
  内容：一行摘要如"baostock 342 只 / 缓存 13 只 / akshare 兜底 2 只 / 失败 2 只 / 最旧 2026-04-15"

G5 验收：
  一次运行后 run_report.json 中 data_provenance 节存在，各字段完整
  故意触发缓存写失败，日志中有 error 记录，不静默
  FAST_FULL_SCAN 模式的 fetch_mode 字段值正确标注

========== Pass 1 验收检查点 ==========

通过 Pass 1 验收后才能进入 Pass 2。

Pass 1 必须验证（全部通过才算完成）：
□ days=730 运行，报告 actual_days_used=730，日志有 days=730 打印
□ 连续两次 days 不同，mask_cache 给出不同 key
□ 问财返回 0，来源区显示对应提示
□ 问财返回 45，来源区显示"wencai 返回 45 只"
□ 全A 5000 档位，文案与问财模式不同
□ run_report.json 有 source_info（query_text、actual_count、api_called、elapsed_s）
□ 问财授权机制已明确（修复或文档说明）
□ 命中 0 时诊断 section 自动展开，why_zero 字段有值
□ 三个不同清零场景各分别产生不同的 why_zero 层指向
□ run_report.json 有 data_provenance 节，字段完整
□ 写缓存失败不静默，有日志

========== Pass 2：结构与架构 ==========

覆盖目标：G6、G7、G4-Bridge、G8（G8 必须最后做）
执行顺序：G6 → G7 → G4-Bridge → G8

--- G6：主操盘台与管理中心分流 ---

主操盘台只保留 7 项（必须严格执行）：
  1. 股票来源选择（含 PRO 5000 提示、Bridge 模式选项）
  2. 技能开关与参数
  3. 执行路径选择
  4. 启动按钮 + 进度状态
  5. 命中结果列表
  6. 本轮全局解释（折叠 section，Pass 1 已实现）
  7. 本轮数据血缘摘要（折叠 section，Pass 1 已实现）

管理中心（单一入口按钮/链接，不是导航栏）承接：
  - 历史运行记录列表
  - 分层缓存清理（三层独立）
  - 系统设置（wencai key、取数模式、默认参数）
  - 帮助文档（只读）
  - 问财授权状态（G4-auth 完成后显示）

管理中心禁止：启动运行按钮、技能参数调节、任何分析动作入口

需要改的文件：
  web/index.html — 结构调整，管理入口独立
  web/app.js — 管理中心 JS 逻辑
  web/styles.css — 管理中心样式

G6 验收：
  主操盘台打开，只见以上 7 项，无历史列表、无缓存清理按钮
  管理中心打开，可见历史、缓存清理、设置、帮助，无"启动运行"按钮

--- G7：运行管理语义正式化 ---

abort 语义（步骤边界停止）：
  修改 execution_engine.py，在预取完成后、每个技能执行完成后插入 abort 检查点
  abort 触发时：当前步骤完成，下一步骤不启动，已完成缓存保留
  前端：abort 按钮运行时激活，非运行时灰化；abort 后显示"已中止于 [步骤名]"

分层缓存清理（三层独立）：
  ★ 来源快照：清理问财/全A返回的名单缓存，下次运行重新拉取
  ★★ K线数据库：清理本机 ohlcv pickle 文件，需要重新预取
  ★★★ 技能结果库：清理 mask_cache，需要技能重新计算
  三层独立，清理某层不影响其他层
  前端：管理中心里三个独立按钮，各自有清理前确认提示

历史运行记录：
  每条记录存储：时间戳、来源类型、来源参数、技能开关状态、路径模式、days 值、命中数
  点击历史记录：恢复参数到主操盘台（来源/技能/路径/days），不自动启动运行
  最多保留 20 条，超出删最旧

需要改的文件：
  scripts/execution_engine.py — abort 检查点
  web/app.py — 分层缓存清理 API（各层独立端点）
  web/app.js — abort 状态管理、历史记录恢复参数逻辑

G7 验收：
  运行中 abort，确认在下一个步骤边界停止，已完成缓存保留
  分别清理 ★ / ★★ / ★★★ 三层，确认各层独立生效，不影响其他层
  点击历史记录，参数恢复到主操盘台，不自动启动运行

--- G4-Bridge：Bridge 双角色落地 ---

Constrained mode：
  修改 scripts/sources/wencai_source.py
  新增入口：接受 scope_codes 参数，把查询限定在该 codes 列表范围内
  修改 execution_engine.py：当 Bridge constrained mode 启动时，传入现有股票池
  前端（来源区）：新增 Bridge constrained 选项，输入问财查询语句，同时显示约束范围来源

Second-pass mode：
  修改 execution_engine.py：在技能执行完成后，对 hit_list 发起问财验证调用
  wencai 在此模式下返回每只股票的标签字段（概念、行业、公告等）
  命中列表不改变，只是每只股票附加问财返回的标签信息
  前端（结果区）：二次标注的信息附在每只命中股票条目下

报告字段新增：
  bridge_mode.mode: null | "constrained" | "second_pass"
  bridge_mode.constrained_input_count: int
  bridge_mode.constrained_output_count: int
  bridge_mode.second_pass_annotated: int

G4-Bridge 验收：
  Constrained mode：给 100 只初始池，问财约束后结果是子集（≤100 只）
  Second-pass mode：技能筛选后 10 只，问财标注后仍是 10 只，每只附有标签字段
  报告 bridge_mode.mode 字段值正确

--- G8：执行路径统一（图执行器）—— 最后做 ---

警告：G8 是风险最高的变更，必须在 G6 G7 G4-Bridge 全部通过验收后才开始。
G8 如果引入严重回归（任何一条路径结果与 G8 前不一致），立即还原 G8 的代码变更，
保留 G1-G7 的全部成果，G8 在 Pass 3 中单独修复。G8 不允许永久后置。

需要改的文件：
  scripts/execution_engine.py:780-811
    现状：sequential 和 simple_hybrid 用手写集合操作（pre_exclude_codes）
    修改：改为调用 expression_runner，与 parallel_and 路径对齐
  scripts/strategy_graph_builder.py
    expression_spec 字段从描述性字符串升级为结构化的 AST 节点
  scripts/expression_runner.py
    如果 sequential/hybrid 所需的操作符（如 THEN_FILTER）不存在，需要补充实现

报告字段变化：
  execution_path.expression_spec: 从描述字符串改为结构化节点（如 {op, args}）

G8 验收（全部通过才算完成）：
  sequential 路径：日志中有 expression_runner 执行记录，报告 expression_spec 非纯字符串
  parallel_and 路径：与 G8 前结果完全一致（无回归）
  simple_hybrid 路径：与 G8 前结果完全一致（无回归）
  同一组股票和技能，三路径各运行一次，结果符合各自路径语义预期

========== Pass 2 验收检查点 ==========

通过 Pass 2 验收后才能进入 Pass 3。

Pass 2 必须验证（全部通过才算完成）：
□ 主操盘台打开只见 7 项操盘内容
□ 管理中心打开，无启动运行按钮
□ abort 在步骤边界停止，已完成缓存保留
□ 三层缓存分别独立清理，互不影响
□ 历史记录恢复参数，不自动启动
□ Bridge constrained mode 返回交集子集，报告字段正确
□ Bridge second-pass mode 附加标签，命中列表不变
□ G8：三条路径都走 expression_runner，无回归

如果 G8 验收失败（有回归）：
  立即还原 G8 变更，G1-G7 成果保留
  在 Pass 2 验收中标注"G8 待 Pass 3 修复"
  继续进入 Pass 3

========== Pass 3：验收补漏 ==========

Pass 3 不新增任何大目标，只做：
  1. G8 如果在 Pass 2 还原了：Pass 3 单独处理 G8 + 三路径回归验收
  2. 文案修正（PRO 5000 提示、诊断 section 措辞）
  3. 边界字段补齐（任何 Pass 1/2 中发现的漏掉字段）
  4. 验收场景补测（覆盖下方完整验收清单中未测到的场景）
  5. 如果 G8 在 Pass 3 中仍无法解决：必须出具一份说明文档，注明原因和预计修复方式

Pass 3 完成后，第二阶段正式关闭。

========== 完整验收场景清单 ==========

以下场景必须全部测过，记录结果：

来源层：
  □ 问财返回 0                   → 来源区显示警告，why_zero 指向来源层
  □ 问财返回 45                  → 来源区显示"wencai 返回 45 只"，无警告
  □ 问财接近 5000 返回           → 来源区显示截断提示
  □ 全A 5000 档位               → 文案显示"从本地名单截取"，与问财模式不同

参数层：
  □ days=365 运行               → 报告 actual_days_used=365
  □ days=730 运行               → 报告 actual_days_used=730，结果与 365 不同（如本地有 730 天数据）
  □ 两次 days 不同              → mask_cache key 不同，不互命中

数据层：
  □ K线本地已有                 → data_provenance.from_cache > 0
  □ K线新拉                     → data_provenance.fetched_new > 0
  □ K线取数失败                 → data_provenance.failed > 0，日志有记录
  □ K线旧数据                   → trust_level="stale"，oldest_data_date 有值

技能层：
  □ 单技能筛空（命中 0）         → skill_layer 该技能 hit=0，why_zero 指向技能层
  □ 排雷剔除股票                 → skill_layer 排雷 miss > 0，理解负向语义：命中=剔除

路径层：
  □ 顺序路径全程筛空             → path_layer.after_each_step 某步降为 0，why_zero 指向路径层
  □ 并行交集为空                 → parallel_and 路径 path_layer.final=0

Bridge：
  □ Constrained mode            → 结果是已有池的子集，bridge_mode.mode="constrained"
  □ Second-pass mode            → 命中数不变，每只股票附有标签，bridge_mode.mode="second_pass"

运行管理：
  □ abort                       → 步骤边界停止，状态标注"已中止于[步骤名]"
  □ 清理 ★ 来源快照             → 下次运行重新拉取问财，K线缓存不受影响
  □ 清理 ★★ K线数据库           → K线需要重新预取，技能结果库不受影响
  □ 清理 ★★★ 技能结果库         → 技能重新计算，K线不重新拉取
  □ 历史记录恢复参数             → 参数恢复到主操盘台，不自动启动运行

G8：
  □ sequential 走 expression_runner → 日志有执行记录
  □ parallel_and 无回归           → 与 G8 前结果一致
  □ simple_hybrid 走 expression_runner → 日志有执行记录，结果与 G8 前一致

========== 禁止行为 ==========

- 不能砍目标，不能缩范围
- G8 如果困难，不能永久后置，只能进 Pass 3
- 不能在 Pass 3 里新增大功能
- 不能为任何新概念（Data Provenance、Bridge、解释层）创建独立的可路由页面
  所有诊断信息必须展示在主操盘台结果区的折叠 section 内
- 管理中心不得有"启动运行"入口
- 不得因为 G8 困难就跳过 G8 直接宣布完成

每个 Pass 完成后，输出简短的 Pass 验收报告，说明通过了哪些检查点，失败了哪些，以及 Pass 3 的补漏计划。
```

---

# 第三部分：检测依据 / 验收依据

---

## 一、验收依据来源

**原始大纲（rescue_charter）提供的原则基础：**
- 单页操盘台不是把所有内容塞进一页，而是"主操盘动线不需要跳页"
- 参数可调的真实含义是"设了会真的影响结果"
- 三源降级链路（baostock→akshare→yfinance→旧缓存）应有明确的失败记录

**第一阶段风险审计（V6OP-030）提供的具体问题：**
- czsc_producer.py:199 days 硬编码（已确认为代码事实）
- wencai_source.py:147-152 api_key 未传入（已确认）
- execution_engine.py:359/449 lookback_days 未传入（已确认）
- source_resolver.py:114-146 诊断字段丢弃（已确认）
- ohlcv_provider.py:195 写缓存静默失败（已确认）

**020 的 8 个大目标**作为验收框架，每个目标对应一组验收场景。

**用户真实事故（已报告的混乱来源）：**
- 问财跑空（wencai 返回 0 但无解释）
- scope 为 0（命中为 0 但不知道原因）
- 改了 days 但结果没变（参数未端到端生效）
- 报告显示的执行逻辑和实际路径不一致（G8 的架构债）

---

## 二、总验收表

| 验收项 | 检测方式 | 通过标准 | 对应目标 | 失败时说明 |
|--------|---------|---------|---------|----------|
| 问财返回 0 | 构造必然无结果的问财查询词，运行 | 来源区显示"wencai 返回 0 只，请检查查询语句或授权"；run_report.json source_info.actual_count=0；诊断 section 展开，why_zero 指向来源层 | G2 G3 | 如果无任何提示：G3 诊断字段未保留；如果诊断未展开：G2 自动展开逻辑未实现 |
| 问财返回少量（如 45） | 构造返回 45 只的问财查询词 | 来源区显示"wencai 返回 45 只"（不是警告，不是错误）；actual_count=45；结果区显示 45 只进入技能层 | G3 | 如果显示错误或警告：边界条件判断有误，45 只属于正常结果 |
| 问财接近上限 | 构造宽泛查询词，使返回数接近 5000 | 来源区显示截断提示："可能已触发返回上限，实际结果可能更多"；actual_count≥4900 | G3 | 如果没有截断提示：边界判断阈值未设置 |
| 全A 5000 | 选全A来源，选 5000 档位，运行 | 来源区显示"从本地A股名单截取最多 5000 只"，措辞与问财 5000 明显不同 | G3 | 如果文案相同：来源模式区分逻辑未实现 |
| days=365 运行 | 设 days=365，运行，检查报告 | run_report.json actual_days_used=365；日志有"days=365 传入取数" | G1 | 如果字段缺失：G1 报告字段未新增 |
| days=730 运行 | 设 days=730，运行，检查报告 | actual_days_used=730；日志有"days=730 传入取数"；与 days=365 的 mask_cache key 不同 | G1 | 如果结果与 365 完全相同且无日志：days 参数仍未传入，G1 修复未生效 |
| K线本地已有 | 已预取的股票再次运行 | data_provenance.from_cache>0；对应股票 is_new_fetch=false | G5 | 如果 from_cache=0：provenance 元信息未正确记录缓存命中情况 |
| K线新拉 | 清空K线缓存，运行 | data_provenance.fetched_new>0；对应股票 is_new_fetch=true | G5 | 如果 fetched_new=0：新拉状态未记录，或缓存未正确清理 |
| K线取数失败 | 断网或屏蔽 baostock，运行 | data_provenance.failed>0；日志有失败记录（非静默）；写缓存失败也有日志 | G5 | 如果静默无日志：G5 写缓存失败修复未生效（ohlcv_provider.py:195） |
| K线旧数据 | 使用超过设置天数的旧缓存，运行 | per_stock 中对应股票 trust_level="stale"；oldest_data_date 有值 | G5 | 如果 trust_level 字段缺失：per_stock provenance 元信息未携带 |
| 技能筛空 | 设置极严技能参数（如 czsc 最短周期），运行 | skill_layer 该技能 hit=0，miss=所有输入；why_zero 指向技能层；诊断 section 自动展开 | G2 | 如果 hit/miss 字段缺失：G2 per-skill 统计未接入 |
| 顺序路径筛空 | 顺序路径，某个中间技能确保返回 0 | path_layer.after_each_step 某步降为 0；final=0；why_zero 指向路径层 | G2 | 如果 after_each_step 缺失：路径层诊断未实现 |
| 并行交集为空 | 并行路径，两个技能选择互斥股票 | path_layer.mode="parallel"；final=0；why_zero 指向路径层，说明交集为空 | G2 | 如果交集为空但无解释：路径层清零原因未区分 |
| 排雷剔除 | 选入包含 ST/次新股的股票池，开启排雷技能 | 排雷 skill_layer 中 hit>0（命中=剔除）；命中的股票不出现在最终结果中；负向语义符合预期 | G2 | 如果排雷命中的股票仍出现在结果中：排雷负向语义处理有误（此项不属于 G2 新增，属于验证现有功能） |
| Bridge constrained mode | 选全A池 100 只，启用 constrained Bridge，设置问财约束查询，运行 | 结果≤100 只；结果是已有池与问财结果的交集；bridge_mode.mode="constrained"；constrained_input_count=100 | G4-Bridge | 如果结果=全量问财结果而非交集：constrained mode 逻辑未实现 |
| Bridge second-pass mode | 技能筛选出 10 只，启用 second-pass Bridge，设置问财查询，运行 | 结果仍是 10 只；每只附有问财返回的标签字段；bridge_mode.mode="second_pass"；second_pass_annotated=10 | G4-Bridge | 如果命中数改变：second-pass 不应改变命中数，只附加标签 |
| abort | 启动运行，在预取或技能执行阶段点 abort | 当前步骤完成后停止；已完成步骤缓存保留；前端显示"已中止于[步骤名]" | G7 | 如果 abort 立即强中止：步骤边界语义未实现 |
| 分层清理★来源快照 | 管理中心清理来源快照，再次运行 | 问财重新发起查询（api_called=true）；K线缓存不受影响（from_cache 不减少） | G7 | 如果K线缓存也被清除：三层清理未独立实现 |
| 分层清理★★K线数据库 | 管理中心清理K线，再次运行 | K线需要重新预取（fetched_new 增加）；mask_cache 技能结果不受影响（技能命中结果与清理前一致，如果 days 和股票池未变） | G7 | 如果技能结果也重新计算：清理层级边界有误 |
| 分层清理★★★技能结果库 | 管理中心清理 mask_cache，再次运行 | 技能重新计算（mask_cache miss；日志有重新计算记录）；K线不重新拉取（from_cache 不变） | G7 | 如果K线也重新拉取：清理层级边界有误 |
| 历史记录恢复参数 | 运行一次记录到历史，修改参数，点击历史记录 | 主操盘台来源/技能/路径/days 恢复到历史值；运行未自动启动；需要用户手动点启动 | G7 | 如果恢复后自动启动：历史恢复逻辑有误 |
| G8 sequential 路径统一 | 运行 sequential 路径，检查日志和报告 | 日志中出现 expression_runner 执行记录；报告 expression_spec 为结构化节点，非纯字符串 | G8 | 如果日志无 expression_runner 记录：G8 路径改写未生效 |
| G8 parallel_and 无回归 | G8 前后各运行 parallel_and 一次，比较结果 | 两次结果完全一致 | G8 | 如果结果不一致：G8 引入了回归，需要还原 G8 并进入 Pass 3 修复 |
| G8 simple_hybrid 路径统一 | 运行 simple_hybrid 路径，检查日志和报告 | 日志中出现 expression_runner 执行记录；结果与 G8 前一致 | G8 | 如果不一致：G8 回归，还原 G8，进入 Pass 3 |
| 管理中心不含分析能力 | 打开管理中心，查看所有可用操作 | 没有"启动运行"按钮；没有技能选择；没有参数调节；只有历史/清缓存/设置/帮助 | G6 | 如果有分析入口：G6 边界实现有误 |
| 主操盘台精简 | 打开主操盘台，计数操盘动线项目 | 只见以下 7 项：来源选择、技能开关、路径选择、启动/进度、结果列表、诊断折叠、血缘折叠 | G6 | 如果有额外区域：G6 分流未执行完整 |

---

## 四、收口判断

### 1. 020 的开发计划是否可以作为第二阶段开发依据？

**是，可以直接作为开发依据。**

020 包含：8 个大目标的完整定义、每个目标需要改的具体模块和代码行、需要新增的报告字段、需要新增的前端区域、Pass 1/2/3 的内部顺序和依赖关系、每个 Pass 的验收清单。这些内容对代码执行 Claude 来说是可以直接按图索骥的。

唯一补充：本轮 022 在 020 的基础上把代码执行提示词整合成了可复制的完整格式，并把验收表补全到 25 个具体测试场景。020 + 022 合用才是完整的开发依据。

### 2. 这轮输出的升级大纲、升级提示词、检测依据是否足以交给代码执行 Claude？

**是，三份交付物合用已足够。**

- 升级大纲（第一部分）：提供定性方向、概念边界、Pass 关系，是架构决策的依据
- 升级提示词（第二部分）：提供可直接复制使用的具体任务规格，含文件路径、字段名、顺序要求
- 检测依据（第三部分）：提供 25 个具体验收场景，每个场景有通过标准和失败说明

代码执行 Claude 接手时，拿到的是：知道要做什么（大纲）、知道怎么做（提示词）、知道做完怎么算合格（验收表）。三份材料形成闭环。

### 3. 是否还需要继续架构讨论？

**不需要。** 第二阶段的范围、目标、概念定义、开发顺序、验收标准都已经完整定义。以下情形不需要继续架构讨论，直接进入代码执行：

- G1-G7 的实施细节：已有具体文件路径和字段定义，代码执行 Claude 读代码可以自行判断实现方式
- G8 的实现方式：已明确改写路径（execution_engine.py:780-811），有回归时的处理方式也已明确

**唯一可能需要补充的（只列，不展开）：**
- 如果代码执行 Claude 在 G8 实现中发现 expression_runner 缺少 sequential 所需操作符，可能需要一次关于"THEN_FILTER 操作符语义"的短讨论，但这属于实施细节，不是新的架构问题
- 如果问财 Bridge second-pass mode 在执行时序上与 execution_engine 现有结构存在深层冲突，可能需要补充说明，但当前架构讨论已经把 second-pass 的时序定义清楚了（技能执行完成后发起）

---

```
Claude 分析员本轮讨论任务完成，可以退出。
```
