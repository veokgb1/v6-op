# V6OP-016 清理 raw JSON 旧 prefetch_report 残留报告

> 执行日期：2026-05-05
> 执行者：Claude (claude-sonnet-4-6)

---

## 概述

V6OP-015 通过了 run_report.md 层面的检查，但 `execution_result.json` 和 `run_report.json` 的 `fetch_plan.prefetch_report` 字段仍原样保留历史 prefetch 数据，包含 scope 外的 `000003.SZ` / `000005.SZ`。

本轮修复：`prefetch_triggered=False` 时将 `fetch_plan.prefetch_report` 置为 `null`，不写入当前运行的输出文件。

---

## 根因分析

`fetch_planner.plan()` 从磁盘读取 `output/current/prefetch_report.json`，将其内容放入返回值的 `prefetch_report` 字段。该字段随后被 `execution_engine` 原样写进 `execution_result`（`"fetch_plan": fetch`），再由 `run_report.generate()` 传播到 `run_report.json`。

V6OP-012 已修复了 `failed_codes`/`stale_codes` 的 scope 过滤，但 `prefetch_report` 原始对象并未被过滤——历史 `prefetch_report.json` 中的 `failed_codes` 列表仍原样写入。

---

## 修复（1 行有效改动）

**`scripts/execution_engine.py`**，在构建 `execution_result` 前：

```python
# prefetch_triggered=False 时历史 prefetch_report 不代表本次运行；
# 清空避免把 scope 外旧失败代码写入当前 execution_result / run_report。
fetch_for_result = {
    **fetch,
    "prefetch_report": fetch.get("prefetch_report") if _prefetch_triggered else None
}
```

`execution_result["fetch_plan"]` 改用 `fetch_for_result`（原 `fetch` 变量仅在步骤 3 重规划内部使用，不受影响）。

---

## 效果

| 字段 | 修复前 | 修复后 |
|---|---|---|
| `execution_result.fetch_plan.prefetch_report` | `{"failed_codes": [{"code":"000003.SZ"},{"code":"000005.SZ"}], ...}` | `null` |
| `run_report.json["prefetch_report"]` | 同上（从 execution_result 传播）| `null` |
| `run_report.md` 第五章 | "未触发本次预热"（V6OP-012 已修复）| 不变 |

---

## 新生成 output/current

重新运行 SMC strict 验收策略后：

| 项目 | 值 |
|---|---|
| run_id | run_20260505_180215_b8e84e |
| final_hit_count | 5 |
| prefetch_triggered | False |
| fetch_plan.prefetch_report | null |
| fetch_plan.failed_codes | [] |
| execution_result.json 全文含 000003.SZ | 否 |
| run_report.json 全文含 000003.SZ | 否 |
| run_report.md 全文含 000003.SZ | 否 |

---

## 更新 guard tests（TestV6OP014RealCurrentGuard 扩展至 10 项）

新增 3 项（V6OP-016）：

| 测试 | 验证内容 |
|---|---|
| `test_execution_result_json_no_out_of_scope_codes` | execution_result.json 全文不含 000003/000005（prefetch_report 清空验证）|
| `test_run_report_json_no_out_of_scope_codes` | run_report.json 全文不含 000003/000005 |
| `test_prefetch_report_null_when_not_triggered` | fetch_plan.prefetch_report=null（prefetch_triggered=False 时）|

---

## 测试结果

```
269 passed, 3817 warnings in 4.96s
```

（V6OP-016 guard tests 新增 3 项；总计 269）

---

## 修改文件清单

| 文件 | 变更类型 | 说明 |
|---|---|---|
| `scripts/execution_engine.py` | 修复 | 引入 `fetch_for_result`；`prefetch_triggered=False` 时 `prefetch_report=None` |
| `tests/test_phase2_execution.py` | 扩展类 | TestV6OP014RealCurrentGuard 新增 3 项（10 项总计）|
| `output/current/*` | 重新生成 | run_20260505_180215_b8e84e，三文件全文无 scope 外代码 |
| `docs/claude_v6op/current_status.md` | 更新 | V6OP-016 + 269 通过 |
| `docs/claude_v6op/latest_report.md` | 更新 | V6OP-016 + 报告链接 |

---

## 不变式

| 不变式 | 保证 |
|---|---|
| `prefetch_triggered=False` 时 `fetch_plan.prefetch_report=null` | execution_engine `fetch_for_result` |
| execution_result.json 全文不含 scope 外代码 | guard test 持续验证 |
| run_report.json 全文不含 scope 外代码 | guard test 持续验证 |
| `prefetch_triggered=True` 时仍保留真实 prefetch_report | `fetch.get("prefetch_report") if _prefetch_triggered else None` |

---

## 安全

- 未修改 V5.10 / V6
- 未读取或泄露密钥
- 未使用 fixture 冒充真实结果
- 所有修改均为 v6-op 目录内的代码修正
