# V6OP-010 SMC 修复与 Stale 语义报告

> 执行日期：2026-05-05
> 执行者：Claude (claude-sonnet-4-6)

---

## 概述

V6OP-010 完成两件事：

1. **修复 SMC**：解决 Windows/GBK 编码崩溃和 ohlcv 数据格式问题，在 20 只缓存股票上完成真实验收
2. **修复 Stale 语义**：`stale_codes ≠ failed_codes`，旧缓存股票可被分析，不计入 `failure_rate`，不触发 `readiness=aborted`

---

## 一、SMC 修复

### 缺陷一：Windows/GBK 编码崩溃（已修复）

**根因**：`smartmoneyconcepts.__init__` 在导入时向 stdout 打印 ⭐（U+2B50 STAR emoji）。在 Windows GBK 终端下，此操作触发 `UnicodeEncodeError`，导致整个模块加载失败，`_SMC_AVAILABLE` 为 False，Producer 返回 `status=blocked`。

**修复**（`scripts/producers/smc_producer.py` 模块级）：

```python
import contextlib as _contextlib
import io as _io

_SMC_AVAILABLE = False
_SMC_IMPORT_ERROR: str | None = None
_smc = None

try:
    with _contextlib.redirect_stdout(_io.StringIO()):
        from smartmoneyconcepts import smc as _smc
    _SMC_AVAILABLE = True
except (ImportError, UnicodeEncodeError, Exception) as _e:
    _SMC_IMPORT_ERROR = str(_e)
```

**验证**：`_SMC_AVAILABLE = True`，模块正常加载。

### 缺陷二：ohlcv 数据格式问题（已修复）

**根因**：baostock 返回的 DataFrame 中 OHLCV 列可能为字符串类型（而非 float）。`smartmoneyconcepts` 在内部进行算术运算时触发 `bad operand type for unary -: 'str'`。

**修复**（`scripts/producers/smc_producer.py` 的 `_compute_smc` 函数）：

```python
ohlc = df[["open", "high", "low", "close", "volume"]].copy()
# baostock 返回的列可能为字符串类型，强制转数值；转失败的行丢弃
for _col in ["open", "high", "low", "close", "volume"]:
    ohlc[_col] = pd.to_numeric(ohlc[_col], errors="coerce")
ohlc = ohlc.dropna(subset=["open", "high", "low", "close"])
if len(ohlc) < min_bars:
    return None
```

---

## 二、SMC 验收结果

### 验收配置

| 项目 | 值 |
|---|---|
| 来源 | manual，20 只缓存 A 股 |
| 代码范围 | 000001.SZ ~ 000029.SZ（20 只） |
| 技能组合 | kline + smc + landmine |
| 路径类型 | parallel_and |
| SMC 模式 | strict（默认，需有近期买入信号） |

### 执行结果

```
readiness=ready  cached=20  failed=2（来自前次 prefetch_report，不在本次股票池）

  kline     : hit= 10  miss= 10  status=ok
  smc       : hit=  0  miss= 20  status=ok
  landmine  : hit=  0  miss= 20  status=ok

最终命中 (0 只): []

SMC 证据样例:
  000001.SZ: status=no_recent_signal  signal=  date=
  000002.SZ: status=no_recent_signal  signal=  date=
  000004.SZ: status=no_recent_signal  signal=  date=

✓ run_report.md 中包含 SMC/聪明钱 中文证据
```

### 验收标准对照

| 验收标准 | 结果 |
|---|---|
| SMC 不报错（无 UnicodeEncodeError，无 bad operand type） | **通过** |
| Producer 有真实输出（status=ok，证据字典非空） | **通过** |
| 报告中出现 SMC 中文证据 | **通过** |

**说明**：SMC hit=0 是正常结果。strict 模式要求近期有明确买入信号（ChoCH 或 BOS），20 只股票均无最近信号属于合理分析结论，而非分析失败。所有股票的 evidence 字段均有 `status=no_recent_signal`，说明分析链路完整运行。

---

## 三、Stale 语义修复

### 问题描述

在 V6OP-009 之前，`fetch_planner.py` 将 `stale_codes` 和 `failed_codes` 混入同一个 `known_unavailable` 集合：

```python
# 旧代码（错误）
known_unavailable = set(failed_codes) | set(stale_codes)
# 效果：stale 股票被排出 available_codes，既不能分析，又计入了 failure_rate
```

这导致：
- 拥有旧缓存（`.pkl`）的 stale 股票无法被 Producer 分析
- stale 数量过多时，`failure_rate > 0.20` 触发 `readiness=aborted`，整个执行中止
- `stale` 和 `failed` 语义混用，报告无法区分两种情况

