# 第二阶段完整范围开发计划

> 作者：Claude 分析员（架构讨论角色）
> 日期：2026-05-06
> 基于：015 第二阶段目标对齐、016 Codex 审核意见、019 输入问题
> 本文件可作为代码执行 Claude 的任务规格，不含施工命令，含验收标准。

---

## 一、总判断：是否能一次完整开发完成

**直接结论：一次开发可以覆盖所有 8 个目标，但 G8（图执行器）必须放在最后且需要独立验收。推荐方案是"2 次主体开发 + 1 次验收修正"，原因不是缩范围，而是降低 G8 引入回归的风险。**

详细说明：

G1 至 G7 七个目标之间的依赖关系清晰，大部分可以串行完成，代码变更面涉及约 12 个文件，没有根本性的结构冲突。唯一的问题是 G8：它要改写 execution_engine.py 里三条路径的执行逻辑，把 sequential 和 simple_hybrid 从手写集合运算改为走 expression_runner。这是对执行核心最大的一次变动，如果在同一个开发会话里和 G1-G7 混在一起，G8 出的回归很难和其他变更隔离验证。

因此：
- **一次完整开发是结构上可行的**，前提是 G8 在本次开发中最后做，并且有独立的 checkpoint 验收。
- **推荐的实际执行方式是 2+1**：第一次主体开发完成 G1 G2 G3 G4-auth G5（5 个目标，建立信任基础）；第二次主体开发完成 G6 G7 G4-Bridge G8（剩余目标，建立结构和架构）；第三次仅做验收补漏，不新增功能。
- 如果执行 Claude 在第二次开发中确认 G8 进度良好，可以在同一次内完成，不强制拆开。关键是 G8 不能比 G6/G7 先做。

**这不是砍目标，是给 G8 保留一条安全回退路径。**

---

## 二、一次完整开发方案（单次全量）

如果决定一次性完成全部 8 个目标，内部执行顺序必须严格遵守以下优先级：

**阶段 A（无依赖，先行）**：G1、G3、G4-auth

这三项都是后端修复，互相没有依赖，可以并列完成。完成后执行一次冒烟测试，确认现有功能无回归。

**阶段 B（依赖 A，次行）**：G2、G5

G2（全局解释层）依赖 G1 的参数链路已修复（否则解释层报告的数据不可信）、依赖 G3 的来源诊断字段已保留。G5（数据血缘）依赖 G1 的实际 days 参数已正确传入（否则血缘字段里的"实际使用天数"是错的）。

**阶段 C（依赖 B，再行）**：G4-Bridge、G6、G7

G4-Bridge 的 second-pass 模式依赖 G4-auth 验证完成。G6（页面分流）在 G2/G5 的诊断内容已成形后才能决定哪些内容进主操盘台、哪些进管理中心。G7（运行管理）依赖 G6 的分流结构。

**阶段 D（最后，独立验收）**：G8

G8 是风险最高的变更，单独做，单独验收，通过后合并。如果 G8 在本次开发中出现严重回归，应该还原 G8 的变更并保留 G1-G7 的成果，由下一次修正解决。

**一次完整开发的内置检查点（不是分批，是执行 checkpoint）：**

```
检查点 CP-A：G1 + G3 + G4-auth 完成
  验收条件：参数链路修复、问财授权明确、来源字段保留
  通过才进入 CP-B

检查点 CP-B：G2 + G5 完成
  验收条件：全局解释层出现在结果区、数据血缘字段进入报告
  通过才进入 CP-C

检查点 CP-C：G4-Bridge + G6 + G7 完成
  验收条件：Bridge 两种模式可选、管理中心独立、运行管理语义清晰
  通过才进入 CP-D

检查点 CP-D：G8 完成
  验收条件：三条路径全部走 expression_runner、报告表达式驱动执行、无回归
  通过：本次开发关闭
  失败：还原 G8、输出 G8 债务说明、其余 G1-G7 保持

```

---

## 三、推荐方案：2 次主体开发 + 1 次验收修正

### 第一次开发（Pass 1）：结果可信 + 解释透明主链

**覆盖目标：G1、G3、G4-auth、G2、G5**

**内部顺序：G1 → G3 → G4-auth → G2 → G5**

**第一次开发完成后用户能看到：**
- 改了 days 参数，结果真的基于新 days 计算（G1）
- 问财返回 45 只时页面说清楚为什么（G3）
- PRO 5000 在问财模式和全A模式下分别有不同提示（G3）
- 问财授权状态明确，如果有问题有提示（G4-auth）
- 命中 0 只时，分层解释出现在结果区（G2）
- 报告里能看到本轮数据来源情况（G5）

