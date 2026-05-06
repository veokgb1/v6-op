# V6OP-P2-002 第二阶段过程：正式改建执行命令

> 指令发出：Codex 秘书 / V6OP 架构协调  
> 执行对象：Claude / V6OP 代码师  
> 工作目录：`F:\v.6\v6-op`  
> 本轮性质：第二阶段正式开发命令，会修改代码  
> 命令文件：`F:\v.6\v6-op\docs\claude_v6op\commands\V6OP-P2-002_phase2_process_formal_rebuild.md`  
> 报告路径：`F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-P2-002_phase2_process_formal_rebuild_report.md`

---

## 0. 先声明

Claude 代码师，你好。

本轮是 **V6OP 第二阶段过程的正式改建执行命令**。

这不是只读审阅命令，也不是只输出计划命令。你需要读取资料、阅读代码、实施代码升级、运行验收，并把报告写到指定路径。

请不要执行旧的 `V6OP-P2-001_phase2_process_full_upgrade.md`。本轮只以 `V6OP-P2-002` 为准。

---

## 1. 必读资料

请先完整阅读：

```text
F:\v.6\v6-op\v6-op_phase2_upgrade_charter.md
F:\v.6\v6-op\v6-op_full_rescue_charter.md
F:\v.6\v6-op\docs\architecture_discussion_tmp\phase1_cleanup_phase2_method\rounds\020_claude_analyst_response_phase2_full_scope_development_plan.md
F:\v.6\v6-op\docs\architecture_discussion_tmp\phase1_cleanup_phase2_method\rounds\022_claude_analyst_response_phase2_final_artifacts.md
```

再阅读第一阶段收尾事实依据：

```text
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-030_full_logic_risk_audit.md
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-031_phase1_work_summary_report.md
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-032_code_alignment_guidelines_report.md
```

