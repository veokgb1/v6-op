# V6OP 资产核对报告与阶段 0 计划

> 文档作者角色：v6-op 架构师（Codex）
> 文档状态：active
> 最后更新时间：2026-05-05

## 1. 当前目录

```text
V6OP 目标目录：F:\v.6\v6-op
V6 后台能力库：F:\v.6\v6
V5 只读参考库：F:\v.6\v5.10
```

`F:\v.6\v6-op` 当前只包含：

```text
v6-op_full_rescue_charter.md
```

## 2. V6 可复用资产

路径：

```text
F:\v.6\v6\scripts\v6
```

已确认存在：

- `contracts.py`
- `expression_runner.py`
- `mask_store.py`
- `selection_condition.py`
- `selection_group.py`
- `mask_expression_executor.py`
- `mask_producers.py`
- `io_utils.py`
- `universe_provider.py`
- `secret_masking.py`
- `live_recapture.py`
- `workbench_server.py`
- `v6_main_chain.py`
- `report_group_summary.py`

使用方式：

- 直接引用：`contracts.py`、`expression_runner.py`、`mask_store.py`、`io_utils.py`、`universe_provider.py`、`secret_masking.py`
- 适配包装：`selection_condition.py`、`selection_group.py`、`mask_expression_executor.py`、`live_recapture.py`
- 只读参考：`mask_producers.py`、`workbench_server.py`、`report_group_summary.py`
- 暂不依赖：closure、status_signoff、`v6_main_chain.py`、现有 workbench 多页面

## 3. V5 可复用资产

路径：

```text
F:\v.6\v5.10\scripts
```

已确认存在：

- `shared_data.py`
- `prefetch_kline_cache.py`
- `step_smc_batch.py`
- `step1_wencai_merged.py`
- `step2_czsc_analysis.py`
- `step4_landmine_filter.py`
- `step5_smc_analysis.py`
- `step6_final_report.py`
- `step7_kline_pattern.py`
- `step8_wave_analysis.py`
- `pipeline_orchestrator.py`
- `skill_registry.py`

使用方式：

- 提取核心、重写：`shared_data.py` -> `ohlcv_provider.py`
- 提取调度、重写：`prefetch_kline_cache.py` -> `data_prefetch.py`
- 借鉴模式：`step_smc_batch.py` 的 baostock 单连接 / monkey patch 思想
- 提取算法、包装：`step2_czsc_analysis.py` -> `CZSCProducer`
- 只读参考：`step6_final_report.py`、`skill_registry.py`
- 不继承：`pipeline_orchestrator.py` 的 Slot / 漏斗池主路径

纯数据可复制：

```text
F:\v.6\v5.10\data\ashare_codes.txt
```

禁止复制：

```text
F:\v.6\v5.10\.env
F:\v.6\v5.10\.venv
F:\v.6\v5.10\var
F:\v.6\v5.10\output
```

## 4. 已发现偏差

charter 中写到 27 张技能卡，但当前本机核对结果是：

- `F:\v.6\v6\data\skill_connection_cards.json`：22 张
- `F:\v.6\v6\data\raw_skill_sample_cards.json`：22 张
- `F:\v.6\v5.10\tonghuashun_skill_orgin`：22 个 zip
- `F:\v.6\v6\data\v5_builtin_capability_cards.json`：6 张内建/候选能力卡

因此后续不能盲按 27 张执行。V6OP 第一阶段只接 charter 明确的 6 个核心能力。

## 5. 阶段 0 目标

阶段 0 只做数据引擎，不碰 UI。

目标：

```text
真实 K 线预热 -> 本地 pickle 缓存 -> CZSCProducer 只读缓存 -> 输出 V6 Mask JSON
```

必须交付：

- V6OP 自己的基础目录结构
- V6OP 自己的 Python 环境与依赖记录
- `scripts/ohlcv_provider.py`
- `scripts/data_prefetch.py`
- `scripts/producers/czsc_producer.py`
- `data/ashare_codes.txt`
- `output/current/prefetch_report.json`
- 一个真实 Mask JSON 输出
- Claude 报告与状态文件

## 6. 阶段 0 禁止事项

- 不写 UI
- 不建账本目录
- 不复制 `.env`
- 不复制 `.venv`
- 不修改 V5.10
- 不修改 V6
- 不使用 fixture 冒充真实数据
- 不把 V5 Slot 输入输出接口带进 V6OP