**第一次开发验收标准：**
见第九节验收清单中标注"Pass 1"的条目。

---

### 第二次开发（Pass 2）：管理分流 + Bridge 落地 + 图执行器

**覆盖目标：G6、G7、G4-Bridge、G8**

**内部顺序：G6 → G7 → G4-Bridge → G8（G8 最后）**

**第二次开发完成后用户能看到：**
- 主操盘台只剩 7 项操盘内容，管理入口独立（G6）
- 清缓存可以选择清哪一层（G7）
- abort 有明确的步骤边界语义（G7）
- 历史运行记录关联到参数快照（G7）
- 问财可以在技能筛选后对剩余股票做二次验证（G4-Bridge）
- 三条执行路径全部走 expression_runner，报告表达式真实驱动执行（G8）

**第二次开发验收标准：**
见第九节验收清单中标注"Pass 2"的条目。G8 验收必须独立运行三条路径并对比结果。

---

### 第三次开发（Pass 3）：验收补漏

**不新增目标，只修补：**
- 文案修正（PRO 5000 提示、分层解释措辞）
- 边界字段缺失（问财 elapsed_s 未进报告等细节）
- 测试补齐（覆盖 wencai=0/45/5000、三路径各一次）
- G8 如果在 Pass 2 末尾有轻微回归，在 Pass 3 修正
- 如果 G8 在 Pass 2 里无法稳定完成（严重回归），Pass 3 单独处理 G8 + 回归验证

**Pass 3 严格限制：不承载任何新大目标。如果 Pass 3 里出现"需要新增功能"的判断，应该开第二阶段补充讨论，不在 Pass 3 里扩展。**

---

## 四、8 个大目标逐项落地计划

### G1：参数-数据-缓存全链路一致化

**解决的核心问题**：用户改了 days 参数，系统内部实际使用的仍然是默认值 365，导致结果不变。

**需要改的主要模块：**
- `scripts/producers/czsc_producer.py:199` — 移除 `days=365` 硬编码，改为从 params 读取 days 并传入 `_fetch_ohlcv()`
- `scripts/execution_engine.py:359,449` — fetch_planner 调用时传入 `lookback_days=user_days`
- `scripts/execution_engine.py:472` — `compute_scope_data_time_max` 调用时传入 days
- `scripts/ohlcv_provider.py` — K线"够用"判断改为基于用户实际设置的 days，不基于 365d.pkl 文件是否存在

**K线文件命名规范说明**：如果当前 pkl 以 `{code}_365d.pkl` 为固定名，可能需要同步调整命名策略（如改为 `{code}_{days}d.pkl`）或在读取时验证实际记录条数而非依赖文件名。需要代码执行 Claude 在看到实际文件名逻辑后做判断，不是架构问题，是实现细节。

**报告字段变化**：`run_report.json` 中增加 `actual_days_used` 字段，标注本次实际使用的 days 值，与用户设置的 days 对比。

**前端变化**：无结构变化，但运行状态区日志应打印 "days=X 传入取数" 而不是静默。

**依赖关系**：G2、G5 依赖 G1 先完成。

**验收测试**：设置 days=730 运行，在报告中确认 `actual_days_used=730`，且 K线数据量与 365 天运行时有明显差异（如果本地有 730 天数据的话）。

---

### G2：全局解释层与分层归零诊断

**解决的核心问题**：命中 0 时用户无法判断是哪一层造成的，无法决定下一步。

**五层解释契约（每层输出字段）：**

| 层 | 输入 | 输出 | 失败/清零原因 | 建议操作 |
|----|------|------|--------------|---------|
| 来源层 | 用户设置的来源参数 | 股票池大小 N | 问财无结果/超时/授权失败/全A截取上限 | 修改查询语句/检查授权/降低档位 |
| 数据层 | 股票池 N 只 | K线覆盖 M 只 | 取数失败/数据不足/旧数据超阈值 | 重新预取/延长缓存有效期/接受旧数据 |
| 技能层 | K线覆盖 M 只 | 每个技能命中数 | 参数过严/信号不足/错误 | 放宽参数/切换技能 |
| 路径层 | 各技能命中集合 | 合并后命中 P | 交集过严/某技能命中为空 | 换路径/关闭某技能 |
| 报告层 | 命中 P 只 | 最终列表 | 解释骨架缺失（稀有边界情况） | 检查 explanation_builder |

