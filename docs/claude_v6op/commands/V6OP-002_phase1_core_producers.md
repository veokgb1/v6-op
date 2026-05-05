# V6OP-002 阶段 1 六个核心能力接通

> 下发角色：v6-op 架构师（Codex）
> 执行角色：Claude
> 状态：ready
> 日期：2026-05-05

## 1. 目标

在 `F:\v.6\v6-op` 内完成 charter 阶段 1：

```text
问财 Source + 缠论 + SMC + K线形态 + 波浪 + 排雷
```

本轮目标是让 6 个核心能力都能进入统一 Producer / Source 体系，并能各自产生结构化输出。

本轮仍不做 UI，不做完整后端 API，不做 Fetch Planner。

## 2. 当前基础

V6OP-001 已完成：

- V6OP 自建 `.venv`
- 真实 K 线预热
- `var/cache/kline_daily` pickle 缓存
- `CZSCProducer`
- `output/current/czsc_mask.json`
- `docs/claude_v6op/reports/V6OP-001_codex_review.md`

请先阅读 V6OP-001 的 Claude 报告和 Codex 审阅：

```text
F:\v.6\v6-op\docs\claude_v6op\latest_report.md
F:\v.6\v6-op\docs\claude_v6op\current_status.md
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-001_phase0_data_engine_and_czsc_report.md
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-001_codex_review.md
```

## 3. 必读文件

```text
F:\v.6\v6-op\v6-op_full_rescue_charter.md
F:\v.6\v6-op\docs\00_v6op_supervision_rules.md
F:\v.6\v6-op\docs\01_asset_audit_and_phase0_plan.md
F:\v.6\v6-op\scripts\ohlcv_provider.py
F:\v.6\v6-op\scripts\data_prefetch.py
F:\v.6\v6-op\scripts\producers\czsc_producer.py
F:\v.6\v6-op\scripts\v6_compat.py
F:\v.6\v5.10\scripts\step1_wencai_merged.py
F:\v.6\v5.10\scripts\step4_landmine_filter.py
F:\v.6\v5.10\scripts\step5_smc_analysis.py
F:\v.6\v5.10\scripts\step7_kline_pattern.py
F:\v.6\v5.10\scripts\step8_wave_analysis.py
```

V5 文件只能只读参考，不允许修改。

## 4. 允许修改

只允许修改 / 新增：

```text
F:\v.6\v6-op\*
```

建议新增：

```text
scripts\sources\__init__.py
scripts\sources\wencai_source.py
scripts\skill_registry.py
scripts\producers\smc_producer.py
scripts\producers\kline_producer.py
scripts\producers\wave_producer.py
scripts\producers\landmine_producer.py
scripts\run_core_producers.py
tests\test_phase1_producers.py
output\current\wencai_scope.json
output\current\smc_mask.json
output\current\kline_mask.json
output\current\wave_mask.json
output\current\landmine_mask.json
output\current\core_producer_summary.json
```

也可以调整阶段 0 文件，但只能是为了兼容阶段 1，例如：

- 依赖锁定
- evidence 字段补 `adjust: hfq`
- `V6_SCRIPTS_PATH` 覆盖
- 统一 Mask JSON 字段

## 5. `.env` 与真实 Key 规则

上一轮规则需要修正：V6OP 不是永远不能使用真实 `.env`。

本轮允许 **受控创建**：

```text
F:\v.6\v6-op\.env
```

用途仅限：

- 问财真实 source
- 后续 AI / MiniMax / DeepSeek / 硅基流动等 key 的 V6OP 独立承载

规则：

1. 如果需要真实问财 key，优先从 `F:\v.6\v6\.env` 读取变量，再视情况参考 `F:\v.6\v5.10\.env`。
2. 只复制必要变量到 `F:\v.6\v6-op\.env`，例如：
   - `IWENCAI_API_KEY`
   - `TONGHUASHUN_API_KEY`
   - `SKILLHUB_API_KEY`
   - 后续 AI 所需 key 可以保留，但本轮不主动调用 AI。
3. `.env` 必须被 `.gitignore` 排除。
4. 不得在日志、报告、测试、JSON 输出、Markdown 中打印或保存真实 key 值。
5. 报告只能写“复制了哪些变量名”，不能写变量值。
6. 如果未复制 `.env`，也要说明原因。

本轮可以读取 `.env`，但只有 `wencai_source.py` 需要真实问财时才读；本地分析 Producer 不得依赖 `.env`。

## 6. 禁止修改

禁止修改：

```text
F:\v.6\v5.10\*
F:\v.6\v6\*
```

禁止：

- 写 UI
- 写后端 API
- 做 Fetch Planner
- 做任意 DAG 编辑器
- 扩张 V6 workbench
- 把 V5 Slot / 漏斗池接口带入 V6OP
- 把问财固定成唯一股票来源
- 使用 fixture 冒充本地 K 线 Producer 结果
- 将真实 key 写入 Git 可追踪文件

## 7. 具体任务

### 7.1 统一 Producer 输出契约

为 6 个能力统一输出字段：

```text
mask_id
producer
skill_id
skill_name
hit_semantics
hit_codes
miss_codes
evidence
params
data_mode
data_requirement
generated_at
```

