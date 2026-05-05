# V6OP-011 SMC 正向命中硬验收报告

> 执行日期：2026-05-05
> 执行者：Claude (claude-sonnet-4-6)

---

## 概述

V6OP-010 证明了 SMC 不崩溃（编码修复 + 数据格式修复），但没有证明 SMC 能产生正向命中。本轮在此基础上：

1. **发现并修复信号日期格式问题**：`last_signal_date` 原为整数 bar index（如 `189`），修复后为日期字符串（如 `2026-02-06`）
2. **探索参数空间**，找到 strict 模式产生 hit > 0 的参数组合
3. **区分 strict 和 soft_filter 模式**，给出各自的语义和生产口径
4. **完成正向命中硬验收**：strict 模式 hit=7，中文证据完整

---

## 一、信号日期格式修复

### 问题

V6OP-010 运行后，SMC 证据中 `last_signal_date` 显示为整数：

```
000001.SZ: status=hit  signal=ChoCH  date=189  fvg=False
```

`189` 是 DataFrame 的整数 bar index，而不是日历日期。根因：`smartmoneyconcepts` 库在内部计算时重置了 DataFrame 的 index 为 `RangeIndex`，导致 `bos_choch["BOS"].index` 变为 `[0, 1, 2, ...]`，而不保留原始 `DatetimeIndex`。

### 修复（`scripts/producers/smc_producer.py` 的 `_compute_smc` 函数）

```python
# smartmoneyconcepts 可能将结果的 index 重置为 RangeIndex；
# 若长度吻合则恢复 ohlc 的 DatetimeIndex，确保 last_signal_date 是日期字符串而非整数。
if len(bos_val) == len(ohlc) and not isinstance(bos_val.index, pd.DatetimeIndex):
    bos_val.index   = ohlc.index
    choch_val.index = ohlc.index
    fvg_val.index   = ohlc.index
```

修复后：`date=2026-02-06`（正确日历日期）

---

## 二、参数空间探索

在 20 只缓存 A 股（000001.SZ~000029.SZ）上系统测试不同参数组合：

| 参数组合 | mode | signal_bars | swing_length | close_break | hit | miss |
|---|---|---|---|---|---|---|
| 默认参数（V6OP-010） | strict | 15 | 10 | True | 0 | 20 |
| 扩展观察窗 | strict | 30 | 10 | True | **1** | 19 |
| **验收参数** | **strict** | **60** | **10** | **True** | **7** | **13** |
| 宽窗 | strict | 90 | 10 | True | 12 | 8 |
| 超宽窗 | strict | 180 | 10 | True | 17 | 3 |
| 小摆动 | strict | 60 | 5 | True | 11 | 9 |
| 小摆动+收盘突破 | strict | 60 | 5 | False | 13 | 7 |
| 小摆动宽窗 | strict | 90 | 5 | True | 18 | 2 |
| soft_filter | soft_filter | 60 | 10 | True | 20 | 0 |

**关键发现**：默认 `signal_bars=15` 在 20 只股票上 hit=0，是因为观察窗过窄（仅看最近 15 根 K 线）；扩展到 `signal_bars=60` 后，strict 模式得到 7 只命中。

---

## 三、strict 模式验收结果

### 验收参数

| 参数 | 值 |
|---|---|
| mode | **strict** |
| signal_bars | **60** |
| swing_length | 10 |
| close_break | True |
| days | 365 |
| 股票池 | manual，20 只缓存 A 股 |
| 技能组合 | kline + smc + landmine，parallel_and |

### 执行结果

```
readiness=ready  cached=20  failed=2（前次遗留，不在本次股票池）

  kline     : hit= 10  miss= 10  status=ok
  smc       : hit=  7  miss= 13  status=ok
  landmine  : hit=  0  miss= 20  status=ok（无排雷触发）

最终命中 (5 只): ['000001.SZ', '000006.SZ', '000008.SZ', '000019.SZ', '000020.SZ']
（kline∩smc AND 后剩 5 只）
```

### SMC strict 命中证据（7 只中前 5 条）

| 股票 | 信号类型 | 最近信号日期 | FVG 确认 |
|---|---|---|---|
| 000001.SZ | **ChoCH** | 2026-02-06 | 否 |
| 000006.SZ | **ChoCH** | 2026-03-26 | 否 |
| 000007.SZ | **BOS** | 2026-03-18 | 否 |
| 000008.SZ | **ChoCH** | 2026-03-13 | 否 |
| 000019.SZ | **BOS** | 2026-01-30 | 否 |

### run_report.md 中文证据（strict 运行示例）

run_report.md 对每只 SMC 命中股票生成如下中文理由：
```
- SMC聪明钱：ChoCH 信号；最近信号日期 2026-02-06
```

### 验收标准对照

