# V6OP-013 测试产物隔离报告

> 执行日期：2026-05-05
> 执行者：Claude (claude-sonnet-4-6)

---

## 概述

V6OP-012 完成后发现：pytest 过程中调用 `execution_engine.execute()` 的任何测试都会将产物写入真实的 `output/current/` 和 `output/runs/<run_id>/`，覆盖最后一次真实操盘结果。

本轮以最小改动修复此问题：引入 `_OUTPUT_ROOT` 模块变量 + `conftest.py` autouse fixture，让所有测试产物自动重定向到 `tmp_path`，无需逐一修改各测试调用。

---

## 根因分析

`execution_engine.execute()` 内部硬编码输出路径：

```python
# 旧代码（每次测试都写真实路径）
output_dir = _PROJECT_ROOT / "output" / "current"
archive_dir = _PROJECT_ROOT / "output" / "runs" / run_id
```

`execute()` 接受的参数只有 `strategy: dict`，没有输出路径控制参数。测试中调用此函数时无法重定向，导致：
- `output/current/run_report.md`、`output/current/run_report.json`、`output/current/execution_result.json` 被测试产物覆盖
- `output/runs/` 下积累大量 `test_run_*` 归档目录

影响规模：`test_phase2_execution.py` 中约 14 处直接调用了 `execute()` 或 `ee.execute()`。

---

## 修复方案

### 1. `scripts/execution_engine.py` — 引入 `_OUTPUT_ROOT`

在模块级别增加可重定向的输出根目录变量：

```python
# 输出根目录。默认 None 表示使用 _PROJECT_ROOT/output。
# 可由测试通过 monkeypatch 设为 tmp_path，防止写入真实 output/current 和 output/runs。
_OUTPUT_ROOT: Path | None = None
```

将 `execute()` 内部的输出路径计算改为：

```python
_out_root = _OUTPUT_ROOT or (_PROJECT_ROOT / "output")
output_dir = _out_root / "current"
archive_dir = _out_root / "runs" / run_id
```

### 2. `tests/conftest.py` — autouse fixture

在已有的 `conftest.py` 中增加 autouse fixture：

```python
@pytest.fixture(autouse=True)
def _isolate_execution_engine_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """把 execution_engine 写输出根目录重定向到 tmp_path。

    防止任何测试（无论是真实 execute() 还是 mock execute()）
    覆盖 output/current/run_report.md 和 output/runs/<run_id>/ 等真实运行产物。
    测试结束后 monkeypatch 自动恢复，不影响下一个测试或真实运行。
    """
    import execution_engine
    monkeypatch.setattr(execution_engine, "_OUTPUT_ROOT", tmp_path)
```

**机制**：
- `autouse=True`：对所有测试函数自动生效，无需每个测试单独声明
- `monkeypatch`：测试结束后自动恢复 `_OUTPUT_ROOT = None`，生产路径不受影响
- `tmp_path`：pytest 内置，每个测试函数获得独立的临时目录，测试间不干扰

### 3. `test_run_archive_created` — 修复路径引用

该测试原来硬编码检查 `_PROJECT_ROOT / "output" / "runs" / run_id`，现在改为读取重定向后的 `execution_engine._OUTPUT_ROOT`：

```python
out_root = execution_engine._OUTPUT_ROOT or (_PROJECT_ROOT / "output")
archive_dir = out_root / "runs" / run_id
```

---

## 新增测试（TestV6OP013OutputIsolation，4 项）

| 测试 | 验证内容 |
|---|---|
| `test_execute_does_not_write_to_real_output_current` | 调用 `execute()` 后，真实 `output/current/run_report.md` 内容不变 |
| `test_execute_output_goes_to_tmp_path` | `execute()` 产物写入 `tmp_path/current/run_report.md` |
| `test_execute_archive_does_not_appear_in_real_runs` | 真实 `output/runs/` 不新增归档目录 |
| `test_mock_execute_does_not_pollute_real_output` | mock Producer 的 `execute()` 同样不写真实路径 |

---

## 测试结果

```
259 passed, 3816 warnings in 18.43s
```

（V6OP-013 新增：TestV6OP013OutputIsolation 4 项；修复存量测试 `test_run_archive_created` 1 项）

---

## 验证：真实 output/current 完好

pytest 全套运行完成后，`output/current/run_report.md` 的最后修改时间仍为 V6OP-011 验收运行时（2026-05-05 17:07:44），未被任何测试改写。

---

## 修改文件清单

| 文件 | 变更类型 | 说明 |
|---|---|---|
| `scripts/execution_engine.py` | 修复 | 引入 `_OUTPUT_ROOT: Path | None = None`；输出路径改用 `_out_root = _OUTPUT_ROOT or ...` |
| `tests/conftest.py` | 新增 fixture | `_isolate_execution_engine_output` autouse，重定向所有测试的 execute() 输出 |
| `tests/test_phase2_execution.py` | 新增类 + 修复 | TestV6OP013OutputIsolation（4 项）；修复 `test_run_archive_created` 路径引用 |

---

## 不变式

| 不变式 | 保证 |
|---|---|
| 测试中 `execute()` 输出 ⊆ `tmp_path` | autouse fixture monkeypatch `_OUTPUT_ROOT` |
| 生产运行 `execute()` 输出 = `output/current` + `output/runs` | `_OUTPUT_ROOT=None` 时回落 `_PROJECT_ROOT/output` |
| 测试间不相互污染 | 每个测试函数获得独立 `tmp_path` |
| 现有测试无需逐一修改 | autouse 自动应用，0 侵入 |

---

## 当前测试状态

```
259 passed, 3816 warnings
```

---

## 安全

- 未修改 V5.10 / V6
- 未读取或泄露密钥
- 未使用 fixture 冒充真实结果
- 所有修改均为 v6-op 目录内的代码修正
