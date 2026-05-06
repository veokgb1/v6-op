# Round 001 Claude 分析员正式回复：第一阶段收尾与第二阶段方法讨论

> 角色：Claude 分析员（架构讨论分析师，不是代码执行方）
> 本轮回复写入：`rounds/002_claude_analyst_response_phase1_closure.md`
> 日期：2026-05-06

---

## 一、本轮读取清单

### 讨论规则文件（全部读取）

- `000_discussion_workspace_readme.md`
- `001_roles_and_response_protocol.md`
- `002_evidence_and_code_reading_rules.md`
- `003_required_and_forbidden_scope.md`
- `004_reference_materials_index.md`
- `005_note_capture_and_discussion_artifacts.md`

### 核心参考文档（全部读取）

- `v6-op_full_rescue_charter.md`（全量章程，含第一至十三章 + V6/V5 继承表 + 11步开发表 + 4阶段计划）
- `V6OP-026_final_first_stage_signoff_report.md`（第一阶段最终签收报告）
- `V6OP-030_full_logic_risk_audit.md`（全链路逻辑风险审计）
- `V6OP-031_phase1_work_summary_report.md`（第一阶段工作总结）
- `V6OP-032_code_alignment_guidelines_report.md`（代码对齐与问题解决规范）

### 代码文件（实际读取）

- `web/index.html`（前端页面结构，含来源选择、档位、问财 Phase A/B、技能区）
- `web/app.js`（前 100 行：API 路由、P1-P6 预设、三层数据帮助文字）
- `scripts/source_resolver.py`（全文：三来源统一解析器）
- `scripts/fetch_planner.py`（全文：K 线预热规划器）
- `scripts/execution_engine.py`（前 750 行：主执行流程、三路径分支、Producer 调用）
- `scripts/data_prefetch.py`（前 100 行：协调者模式入口、FAST_FULL_SCAN 设置）
- `scripts/ohlcv_provider.py`（前 100 行 + 330-380 行：缓存读写、FAST_FULL_SCAN 只走 baostock 逻辑）
- `scripts/sources/wencai_source.py`（120-160 行：`_query_wencai` 函数，pywencai 调用处）
- `scripts/producers/czsc_producer.py`（前 80 行 + 185-215 行：硬编码 days=365 处）
- `scripts/producers/` 目录列表（确认 5 个 producer 文件）

---

## 二、代码证据汇总

以下是本轮直接从代码读到的事实，不是推断。

**CE-01** `scripts/producers/czsc_producer.py:199`
```python
df = fetch_ohlcv(code, days=365, verbose=False)
```
缠论 producer 硬编码 `days=365`，不接收 UI 传入的回看天数。即使用户在前端把缠论 days 改成 180，缠论实际仍按 365 天取 K 线。

**CE-02** `scripts/sources/wencai_source.py:147`
```python
result = pywencai.get(
    query=query,
    query_type="stock",
    perpage=perpage,
    page=page,
)
```
`_query_wencai(query, api_key, limit)` 函数接收了 `api_key` 参数，但调用 `pywencai.get()` 时没有把 `api_key` 传进去。key 是否生效，取决于 pywencai 自身是否有其他机制（如 cookie / session）。从代码字面看，api_key 没有参与请求构造。

**CE-03** `scripts/ohlcv_provider.py:341-356`
```python
if _fast_full_scan():
    try:
        df = _fetch_baostock(code, start, end)
        ...
        return df
    except Exception:
        pass
    return None  # ← baostock 失败后直接返回 None，不走 akshare/yfinance
```
`FAST_FULL_SCAN=true` 模式下，baostock 失败后不会继续降级到 akshare 或 yfinance，直接返回 None。标准模式才有三源降级链（代码证据：同文件 `for name, fn in _FETCHERS:`）。`data_prefetch.py` 工作者进程强制设置 `FAST_FULL_SCAN=true`，所以大规模预取时走的是单源，不是三源降级。

**CE-04** `scripts/source_resolver.py:48`
```python
key = source_type + "|" + ",".join(sorted(codes[:30]))
```
`scope_id` 只用前 30 只代码参与 hash。两个股票池如果前 30 只相同，scope_id 会碰撞，追踪和用户识别可能混淆。

**CE-05** `scripts/fetch_planner.py:71`
```python
def plan(scope_codes, selected_skills, *, ..., lookback_days: int = 365) -> dict:
```
`fetch_planner.plan()` 的 `lookback_days` 默认值 365，且调用处 `execution_engine.py:359` 没有传入本轮技能实际 max days：
```python
fetch = fetch_planner.plan(
    scope_codes=scope_codes,
    selected_skills=selected_skills,
    cache_dir=cache_dir,
)
```
K 线回看天数没有从 UI 参数端到端传到 fetch_planner。

**CE-06** `web/index.html:54-60`
全 A 档位命名和问财档位都有 "PRO 5000"，但语义不同：
- 全 A：`<option value="5000">PRO 5000（上限）</option>` → 从本地 ashare_codes.txt 取前 5000 只
- 问财：limit 参数最大 5000 → 问财语句最多返回 5000 条结果

