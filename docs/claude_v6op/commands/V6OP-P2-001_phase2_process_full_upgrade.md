# V6OP-P2-001 第二阶段过程：全量升级启动命令

> 指令发出：Codex 秘书 / V6OP 架构协调  
> 执行对象：Claude / V6OP 代码师  
> 工作目录：`F:\v.6\v6-op`  
> 本轮性质：第二阶段过程，不属于第一阶段编号续排  
> 主报告路径：`F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-P2-001_phase2_process_full_upgrade_report.md`

---

## 0. 打招呼与工作约定

Claude 代码师，你好。

我们这边的协作方式是：Codex 秘书负责把架构讨论、用户要求和文件路径整理成命令；你负责在代码仓库里读取文件、判断真实代码、实施升级、写报告。讨论必须基于代码，不要只按文字想象。

本轮开始进入 **V6OP 第二阶段过程**。请不要沿用第一阶段的连续编号方式，所有本轮输出都使用 `V6OP-P2-001` 前缀，报告写入本文件指定路径。

---

## 1. 先读文件

请先完整阅读以下主文件：

```text
F:\v.6\v6-op\v6-op_phase2_upgrade_charter.md
F:\v.6\v6-op\v6-op_full_rescue_charter.md
F:\v.6\v6-op\docs\architecture_discussion_tmp\phase1_cleanup_phase2_method\rounds\020_claude_analyst_response_phase2_full_scope_development_plan.md
F:\v.6\v6-op\docs\architecture_discussion_tmp\phase1_cleanup_phase2_method\rounds\022_claude_analyst_response_phase2_final_artifacts.md
```

再读第一阶段收尾事实依据：

```text
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-030_full_logic_risk_audit.md
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-031_phase1_work_summary_report.md
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-032_code_alignment_guidelines_report.md
```

然后阅读关键代码入口：

```text
F:\v.6\v6-op\web\index.html
F:\v.6\v6-op\web\app.js
F:\v.6\v6-op\web\styles.css
F:\v.6\v6-op\scripts\v6op_server.py
F:\v.6\v6-op\scripts\execution_engine.py
F:\v.6\v6-op\scripts\source_resolver.py
F:\v.6\v6-op\scripts\fetch_planner.py
F:\v.6\v6-op\scripts\data_prefetch.py
F:\v.6\v6-op\scripts\ohlcv_provider.py
F:\v.6\v6-op\scripts\run_report.py
F:\v.6\v6-op\scripts\producers\
```

---

## 2. 本轮总目标

请按 `v6-op_phase2_upgrade_charter.md` 执行第二阶段升级，目标覆盖 G1-G8，不得自行缩范围。

第二阶段总宗旨：

```text
让用户在操盘时，能知道自己在相信什么。
```

本轮不是新增功能堆叠，也不是只修几个 bug。你要把第一阶段暴露出的核心不可信问题收束为可执行、可解释、可验收的系统机制。

---

## 3. 内部执行顺序

允许你内部按 Pass 管理，但 Pass 不是缩范围。

### Pass 1：信任基础主链

覆盖：

```text
G1 参数-数据-缓存全链路一致化
G3 来源层语义清晰化与诊断字段保留
G4-auth 问财授权验证
G2 全局解释层与分层归零诊断
G5 数据血缘层定义与取数透明化
```

执行顺序：

```text
G1 -> G3 -> G4-auth -> G2 -> G5
```

### Pass 2：结构与架构

覆盖：

```text
G6 主操盘台与管理中心分流
G7 运行管理语义正式化
G4-Bridge 问财 Bridge 双角色落地
G8 执行路径统一
```

执行顺序：

```text
G6 -> G7 -> G4-Bridge -> G8
```

G8 必须最后做。若 G8 引入严重回归，可以回退 G8 变更并在报告中明确说明，但不得把 G8 永久移出第二阶段。

### Pass 3：验收补漏

只允许做：

```text
文案修正
边界字段补齐
漏测场景补测
G8 轻微回归修复
```

Pass 3 不得新增大目标。

---

## 4. 必须完成的大项

### G1：参数-数据-缓存全链路一致化

重点检查并修复：

```text
scripts\producers\czsc_producer.py
scripts\execution_engine.py
scripts\fetch_planner.py
scripts\ohlcv_provider.py
scripts\mask_cache.py
```

要求：

- `days` 必须从用户参数传到取数、分析、缓存指纹。
- 不得固定使用 365 天判断 K线够用。
- 报告记录 `actual_days_used`。
- 不同 days 的缓存指纹不得互相命中。

### G2：全局解释层与分层归零诊断

要求建立五层解释：

```text
source_layer
data_layer
skill_layer
path_layer
report_layer
why_zero
```

命中为 0 时，页面结果区必须解释是哪一层清零，以及下一步建议。

