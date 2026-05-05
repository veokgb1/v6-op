# V6OP-012 运行报告旧 prefetch 污染修复报告

> 执行日期：2026-05-05
> 执行者：Claude (claude-sonnet-4-6)

---

## 概述

V6OP-011 的 SMC strict 验收运行时发现：run_report.md 显示了 000003.SZ / 000005.SZ 为失败代码，但这两只股票根本不在本次 scope（CODES_20 不包含它们）。根因是 `output/current/prefetch_report.json` 的历史记录污染了当前 run 的报告输出。

本轮修复两个独立问题：

1. `fetch_planner` 未将历史 failed/stale 过滤至当前 scope
2. `run_report.md` 用旧 `prefetch_report` 内容（而非本次运行标志）判断"是否触发预热"

---

## 一、问题一：历史 failed/stale 污染当前 fetch_plan

### 根因

`fetch_planner.plan()` 从 `prefetch_report.json` 读取 `failed_codes` 和 `stale_codes` 后，**未过滤到当前 scope_codes 范围内**：

```python
# 旧代码（错误）
failed_codes = _extract_codes(existing_report.get("failed_codes", []))
stale_codes  = _extract_codes(existing_report.get("stale_codes", []))
```

`prefetch_report.json` 是跨 run 共享的文件（写在 `output/current/`）。上次运行 wencai 时失败的股票（如 000003.SZ）会保留在文件里，下次用不同 scope 运行时，这些历史失败代码直接进入新的 `fetch_plan`，再流入 `run_report.md`。

### 修复（`scripts/fetch_planner.py`）

```python
# 只保留属于本次 scope 的历史失败/stale；跨 scope 的旧记录不污染当前 fetch_plan。
_scope_set = set(scope_codes)
failed_codes: list[str] = [
    c for c in _extract_codes(existing_report.get("failed_codes", []))
    if c in _scope_set
]
stale_codes: list[str] = [
    c for c in _extract_codes(existing_report.get("stale_codes", []))
    if c in _scope_set
]
```

**不变式**：`fetch_plan.failed_codes ⊆ scope_codes`；`fetch_plan.stale_codes ⊆ scope_codes`。

---

## 二、问题二：报告用旧 prefetch_report 内容判断"是否预热"

### 根因

`run_report.py` 的 `_build_markdown` 函数通过读取 `prefetch_report` 的 `fetched_ok/failed/stale_used` 字段来判断本次是否触发了预热：

```python
# 旧代码（错误）
prefetch_rpt = report.get("prefetch_report", {})
prefetch_fetched = prefetch_rpt.get("fetched_ok", 0)
prefetch_happened = bool(prefetch_fetched > 0 or ...)
```

如果上次运行（不同 scope）触发了预热并写入了 `prefetch_report.json`（`fetched_ok=5`），则下次运行（全缓存命中，无需预热）时，`prefetch_happened=True`，报告错误写成"**触发了自动预热**"。

### 修复（三文件联动）

**`execution_engine.py`**：引入 `_prefetch_triggered` 标志，在实际调用 `data_prefetch.run_prefetch()` 前设为 `True`（出现异常也算触发，因为已经尝试访问网络）：

```python
_prefetch_triggered = False
if fetch["prefetch_required"]:
    ...
    try:
        _prefetch_triggered = True
        prefetch_stats = _dp.run_prefetch(...)
```

并将 `prefetch_triggered` 写入 `execution_result`。

**`run_report.py` `generate()`**：从 `execution_result` 传入 `prefetch_triggered` 到 `run_report` dict。

**`run_report.py` `_build_markdown()`**：
```python
# 用 prefetch_triggered 标志，而非旧 prefetch_report 内容
prefetch_triggered = report.get("prefetch_triggered", False)
prefetch_rpt = report.get("prefetch_report", {}) if prefetch_triggered else {}
```

Section 5 文案修正：
- 未触发时：`**未触发本次预热**，使用已有缓存，未访问 baostock / akshare / yfinance。`
- 已触发时：`**触发了自动预热**，访问了网络数据源（baostock / akshare / yfinance 之一）。`

---

## 三、新增测试（TestV6OP012ScopedPrefetch，5 项）

| 测试 | 验证内容 |
|---|---|
| `test_failed_codes_scoped_to_current_scope` | 旧 report 有 000003.SZ failed，当前 scope 无该股 → failed_codes 为空 |
| `test_stale_codes_scoped_to_current_scope` | 旧 report 有 000005.SZ stale，当前 scope 无该股 → stale_codes 为空 |
| `test_run_report_no_out_of_scope_failed_in_markdown` | run_report.md 不显示不属于本次 scope 的失败代码 |
| `test_run_report_no_prefetch_writes_cache_message` | prefetch_triggered=False 时写"未触发本次预热"，不写"触发了自动预热" |
| `test_failed_codes_in_scope_still_reported` | scope 内的 failed 正常保留；scope 外的被过滤 |

---

## 四、修改文件清单

| 文件 | 变更类型 | 说明 |
|---|---|---|
| `scripts/fetch_planner.py` | 修复 | 过滤 failed/stale 至 scope_codes 范围 |
| `scripts/execution_engine.py` | 修复 | 引入 `_prefetch_triggered` 标志并写入 execution_result |
| `scripts/run_report.py` | 修复 | 用 `prefetch_triggered` 替代旧 `prefetch_report` 内容判断；Section 5 文案修正 |
| `tests/test_phase2_execution.py` | 新增类 | TestV6OP012ScopedPrefetch（5 项）|

---

## 五、测试结果

```
255 passed, 3816 warnings in 17.13s
```

（V6OP-012 新增：TestV6OP012ScopedPrefetch 5 项）

---

## 六、当前阶段 4 状态

| 子项 | 状态 |
|---|---|
| stale 语义（stale≠failed，不影响 failure_rate） | **已闭合**（V6OP-010）|
| SMC 崩溃修复（emoji + 数据格式） | **已闭合**（V6OP-010）|
| SMC 正向命中硬验收（strict hit=7/20，中文证据完整） | **已闭合**（V6OP-011）|
| SMC 信号日期格式（整数→日期字符串） | **已闭合**（V6OP-011）|
| 旧 prefetch 污染修复（scope 过滤 + prefetch_triggered 标志） | **已闭合**（V6OP-012）|
| **wencai 预热成功完整端到端** | **未闭合**，需网络环境（代码已完整）|
| 阶段 4 整体 | **SMC 已闭合，wencai 预热成功路径待闭合** |

---

## 七、安全

- 未修改 V5.10 / V6
- 未读取或泄露密钥
- 未使用 fixture 冒充真实结果
- 所有修改均为 v6-op 目录内的代码修正