两个都叫 PRO 5000，但一个是"本地名单截取"，另一个是"问财返回上限"，性质完全不同。

**CE-07** `web/app.js:197-198`（帮助文字里的正确解释已经存在）
```js
'全 A PRO 5000 走本地A股名单，不走问财语句过滤。当前本地名单超过 5000 只，所以 PRO 5000 是"最多拿前 5000 只"，不是无上限完整全量。',
'问财 PRO 5000 是"最多取 5000 条这个问财语句返回的结果"。如果问财只返回 800，只会得到 800；如果问财返回 6000，系统最多保留 5000。',
```
正确解释已经写在小 `i` 帮助里，但是帮助是折叠的，用户不主动展开看不到。档位选择界面本身没有直观区分。

**CE-08** `scripts/execution_engine.py:663-695`（三路径分支手写）
```python
if path_type == "sequential" and pos_skills:
    ...
elif path_type == "simple_hybrid" and pos_skills:
    ...
# parallel_and 走 expression pipeline
```
三路径是分开手写的业务分支，不是统一 graph 驱动。V6OP-026 已明确这是"后置"项。

**CE-09** `web/index.html`（无管理中心）
整个 index.html 是单页，没有管理中心路由或 tab。app.js 中搜索"管理中心/admin/history/历史报告"无结果。清缓存、历史报告、续跑等功能目前前端没有对应入口。

**CE-10** `scripts/execution_engine.py:424-430`（prefetch days 计算方式）
```python
prefetch_days = max(
    (params.get("skills", {}).get(s, {}).get("days", 365)
     for s in selected_skills),
    default=365,
)
```
预热时会从 params 里取各技能 days 的最大值。这说明 prefetch 触发阶段是拿到 days 的。但 fetch_planner 初次 plan（预热前的 readiness 判断）没有拿到这个 days，所以 K线"够不够"的初判是按 365 天文件名检查的，和实际用的 days 可能不一致。

---

## 三、文档证据汇总

**DE-01** V6OP-026：15/15 验收标准全部已闭合，pytest 481 passed，300 只预热 cache_hit=300 PASS。这是历史事实。

**DE-02** V6OP-026：browser_unavailable。Playwright 未安装，没有真实浏览器 DOM 验收，只有 API 层和 pytest 覆盖。

**DE-03** V6OP-026 风险清单：execution_engine.py 三路径分支、Playwright 缺失、mask_store.py 正式接入后置，均列为后续项。

**DE-04** V6OP-030 高风险清单：wencai key 没有传给 pywencai（风险 1）、PRO 5000 语义混乱（风险 2）、K线 days 端到端不一致（风险 4）、FAST_FULL_SCAN 不走三源降级（风险 5）、三路径分支和报告表达式漂移（风险 7）、中止非强中止（风险 8）。

**DE-05** V6OP-031 结论：第一阶段完成了一个能运行的骨架，但不能宣布"完全稳了"，真实使用暴露了需要返工对齐的风险。

**DE-06** V6OP-032：来源层、K线层、技能层、路径组合层、报告层、前端解释层、运行管理层的契约已经定义，作为第二阶段开发的基准。

---

## 四、对十三个问题的逐条回答

---

### 问题 1：第一阶段真实完成了什么？哪些只是结构跑通，不代表稳定可用？

**真实完成（站住了的）：**

| 能力 | 证据类型 | 状态 |
|---|---|---|
| 单页操盘台骨架（index.html + app.js） | 代码证据 CE-09 | 稳定可用，页面可加载 |
| 三来源路由（manual / all_a / wencai） | 代码证据 source_resolver.py | 结构完整，wencai key 未验证 |
| 6个 live producer（含 wencai 来源层） | 文档证据 DE-01 | 可运行，但有 days 硬编码问题 |
| 300只 K 线预热（8-worker 协调者） | 运行证据 DE-01 | cache_hit=300，已验证 |
| 三路径执行（顺序/并线/简单混合） | 代码证据 CE-08 | 可运行，手写分支，不是统一图 |
| Mask 内容寻址缓存（SHA256 指纹） | 代码证据 execution_engine.py | 逻辑已在，days 指纹可能不一致 |
| 中文命中解释（explanation_builder） | 文档证据 DE-01 | 已接通 |
| run_report.json / run_report.md | 文档证据 DE-01 | 基本结构在，字段不完整 |
| 参数面板（各技能展开参数） | 代码证据 app.js | 前端有，后端接收，部分硬编码未生效 |
| P1-P6 预设、问财收藏、板块联动 | 代码证据 CE-07 + index.html | 前端在，localStorage 本地存 |

**结构跑通但不代表稳定可用的：**