**需要改的主要模块：**
- `scripts/explanation_builder.py` — 增加 `build_global_explanation()` 函数，汇总五层诊断数据
- `scripts/source_resolver.py:114-146` — 停止丢弃 `query_hash`、`actual_count`、`api_called`、`elapsed_s`，保留进结果 dict
- `scripts/execution_engine.py` — 在执行结束时收集 per-skill 命中数、失败数、输入代码数，输出到 run_result
- `scripts/run_report.py`（或等效报告组装模块）— 增加 `global_explanation` 字段

**报告字段变化（新增 global_explanation 节）：**
```
global_explanation:
  source_layer: { input: "wencai", count: 45, note: "问财实际返回45只，未触发5000截断" }
  data_layer:   { input: 45, covered: 43, failed: 2, has_old_data: 1 }
  skill_layer:  [ { skill: "czsc", input: 43, hit: 12, miss: 31, error: 0 }, ... ]
  path_layer:   { mode: "sequential", after_each_step: [43, 12, 7, 5], final: 5 }
  report_layer: { final_hit: 5, explanation_missing: 0 }
  why_zero: null  # 如果 final_hit=0，此字段说明哪层导致了清零
```

**前端变化：**
- 结果区新增可折叠的"本轮运行诊断"section，展示五层数字汇总
- 命中为 0 时该 section 自动展开，不折叠
- 每层用一行简短文字 + 数字表示（不是大段说明）

**依赖关系**：依赖 G1（参数链路已修复，诊断数据可信）、依赖 G3（来源诊断字段已保留）。

**验收测试**：运行三个场景：问财返回 0、技能过严导致 0、交集过严导致 0，每个场景诊断区显示出不同层的清零原因。

---

### G3：来源层语义清晰化与诊断字段保留

**解决的核心问题**：PRO 5000 在两种来源下含义不同；问财返回 45 只时无法知道为什么；诊断字段被丢弃。

**需要改的主要模块：**
- `scripts/source_resolver.py:114-146` — 保留 wencai 返回的 `query_hash`、`actual_count`、`api_called`、`elapsed_s` 字段，传递给 engine 和报告
- `web/app.js` 和 `web/index.html` — PRO 5000 标签文案按来源模式动态变化：
  - 问财模式：显示"最多取 N 条结果（本次实际返回 M 条）"
  - 全A模式：显示"从本地名单截取最多 N 只"
- 问财三种边界情况的提示文案：
  - 返回 0：检查查询语句或网络/授权
  - 返回极少（如 45）：正常，问财筛选结果就这些
  - 返回接近上限：提示可能已触发截断

**报告字段变化**：在 `source_info` 节下新增：`query_text`、`actual_count`、`api_called`（bool）、`elapsed_s`。

**前端变化**：
- 来源区在选择问财模式后，运行完成时在档位旁内联显示"本次 wencai 返回 M 只"
- 来源区在全A模式时，档位提示语不变，但明确标注"本地截取"

**依赖关系**：G2 依赖 G3（来源字段进入全局解释层）。

**验收测试**：问财查询词分别给出 0 只、45 只、接近 5000 只三种场景，页面分别显示对应的提示文案。全A模式下选择 5000 档位，确认提示文案与问财模式不同。

---

### G4：问财授权验证与 Bridge 双角色定义

**解决的核心问题**：不确定问财授权是否在清洁环境下可靠；问财只能做来源，不能对已有股票池做验证。

**G4 分为两部分，Pass 1 完成授权验证，Pass 2 完成 Bridge 落地。**

**G4-auth（Pass 1）：**
- 在清洁环境下（无已有 session/cookie）测试 pywencai.get() 是否正确使用 api_key
- 如果 `wencai_source.py:147-152` 确认 api_key 没有传入，修复传入路径
- 如果 pywencai 使用自维护的 session 机制，在代码注释和 UI 帮助文字中明确说明（不是 bug，是机制说明）
- 管理中心（Pass 2 实现）增加"问财授权状态"显示，让用户能确认当前 key 是否有效

**G4-Bridge（Pass 2）：**

**Bridge Capability 两种模式定义（这是本轮最终确认的语义规格）：**

- **Constrained mode（约束模式）**：问财查询在已有股票池范围内执行，返回该池中符合问财语句的子集。用户选法：先用技能/全A生成池，再用问财约束。语义等价于：`result = wencai_query ∩ existing_pool`。使用场景：已经有一批候选股票，想用自然语言进一步筛选。