然后阅读关键代码：

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
F:\v.6\v6-op\scripts\mask_cache.py
F:\v.6\v6-op\scripts\producers\
F:\v.6\v6-op\scripts\sources\
```

---

## 2. 总目标

第二阶段总宗旨：

```text
让用户在操盘时，能知道自己在相信什么。
```

本轮必须覆盖 G1-G8，不得自行缩小范围。

```text
G1 参数-数据-缓存全链路一致化
G2 全局解释层与分层归零诊断
G3 来源层语义清晰化与诊断字段保留
G4 问财授权验证与 Bridge 双角色定义
G5 数据血缘层定义与取数透明化
G6 主操盘台与管理中心分流
G7 运行管理语义正式化
G8 执行路径统一
```

你可以内部按 Pass 管理，但 Pass 只是执行顺序，不是减少目标。

---

## 3. 执行顺序

### Pass 1：可信运行主链

顺序：

```text
G1 -> G3 -> G4-auth -> G2 -> G5
```

完成标准：

- 用户设置的 `days` 真实影响 K线取数、技能分析和缓存指纹。
- 问财 0、少量返回、接近上限都有来源层解释。
- 问财授权是否真实生效有代码证据。
- 命中 0 时有五层诊断，能指出是哪一层清零。
- 报告和页面有本轮数据血缘摘要。

### Pass 2：页面与架构主链

顺序：

```text
G6 -> G7 -> G4-Bridge -> G8
```

完成标准：

- 主操盘台只保留 7 项操盘内容。
- 管理中心承接历史、缓存、设置、帮助、问财授权状态，不得有启动分析入口。
- abort、三层缓存清理、历史参数恢复有明确语义。
- Bridge constrained mode 和 second-pass mode 可用，并写入报告。
- 三条路径统一到 `expression_runner` 或结构化执行规格，报告表达式与真实执行一致。

### Pass 3：验收补漏

Pass 3 只允许修：

```text
文案
边界字段
漏测场景
G8 回归
```

Pass 3 不得新增大目标。

---

## 4. 具体改建要求

### G1 参数-数据-缓存全链路一致化

必须修复：

- `days` 不得在 producer、fetch planner、K线读取、缓存指纹中退回固定 365。
- K线“够用”判断必须基于用户实际设置天数。
- `run_report` 必须记录 `actual_days_used`。
- 不同 `days` 的技能结果缓存不得互相命中。

重点文件：

```text
scripts\producers\czsc_producer.py
scripts\execution_engine.py
scripts\fetch_planner.py
scripts\ohlcv_provider.py
scripts\mask_cache.py
scripts\run_report.py
```

### G2 全局解释层与分层归零诊断

必须新增或完善五层解释：

```text
source_layer
data_layer
skill_layer
path_layer
report_layer
why_zero
```

命中 0 时，结果区必须自动显示原因：

- 来源层为空。
- 数据层 K线不足或失败。
- 技能层某技能筛空。
- 路径层顺序漏斗/并行交集清零。
- 报告层解释字段缺失。

### G3 来源层语义清晰化

必须实现：

- 问财模式的 PRO 5000 显示为“最多接收问财返回结果”，不保证返回 5000。
- 全A模式的 5000 显示为“本地A股名单最多截取 5000”。
- 问财 0、少量返回、接近上限分别给不同提示。
- `query_text`、`actual_count`、`api_called`、`elapsed_s` 保留进报告。

### G4 问财授权与 Bridge

必须实现两部分：

1. 问财授权验证：
   - 检查 `api_key` 是否真实传入实际问财调用路径。
   - 如果没有生效，不能写“已授权”，必须写清楚实际状态。

2. Bridge 双模式：
   - constrained mode：结果必须是当前股票池与问财结果的交集。
   - second-pass mode：对已命中股票附加问财标签，不改变命中列表。

Bridge 是主操盘台参数/来源能力，不得新建独立分析页面。

### G5 Data Provenance

每轮报告必须记录：

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

写缓存失败不得静默吞掉，必须进日志或报告。

### G6 主操盘台与管理中心分流

主操盘台只保留：

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

管理中心不得出现启动运行按钮，不得成为第二套操盘台。

### G7 运行管理语义正式化

必须实现：

- abort 是步骤边界停止。
- 缓存清理分三层：来源快照、K线数据库、技能结果库。
- 三层清理互不误伤。
- 历史记录恢复参数到主操盘台，但不自动启动。
- 续跑必须有前提检查。

### G8 执行路径统一

必须最后做：

- `sequential`、`parallel_and`、`simple_hybrid` 的报告表达式与真实执行一致。
- 能走 `expression_runner` 的路径必须走 `expression_runner`。
- 如果某路径暂时不能完全迁移，必须在报告中写清结构原因、剩余缺口和不回归证据。
- G8 不得永久后置。

---

## 5. 验收场景

必须逐项验收并写入报告：

```text
问财返回 0
问财返回少量，例如 45
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
G8 sequential 验收
G8 parallel_and 验收
G8 simple_hybrid 验收
```

---

## 6. 必跑命令

至少运行：

```powershell
node --check web/app.js
node --check web/*.js
F:\v.6\v6-op\.venv\Scripts\python.exe -m pytest -q
```

如新增测试脚本或验收脚本，也必须运行。

如果 Playwright 或真实浏览器不可用，报告中写 `browser_unavailable`，不得把 HTTP smoke 冒充真实浏览器验收。

---

## 7. 禁止事项

禁止：

- 不得缩小 G1-G8 范围。
- 不得把 G8 永久后置。
- 不得把 Bridge、Data Provenance、分层解释器做成独立资料浏览页。
- 不得让管理中心具备启动分析能力。
- 不得只修一个问财 query 就宣布第二阶段完成。
- 不得用旧 output/current 冒充当前结果。
- 不得修改 `F:\v.6\v5.10`。
- 不得修改 `F:\v.6\v6`。
- 不得泄露 `.env` 或 API key。

---

## 8. 报告要求

最终报告必须写入：

```text
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-P2-002_phase2_process_formal_rebuild_report.md
```

报告必须包含：

1. 修改文件清单。
2. G1-G8 逐项完成状态。
3. Pass 1 / Pass 2 / Pass 3 的实际执行情况。
4. 每个新增字段和前端显示位置。
5. Data Provenance 示例。
6. 五层解释器示例。
7. Bridge 两种模式实现与验收结果。
8. 主操盘台 7 项与管理中心边界验收。
9. 三层缓存、abort、历史参数恢复的验收结果。
10. G8 三路径验收结果。
11. 必跑命令输出摘要。
12. 未完成项或失败项，不得掩盖。

报告最后签名：

```text
Claude / V6OP 代码师
V6OP-P2-002 第二阶段过程：正式改建
```