| 点 | 证据 | 真实风险 |
|---|---|---|
| 真实浏览器验收 | DE-02 | Playwright 未安装，DOM 级别未验收 |
| 问财 API key 是否真正生效 | CE-02 | api_key 没有传给 pywencai.get()，能不能访问是玄学 |
| 大规模预热三源降级 | CE-03 | FAST_FULL_SCAN 只走 baostock，baostock 失败直接 None |
| 缠论 days 参数生效 | CE-01 | 用户改了 days，缠论仍按 365 跑 |
| K线 days 端到端一致 | CE-05 | fetch_planner 初判按默认 365，不是 UI 参数 |
| output/current 旧文件残留 | DE-04 风险9 | 新 run 失败时，旧 prefetch_report 仍在目录里 |
| 三路径报告表达式与实际执行一致 | CE-08 | sequential/hybrid 靠手写分支计算，不是靠 expression runner |
| 中止运行（强中止） | DE-04 风险8 | 只设 abort flag，worker 子进程没有强杀 |
| scope_id 碰撞 | CE-04 | 只用前 30 只 hash，大池子有碰撞风险 |

**一句话结论（文档证据 DE-05 + 代码证据综合）：**
第一阶段建立了一个能跑、结构正确的骨架，验收标准按当时测试场景通过了。但真实使用场景（特别是问财来源不稳定、大范围全A、days参数修改）下，有多个链路没有端到端验证。它是"可用的骨架"，不是"稳定可用的系统"。

---

### 问题 2：原始大纲里有没有需要重新解释或修正的地方？

以下几处原始大纲写法在实现后需要重新解释，不是大纲错了，而是它被误读了：

**2.1 单页操盘台（章程第五章、四章）**

章程说"单页操盘台"，意思是"操盘主动线在一个页面完成"，不需要跳转。这个意图是对的。但在实现过程中，"单页"被解读成"所有功能都往这个页面塞"，导致主页面越来越重（来源、问财、板块联动、Phase A/B、P1-P6、收藏、技能面板、路径、参数、日志、结果、帮助全在一个视图里）。管理功能（历史报告、清缓存、续跑）没有独立的承接位置。

需要重新解释：单页体验 = 主动线单页，不等于所有内容单页。

**2.2 内容寻址缓存（章程第十章）**

章程第十章对技能结果缓存的指纹字段写得很清楚，包含 data_date。但实现时 fetch_planner 没有把本轮 days 传进去，而缠论 producer 自己硬编码了 days=365，导致 data_date 的计算来源和实际用到的 K 线来源不完全一致。章程的设计没有错，是实现没有完整落地。

需要说明：章程第十章写的是设计目标，第一阶段只完成了指纹计算框架，days 端到端一致是第二阶段的补齐任务。

**2.3 三源降级（章程第四章，V5继承表）**

章程明确说 V5 的三源降级（baostock → akshare → yfinance → 旧 K 线）必须进入 v6-op。实现时 ohlcv_provider.py 标准模式确实有三源降级（CE-03），但 data_prefetch.py 工作者强制设 FAST_FULL_SCAN=true，大规模预取走的是单源 baostock。baostock 失败后直接返回 None，不走后备源。章程目标和实现之间有缺口。

需要说明：三源降级在标准路径存在，在大规模预取路径（FAST_FULL_SCAN）没有完整继承。

**2.4 PRO 5000 的命名（章程第五章 + V5 继承表）**

章程在"扫描上限"参数项里说"问财返回最多 N 只（默认 300）"，没有强调全A和问财两个档位用同一个名字的问题。实现后两者都叫 PRO 5000，但语义完全不同（CE-06）。这是实现时的命名决策，章程没有明确要求统一名字，但没有预防这个混淆。

需要修正：全A档位和问财档位应该用不同的名字，不能都叫 PRO 5000。

---

### 问题 3：用户当前体验混乱的根因是什么？

根因不是单一的，而是三层叠加：

**根因 A：来源透明度不足**（最根本）

用户提交一个问财语句，看到"来源总数 = 45"或"来源总数 = 0"，但不知道这是因为：
- 问财语句本身筛出来就是这么多（正常）
- 问财 API 没有授权或 session 失效（问题）
- 问财 API 能连但字段解析失败（问题）
- 网络超时（问题）

报告里没有区分这四种情况（文档证据 DE-04 风险 3 + V6OP-032 规范）。用户唯一能看到的是"来源总数 = 45/0"，看不到 raw 信息。

**根因 B：多义词造成认知负担**（体验层）

代码证据 CE-06 + CE-07：PRO 5000 对两个来源类型含义不同，但界面上共享同一个名字。"缓存"在帮助文字里已经拆成三层解释（CE-07 的 HELP_TEXT 已经写对了），但帮助是折叠的，用户不看帮助就不知道区别。"预热"/"K线数据库够用"这类词传达的信号不准确（"够用"不等于"最新"）。

**根因 C：主页功能过重但缺少管理出口**（结构层）

代码证据 CE-09：整个 index.html 是单页，没有管理中心。历史报告、清缓存、续跑没有入口。问财收藏和板块收藏目前存在 localStorage，用户不知道这些数据的持久性边界。当主页面集中了过多功能，用户容易在操盘流程里迷失。

