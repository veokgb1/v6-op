# V6OP-031 第一阶段工作总结

日期：2026-05-06

范围：第一阶段从救场章程、真实数据主链、6 个 live 能力、单页操盘台、执行引擎、报告体系到最终签收的整体总结。本文同时吸收 V6OP-030 全链路风险审计结论，避免把“历史签收”误读为“无需再对齐”。

## 1. 阶段定位

V6OP 第一阶段的目标不是重做一个 V7，也不是简单复制 V5，而是在 V6 的蒙版/表达式能力基础上，重建一个能每天使用的单页操盘驾驶舱。

第一阶段的核心定位有三条：

1. 用户入口收敛：从 V6 多页面概念工作台，收敛为一个可操作页面。
2. 真实数据闭环：从 fixture / 样本数据，转为问财、全 A、本地 K 线缓存和真实 producer。
3. 执行路径落地：支持顺序漏斗、并行取交集、简单混合三种路径，让 V6 的组合能力先有可用形态。

## 2. 已完成的关键能力

### 2.1 单页操盘台

已形成 `web/index.html` + `web/app.js` + `web/styles.css` 的单页前端：

- 左侧：股票来源、问财语句、档位、技能选择、技能参数、执行路径、启动按钮。
- 中间：运行日志、数据状态、数据标记、本轮取数记录、警告、技能运行摘要。
- 右侧：命中结果、失败/未分析、报告入口。

这个页面已经从早期“像系统博物馆”转向“操盘动线”：选来源、选技能、调参数、启动、看结果。

### 2.2 股票来源

第一阶段接入三类来源：

- 手动输入代码：用户粘贴股票代码，直接作为本轮股票池。
- 全 A 股：从本地 A 股代码清单取用，按档位限制数量。
- 问财选股：使用自然语言语句请求问财，返回股票池。

当前必须强调：`PRO 5000` 对问财来说是“最多取 5000”，不是保证返回 5000，也不是全 A 全量。这个语义已经在 V6OP-030 中列为高风险，需要继续对齐。

### 2.3 六个 live 能力

第一阶段 live 能力为：

| 能力 | 类型 | 当前作用 |
|---|---|---|
| 问财 | 来源层 | 用自然语言生成股票池 |
| 缠论买点 | 正向技能 | 识别一买/二买/三买等买点 |
| K线形态 | 正向技能 | 识别锤子、吞没、启明星等形态 |
| SMC 聪明钱 | 正向/标注技能 | 识别 BOS / ChoCH / FVG 等结构信号 |
| 波浪分析 | 辅助/正向技能 | 用摆动点和 Fibonacci 容差识别波浪信号 |
| 排雷过滤 | 负向技能 | 剔除 ST、退市、K线不足、本地数据缺失等风险 |

其余 V6 技能资产保留为灰色，第一阶段不强行接通，防止范围继续膨胀。

### 2.4 参数面板

第一阶段已把主要技能参数放到页面：

- 缠论：买点窗口、买点类型、回看天数。
- K线形态：形态窗口、实体阈值、影线倍数、中性放行、回看天数。
- SMC：信号窗口、摆动窗口、收盘突破、分析模式、回看天数。
- 波浪：波浪回看、Swing 窗口、Fib 容差、每浪最少 K 线、K线回看。

后续已补充小 `i` 帮助按钮，方向是正确的：参数不要求用户死记硬背，而是在界面内解释。

### 2.5 执行路径

第一阶段支持三种固定路径：

| 路径 | 用户理解 | 当前实现状态 |
|---|---|---|
| 顺序漏斗 `sequential` | 上游筛完再给下游 | 已可运行 |
| 并行取交集 `parallel_and` | 每个技能对同一股票池跑，最后取共同命中 | 已可运行 |
| 简单混合 `simple_hybrid` | 前两个正向技能先并行取交集，后面再顺序过滤 | 已可运行 |

注意：当前 `execution_engine.py` 仍保留三路径手写分支。`strategy_graph_builder.py` 已能输出可检查的 `execution_plan` / `topological_order`，但“统一图节点执行器”尚未完成，属于后续架构收敛任务。

### 2.6 数据准备与本地 K线

第一阶段建立了两阶段执行理念：

1. 网络阶段：问财取股票池，缺 K线时预取日线数据。
2. 本地阶段：producer 只读本地 K线，不在分析阶段碰网络。

已形成的组件：

- `fetch_planner.py`：判断本地 K线是否足够。
- `data_prefetch.py`：批量预取。
- `ohlcv_provider.py`：读写本地 K线数据。
- `var/cache/kline_daily`：本地 K线数据库。

当前风险：V6OP-030 发现 full scan 下可能只走 baostock，不完全符合章程要求的 baostock → akshare → yfinance → 旧 K线降级链路；K线“够用”也不等于行情“最新”。这些需要后续修正。

### 2.7 技能结果缓存

已建立 `mask_cache.py` 内容寻址思路：

- 股票池
- 参数
- 算法版本
- 数据日期
- 技能 ID

这些共同构成技能结果库的复用条件。前端用 `★★★ 技能结果库` 解释给用户，这是正确方向。