- **Second-pass mode（二次验证模式）**：先用缠论/K线/SMC/排雷跑完，对剩余命中股票再发起问财查询，用于添加概念、公告、资金、行业等标签或验证信息。语义：`final = skill_filtered → wencai_verify(hit_list)`。问财在此模式下不做进一步筛选，只返回标签/附属信息，命中列表不变。使用场景：想知道技能筛出来的股票有没有特定的基本面支撑。

**需要改的主要模块（Bridge）：**
- `scripts/sources/wencai_source.py` — 增加 constrained mode 入口，接受 `scope_codes` 参数限制查询范围
- `scripts/execution_engine.py` — 增加 second-pass 调用时序（在技能执行完成后，对 hit_list 发起问财验证）
- `web/index.html / app.js` — 来源区增加 Bridge 模式选项（下拉或 radio），不新增独立页面
- 报告中增加 `bridge_mode` 字段，标注本轮是否使用了 Bridge 以及使用的是哪种模式

**依赖关系**：G4-auth 是 G4-Bridge 的前提；G4-Bridge second-pass 依赖执行引擎的时序支持。

**验收测试**：
- Constrained mode：给 100 只股票的初始池，问财查询语句，验证结果是交集而非全量
- Second-pass mode：技能筛选后剩 10 只，问财标注后结果列表仍是 10 只，但每只附有问财返回的标签信息

---

### G5：数据血缘层定义与取数透明化

**解决的核心问题**：用户不知道本轮数据从哪里来、是否降级、是否是今天的数据。

**Data Provider Adapter 接口规范（这是本轮最终确认的语义规格）：**

统一封装 baostock / akshare / yfinance / 问财 / 手动导入的接口，每个 provider 都返回以下元信息：

```
per_stock_provenance:
  source: "baostock" | "akshare" | "yfinance" | "old_cache" | "wencai" | "manual"
  is_new_fetch: bool
  is_degraded: bool  # 从非首选 provider 取的
  latest_date: "2026-05-05"  # 本地数据最新日期
  trust_level: "fresh" | "stale" | "missing"  # 给用户看的简化状态
```

**需要改的主要模块：**
- `scripts/ohlcv_provider.py:195` — 修复写缓存静默失败（`except Exception: pass` 改为记录日志并标记失败状态）
- `scripts/ohlcv_provider.py:342-356` — FAST_FULL_SCAN 模式在报告和日志中明确标注"快速扫描模式，baostock 失败不降级"
- `scripts/data_prefetch.py:91` — FAST_FULL_SCAN 调用处增加日志标注
- 新增或扩充 `ohlcv_provider.py` 的返回值，携带 per_stock_provenance 元信息
- `scripts/execution_engine.py` — 汇总 provenance 数据生成本轮数据血缘摘要

**报告字段变化（新增 data_provenance 节）：**
```
data_provenance:
  fetch_mode: "FAST_FULL_SCAN" | "FULL_WITH_DEGRADATION"
  total: 45, fetched_new: 30, from_cache: 13, failed: 2
  degraded: 2  # 从非首选 provider 取的数量
  oldest_data_date: "2026-04-15"
  per_stock: { "000001": { source: "baostock", is_new_fetch: true, latest_date: "2026-05-05" }, ... }
```

**前端变化：**
- 结果区新增折叠section "本轮数据来源"，一行摘要："baostock 30 只 / 缓存 13 只 / akshare 兜底 2 只 / 失败 2 只 / 最旧数据 2026-04-15"
- 命中列表里每只股票旁可选显示数据状态图标（fresh/stale/missing）

**依赖关系**：依赖 G1（actual_days_used 是 provenance 的组成部分）。

**验收测试**：一次运行中混合 baostock 成功、akshare 降级、旧缓存三种情况，报告中三类来源数量均正确统计。

---

### G6：主操盘台与管理中心分流

**解决的核心问题**：页面信息密度过高，操盘必需内容和管理诊断内容混在一起。

**主操盘台严格保留（仅这 7 项）：**
1. 股票来源选择（包含 PRO 5000 语义提示、Bridge 模式选项）
2. 技能开关和参数
3. 执行路径选择
4. 启动按钮 + 实时进度状态
5. 命中结果列表
6. 本轮全局解释（分层诊断，在结果区内折叠展开）
7. 数据血缘摘要（在结果区内折叠展开）

**管理中心承接（严格不含分析能力）：**
- 历史运行记录（时间序列列表 + 参数快照 + 命中数，点击可恢复参数）
- 分层缓存清理（★来源快照 / ★★K线数据库 / ★★★技能结果库 三层独立）
- 系统设置（wencai key 配置、取数模式、默认参数）
- 帮助文档（技能说明、操作指南）
- 问财授权状态检查