三层根因的优先级：
- 根因 A 最急（直接影响用户判断执行结果），属于 P0/P1
- 根因 B 中等（影响可解释性），属于 P1
- 根因 C 较慢（影响长期可维护性），属于 P2

---

### 问题 4：网络拉取路径白话解释

基于代码证据（source_resolver.py + fetch_planner.py + data_prefetch.py + ohlcv_provider.py + producers/）：

```
用户点启动
  │
  ▼
[来源层] source_resolver.py
  问财模式：发请求给问财 API（pywencai），返回股票代码列表
            问财返回 45 只 → 本轮股票池 = 45 只
            问财返回 0 只 → 本轮股票池 = 0 只，后面管道停止
  全A模式：从本地 data/ashare_codes.txt 读取，按 limit 截断
            PRO 5000 → 最多读 5000 只，不经过问财语句过滤
  手动模式：用户粘贴的代码列表直接用
  ↓
本轮股票池（scope_codes 列表）确定
  │
  ▼
[K线准备层] fetch_planner.py
  检查本地 var/cache/kline_daily/ 里有没有每只股票的 K 线文件
  有且不是已知失败 → 计入"本地已有"
  没有 → 计入"缺 K 线，需要预取"
  失败率 > 20% → 中止，不跑后续技能
  │
  ├─── 本地已有，不缺 K 线 → 跳过网络阶段，直接进技能
  │
  └─── 缺 K 线 → 触发 data_prefetch.py
         启动 8 个子工作者进程，round-robin 分配股票
         每个工作者：
           当前用 FAST_FULL_SCAN=true → 只走 baostock
           baostock 成功 → 写入 var/cache/kline_daily/{code}_365d.pkl
           baostock 失败 → 该股票标记失败（注意：当前不走 akshare/yfinance 备用）
  │
  ▼
[本地分析层] producers/（只读本地缓存，不访问网络）
  缠论 / K线形态 / SMC / 波浪 → 从本地 .pkl 读 K 线 → 分析 → 输出命中/未命中
  排雷 → 检查 ST/退市/次新/K线不足 → 输出剔除名单（负向）
  │
  ▼
[路径组合层] execution_engine.py
  顺序漏斗：技能 A 输出作为技能 B 的输入
  并线取交集：所有正向技能对同一股票池跑，取共同命中
  简单混合：前两个技能并线取交集，结果再接顺序过滤
  最后 EXCLUDE 掉排雷命中的股票
  │
  ▼
[解释层] explanation_builder.py + run_report.py
  从各技能的 evidence 字典生成中文命中解释
  输出 run_report.json（机器读）+ run_report.md（用户读）
```

**两个模式的关键区别（重要）：**

- **问财选股**：股票池的大小由问财语句决定，不是由系统决定。问财返回 45 只，池子就是 45 只；返回 0 只，管道就停在第一步。后续所有技能都在这 45 只里跑，不会自动补全。
- **全A扫描**：从本地名单取，不经过问财语句，数量由 limit 档位决定。PRO 5000 意味着最多 5000 只，但实际跑完还取决于这些股票的 K 线是否能取到。

---

### 问题 5：问财选股和全A扫描的区别

代码证据：source_resolver.py 里两个分支完全不同。

**问财选股（wencai）：**

1. 把用户输入的自然语言语句发给问财 API（通过 pywencai）
2. 问财在云端根据语句筛选，返回符合条件的股票列表
3. 返回多少只，本轮就用多少只
4. `PRO 5000 = 最多接收 5000 条问财返回结果`
5. 如果语句很严（"今日站上20日线且净流入且XX条件"），可能只返回 45 只甚至 0 只
6. 如果语句宽松（"非ST，按成交额降序"），可能返回接近 5000 只
7. 问财返回 0 → 管道第一步就停，后面的技能没有任何输入

**全A扫描（all_a）：**

1. 读取本地 `data/ashare_codes.txt` 文件（预先保存的全 A 股代码列表）
2. 按 limit 档位截取前 N 只
3. 不经过任何问财语句筛选，不依赖网络（读本地文件）
4. `PRO 5000 = 从本地 A 股名单取前 5000 只`
5. 取出来的 5000 只再去检查 K 线，缺的才去拉网络数据
6. 不受问财 API 状态影响

**核心差异一句话：**
问财是"让问财帮你筛，筛完多少就多少"；全A是"自己从本地名单里取一批，不筛直接用"。两者都可以设 PRO 5000 档位，但这个数字在两种模式下含义完全不同。

---

### 问题 6：PRO 5000 怎么解释

**对问财来说：**
- `PRO 5000` = "最多接收 5000 条问财语句筛选结果"
- 不是保证返回 5000 只
- 问财根据你的语句筛，筛出多少就是多少，最多截到 5000
- 如果问财只返回 45 只，你得到的就是 45 只，不是 5000 只

**对全A来说：**
- `PRO 5000` = "从本地A股名单里取前 5000 只"
- 不是"全A股完整量"（当前 A 股超过 5000 只，PRO 5000 是截取，不是全量）
- 不是"通过问财筛选的 5000 只"
- 也不是"保证能拿到 K 线数据的 5000 只"（后续预取失败的会被排除）

