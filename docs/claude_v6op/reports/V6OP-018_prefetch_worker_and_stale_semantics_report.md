# V6OP-018 prefetch worker 与 stale/landmine 语义闭合报告

> 执行日期：2026-05-05
> 执行者：Claude 新代码师 (claude-sonnet-4-6)
> 指令来源：Codex / V6OP 新架构师
> 等待：Codex / V6OP 新架构师验收签收

---

## 概述

本轮修复两处独立问题：

1. **`data_prefetch.py`**：workers>1 在 Windows 下子进程退出码为 1，导致所有 worker 代码被计入 `worker_failed`，预热完全失效。
2. **`landmine_producer.py`**：`_load_prefetch_failures()` 把 `stale_codes` 与 `failed_codes` 合并处理，导致有旧缓存的 stale 股票被排雷命中，违背 fetch_planner 语义。

---

## 问题一：data_prefetch workers>1 exit code 1

### 根因

`_worker_main()` 和 `main()` 均执行：

```python
import io as _io
if hasattr(sys.stdout, "buffer"):
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
```

在 Windows 子进程退出时，Python 的 shutdown 序列要关闭所有文件对象。用新 `TextIOWrapper` 替换 `sys.stdout`/`sys.stderr` 会在 shutdown 期间触发双关闭（原 buffer 已由父进程侧关闭），导致：

```
ValueError('I/O operation on closed file.')
lost sys.stderr
```

子进程以 exit code 1 退出，协调者将该 worker 的全部代码计入 `worker_failed`。

### 修复

新增模块级 helper `_configure_streams()`，使用 `reconfigure()` **原地**修改现有 `TextIOWrapper` 的编码，不替换 `sys.stdout`/`sys.stderr` 对象：

```python
def _configure_streams() -> None:
    """Windows UTF-8 编码修正 — 原地 reconfigure，不替换 sys.stdout/sys.stderr 对象。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
```

`_worker_main()` 和 `main()` 开头均改为调用 `_configure_streams()`，移除 `import io as _io` 和原有的对象替换代码。

---

## 问题二：stale_codes 被 landmine 错误排雷

### 根因

`landmine_producer._load_prefetch_failures()` 末尾：

```python
failed: set[str] = _extract(data.get("failed_codes", []))
stale: set[str]  = _extract(data.get("stale_codes", []))
return failed | stale   # ← 错误：stale 被当作 failed
```

fetch_planner 语义定义：
- `failed_codes`：prefetch 完全失败，无可用数据，**不得分析**
- `stale_codes`：有旧 .pkl 缓存，仍可分析，仅做时效提示

合并后，stale 股票被 landmine 的规则 0 命中（原因字符串 "prefetch_report 已知无数据（failed/stale）"），产生伪负向信号，从最终命中列表中被错误剔除。

### 修复

`_load_prefetch_failures()` 只返回 `failed`，stale 不进入排雷集合：

```python
failed: set[str] = _extract(data.get("failed_codes", []))
# stale_codes 仍有旧缓存可分析，不视为不可用
return failed
```

原因字符串同步修正（去除 "/stale"）：

```python
reasons.append(f"prefetch_report 已知无数据（prefetch failed）")
```

---

## 修改文件清单

| 文件 | 变更类型 | 说明 |
|---|---|---|
| `scripts/data_prefetch.py` | 修复 | 新增 `_configure_streams()`；`_worker_main()` 和 `main()` 改用 helper，移除 TextIOWrapper 替换 |
| `scripts/producers/landmine_producer.py` | 修复 | `_load_prefetch_failures()` 去掉 `stale` 并集；原因字符串去掉 "/stale" |
| `tests/test_phase1_producers.py` | 新增测试类 | `TestV6OP018LandmineStale`（2 项：failed 仍命中 / stale 不因 stale 命中）|
| `tests/test_phase2_execution.py` | 修改 + 新增 | `test_reads_stale_codes` → `test_stale_codes_not_in_unavailable`（语义反转）；新增 `TestV6OP018DataPrefetchWorkers`（1 项：workers 不出现 worker_failed）|

---

## 新增/修改测试

### TestV6OP018LandmineStale（test_phase1_producers.py，2 项）

| 测试名 | 验证内容 |
|---|---|
| `test_failed_code_hits_landmine` | `failed_codes` 中的代码进入 `_load_prefetch_failures` 返回集合，并被 landmine 排雷命中 |
| `test_stale_code_not_hit_by_landmine` | `stale_codes` 中的代码不在 `_load_prefetch_failures` 返回集合；有缓存时不因 stale 被排雷命中 |

### test_stale_codes_not_in_unavailable（test_phase2_execution.py，旧测试语义反转）

原 `test_reads_stale_codes` 断言 stale 在返回集合中（验证的是 bug 行为），现改为断言 stale **不在**返回集合（验证修复后的正确行为）。

### TestV6OP018DataPrefetchWorkers（test_phase2_execution.py，1 项）

| 测试名 | 验证内容 |
|---|---|
| `test_workers_2_no_worker_failed` | workers=2，真实缓存代码，临时 report_dir；验证 worker_N_report.json 存在（worker 正常退出）、failed_codes 中无 `error="worker_failed"` |

---

## pytest 结果

```
272 passed, 3816 warnings in 20.15s
（基线 269 → +3，全部通过，0 failed，0 skipped）
```

## node --check

```
node --check web/app.js → OK
```

---

## Isolated 验收结果

### 验收 1：workers=2 不出现 worker_failed

```
代码: ['000001.SZ', '000002.SZ', '000004.SZ', '000006.SZ', '000007.SZ', '000008.SZ']
Worker-0 启动 → 3 只；Worker-1 启动 → 3 只
Worker-0 进度 3/3  命中=3（缓存命中）  失败=0
Worker-1 进度 3/3  命中=3（缓存命中）  失败=0

worker_N_report.json 数量: 2
  worker_0_report.json ✓
  worker_1_report.json ✓
worker_failed 错误数: 0
cache_hit=6  fetched_ok=0  failed=0

PASS：workers 验收通过
```

### 验收 2：000001.SZ 不因 stale 进入 hit_codes

```
构造 prefetch_report: failed_codes=[], stale_codes=["000001.SZ"]
_load_prefetch_failures 返回: set()（空集，stale 不进入）
000001.SZ 在返回集合中: False

landmine.run 结果:
  hit_codes: []
  evidence: {'status': 'clear', 'bars': 242, 'adjust': 'hfq'}
  stale 触发排雷: False

PASS：000001.SZ 未因 stale 进入排雷
```

---

## output/current 污染检查

```
run_id: run_20260505_180215_b8e84e（未变，仍为 V6OP-016 真实产物）
000003.SZ in execution_result.json: False
000005.SZ in execution_result.json: False
prefetch_triggered: False
```

**output/current 未被污染。** 所有测试写入 tmp_path（conftest.py autouse fixture 保护）；isolated 验收使用 tempfile.TemporaryDirectory，不写 output/current。

---

## 安全

- 未修改 `F:\v.6\v5.10` 或 `F:\v.6\v6`
- 未读取或泄露 .env / API key
- 未使用 fixture 冒充真实结果
- isolated 验收使用真实本地缓存（READ_CACHE_ONLY 模式）

---

## 等待 Codex / V6OP 新架构师验收签收

— Claude 新代码师 (claude-sonnet-4-6)，2026-05-05