**管理中心入口**：主操盘台右上角一个"管理"按钮或链接，不是导航栏，不是侧边栏。

**需要改的主要模块：**
- `web/index.html` — 结构调整，把管理功能从主操盘台移出，新增管理中心 section 或独立区域
- `web/app.js` — 历史记录、缓存管理、设置的 JS 逻辑移入管理中心对应 section
- `web/styles.css` — 管理中心样式
- 已有的历史 Tab（Pass 1 后应已实现基础版）扩展为管理中心功能集

**前端变化：**
- 主操盘台视觉更简洁，移除当前与操盘无关的按钮/区域
- 管理中心可以是同一页面的 modal、drawer 或独立 section，但不能是一个新的路由/页面（原因：不增加跳页操作）

**依赖关系**：G6 在 G2/G5 的诊断区域已确定展示位置后做，避免分流后又要回来调整诊断区域位置。

**验收测试**：主操盘台打开后，只见 7 项操盘内容；进入管理中心，只见管理功能，无"启动运行"入口。

---

### G7：运行管理语义正式化

**解决的核心问题**：abort / 清缓存 / 历史报告 / 续跑没有清晰的后端语义，用户无法判断操作后系统处于什么状态。

**各操作语义定义（本轮最终确认）：**

**abort（中止）：**
- 只在步骤边界触发（预取完成后、技能执行完成后），不在技能中间强中止
- abort 后系统状态：已完成步骤的缓存保留，未完成步骤的任务标记为 aborted
- 前端：abort 按钮在运行时激活，非运行时灰化；abort 后显示"已中止于 [步骤名]"

**分层缓存清理：**
- ★ 来源快照（问财/全A返回的股票名单）：清理后下次运行重新拉取
- ★★ K线数据库（本机 ohlcv pickle）：清理后需要重新预取，耗时较长
- ★★★ 技能结果库（mask_cache 内容）：清理后所有技能重新计算
- 用户可以选择只清某一层，不强制全清
- 清理前显示每层大小估计（如"K线数据库 约 400 只 / 2.1GB"）

**续跑（resume）：**
- 前提条件：数据层（★★K线）未超过有效期、技能结果指纹未变化
- 支持从"预取完成"或"某技能完成"状态续跑
- 如果数据已过期，须先重新预取，再续跑分析部分

**历史运行记录：**
- 每条记录存储：时间戳、来源类型、来源参数、技能开关状态、路径模式、days 设置、命中数
- 点击历史记录：恢复上述参数到主操盘台，不自动启动运行
- 历史记录最多保留 20 条（超出后删最旧的）

**需要改的主要模块：**
- `scripts/execution_engine.py` — abort 检查点插入步骤边界；run_state 增加 aborted 状态
- `web/app.js` — abort 按钮状态管理；历史记录恢复参数逻辑
- 后端新增分层缓存清理 API 端点（各层分别清理）
- `web/app.py` 或等效 Flask/HTTP 接口 — 新增 `/api/cache/clear?layer=★★` 等接口

**依赖关系**：G7 依赖 G6（管理中心结构先确立，G7 的各功能才知道放在哪里）。

**验收测试**：
- 运行中点 abort，确认在下一个步骤边界停止，已完成步骤缓存保留
- 分别清理三层缓存，确认每层独立生效，不影响其他层
- 加载历史记录，确认参数恢复到主操盘台但未自动启动

---

### G8：执行路径统一（图执行器）

**解决的核心问题**：sequential 和 simple_hybrid 路径绕过 expression_runner，用手写集合运算实现，导致报告里的表达式（`czsc AND kline MINUS landmine`）不真正对应实际执行逻辑。调试和验证时无法信任报告。

**需要改的主要模块：**
- `scripts/execution_engine.py:780-811` — 把 sequential 和 simple_hybrid 的手写集合运算改为调用 expression_runner，与 parallel_and 对齐
- `scripts/strategy_graph_builder.py` — 图结构（expression_spec）与实际执行逻辑对齐，不再是文档性描述
- `scripts/expression_runner.py` — 确认 sequential 和 simple_hybrid 的表达式语义被正确支持（如 `THEN_FILTER` 操作符是否存在，如不存在需扩充）

**报告变化**：`execution_path.expression_spec` 字段从"描述性字符串"升级为"驱动执行的 AST 或结构化规格"，可以在报告中看到实际运行了哪个表达式节点。