**当前命名问题（代码证据 CE-06）：**
两者都叫 PRO 5000，用户自然会混淆。帮助文字里的正确解释（CE-07）已经存在，但折叠在小 `i` 里，主界面上没有直观区分。

**建议改名（推断 + 人类需求）：**
- 全A档位：`本地A股 5000（截取）` 或 `全A扫描 5000`
- 问财档位：`问财最多 5000（实返由语句决定）`
- 这个改名属于 P1 优先级文案工作，不需要改后端逻辑。

---

### 问题 7：缓存/本地保存应该拆成哪三层？各层当前状态如何？

三层拆分框架（结合代码证据和人类需求）：

---

**★ 第一层：来源快照（Source Snapshot）**

是什么：
```
本轮从问财、全A或手动输入得到的股票代码列表。
这次问财语句返回了 45 只，这 45 只就是本轮来源池。
下次换语句，可能变成 80 只或 0 只。
```

当前代码状态（代码证据：source_resolver.py、execution_engine.py）：
- 来源快照以 `scope_codes` 形式存在于当前运行的内存和 `output/current/execution_result.json` 里
- 没有独立持久化的"历史来源快照"存储，每次 run 的来源包含在运行 JSON 归档里
- **已存在，基本稳定**。但前端没有清晰地把它标注为"仅本轮有效，下轮可能覆盖"

前端建议展示：
- 标注"★ 来源快照：本轮 XX 只，来自[问财/全A/手动]，下次重新运行可能覆盖"
- 不需要让用户操作，只需要让他知道"这不是长期数据库"

---

**★★ 第二层：K线数据库（OHLCV Cache）**

是什么：
```
系统已经把 000001.SZ 最近 365 天日K线保存到本机
var/cache/kline_daily/000001_SZ_365d.pkl。
下次再分析 000001.SZ，通常不用重新访问行情源。
但它可能不是今天最新的行情，要显示最新K线日期。
```

当前代码状态（代码证据：ohlcv_provider.py、fetch_planner.py）：
- 物理文件在 `var/cache/kline_daily/{code}_{days}d.pkl`
- fetch_planner 检查文件是否存在，存在就认为"够用"
- **已存在，物理稳定（电脑重启后仍在），但"够用"的判断标准不完整**：文件存在 ≠ 行情最新
- 旧 K 线（stale）有单独机制，但 UI 显示"K线数据库已够用"时没有同屏显示最新 K 线日期

前端建议展示：
- "★★ K线数据库"旁边必须显示"最新K线日期"（yyyy-MM-dd）
- 如果日期超过 3 个交易日，用黄色提示"行情数据可能不是最新"
- 不需要区分每只股票的日期，只显示本轮 scope 里最早/最晚 K 线日期即可

---

**★★★ 第三层：技能结果库（Mask Cache）**

是什么：
```
同一批股票（000001、000002、000063）、
同一个技能（SMC）、
同一组参数（signal_bars=15）、
同一个K线日期（2026-04-30），
系统已经算过一次，结果保存在 output/mask_cache/{fingerprint}.json。
下次条件完全一样，可以跳过重算。
```

当前代码状态（代码证据：execution_engine.py 579-601，mask_cache.py）：
- 指纹 = SHA256(skill_id + scope_codes + params + data_date + algo_version)
- 物理文件在 `output/mask_cache/{fp}.json`
- **已存在，逻辑正确**
- 但 data_date 的计算来源有问题（CE-05）：如果 fetch_planner 用默认 365 判断，而技能实际用了不同 days，data_date 可能不匹配

前端建议展示：
- "★★★ 技能结果库"显示"命中缓存 X 个技能 / 重新计算 Y 个技能"
- 解释："技能结果库"让用户明白：改了参数就会重新算，没改就直接用上次结果

---

**三层综合前端展示建议：**

不要叫"缓存"。叫"本轮数据来源"，分三行：
```
★  来源快照：本轮 45 只 [问财语句]，仅本轮有效
★★ K线数据库：已有 43 只，最新数据日期 2026-04-30 [黄色提示：距今6日]
★★★ 技能结果库：命中缓存 2 个技能，重新计算 1 个技能
```

---

### 问题 8：解释器/桥接层应该放在哪一层？

**当前代码状态（代码证据：execution_engine.py、explanation_builder.py、run_report.py）：**
- 后端已经有 `explanation_builder.py` 生成中文命中解释（按技能 evidence 拼）
- `run_report.py` 输出 JSON + Markdown 报告
- 前端读取 `run_report.json` 渲染结果

这已经是"后端生成结构化解释，前端展示"的模式，方向正确。

**差距在哪里（推断 + 文档证据 DE-04）：**

当前的解释层缺少"诊断型"字段。explanation_builder 生成的是命中解释（"缠论近3根有二买"），但没有：
- "为什么最终结果为 0？"的诊断
- "你下一步应该怎么办？"的建议

