# V6OP-001 阶段 0 数据引擎与 CZSC Producer 闭环

> 下发角色：v6-op 架构师（Codex）
> 执行角色：Claude
> 状态：ready
> 日期：2026-05-05

## 1. 目标

在 `F:\v.6\v6-op` 内完成 charter 阶段 0：

```text
真实 K 线预热 -> 本地 pickle 缓存 -> CZSCProducer 只读缓存 -> 输出 V6 Mask JSON
```

本轮不做 UI，不做后端 API，不接完整 6 个 Producer。

## 2. 背景

V6OP 不是推翻 V6，也不是复制 V5。

它要把 V6 的 `Universe / Mask / MaskExpression` 后台能力，和 V5 已验证的数据预热、本地分析能力结合起来，重建一个每天能用的操盘主线。

当前路径：

```text
V6OP 工作目录：F:\v.6\v6-op
V6 后台能力库：F:\v.6\v6
V5 只读参考库：F:\v.6\v5.10
```

## 3. 必读文件

请先读：

```text
F:\v.6\v6-op\v6-op_full_rescue_charter.md
F:\v.6\v6-op\docs\00_v6op_supervision_rules.md
F:\v.6\v6-op\docs\01_asset_audit_and_phase0_plan.md
F:\v.6\v6\scripts\v6\contracts.py
F:\v.6\v6\scripts\v6\mask_store.py
F:\v.6\v6\scripts\v6\io_utils.py
F:\v.6\v5.10\scripts\shared_data.py
F:\v.6\v5.10\scripts\prefetch_kline_cache.py
F:\v.6\v5.10\scripts\step2_czsc_analysis.py
F:\v.6\v5.10\scripts\utils\runtime_paths.py
F:\v.6\v5.10\scripts\utils\code_list.py
```

V5 文件只能只读参考，不允许修改。

## 4. 允许修改

只允许修改 / 新增：

```text
F:\v.6\v6-op\*
```

建议建立：

```text
requirements.txt
.env.example
.gitignore
scripts\__init__.py
scripts\ohlcv_provider.py
scripts\data_prefetch.py
scripts\producers\__init__.py
scripts\producers\czsc_producer.py
scripts\v6_contracts.py 或 scripts\v6_compat.py
data\ashare_codes.txt
output\current\
var\cache\kline_daily\
tests\
docs\claude_v6op\reports\
```

可以创建 V6OP 自己的 `.venv`，可以安装阶段 0 必要依赖。

当前机器可见：

```text
Python 3.13.3
```

如某些库不支持 Python 3.13，请在报告中说明阻断点，并给出建议方案。不要复制 V5/V6 的 `.venv`。

## 5. 禁止修改

禁止：

```text
F:\v.6\v5.10\*
F:\v.6\v6\*
```

禁止复制：

```text
F:\v.6\v5.10\.env
F:\v.6\v5.10\.venv
F:\v.6\v6\.env
F:\v.6\v6\.venv
F:\v.6\v5.10\var
F:\v.6\v5.10\output
```

禁止：

- 写 UI
- 新建 V6 账本目录
- 扩张现有 V6 workbench 页面
- 直接运行 V5 脚本作为主路径
- 从 `F:\v.6\v5.10` import 业务模块作为运行依赖
- 使用 fixture 冒充真实行情数据
- 把 V5 Slot / 漏斗池接口带进 V6OP
- 把真实 key 写入代码、测试、报告或输出

## 6. 具体任务

### 6.1 基础工程与环境

在 `F:\v.6\v6-op` 建立最小工程结构。

如果需要依赖，创建 V6OP 自己的 `requirements.txt`。依赖应尽量少，优先满足阶段 0。

可以使用：

- `pandas`
- `baostock`
- `akshare`
- `yfinance`
- `czsc`
- `pytest`

但请按实际需要安装，不要机械复制 V5 的全量 requirements。

### 6.2 V6 合约引用层

建立一个轻量兼容层，让 V6OP 能引用 V6 的稳定合约：

```text
F:\v.6\v6\scripts\v6\contracts.py
```

要求：

- 不复制 V6 文件
- 不修改 V6 文件
- 能在 V6OP 的 producer 中生成或序列化 Mask 形态
- 如果直接 import 路径不稳定，可以写清晰的 `v6_compat.py`

### 6.3 复制纯数据

复制：

```text
F:\v.6\v5.10\data\ashare_codes.txt
```

到：

```text
F:\v.6\v6-op\data\ashare_codes.txt
```

这是本轮唯一允许从 V5 直接复制的文件。

### 6.4 实现 `ohlcv_provider.py`

参考 V5 `shared_data.py`，在 V6OP 内重写：