### G3：来源层语义清晰化

要求：

- 问财模式的 PRO 5000 解释为“最多接收问财返回结果”，不是保证返回 5000。
- 全A模式的 5000 解释为“本地A股名单最多截取 5000”。
- 问财 0、少量返回、接近上限三种情况有不同提示。
- `query_text`、`actual_count`、`api_called`、`elapsed_s` 保留到报告。

### G4：问财授权与 Bridge

Pass 1 完成授权验证：

- 明确 `api_key` 是否真实传入 `pywencai.get()` 或实际问财调用路径。
- 如果 key 当前无效或未使用，报告中写清楚，不得写成已验证通过。

Pass 2 完成 Bridge：

- Constrained mode：在已有股票池内做问财约束，结果必须是已有池子集。
- Second-pass mode：技能筛选后做问财标签/验证，不能改变命中列表，只附加标签。
- Bridge 是主操盘台来源/参数选项，不是独立页面。

### G5：Data Provenance

每轮运行必须记录：

```text
fetch_mode
total
fetched_new
from_cache
failed
degraded
oldest_data_date
per_stock.source
per_stock.is_new_fetch
per_stock.is_degraded
per_stock.latest_date
per_stock.trust_level
```

写缓存失败不得静默吞掉，必须有日志或报告字段。

### G6：主操盘台与管理中心分流

主操盘台只保留 7 项：

```text
股票来源选择
技能开关与参数调节
执行路径选择
启动按钮 + 实时进度状态区
命中结果列表
本轮全局解释
本轮数据血缘摘要
```

管理中心承接：

```text
历史运行记录
分层缓存清理
系统设置
帮助文档
问财授权状态检查
```

管理中心不得有启动运行入口，不得变成第二个操盘台。

### G7：运行管理语义

要求：

- abort 是步骤边界停止。
- 清缓存分三层：来源快照、K线数据库、技能结果库。
- 三层清理互不误伤。
- 历史记录恢复参数到主操盘台，但不自动启动。
- 续跑必须有前提检查。

### G8：执行路径统一

要求：

- `sequential` 和 `simple_hybrid` 逐步改为走 `expression_runner`。
- `parallel_and` 不回归。
- 报告中的 `expression_spec` 变成结构化规格，并与真实执行一致。
- G8 必须单独验收三条路径。

---

## 5. 验收场景

至少覆盖以下场景，并在报告中逐项说明结果：

```text
问财返回 0
问财返回少量，如 45
问财接近上限
全A 5000
days=365
days=730
不同 days 缓存不互相命中
K线本地已有
K线新拉
K线取数失败
K线旧数据
单技能筛空
顺序路径中途筛空
并行交集为空
排雷负向过滤
Bridge constrained mode
Bridge second-pass mode
abort
三层缓存分别清理
历史记录恢复参数但不启动
管理中心无启动运行入口
主操盘台只保留 7 项操盘内容
G8 sequential 走 expression_runner
G8 parallel_and 无回归
G8 simple_hybrid 走 expression_runner
```

---

## 6. 必跑检查

至少运行：

```powershell
node --check web/app.js
node --check web/*.js
F:\v.6\v6-op\.venv\Scripts\python.exe -m pytest -q
```

如新增或修改专门脚本，请运行对应脚本。

如浏览器/Playwright 不可用，报告中写 `browser_unavailable`，不得把 HTTP smoke 冒充真实浏览器验收。

---

## 7. 禁止事项

本轮禁止：

- 不得缩小 G1-G8 范围。
- 不得把 G8 永久后置。
- 不得把 Bridge、Data Provenance、分层解释器做成独立资料浏览页。
- 不得让管理中心具备启动分析能力。
- 不得只修一个问财 query 后宣布第二阶段完成。
- 不得用旧 output/current 冒充当前结果。
- 不得修改 `F:\v.6\v5.10`。
- 不得修改 `F:\v.6\v6`。
- 不得泄露 `.env` 或 API key。

---

## 8. 报告要求

最终报告必须写入：

```text
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-P2-001_phase2_process_full_upgrade_report.md
```

报告必须包含：

1. 修改文件清单。
2. G1-G8 逐项完成状态。
3. Pass 1 / Pass 2 / Pass 3 的实际执行情况。
4. 每个新增报告字段和前端显示位置。
5. Data Provenance 字段与示例。
6. 五层解释器字段与示例。
7. Bridge 两种模式实现方式与验收结果。
8. 主操盘台 7 项与管理中心边界验收。
9. 三层缓存、abort、历史恢复参数的验收结果。
10. G8 三路径验收结果。
11. 必跑命令输出摘要。
12. 未完成项或失败项，不得掩盖。

签名：

```text
Claude / V6OP 代码师
V6OP-P2-001 第二阶段过程：全量升级
```