**风险说明（这是全局最大风险项）：**
- G8 改写执行核心，如果有回归，会影响所有三条路径的结果
- G8 必须在 G1-G7 验收通过后、在独立验收环境下完成
- G8 完成后需要逐路径运行测试（sequential 一次、parallel_and 一次、simple_hybrid 一次），对比结果与 expression_spec 的预期

**如果 G8 在 Pass 2 中验证失败的处理：**
- 保留 G1-G7 的全部成果（不回滚）
- 还原 execution_engine.py 的 G8 部分变更
- 在 Pass 3 或补充开发中单独处理 G8
- 在报告中明确标注"expression_spec 为描述性字段，暂未驱动执行"

**依赖关系**：G8 不依赖 G1-G7（独立后端变更），但必须在 G1-G7 稳定后做，避免回归影响信任基础。

**验收测试**：
- 运行 sequential 路径，报告中 expression_spec 与 execution_engine 实际调用 expression_runner 的节点一一对应
- 运行 parallel_and 路径，结果与 G8 前相同（无回归）
- 运行 simple_hybrid 路径，结果与 G8 前相同（无回归）

---

## 五、涉及模块清单

**后端（Python）：**

| 模块 | 变更性质 | 对应目标 |
|------|---------|---------|
| `scripts/producers/czsc_producer.py` | 修复 days 硬编码 | G1 |
| `scripts/execution_engine.py` | 多处修复（days 传递、abort、G8 路径统一） | G1 G7 G8 |
| `scripts/ohlcv_provider.py` | K线"够用"判断修复、写缓存失败修复、FAST_FULL_SCAN 标注、provenance | G1 G5 |
| `scripts/sources/wencai_source.py` | 授权链路验证修复、constrained mode 入口 | G4 |
| `scripts/source_resolver.py` | 保留 wencai 诊断字段 | G3 G2 |
| `scripts/explanation_builder.py` | 新增 global_explanation / why_zero | G2 |
| `scripts/data_prefetch.py` | FAST_FULL_SCAN 日志标注 | G5 |
| `scripts/strategy_graph_builder.py` | 图结构与执行对齐 | G8 |
| `scripts/expression_runner.py` | sequential/hybrid 所需操作符补充（如需） | G8 |
| `web/app.py`（或 Flask 接口层） | 新增分层缓存清理 API | G7 |

**可能新增文件：**
- `scripts/run_provenance.py`（或在现有模块内扩充）— 汇总本轮数据血缘摘要

---

## 六、前端变化清单

| 区域 | 变化 | 对应目标 |
|------|------|---------|
| 来源区 | PRO 5000 文案按来源模式动态变化 | G3 |
| 来源区 | 运行后内联显示"wencai 返回 M 只" | G3 |
| 来源区 | 新增 Bridge 模式选项（下拉/radio） | G4-Bridge |
| 结果区 | 新增折叠 section"本轮运行诊断"（五层） | G2 |
| 结果区 | 新增折叠 section"本轮数据来源"（血缘摘要） | G5 |
| 结果区 | 命中列表每只股票可附数据状态图标 | G5 |
| 运行状态区 | 日志中打印实际 days 值 | G1 |
| 运行状态区 | abort 按钮激活/灰化状态管理 | G7 |
| 管理中心 | 独立区域：历史记录 + 分层缓存清理 + 设置 + 帮助 | G6 G7 |
| 管理中心 | 历史记录含参数快照，点击可恢复 | G7 |
| 管理中心 | 分层缓存清理（三层独立按钮） | G7 |
| 管理中心 | 问财授权状态显示 | G4-auth |
| 主操盘台 | 移除与操盘无关的管理性内容 | G6 |

---

## 七、后端变化清单

| 变化 | 对应目标 |
|------|---------|
| czsc days 传递链路修复 | G1 |
| fetch_planner lookback_days 传入 | G1 |
| K线"够用"判断基于 user days | G1 |
| source_resolver 保留 wencai 诊断字段 | G3 |
| explanation_builder 增加 global_explanation | G2 |
| per-skill 命中/失败数汇总进 engine | G2 |
| wencai api_key 传递验证（修复或记录） | G4-auth |
| wencai constrained mode 接口 | G4-Bridge |
| second-pass 模式执行时序 | G4-Bridge |
| DataProviderAdapter 统一封装 | G5 |
| per_stock provenance 元信息 | G5 |
| 写缓存失败静默修复 | G5 |
| FAST_FULL_SCAN 行为标注 | G5 |
| abort 步骤边界检查点 | G7 |
| 分层缓存清理 API | G7 |
| 运行参数快照记录 | G7 |
| sequential/hybrid 走 expression_runner | G8 |
| expression_spec 驱动执行 | G8 |