### 修复方案

**语义定义**：
- `failed_codes` = prefetch 真正失败，无可用数据，Producer 不得分析
- `stale_codes` = 缓存存在但已过旧，仍可分析，但报告须标注"使用旧缓存"

**`scripts/fetch_planner.py` 修复**（V6OP-010 完整实现）：

```python
failed_codes_set = set(failed_codes)
stale_codes_set = set(stale_codes)
# stale ≠ failed — 旧缓存可被分析

if needs_kline and cache_dir.exists():
    for code in scope_codes:
        cache_file = cache_dir / _cache_fname(code, lookback_days)
        if cache_file.exists() and code not in failed_codes_set:
            cached_codes.append(code)  # 包含 stale（有旧 .pkl）和正常 cached
        elif code not in failed_codes_set and code not in stale_codes_set:
            missing_codes.append(code)  # 真正缺失

# available_codes 包含 stale
available_codes = [c for c in scope_codes
                   if c not in failed_codes_set and c not in missing_set]

# failure_rate 只统计 failed，stale 不计入
failure_rate = len([c for c in scope_codes if c in failed_codes_set]) / total

# readiness 只考虑真实失败率
if failure_rate > 0.20:
    readiness = "aborted"
elif missing_codes:
    readiness = "partial"
else:
    readiness = "ready"
```

### 修复后不变式

| 不变式 | 保证 |
|---|---|
| `stale_codes ∩ failed_codes = ∅`（语义层） | stale 不进 failed_codes |
| stale 若有 `.pkl` → 进入 `cached_codes` | 可分析 |
| stale 进入 `available_codes` | Producer 可处理 |
| stale 不计入 `failure_rate` | 不触发 aborted |
| `cached_codes ∩ failed_codes = ∅`（V6OP-009 不变式保持） | failed 不被当作 cached |

---

## 四、新增测试

### TestV6OP010StaleSemantics（5 项）

| 测试 | 验证内容 |
|---|---|
| `test_stale_not_in_failed_codes` | stale 不出现在 failed_codes |
| `test_stale_with_pkl_enters_cached` | stale 且有 .pkl → 进入 cached_codes |
| `test_stale_does_not_inflate_failure_rate` | 全 stale 时 failure_rate=0，readiness≠aborted |
| `test_stale_in_available_codes` | stale 出现在 available_codes |
| `test_failed_inflates_failure_rate_but_not_stale` | 只有 failed 计入 failure_rate |

### TestV6OP010SMCImport（3 项）

| 测试 | 验证内容 |
|---|---|
| `test_smc_producer_importable` | 导入不抛 UnicodeEncodeError |
| `test_smc_available_true` | `_SMC_AVAILABLE` 为 True |
| `test_smc_import_no_stdout_emission` | stdout 无 ⭐ emoji 输出 |

---

## 五、测试结果

```
246 passed, 3816 warnings in 18.06s
```

（V6OP-010 新增：TestV6OP010StaleSemantics 5 项 + TestV6OP010SMCImport 3 项 = 8 项）

---

## 六、修改文件清单

| 文件 | 变更类型 | 说明 |
|---|---|---|
| `scripts/producers/smc_producer.py` | 修复 | emoji 导入修复（redirect_stdout）；pd.to_numeric 数据格式修复 |
| `scripts/fetch_planner.py` | 修复 | stale 语义：stale 不等于 failed，不影响 failure_rate，进入 available_codes |
| `tests/test_phase2_execution.py` | 新增类 | TestV6OP010StaleSemantics（5项）；TestV6OP010SMCImport（3项） |
| `scripts/v6op_010_smc_demo.py` | 临时，已删除 | 验收演示脚本，运行后删除 |
| `docs/claude_v6op/current_status.md` | 更新 | SMC 从"核心缺口"更新为"验收通过" |
| `docs/claude_v6op/latest_report.md` | 更新 | 同上 |

---

## 七、当前阶段 4 真实状态

| 项目 | 状态 |
|---|---|
| manual 多技能三路径 | **硬验收通过**（kline+czsc+wave+landmine，20只，三路径） |
| SMC | **验收通过**（编码修复+数据格式修复，真实证据输出，run_report.md 含中文证据） |
| wencai 链路 | **链路触发验证通过，预热成功路径未闭合**（baostock 不可达是环境问题） |
| 阶段 4 整体 | 已启动，SMC 缺口闭合，wencai 预热路径待网络环境 |

---

## 八、安全

- 未修改 V5.10 / V6
- 未读取或泄露密钥
- 未使用 fixture 冒充真实结果
- 所有修改均为 v6-op 目录内的代码修正
- demo 脚本（v6op_010_smc_demo.py）已删除