| 验收标准 | 结果 |
|---|---|
| strict 模式 hit_count > 0 | **通过**（7/20）|
| 参数已记录 | **通过**（见验收参数表）|
| run_report.md 出现 SMC 中文证据 | **通过**（ChoCH/BOS + 日期）|
| 至少一只股票有完整中文证据 | **通过**（5 只具有信号日期和类型）|

---

## 四、soft_filter 模式：语义说明与生产口径

### soft_filter 行为

```
soft_filter: hit=20  miss=0（全量透传）
其中 has_signal=True（真实有信号）: 7 只
  000001.SZ: signal=ChoCH  date=2026-02-06
  000006.SZ: signal=ChoCH  date=2026-03-26
  000007.SZ: signal=BOS    date=2026-03-18
  000008.SZ: signal=ChoCH  date=2026-03-13
  000019.SZ: signal=BOS    date=2026-01-30
```

### strict vs soft_filter 语义对比

| 维度 | strict | soft_filter |
|---|---|---|
| 命中条件 | 近 N 根 K 线内有 BOS/ChoCH 买入信号 | 无条件通过，仅记录信号 |
| hit_count | 7（有真实信号） | 20（全部）|
| 生产用途 | 正向过滤筛选 | 调试/观察，了解信号分布 |
| run_report.md 标注 | 无额外标注 | **⚠ soft_filter 软过滤模式** |
| 是否作为生产命中口径 | **是** | **否** |

**结论**：soft_filter 不等于 SMC 验收通过。soft_filter 的 hit=20 只说明"所有股票都被放行"，不代表 SMC 检测出信号。正式生产路径必须用 **strict** 模式。

### 执行引擎对 soft_filter 的自动警告

执行引擎检测到 SMC 使用 soft_filter 模式时，会在日志和 run_report.md 中自动标注：
```
⚠ SMC 使用了 soft_filter 模式（全量透传），结果已标注；正式路径应使用 strict 模式。
```

---

## 五、默认参数调整建议

经过本轮探索，SMC 默认 `signal_bars=15` 对大多数 A 股在365天缓存数据上几乎不产生 strict 命中。这是参数语义问题（观察窗过窄），而非 SMC 算法失效。

**建议**（不在本轮修改，记录供后续参考）：

| 场景 | 建议 signal_bars |
|---|---|
| 严格动量筛选（近期信号）| 15~30 |
| 中期趋势确认 | **60**（本轮验收参数）|
| 历史回测/宽松确认 | 90~180 |

---

## 六、新增测试（TestV6OP011SMCSignal，4 项）

| 测试 | 验证内容 |
|---|---|
| `test_signal_date_is_date_string_not_integer` | last_signal_date 是日期字符串，不是整数 |
| `test_compute_smc_restores_datetime_index` | _compute_smc 返回 series 具有 DatetimeIndex |
| `test_smc_explanation_no_integer_date` | explanation_builder 生成 ChoCH+日期字符串 |
| `test_soft_filter_labeled_in_explanation` | soft_filter 命中在 reason_cn 中标注 |

---

## 七、修改文件清单

| 文件 | 变更类型 | 说明 |
|---|---|---|
| `scripts/producers/smc_producer.py` | 修复 | 恢复 DatetimeIndex：smartmoneyconcepts 重置 RangeIndex 后对齐回 ohlc.index |
| `tests/test_phase2_execution.py` | 新增类 | TestV6OP011SMCSignal（4 项）|
| `scripts/v6op_011_smc_probe.py` | 临时，已删除 | 参数探索脚本 |
| `scripts/v6op_011_smc_accept.py` | 临时，已删除 | 验收脚本 |
| `docs/claude_v6op/current_status.md` | 更新 | SMC 正向命中硬验收闭合 |
| `docs/claude_v6op/latest_report.md` | 更新 | 同上 |

---

## 八、测试结果

```
250 passed, 3816 warnings in 17.18s
```

（V6OP-011 新增：TestV6OP011SMCSignal 4 项）

---

## 九、当前阶段 4 准确状态

| 子项 | 状态 |
|---|---|
| stale 语义（stale≠failed，不影响 failure_rate） | **已闭合**（V6OP-010）|
| SMC 运行崩溃修复（emoji + 数据格式） | **已闭合**（V6OP-010）|
| SMC 信号日期格式修复（整数→日期字符串） | **已闭合**（V6OP-011）|
| SMC 正向命中硬验收（strict hit>0，中文证据完整） | **已闭合**（V6OP-011，strict signal_bars=60：hit=7/20）|
| wencai 预热成功完整端到端 | 待闭合（需网络环境，代码已完整）|

---

## 十、安全

- 未修改 V5.10 / V6
- 未读取或泄露密钥
- 未使用 fixture 冒充真实结果
- 所有修改均为 v6-op 目录内的代码修正
- 两个临时脚本（probe.py、accept.py）已删除