用户需要的不是"来源=0，技能跳过"，而是：
```
"本轮来源为 0 只，原因可能是：
  A. 问财语句过严（建议放宽条件）
  B. 问财 API 返回失败（建议检查连接）
  C. 问财 query 字段无法解析（建议用更简单的语句）
  下一步建议：先试 '非ST，收盘价大于20日均线，按成交额降序' 验证来源是否正常。"
```

**判断：应该用第三种（后端给标准解释字段，前端按用户视角展示）（推断 + 人类需求）：**

理由：
1. 运行诊断需要读 run_report.json 里的多个字段（source status、scope_count、prefetch report、各技能 hit_count），这个逻辑不适合放在前端 JS 里用字符串拼接，容易维护混乱。
2. 后端最了解每个字段的含义和边界条件，诊断逻辑应该在后端生成结构化字段（如 `diagnosis_code`、`suggestion`、`next_action`）。
3. 前端负责把这些字段翻译成用户可读的中文，可以按用户当前状态（选了什么来源、哪个技能、什么路径）进行上下文化展示。

**具体建议（讨论口吻，不是施工命令）：**

后端 run_report.json 应该增加一个 `run_diagnosis` 结构，包含：
```json
{
  "run_diagnosis": {
    "zero_reason": "source_empty | prefetch_failed | skill_too_strict | path_too_strict",
    "zero_explanation": "本轮来源为 0 只，问财 API 返回 empty_result",
    "suggestion": "建议放宽问财语句，或先用宽松 query 验证 API 连接正常",
    "data_freshness": "ok | stale | outdated",
    "data_freshness_note": "最新K线日期 2026-04-30，距今6个自然日"
  }
}
```

前端读取这个结构，按用户视角渲染。这样前端不需要重复诊断逻辑，后端也不需要生成 UI 字符串。

---

### 问题 9：问题归类框架是否合理？

**原有分类（来自问题文件）：**
来源层、网络取数层、本地保存层、技能层、路径层、报告/解释层、前端体验层、管理功能层

**判断：框架合理，但有一个重要补充（推断）：**

**需要补充"运行管理层"**（或把"管理功能层"拆成两个子层）：

当前"管理功能层"包含的东西太杂：
- 收藏/预设（来源配置管理）：属于"用户配置层"
- 历史报告（报告存档与查看）：属于"报告存档层"
- 清缓存/清日志（数据维护）：属于"系统维护层"
- 续跑/强中止（运行过程控制）：属于"运行控制层"

把这四类都叫"管理功能层"，开发时很容易把它们混在一起，优先级和实现难度完全不同：
- 收藏/预设：前端 localStorage，几乎不涉及后端，容易做
- 历史报告：读取 output/runs/ 目录，中等难度
- 清缓存：需要明确哪些目录/文件，有一定风险
- 续跑/强中止：需要改执行引擎，高难度

建议把"管理功能层"拆成：
- **用户配置层**：问财收藏、板块收藏、P1-P6 预设维护
- **运行控制层**：强中止、续跑、超时控制
- **数据维护层**：清 K 线缓存、清技能结果库、清日志
- **历史报告层**：历史运行记录查看、对比

**修正后的完整框架（9层 + 2个可合并）：**

| 层级 | 覆盖内容 |
|---|---|
| 来源层 | 问财、全A、手动、板块注入 |
| 网络取数层 | 是否访问 baostock/akshare/yfinance，是否补K线，三源降级 |
| 本地保存层 | 来源快照、K线数据库、技能结果库 |
| 技能层 | 缠论、K线、SMC、波浪、排雷，各技能参数 |
| 路径层 | 顺序、并线、简单混合，负向排雷 EXCLUDE |
| 报告/解释层 | 命中原因、为什么为 0、下一步建议、数据时效 |
| 前端体验层 | 页面布局、术语可读性、帮助可访问性、三层数据标记 |
| 用户配置层 | 问财收藏、板块收藏、P1-P6 预设 |
| 运行控制层 | 强中止、续跑、超时 |
| 数据维护层 | 清K线缓存、清技能结果库、清日志 |
| 历史报告层 | 历史运行查看、对比 |

---

### 问题 10：单页操盘台是否被误解了？

**是的，单页体验被误解了（推断 + 代码证据 CE-09 + 文档证据 DE-05）。**

章程的原意是：用户不需要跳转页面，在一个页面完成"选来源 → 选技能 → 调参数 → 启动 → 看结果"的完整操盘动线。

但在实现过程中，"单页"变成了"所有功能都在 index.html 里"，包括：
- 操盘主动线（对，该在这里）
- 问财收藏管理（可以在这里，但需要足够简洁）
- 板块联动 Phase A/B（可以在这里，但 UI 已经很重了）
- P1-P6 预设（适合在这里）
- 历史报告查看入口（目前没有，但如果加了就更重了）
- 清缓存/清日志（目前没有，但加了会更重）
- 续跑管理（没有，加了也会更重）
- 技能资产列表（灰色技能说明，帮助文字）