---

## 八、报告/日志变化清单

**run_report.json 新增字段：**

```
run_report.json
├── actual_days_used          # G1：实际使用的 days 值
├── source_info               # G3（扩充）
│   ├── query_text
│   ├── actual_count
│   ├── api_called
│   └── elapsed_s
├── global_explanation        # G2（新增）
│   ├── source_layer          # { count, note }
│   ├── data_layer            # { input, covered, failed, has_old_data }
│   ├── skill_layer           # [ { skill, input, hit, miss, error } ]
│   ├── path_layer            # { mode, after_each_step, final }
│   ├── report_layer          # { final_hit, explanation_missing }
│   └── why_zero              # 若清零，说明哪层导致
├── data_provenance           # G5（新增）
│   ├── fetch_mode
│   ├── total / fetched_new / from_cache / failed / degraded
│   ├── oldest_data_date
│   └── per_stock             # { code: { source, is_new_fetch, is_degraded, latest_date } }
├── bridge_mode               # G4-Bridge（新增）
│   └── mode: null | "constrained" | "second_pass"
└── execution_path            # G8（扩充）
    └── expression_spec       # 从描述性字符串升级为结构化节点（如可实现）
```

**日志新增：**
- 每次取数记录 source 和 is_degraded
- FAST_FULL_SCAN 模式明确标注在 prefetch 日志中
- abort 事件记录中止于哪个步骤
- G8 完成后：expression_runner 节点执行记录

---

## 九、完整验收清单

以下为 8 个目标联合验收的完整场景清单，标注所属 Pass。

### 来源层验收（G3 / Pass 1）

- [ ] **问财返回 0**：页面来源区显示"wencai 返回 0 只，请检查查询语句或授权状态"，命中结果区显示归零诊断
- [ ] **问财返回 45**：页面来源区显示"wencai 返回 45 只"，无额外警告（45 只是正常结果）
- [ ] **问财返回接近 5000**：页面显示"可能已触发返回上限截断，实际结果可能更多"提示
- [ ] **全A 5000 档位**：显示"从本地A股名单截取 5000 只"，文案与问财 5000 明显不同
- [ ] **全A 1000 档位**：显示"从本地A股名单截取 1000 只"

### 参数层验收（G1 / Pass 1）

- [ ] **days=730 运行**：报告中 `actual_days_used=730`，日志中打印"days=730 传入取数"
- [ ] **days=730 与 days=365 的缓存指纹不同**：两次运行 mask_cache 给出不同 key，不互相命中
- [ ] **K线"够用"判断基于 user days**：设 days=730，系统检查的是 730 天范围的数据，而非 365d.pkl

### 数据层验收（G5 / Pass 1）

- [ ] **本轮数据来源摘要出现在报告中**：`data_provenance` 节存在，字段完整
- [ ] **写缓存失败有日志**：故意触发缓存写失败，日志中有错误记录，不静默
- [ ] **FAST_FULL_SCAN 在日志和报告中标注**：运行后日志中能看到取数模式说明

### 技能层验收（G2 / Pass 1）

- [ ] **每个技能命中/失败数在报告中**：`global_explanation.skill_layer` 每个技能都有 `hit` 和 `miss`
- [ ] **某技能命中为 0 时诊断说明**：归零诊断指出该技能命中数为 0，建议放宽参数

### 路径层验收（G2 / Pass 1）

- [ ] **顺序路径：逐步命中数在报告中**：`path_layer.after_each_step` 有逐步数字
- [ ] **并行路径：交集结果在报告中**：`path_layer.final` 是交集结果
- [ ] **混合路径：混合执行步骤在报告中**：`path_layer` 反映混合步骤序列

### 全局解释层验收（G2 / Pass 1）

- [ ] **命中 0 时诊断自动展开**：结果区"本轮运行诊断"section 在 final_hit=0 时自动展开
- [ ] **诊断 section 在有命中时折叠但可展开**
- [ ] **why_zero 字段准确定位清零层**：分别构造来源为 0、K线不足、技能过严三种场景，why_zero 各指向不同层

### Bridge 验收（G4-Bridge / Pass 2）

- [ ] **Constrained mode**：给 100 只初始池，问财约束后结果是交集（≤100 只）
- [ ] **Second-pass mode**：技能筛选后 10 只，问财验证后仍是 10 只，每只附有问财标签
- [ ] **Bridge 模式记录在报告中**：`bridge_mode.mode` 字段值正确