`hit_semantics`：

- 问财：`positive`
- 缠论：`positive`
- SMC：`positive`
- K线形态：`positive`
- 波浪：`positive`
- 排雷：`negative`

本地 K 线类 Producer 必须标注：

```text
data_mode: read_cache_only
adjust: hfq
```

### 7.2 `skill_registry.py`

建立 V6OP 自己的 6 个核心能力注册表。

至少包含：

- skill_id
- 中文名
- producer/source 类名
- hit_semantics
- data_requirement
- 默认参数
- 是否已接通真实数据

不要直接复用 V5 `skill_registry.py` 格式。

### 7.3 `WencaiSource`

从 V5 `step1_wencai_merged.py` 只读提取问财调用经验，在 V6OP 中重写：

- 支持自然语言 query
- 读取 V6OP 自己 `.env` 的问财 key
- 输出 `scope_codes`
- 输出 `output/current/wencai_scope.json`
- request/response 必须脱敏

CLI 示例：

```powershell
.venv\Scripts\python.exe scripts\sources\wencai_source.py --query "近20日涨幅小于10%，成交额放大" --limit 50 --out output\current\wencai_scope.json
```

如果 key 缺失或接口失败，不要伪造结果。可以降级为明确的 blocked 状态，并保留手动 codes / 全 A 股来源可用。

### 7.4 `SMCProducer`

参考 V5 `step5_smc_analysis.py`，在 V6OP 中重写：

- 只读本地缓存
- 检测 BOS / ChoCH / FVG
- 支持基础参数
- 输出 `smc_mask.json`

如果第三方库兼容性不足，可以先实现 V5 核心逻辑可行子集，但报告必须写清“完整/简化/阻断”。

### 7.5 `KlineProducer`

参考 V5 `step7_kline_pattern.py`，在 V6OP 中重写：

- 只读本地缓存
- 检测锤子线、吞没、早晨之星等核心形态
- 输出 `kline_mask.json`

### 7.6 `WaveProducer`

参考 V5 `step8_wave_analysis.py`，在 V6OP 中重写：

- 只读本地缓存
- swing window + Fibonacci tolerance
- 输出 `wave_mask.json`

可以先交付可运行的轻量版，但不能假装完整 Elliott 引擎已经完美生产化。

### 7.7 `LandmineProducer`

参考 V5 `step4_landmine_filter.py`，在 V6OP 中重写：

- `hit_semantics = negative`
- 标记 ST / 退市 / 次新股 / K 线不足 / 缓存缺失 / 数据不可用
- 输出 `landmine_mask.json`

本轮必须把 V6OP-001 的 baostock 失败代码纳入数据不可用或缓存缺失证据，不让它们混入正向命中。

### 7.8 一键阶段 1 汇总

新增：

```text
scripts\run_core_producers.py
```

支持在已有缓存上运行本地 5 个 Producer：

```powershell
.venv\Scripts\python.exe scripts\run_core_producers.py --codes data\ashare_codes.txt --limit 50 --cache-dir var\cache\kline_daily
```

输出：

```text
output/current/core_producer_summary.json
```

summary 至少包含：

- 每个能力是否完成
- 每个 mask 路径
- hit_count / miss_count
- failed_count
- data_mode
- 是否读取 `.env`
- 是否访问外部接口

## 8. 验收命令

优先执行：

```powershell
cd F:\v.6\v6-op
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts\run_core_producers.py --codes data\ashare_codes.txt --limit 50 --cache-dir var\cache\kline_daily
.venv\Scripts\python.exe scripts\sources\wencai_source.py --query "近20日涨幅小于10%，成交额放大" --limit 50 --out output\current\wencai_scope.json
```

如果问财 key 或接口阻断，第三条可以失败，但必须是安全失败，且报告要写清原因。

## 9. 输出要求

必须更新：

```text
docs\claude_v6op\latest_report.md
docs\claude_v6op\current_status.md
```

必须新增：

```text
docs\claude_v6op\reports\V6OP-002_phase1_core_producers_report.md
```

## 10. 报告必须说明

- 改了哪些文件
- 是否创建或更新 `F:\v.6\v6-op\.env`
- `.env` 复制了哪些变量名，不能写变量值
- 是否真实访问问财接口
- 是否访问 baostock / akshare / yfinance
- 是否读取或落盘真实密钥
- 是否修改 V5.10 / V6
- 每个 Producer 的完成度：完整 / 简化 / 阻断
- 测试命令和结果
- 需要 v6-op 架构师审阅的 3-5 点
- 下一步建议

## 11. 完成后回复

Claude 聊天窗口短回复：

```text
Claude 已完成 V6OP-002 阶段 1 六个核心能力接通。

报告已写入：
- docs/claude_v6op/latest_report.md
- docs/claude_v6op/current_status.md
- docs/claude_v6op/reports/V6OP-002_phase1_core_producers_report.md

测试：
- <命令>：<结果>

.env：
- 是否创建/更新：是/否
- 复制变量名：<只列变量名，不列值>

真实外部接口：
- 问财：是/否/阻断
- 行情源：是/否

是否修改 V5.10 / V6：否

需要 v6-op 架构师审阅：
- ...
```