**建议的切分（讨论口吻）：**

**主页面保留（操盘主动线）：**
```
股票来源选择（含 P1-P6 预设入口、问财收藏快速访问）
核心技能勾选（6个 live 技能 + 简明参数）
路径选择（三选一）
启动 / 中止按钮
实时运行日志
当前运行状态（三层数据标记 + 诊断说明）
命中结果（含可展开证据）
本轮解释（run_diagnosis）
```

**管理中心承接（独立页面或侧边抽屉）：**
```
问财语句收藏管理（增删改查）
板块语句收藏管理
预设维护（修改 P1-P6 内容）
历史报告查看（按日期、run_id 列表）
K线数据库状态（当前有多少只、最新日期、大小）
清K线缓存 / 清技能结果库
技能资产列表（6个 live + 17个 gray，各技能说明）
压力测试说明
完整帮助文档
```

**折叠帮助保留在主页面（不移走）：**
```
三层数据标记的 ★ i 说明
各参数的 i 说明
PRO 5000 的含义说明
路径类型说明
```

**后端生成（不应该在前端硬拼）：**
```
run_diagnosis（为什么 0、下一步建议）
数据时效说明（最新K线日期、是否旧数据）
各技能命中/未中/失败摘要
```

**当前主要问题（代码证据 CE-09）：**
主页面已经承接了大量内容，但没有管理中心来接收"不需要每次用都看的功能"。如果继续往主页加历史报告、清缓存、续跑，主页会越来越重，反而背离了"五分钟能启动一次运行"的目标。

---

### 问题 11：页面分流是否应该成为当前架构优先级？

**判断：是重要的方向，但不是当前最紧急的（推断 + 文档证据 DE-04 + V6OP-032 优先级）。**

最紧急的仍然是来源真实性、K线 days 一致、强中止这些 P0/P1 问题。这些问题如果不解决，即使前端再整洁，用户也拿不到可信的结果。

但页面分流应该在第二阶段早期就决定，因为：
1. 如果管理功能先随意加到主页，后来再移到管理中心，会带来前端重构成本。
2. 现在趁主页还不太重，是建立"什么进主页、什么进管理中心"分流规则的好时机。
3. 规则一旦定好，后续功能加进来时就有明确归属，不需要每次讨论。

**建议：在第二阶段启动前，先讨论并签收"主页/管理中心分流边界"，然后再推进功能开发。**

---

### 问题 12：下一步应该继续讨论哪些问题，而不是马上改哪些代码？

以下问题需要先讨论（或先设计），不要直接施工：

**D1：问财授权机制（优先级最高）**
- pywencai 当前版本到底如何传 api_key？是否支持 key 参数？还是用 cookie / session？
- CE-02 发现 api_key 没有传给 pywencai.get()，但这不一定是 bug，可能是 pywencai 的设计就不接受 key 参数。
- 需要查 pywencai 文档或源码，再决定如何修。不能直接加 api_key=api_key 参数，可能会报错。

**D2：K线 days 端到端一致方案**
- 当前：fetch_planner 用默认 365，prefetch 用技能 max days，cz_producer 硬编码 365
- 应该讨论：days 应该有一个统一来源，从 UI → execution_engine → fetch_planner → prefetch → producer 全程传递，不用默认值偷跑
- 改之前需要明确：哪个技能的 days 改了后会影响 K 线文件命名（因为文件名包含 days，如 `000001_SZ_365d.pkl`，改成 180d 会产生新文件）

**D3：强中止机制设计**
- 当前 abort 只是设 flag，worker subprocess 没有强杀
- 需要讨论：强中止是否需要 terminate() 子进程？信号怎么传？已预取的 K 线是否保留？
- 这涉及资源管理，不能随便改，需要先写设计

**D4：管理中心架构**
- 历史报告：读取 output/runs/ 列表，每次 run 有 run_id，前端需要 API 拿列表和详情
- 清缓存：到底清哪一层？只清技能结果库？还是同时清 K 线缓存？需要明确边界和确认流程
- 续跑：断点续跑的语义是什么？从哪个步骤恢复？需要先定义 run state

**D5：PRO 5000 命名统一**
- 这是 P1 文案工作，改法简单，但需要确认新名字
- 建议讨论：全A档位叫什么、问财档位叫什么，两个命名要有直观区分

---

### 问题 13：如果未来进入第二阶段开发，应拆成哪些大块任务？

基于文档证据（V6OP-032 优先级分级）和代码证据，建议按以下顺序和分块：

---

**第二阶段 Block 1：链路稳定化（先做，不阻塞后续）**

子任务：
- 1a. 修复 czsc_producer 硬编码 days=365，接收 UI 参数（CE-01）
- 1b. K线 days 端到端传递：execution_engine → fetch_planner → prefetch → producer（CE-05）
- 1c. 问财 API key 机制明确：查 pywencai 文档 → 修 wencai_source → 更新日志和报告字段（CE-02）
- 1d. SMC 默认模式统一：registry / producer / engine / UI 默认值一致（文档证据 DE-04 风险 14）
- 1e. 时间统一 CST（文档证据 V6OP-032 规范）