### 问财授权验收（G4-auth / Pass 1）

- [ ] **清洁环境测试结论记录**：代码注释或帮助文档中明确说明 api_key 的实际授权机制
- [ ] **管理中心显示问财授权状态**：Pass 2 完成后，管理中心有授权状态指示

### 数据血缘完整验收（G5 / Pass 1+2）

- [ ] **per_stock 来源字段**：至少一次运行中，部分股票 source=baostock，部分 source=akshare（如触发降级），部分 source=old_cache
- [ ] **oldest_data_date 字段正确**：反映本轮使用的最旧数据日期

### 管理分流验收（G6 / Pass 2）

- [ ] **主操盘台打开**：只见 7 项操盘内容，无历史列表、无缓存清理按钮、无完整帮助
- [ ] **管理中心打开**：见历史记录、缓存清理、设置、帮助，无"启动运行"按钮

### 运行管理验收（G7 / Pass 2）

- [ ] **abort 在步骤边界停止**：运行中 abort，下一个步骤不开始，已完成缓存保留
- [ ] **分层清理 ★ 来源快照**：清理后下次运行重新拉取问财，其余缓存不受影响
- [ ] **分层清理 ★★ K线数据库**：清理后 K线数据消失，技能结果库（mask_cache）不受影响
- [ ] **分层清理 ★★★ 技能结果库**：清理后技能结果需重新计算，K线不重新拉取
- [ ] **历史记录恢复参数**：点击历史记录，主操盘台来源/技能/参数恢复到历史值，不自动启动

### 图执行器验收（G8 / Pass 2）

- [ ] **sequential 路径走 expression_runner**：日志中有 expression_runner 执行记录，报告 expression_spec 非纯描述字符串
- [ ] **parallel_and 路径无回归**：与 G8 前结果一致
- [ ] **simple_hybrid 路径走 expression_runner**：同 sequential 要求
- [ ] **全三路径结果对比**：G8 完成后，同一组股票和技能，三路径各运行一次，结果与预期语义一致

---

## 十、最大风险与处理方式

### 风险 1：G8 引入执行回归（最大风险）

**描述**：G8 改写执行核心，regression 会破坏 G1-G7 建立的信任基础。

**处理方式（不砍目标）**：
- G8 在所有其他目标稳定后最后做
- G8 做完后立即运行三路径对比测试（上述验收清单 G8 部分）
- 如果 G8 产生回归但无法快速修复：还原 G8 的代码变更，G1-G7 结果不受影响，G8 进入 Pass 3 或追加处理
- 在 G8 完成之前，报告中 expression_spec 字段标注为"描述性字段，暂未驱动执行"，不隐瞒现状

### 风险 2：问财授权机制不明确（中等风险）

**描述**：pywencai 可能依赖 session/cookie 机制，api_key 传递不是关键路径，但这需要在清洁环境中确认。

**处理方式（不砍目标）**：
- G4-auth 的任务是"搞清楚授权机制"，不是"一定要修复 api_key 传递"
- 如果确认 pywencai 依赖 session，在代码注释 + 管理中心 + 帮助文档三处明确说明 session 维护方式，这本身就是 G4-auth 的完成状态
- G4-Bridge 不依赖 api_key 传递路径，只依赖问财能够正确返回结果

### 风险 3：Bridge second-pass 模式时序复杂（低中风险）

**描述**：second-pass 需要在技能执行完成后对 hit_list 发起额外的问财查询，涉及执行时序改变。

**处理方式**：
- second-pass 在 Pass 2 中做，前提是 G4-auth 已明确授权稳定
- 如果 second-pass 实现遇到时序问题，可以先实现 constrained mode，second-pass 在 Pass 3 补完
- 注意：这不是"砍目标"，是 G4-Bridge 内部的实现顺序，两种 Bridge 模式都必须完成

### 风险 4：管理中心演化成第二个操盘台（组织风险）

**描述**：如果执行 Claude 在实现管理中心时误将分析功能加入，会偏离单页操盘动线。

**处理方式**：
- G6 验收标准明确：管理中心不得有"启动运行"入口，无技能选择，无参数调节
- 管理中心的功能边界在本文件第四节 G6 中已定义，验收时严格对照

---

*本文件为第二阶段完整开发计划规格，8 个大目标全部纳入，不削减范围。Pass 1 + Pass 2 完成主体，Pass 3 仅做补漏。G8 如遭遇严重回归，允许进入 Pass 3，但不允许永久后置。*