当前风险：V6OP-030 发现本轮数据日期和技能回看天数可能没有端到端一致，尤其缠论 producer 存在硬编码 365 天风险。需要优先对齐。

### 2.8 报告体系

第一阶段已形成多份报告文件：

- `execution_result.json`：机器执行结果。
- `run_report.json`：前端读取的结构化报告。
- `run_report.md`：中文可读报告。
- `output/runs/<run_id>`：归档运行目录。

报告方向是对的：参数、路径、来源、数据覆盖、命中、失败、警告都应该被记录。

当前风险：问财 query、query_hash、分页、raw schema、接口状态等来源证据仍不够完整，导致排查“为什么只返回 45 / 0”时信息不足。

### 2.9 测试与验收

V6OP-026 历史签收记录：

- `pytest`: 481 passed
- `node --check web/app.js`: 通过
- 300 只预热 smoke: PASS
- skill catalog: live_count=6
- V6 资产矩阵: adapted=3 / read_only_reference=7
- Playwright: 当前环境 browser_unavailable，不冒充真实浏览器验收

这些是第一阶段的重要历史成果。

## 3. 架构设计总结

### 3.1 分层结构

当前 V6OP 大致可分为：

| 层级 | 主要文件 | 职责 |
|---|---|---|
| 前端层 | `web/app.js` / `index.html` / `styles.css` | 单页操盘台、参数、状态、报告展示 |
| API 层 | `scripts/v6op_server.py` | `/api/run`、`/api/stream`、`/api/result`、`/api/abort` 等 |
| 来源层 | `scripts/source_resolver.py`、`scripts/sources/*` | manual / all_a / wencai / sector scan |
| 数据层 | `fetch_planner.py`、`data_prefetch.py`、`ohlcv_provider.py` | K线检查、预取、读写 |
| 技能层 | `scripts/producers/*.py` | 缠论、K线、SMC、波浪、排雷 |
| 组合层 | `execution_engine.py`、`expression_auto_generator.py` | 路径执行、表达式、命中组合 |
| 报告层 | `run_report.py`、`explanation_builder.py` | JSON/Markdown/中文解释 |
| 资产层 | `skill_registry.py`、`skill_catalog.py`、`v6_asset_alignment.py` | 技能注册、V6 资产继承 |

### 3.2 用户概念收敛

内部可以有 Mask、Scope、Producer、Expression，但界面必须翻译成用户能懂的词：

- Scope → 来源股票池 / 来源总数
- Cache → 本地保存，且要分成问财来源快照、K线数据库、技能结果库
- Prefetch → 本轮补 K线
- Stale → 旧 K线
- Failure rate → 取数失败率

这项工作已经开始，但还没有完全完成。

## 4. 第一阶段真实结论

第一阶段不是失败，它已经完成了一个能运行的骨架，也把 V5 的实战能力和 V6 的组合能力初步接到同一个入口。

但第一阶段也不能简单宣布“完全稳了”。真实使用已经暴露出几个必须返工对齐的风险：

1. 问财来源真实性和 `PRO 5000` 语义必须讲清。
2. K线库“够用”和行情“最新”必须区分。
3. 技能回看天数必须端到端一致。
4. 三路径执行和报告表达式不能长期双轨。
5. 强中止、清理、续跑、历史报告等运行管理能力不能只做前端按钮。
6. V5 报告格式和流水日志不能退化。

因此，下一步不是盲目进入大规模新增技能，而应该先做“第一阶段稳定化与对齐”。

## 5. 后续工作建议

### 5.1 先易后难

优先做边界清晰、不容易牵动全局的事情：

1. 前端术语统一：把缓存、预热、scope、stale 改成中文可懂的词。
2. 报告补字段：问财 query、limit、实际返回、分页、query_hash、接口状态。
3. 小 `i` 帮助完善：参数、数据标记、压力测试说明。
4. run_id 对齐：当前页面只展示当前 run 的结果，避免旧文件误导。

### 5.2 中等难度

这些需要改后端，但边界仍清楚：

1. 修复 K线回看天数端到端一致。
2. 修复缠论 producer 硬编码 365 天。
3. 统一 SMC 默认模式。
4. 写缓存失败不再静默吞掉。
5. 所有时间统一 CST。

### 5.3 高难度，必须多人审

这些不要单人拍脑袋直接改：

1. 问财授权/key/session/pywencai 真实机制。
2. full scan 三源降级与 worker 中止。
3. 三路径统一成 graph execution。
4. 断点续跑、强中止、清缓存、历史报告的完整语义。
5. 后续打分制、抗压排名、并行积分模型。

## 6. 交付物索引

关键文档：

- `v6-op_full_rescue_charter.md`
- `docs/claude_v6op/reports/V6OP-026_final_first_stage_signoff_report.md`
- `docs/claude_v6op/reports/V6OP-030_full_logic_risk_audit.md`
- `docs/claude_v6op/reports/V6OP-031_phase1_work_summary_report.md`

关键代码入口：

- `web/app.js`
- `scripts/v6op_server.py`
- `scripts/execution_engine.py`
- `scripts/source_resolver.py`
- `scripts/fetch_planner.py`
- `scripts/data_prefetch.py`
- `scripts/ohlcv_provider.py`
- `scripts/producers/`
- `scripts/run_report.py`

