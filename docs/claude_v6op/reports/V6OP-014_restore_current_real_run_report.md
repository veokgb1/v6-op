# V6OP-014 output/current 恢复与污染防卫报告

> 执行日期：2026-05-05
> 执行者：Claude (claude-sonnet-4-6)

---

## 概述

V6OP-013 实现了测试产物隔离机制（`_OUTPUT_ROOT` + autouse fixture），机制本身正确，但验收结论不成立：`output/current` 在 V6OP-013 机制生效前已被历史 pytest 运行污染，包含 mock 产物。

本轮三件事：
1. 从真实 SMC strict 验收运行归档恢复 `output/current`
2. 新增 `TestV6OP014RealCurrentGuard`（4 项）持续防卫 output/current 纯净性
3. 修正 latest_report / current_status 中 V6OP-013 的验收描述

---

## 根因分析

V6OP-013 之前，pytest 每次调用 `execute()` 都会写入 `output/current`。V6OP-013 的 autouse fixture 需要 `execution_engine` 模块已被导入，但历史测试在 fixture 生效前已经污染了 `output/current`。

污染内容（run_id: `run_20260505_170744_78bbde`）：
- `skills: ["kline"]`（只有 kline，不是真实操盘）
- `producer_results` 包含 `kline_mock`
- `cache_dir` 指向 `Temp\pytest-of-devic`（pytest 临时目录）

真实最后一次操盘运行：`run_20260505_165255_f6eaba`（V6OP-011 SMC strict 验收）
- `final_hit_count: 5`
- `final_hit_codes: ['000001.SZ', '000006.SZ', '000008.SZ', '000019.SZ', '000020.SZ']`
- `skills: kline + smc + landmine`，`signal_bars=60`，严格模式

---

## 修复步骤

### 1. 恢复 output/current

从 `output/runs/run_20260505_165255_f6eaba/` 复制三个文件到 `output/current/`：

```
execution_result.json  →  output/current/execution_result.json
run_report.json        →  output/current/run_report.json
run_report.md          →  output/current/run_report.md
```

恢复后验证：
- `run_id: run_20260505_165255_f6eaba` ✓
- `kline_mock in content: False` ✓
- `test_run in content: False` ✓
- `pytest-of in content: False` ✓
- `Temp\pytest in content: False` ✓

### 2. 新增 TestV6OP014RealCurrentGuard（4 项）

| 测试 | 验证内容 |
|---|---|
| `test_run_report_md_has_no_mock_markers` | run_report.md 不含 kline_mock/test_run/pytest-of/Temp\pytest |
| `test_execution_result_json_has_no_mock_markers` | execution_result.json 不含上述标记 |
| `test_run_id_is_not_test_run` | run_id 不以 test_run 开头 |
| `test_real_run_is_smc_acceptance_run` | run_id == run_20260505_165255_f6eaba |

**关键设计**：这 4 项测试直接读取真实 `output/current/`（只读，不调用 `execute()`），autouse fixture 不影响读取操作，因此每次 pytest 运行后都能持续检验 output/current 未被污染。

### 3. 验证 output/current 在完整 pytest 后仍干净

运行 `pytest tests/ -q` 后再次确认：
- `run_id: run_20260505_165255_f6eaba`（不变）
- `final_hit_count: 5`（不变）

---

## 测试结果

```
263 passed, 3817 warnings in 6.41s
```

（V6OP-014 新增：TestV6OP014RealCurrentGuard 4 项）

---

## 修改文件清单

| 文件 | 变更类型 | 说明 |
|---|---|---|
| `output/current/execution_result.json` | 恢复 | 从 run_20260505_165255_f6eaba 覆盖 |
| `output/current/run_report.json` | 恢复 | 从 run_20260505_165255_f6eaba 覆盖 |
| `output/current/run_report.md` | 恢复 | 从 run_20260505_165255_f6eaba 覆盖 |
| `tests/test_phase2_execution.py` | 新增类 | TestV6OP014RealCurrentGuard（4 项）|
| `docs/claude_v6op/current_status.md` | 更新 | V6OP-014 状态 + 263 通过 |
| `docs/claude_v6op/latest_report.md` | 更新 | V6OP-014 状态 + 报告链接 |

---

## 不变式

| 不变式 | 保证 |
|---|---|
| output/current 是真实操盘结果 | V6OP-013 autouse 阻止 execute() 写入真实路径 |
| output/current 不含 mock 标记 | TestV6OP014RealCurrentGuard 4 项持续验证 |
| 未来 pytest 不污染 output/current | _OUTPUT_ROOT + monkeypatch（V6OP-013，已验证）|

---

## V6OP-013 验收订正

V6OP-013 的隔离机制（`_OUTPUT_ROOT` + autouse fixture）是正确的，方向正确，代码完整。

订正项：
- **旧描述**："output/current 保持真实运行产物不被覆盖"（验收时 output/current 已经是污染状态，此结论不成立）
- **正确描述**："V6OP-013 机制已实现，防止未来污染；V6OP-014 完成 output/current 恢复与防卫测试"

---

## 安全

- 未修改 V5.10 / V6
- 未读取或泄露密钥
- 未使用 fixture 冒充真实结果
- 所有修改均为 v6-op 目录内的代码修正