- 股票代码格式转换
- pickle 缓存读写
- 缓存 TTL
- `READ_CACHE_ONLY` 等价能力
- baostock / akshare / yfinance 三源降级
- stale cache 降级，并在 report 中标记

路径必须使用 V6OP 自己的：

```text
var\cache\kline_daily\
```

不要使用 V5 的 `utils.runtime_paths` 作为运行依赖；可以只读参考它的目录思想。

### 6.5 实现 `data_prefetch.py`

参考 V5 `prefetch_kline_cache.py`，在 V6OP 内重写：

- coordinator / worker 模式
- 默认 8 worker
- round-robin 分片
- 每个 worker 独立拉取自己那份代码
- baostock 单连接复用或等价保护
- worker report
- 汇总 report

CLI 至少支持：

```text
python scripts\data_prefetch.py --codes data\ashare_codes.txt --limit 50 --days 365 --workers 8
```

输出：

```text
output\current\prefetch_report.json
```

report 至少包含：

```text
total_codes
kline_days
workers
cache_hit
fetched_ok
stale_used
failed
failed_codes
stale_codes
duration_seconds
cache_dir
```

### 6.6 实现 `CZSCProducer`

参考 V5 `step2_czsc_analysis.py`，在 V6OP 内重写 / 包装核心分析逻辑：

- 输入：股票代码列表 + 本地缓存路径 + 参数
- 只读缓存，不触网
- 检测 CZSC 买点
- 过滤最近 N 根无信号的股票
- 输出 Mask JSON

CLI 至少支持：

```text
python scripts\producers\czsc_producer.py --codes data\ashare_codes.txt --limit 50 --cache-dir var\cache\kline_daily --out output\current\czsc_mask.json
```

输出 Mask JSON 至少包含：

```text
mask_id
producer
hit_semantics
hit_codes
miss_codes
evidence
params
data_mode
cache_dir
generated_at
```

`hit_semantics` 应为：

```text
positive
```

如果 `czsc` 依赖无法在当前 Python 环境安装或运行，不要伪造命中。请明确报告阻断，并尽量保留可运行的缓存读取、输入输出框架和依赖错误信息。

### 6.7 测试

至少补充 smoke tests：

- 代码文件读取
- 缓存路径生成
- prefetch report 结构
- CZSCProducer 输出结构
- V6OP 不引用 V5 运行路径

测试不能要求真实网络才能通过；真实网络预热作为手动验收命令。

## 7. 输出要求

必须输出：

```text
requirements.txt
scripts\ohlcv_provider.py
scripts\data_prefetch.py
scripts\producers\czsc_producer.py
data\ashare_codes.txt
output\current\prefetch_report.json        # 如果已实际跑预热
output\current\czsc_mask.json              # 如果已成功跑 Producer
docs\claude_v6op\latest_report.md
docs\claude_v6op\current_status.md
docs\claude_v6op\reports\V6OP-001_phase0_data_engine_and_czsc_report.md
```

如果真实预热因为网络、依赖或环境阻断不能完成，报告必须写清：

- 阻断命令
- 错误摘要
- 已完成到哪一步
- 下一步需要 Codex / 用户确认什么

## 8. 验收命令

优先尝试：

```powershell
python --version
python -m pytest -q
python scripts\data_prefetch.py --codes data\ashare_codes.txt --limit 50 --days 365 --workers 8
python scripts\producers\czsc_producer.py --codes data\ashare_codes.txt --limit 50 --cache-dir var\cache\kline_daily --out output\current\czsc_mask.json
```

如果创建了 `.venv`，请在报告里写实际使用的 Python 路径，并用 `.venv` 复跑。

## 9. 报告落点

必须更新：

```text
docs\claude_v6op\latest_report.md
docs\claude_v6op\current_status.md
```

必须新增：

```text
docs\claude_v6op\reports\V6OP-001_phase0_data_engine_and_czsc_report.md
```

报告必须包含：

- 改了哪些文件
- 没碰哪些敏感文件
- 是否复制 `.env` / `.venv`
- 是否修改 V5.10
- 是否修改 V6
- 是否真实访问外部接口
- 是否读取真实 key
- 测试命令和结果
- 阻断点
- 需要 v6-op 架构师审阅的 3-5 点
- 下一步建议

## 10. 完成后回复

Claude 聊天窗口只需要短回复：

```text
Claude 已完成 V6OP-001 阶段 0 数据引擎与 CZSC Producer 闭环。

报告已写入：
- docs/claude_v6op/latest_report.md
- docs/claude_v6op/current_status.md
- docs/claude_v6op/reports/V6OP-001_phase0_data_engine_and_czsc_report.md

测试：
- <命令>：<结果>
- <命令>：<结果>

是否真实访问外部接口：是/否
是否读取或落盘真实密钥：否
是否修改 V5.10 / V6：否

需要 v6-op 架构师审阅：
- ...
```

