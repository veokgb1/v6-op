# V6OP-015 重新生成干净 current 报告

> 执行日期：2026-05-05
> 执行者：Claude (claude-sonnet-4-6)

---

## 概述

V6OP-014 从旧归档 `run_20260505_165255_f6eaba` 恢复了 output/current，但该归档是 V6OP-012 修复前生成的：

- `fetch_plan.failed_codes` 包含 `000003.SZ` / `000005.SZ`（本次 scope 不含这两只）
- `run_report.md` 显示它们为失败代码
- 第五章写"触发了自动预热"（prefetch_triggered 标志修复前）

本轮用当前已修复代码重新跑一次 SMC strict 验收策略，生成全新干净的 output/current。

---

## 根因分析

旧归档 `run_20260505_165255_f6eaba`（V6OP-011）在以下修复前生成：
- **V6OP-012**：fetch_planner scope 过滤 + prefetch_triggered 标志

因此该归档的 fetch_plan 仍含 scope 外历史代码，报告第五章仍误显示"触发了自动预热"。复制旧归档无法解决语义问题——必须用修复后的代码重新运行。

---

## 策略配置

```python
strategy = {
    "source": {"type": "manual", "codes": CODES_20},
    "skills": ["kline", "smc", "landmine"],
    "path_type": "parallel_and",
    "params": {
        "skills": {
            "smc": {
                "signal_bars": 60,
                "swing_length": 10,
                "mode": "strict",
            }
        }
    },
}
```

`CODES_20`（与 V6OP-011 同批，不含 000003/000005）：
`000001 000002 000004 000006 000007 000008 000009 000010 000011 000012 000014 000016 000017 000019 000020 000021 000026 000027 000028 000029`（均带 .SZ 后缀）

---

## 运行结果

| 项目 | 值 |
|---|---|
| run_id | run_20260505_174441_7c76b8 |
| status | completed |
| final_hit_count | 5 |
| final_hit_codes | 000001, 000006, 000008, 000019, 000020 |
| kline hit | 10/20 |
| smc hit（bars=60）| 7/20 |
| landmine hit（负向）| 0/20（无雷区） |
| elapsed | 1.08s |
| prefetch_triggered | False |
| fetch_plan.failed_codes | [] |
| fetch_plan.stale_codes | [] |

---

## 验收检查（8 项全部通过）

| # | 验收项 | 结果 |
|---|---|---|
| 1 | 新 run_id，不是 run_20260505_165255_f6eaba | PASS |
| 2 | execution_result.json / run_report.md 无 kline_mock/test_run/pytest-of/Temp\pytest | PASS |
| 3 | fetch_plan.failed_codes ⊆ scope_codes | PASS（failed=[]）|
| 4 | fetch_plan.stale_codes ⊆ scope_codes | PASS（stale=[]）|
| 5 | prefetch_triggered=false | PASS |
| 6 | run_report.md 第五章含"未触发本次预热" | PASS |
| 7 | run_report.md 不显示 000003.SZ / 000005.SZ | PASS |
| 8 | SMC strict hit>0，有 ChoCH/BOS 中文证据 | PASS（hit=5）|

---

## 参数格式发现

V6OP-011 时调用参数格式为 `{"skills": {"smc": {...}}}`，即技能参数须嵌套在 `"skills"` 键下。`_sp()` 函数签名：

```python
def _sp(skill_id: str, key: str, default: Any) -> Any:
    skill_scoped = params.get("skills", {}).get(skill_id, {})  # 先找 skills.<id>
    if key in skill_scoped:
        return skill_scoped[key]
    if key in params:
        return params[key]  # 再找 flat params
    return default
```

直接传 `{"smc": {"signal_bars": 60}}` 时 `_sp` 找不到（它找 `params["skills"]["smc"]`，而非 `params["smc"]`），退回默认值 15。这是 V6OP-015 第一次尝试 hit=0 的原因。

---

## 更新 guard tests（TestV6OP014RealCurrentGuard 扩展至 7 项）

| 测试 | 验证内容 |
|---|---|
| `test_run_report_md_has_no_mock_markers` | run_report.md 无 mock 标记 |
| `test_execution_result_json_has_no_mock_markers` | execution_result.json 无 mock 标记 |
| `test_run_id_is_not_test_run` | run_id 不以 test_run 开头 |
| `test_failed_codes_subset_of_scope` | failed_codes ⊆ scope（V6OP-012 不变式）|
| `test_stale_codes_subset_of_scope` | stale_codes ⊆ scope（V6OP-012 不变式）|
| `test_run_report_md_no_out_of_scope_failed_codes` | md 不显示 scope 外失败代码（硬保护 000003/000005）|
| `test_prefetch_triggered_false_means_no_prefetch_claim_in_md` | prefetch_triggered=False 时无"触发了自动预热" |

---

## 测试结果

```
266 passed, 3817 warnings in 4.94s
```

（V6OP-015 guard tests：TestV6OP014RealCurrentGuard 从 4 项扩展为 7 项，净增 3 项）

---

## 修改文件清单

| 文件 | 变更类型 | 说明 |
|---|---|---|
| `output/current/execution_result.json` | 重新生成 | run_20260505_174441_7c76b8（修复代码运行）|
| `output/current/run_report.json` | 重新生成 | 同上 |
| `output/current/run_report.md` | 重新生成 | 同上，prefetch_triggered=False，无 scope 外代码 |
| `tests/test_phase2_execution.py` | 扩展类 | TestV6OP014RealCurrentGuard 7 项（+3：failed/stale/prefetch）|
| `docs/claude_v6op/current_status.md` | 更新 | V6OP-015 + 266 通过 |
| `docs/claude_v6op/latest_report.md` | 更新 | V6OP-015 + 报告链接 |

---

## 不变式

| 不变式 | 验证方式 |
|---|---|
| output/current 是当前修复代码产物 | run_id=run_20260505_174441_7c76b8（非旧归档）|
| fetch_plan.failed_codes ⊆ scope | guard test 持续验证 |
| fetch_plan.stale_codes ⊆ scope | guard test 持续验证 |
| md 不显示 scope 外失败代码 | guard test 持续验证 |
| prefetch_triggered 语义与 md 一致 | guard test 持续验证 |
| 测试不污染 output/current | V6OP-013 _OUTPUT_ROOT + autouse（266/266 通过后仍干净）|

---

## 安全

- 未修改 V5.10 / V6
- 未读取或泄露密钥
- 未使用 fixture 冒充真实结果
- 所有修改均为 v6-op 目录内的代码修正
