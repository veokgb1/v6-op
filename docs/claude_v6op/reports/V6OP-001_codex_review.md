# V6OP-001 Codex 审阅与答复

> 文档作者角色：v6-op 架构师（Codex）
> 写入性质：Claude V6OP-001 交付后的独立审阅，不替代 Claude 原始报告
> 最后更新时间：2026-05-05

## 1. 签收结论

V6OP-001 可以阶段性签收。

本机复跑：

```text
.venv\Scripts\python.exe -m pytest -q
结果：20 passed
```

已确认 Claude 报告落点存在：

```text
docs/claude_v6op/latest_report.md
docs/claude_v6op/current_status.md
docs/claude_v6op/reports/V6OP-001_phase0_data_engine_and_czsc_report.md
```

阶段 0 主目标已经跑通：

```text
真实 K 线预热 -> 本地 pickle 缓存 -> CZSCProducer 只读缓存 -> 输出 Mask JSON
```

## 2. 对 Claude 待确认点的答复

### 2.1 czsc 版本策略

接受当前 `czsc 0.10.12` 作为 V6OP 当前工作版本。

下一轮要求：

- 不回退到 V5 的 `0.9.68`，除非发现明确兼容性问题。
- 将 `requirements.txt` 从宽松范围改为当前实测可复现版本。
- Producer 报告中继续写入 `czsc_version`。

### 2.2 baostock 失败 8 只代码

这不是阶段 0 阻断。

处理策略：

- 保留在 `prefetch_report.failed_codes`。
- 不混入命中列表。
- 阶段 1 的 `LandmineProducer` / 数据覆盖层要把这类代码标成“数据不可用 / 应剔除或单列失败”。
- 后续 Fetch Planner 按 charter 使用失败率阈值，超过 20% 才 abort；当前 16% 可继续。

### 2.3 V6 合约路径策略

当前兄弟目录自动定位可以接受：

```text
F:\v.6\v6-op -> F:\v.6\v6\scripts
```

下一轮可以增加环境变量覆盖，例如：

```text
V6_SCRIPTS_PATH
```

但不要求创建真实 `.env`，也不允许读取或复制 V6/V5 的 `.env`。默认路径仍以兄弟目录为主。

### 2.4 pandas 3.0.2 风险

当前不降级。

处理策略：

- 以当前 `.venv` 实测版本推进阶段 1。
- 在 `requirements.txt` 锁定已验证版本，减少漂移。
- 每接一个 V5 派生 Producer，都要有 smoke test 覆盖 pandas API 兼容性。
- 如果 SMC / Wave 等依赖明确要求 pandas 2.x，再单独评估是否重建 V6OP `.venv`。

### 2.5 额外观察：价格口径

`ohlcv_provider.py` 当前使用后复权口径：

```text
baostock adjustflag="1"
akshare adjust="hfq"
yfinance auto_adjust=True
```

这对形态/信号分析可接受，但后续报告和 UI 不能把 evidence 里的 `close` 当作未复权真实收盘价展示。

下一轮要求：

- Producer evidence 标注 `adjust: hfq` 或中文“后复权”。
- 中文解释中如果展示价格，要写明价格口径。

## 3. 下一步

可以进入 V6OP-002。

建议 V6OP-002 大步幅覆盖阶段 1：

```text
WencaiSource + SMCProducer + KlineProducer + WaveProducer + LandmineProducer + 技能注册表
```

但仍必须保持：

- 不写 UI
- 不修改 V5/V6
- 本地分析 Producer 只读缓存
- 问财只作为轻量 source，密钥读取与真实请求必须受控