这些改动边界清晰，可以单人做，有测试可以验证。

---

**第二阶段 Block 2：来源可信度增强**

子任务：
- 2a. 报告补字段：query原文、limit、actual_count、分页数、api_called、接口状态（DE-04 风险 10）
- 2b. 来源异常区分：empty_result / api_error / auth_error / parse_error（V6OP-032 规范）
- 2c. run_diagnosis 结构：zero_reason、suggestion、data_freshness（问题8的建议）
- 2d. output/current run_id 对齐：新 run 开始时清理或重命名旧文件（DE-04 风险 9）

---

**第二阶段 Block 3：K线数据库可信度**

子任务：
- 3a. K线"可计算"和"最新日期"分开显示（前端 + 后端字段补充）
- 3b. FAST_FULL_SCAN 三源降级：baostock 失败后继续 akshare → yfinance（CE-03）
- 3c. 写缓存失败进入 failed_codes（不再静默吞掉）
- 3d. Worker 超时和日志回传机制

Block 3 比 Block 1/2 难，3b/3d 需要先写设计。

---

**第二阶段 Block 4：运行控制**

子任务：
- 4a. 强中止：能 terminate worker subprocess，标记 run aborted
- 4b. scope_id 全量 hash：用完整 sorted codes，不只前 30 个（CE-04）
- 4c. 环境变量上下文管理：READ_CACHE_ONLY / FAST_FULL_SCAN / KLINE_CACHE_DIR 用 context manager，避免跨 run 污染

Block 4 的 4a 需要多人审，4b/4c 可单人做。

---

**第二阶段 Block 5：管理中心（架构讨论后再做）**

子任务：
- 5a. 定义主页/管理中心分流边界（讨论，签收）
- 5b. 历史报告 API + 前端：列表页、详情页
- 5c. 清缓存：定义三层清理操作（K线、技能结果、日志），前端确认流程
- 5d. 问财收藏、板块收藏移到管理中心（或在管理中心有独立管理页）
- 5e. 续跑机制：定义 run state、恢复点（高难度，需要先讨论）

Block 5 必须先讨论架构才能动代码，不能直接施工。

---

**第二阶段 Block 6：三路径统一图节点执行（后做）**

子任务：
- 6a. 把 sequential / parallel_and / simple_hybrid 的手写分支替换为 execution_plan 节点执行
- 6b. 报告表达式必须等于真实执行逻辑

这是 V6OP-026 明确后置的项，代码层面有 strategy_graph_builder 已输出 execution_plan，但还没有统一节点执行器。中等难度，可单人实现但需要测试覆盖全三路径。

---

**第二阶段 Block 7：灰色技能逐步接通（按需、逐个）**

- 当前 17 个灰色技能保留 metadata，不强行接通
- 每接通一个技能，先审计 V6 现有资产 + V5.10 历史 → 再包装为 producer → 再补测试
- 不批量接通，防止再次范围膨胀

---

**第二阶段 Block 8：打分制 / 抗压排名（高难度，暂不讨论细节）**

- 章程 Block 4（后续）的范畴
- 多人审，设计优先
- 不在 Block 1-7 完成前讨论实现

---

## 五、综合判断

**第一阶段完成了什么：** 可以用的操盘骨架，6个技能接通，三路径可运行，真实 K 线预取 300 只验收通过，报告体系基础在。

**哪里没站稳：** 问财 API key 生效情况未验证、czsc days 硬编码、K线 days 端到端不一致、大规模取数三源降级缺口、三路径手写分支、强中止未实现、管理功能没有出口。

**用户混乱根因：** 来源透明度不足（不知道问财为什么返回 45/0）+ 多义词（PRO 5000、缓存）+ 主页功能过重无管理出口。

**下一步应该做什么：** 先讨论问财授权机制、K线 days 方案、管理中心边界，然后按 Block 1 → 2 → 3 顺序推进，不要直接跳 Block 5/6/7。

---

## 六、待验证项

| 待验证点 | 原因 | 建议验证方式 |
|---|---|---|
| pywencai 是否支持 api_key 参数 | 代码读到没有传 key，但可能是 pywencai 设计如此 | 查 pywencai 源码或官方文档 |
| 问财 empty_result 是否真的是语句问题 | 当前报告没有 raw_status 字段，区分不清楚 | 运行固定宽松 query 做 smoke 测试 |
| Playwright 浏览器验收 | DE-02 browser_unavailable | 安装 Playwright + Chromium 后补测 |
| 大规模预取（全A 500+）实际效果 | 当前只验收了 300 只 cache_hit 场景，没有真实拉取场景 | 在有网络的环境下触发真实预取 |
| output/current 旧文件残留的实际影响 | 代码审计发现风险，但没有运行复现 | 连续两次 run（第一次成功，第二次来源为空），检查前端展示 |

---

签名：

```
Claude 分析员
V6OP Round 001 正式回复
2026-05-06
```
