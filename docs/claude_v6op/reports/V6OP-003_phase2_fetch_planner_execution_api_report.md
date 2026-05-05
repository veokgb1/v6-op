# V6OP-003 阶段 2 执行报告

> 命令：V6OP-003_phase2_fetch_planner_execution_api.md
> 执行角色：Claude（claude-sonnet-4-6）
> 执行日期：2026-05-05
> 状态：COMPLETED ✓

---

## 1. 执行摘要

阶段 2 目标全部完成：

```
scope 解析 → 数据需求合并 → 预热规划 → Producer 执行
→ MaskExpression 自动生成 → 最终命中 → 中文解释 → JSON/MD 报告 → API / 轮询流
```

验收命令全部通过：

```
pytest -q                                         → 119 passed (含 65 项阶段 2 测试)
execution_engine.py --demo manual                 → status=completed, hit=2, elapsed=1.82s
v6op_server.py --self-test --port 8878            → 15 通过 / 0 失败
```

---

## 2. 改了哪些文件

### 新增文件（全部在 F:\v.6\v6-op 内）

| 文件 | 说明 |
|---|---|
| `scripts/source_resolver.py` | 三来源统一解析（all_a / manual / wencai） |
| `scripts/fetch_planner.py` | 数据预热规划，读 prefetch_report.json，失败率判断 |
| `scripts/strategy_graph_builder.py` | 三种路径图构建（sequential / parallel_and / simple_hybrid） |
| `scripts/expression_auto_generator.py` | MaskExpression 自动生成，SMC/Wave 模式标注 |
| `scripts/execution_engine.py` | 8步执行引擎，`--demo manual` 支持 |
| `scripts/explanation_builder.py` | 中文解释构建器，命中/失败/stale 分类 |
| `scripts/run_report.py` | JSON + Markdown 报告生成器 |
| `scripts/v6op_server.py` | stdlib HTTP 服务器，4 端点，修复锁重入死锁 |
| `tests/test_phase2_execution.py` | 47 项阶段 2 测试 |
| `tests/test_v6op_server.py` | 18 项服务器测试 |

### 修改文件

| 文件 | 修改内容 |
|---|---|
| `scripts/producers/landmine_producer.py` | 移除 `_KNOWN_UNAVAILABLE` 硬编码集合，改为动态读取 `prefetch_report.json`（V6OP-003 约束） |
| `tests/test_phase1_producers.py` | 更新 TestLandmineProducer 测试，适配动态加载（`_KNOWN_UNAVAILABLE` → `_load_prefetch_failures`） |

---

## 3. 是否读取 .env

- **manual / all_a 来源**：否（不读取 .env，不依赖任何 key）
- **wencai 来源**：是（通过 `WencaiSource`，key 缺失时安全降级）
- 演示命令 `--demo manual` 和 server self-test 均不读取 .env

---

## 4. 是否真实访问问财接口

否。本轮演示使用 `source_type=manual`，不访问任何外部接口。

---

## 5. 是否访问 baostock / akshare / yfinance

否。所有 Producer 继续使用 `READ_CACHE_ONLY=true`，只读本地 pickle 缓存。

---

## 6. 是否修改 V5.10 / V6

**否。**

- `F:\v.6\v5.10\*`：未修改
- `F:\v.6\v6\*`：未修改（通过 `v6_compat.py` 间接引用 `ExpressionRunner` 和 `combine_code_sets`）

---

## 7. API 可用性

| 端点 | 状态 |
|---|---|
| `GET /api/health` | ✅ 可用，返回 Python 版本、关键文件状态、变量名列表（不含值） |
| `POST /api/run` | ✅ 可用，接受策略 JSON，后台线程执行，返回 run_id（202） |
| `GET /api/result` | ✅ 可用，返回最近 `execution_result.json` |
| `GET /api/stream` | ✅ 可用（JSON 轮询，见下） |

**启动命令：**
```
.venv\Scripts\python.exe scripts\v6op_server.py --port 8876
```
本地 URL：`http://127.0.0.1:8876`（端口占用时自动尝试 8877 / 8878）

---

## 8. POST /api/run 是否跑通

是。demo 策略（manual 来源，3只股票，kline + landmine 技能）：

```
POST /api/run → 202 (run_id=run_20260505_132710_4b602b)
  scope: manual  count=3
  readiness=aborted (000063.SZ 在 prefetch_report 失败列表)
  kline: hit=2  miss=1
  landmine: hit=1 (000063.SZ 被排雷)
  expression: AND(1正向) → EXCLUDE(landmine) → 最终命中=2 (000001.SZ, 000002.SZ)
  elapsed=0.49s
```

---

## 9. SSE 是否真实实现

否。`/api/stream` 实现为 **JSON 轮询**（非 true SSE）。

- 每次 `GET /api/stream` 返回最近 50 条执行事件的 JSON 数组
- 包含 `run_id`、`status`、`started_at`、`completed_at`、`final_hit_count`、`events`
- `"note"` 字段明确说明："本实现为 JSON 轮询（非 true SSE）。每次 GET /api/stream 返回最近 50 条事件。建议每 1-2 秒轮询一次。"

原因：stdlib `http.server` 单线程，true SSE 需要长连接阻塞处理器，与单线程服务器不兼容。Flask 可实现 true SSE，但 Flask 未在 requirements.txt 中，避免增加依赖。

---

## 10. 测试命令与结果

### 全量测试

```powershell
cd F:\v.6\v6-op
.venv\Scripts\python.exe -m pytest -q
```

**结果：119 passed in 8.52s**
- 20 项（Phase 0 Smoke）
- 34 项（Phase 1 Producers）
- 47 项（Phase 2 新增：source/fetch/graph/expr/explain/report/engine）
- 18 项（Server 测试）

### execution_engine demo

```powershell
.venv\Scripts\python.exe scripts\execution_engine.py --demo manual
```

**结果：**
```json
{
  "status": "completed",
  "run_id": "run_20260505_132122_470b98",
  "final_hit_count": 2,
  "elapsed_seconds": 1.82,
  "warnings_count": 2
}
```

输出文件：
- `output/current/execution_result.json` ✅
- `output/current/run_report.json` ✅
- `output/current/run_report.md` ✅

### v6op_server self-test

```powershell
.venv\Scripts\python.exe scripts\v6op_server.py --self-test --port 8878
```

**结果：15 通过 / 0 失败**

---

## 11. Codex 约束落实情况

| 约束 | 落实方式 |
|---|---|
| Fetch Planner 不依赖问财成功 | `source_resolver` 三来源独立；manual/all_a 完全不涉及 wencai |
| Landmine 动态读取 prefetch_report | 移除 `_KNOWN_UNAVAILABLE`，改为 `_load_prefetch_failures()` 动态加载 |
| SMC soft_filter 只能作为调试 | `execution_engine` 默认 `smc_mode=strict`；soft_filter 需显式传入 params |
| Wave no_top 标注为弱信号 | `expression_auto_generator` 检测 no_top verdict，标注 `weak_signal_skills` |
| 报告不得被 .gitignore 忽略 | `docs/claude_v6op/reports/*.md` 不在 .gitignore 中（V6OP-002 Codex 已修正） |

---

## 12. 关键技术决策

### SMC 模式默认值

`execution_engine` 中 SMC 默认为 `strict`（正式路径），用户可通过 `params.smc_mode=soft_filter` 显式切换：
```python
smc_mode = params.get("smc_mode", "strict")
```

### 表达式执行链

使用 V6 `combine_code_sets` 函数（通过 `v6_compat.py` 引用），不调用 V6 `ExpressionRunner`（因其 `resolve_ref` 需要预先注册 mask），而是自行管理 mask 注册表。两步表达式：
1. AND/K_OF_N（合并正向）→ 注册结果 mask
2. EXCLUDE（排除负向）→ 最终命中

V6 不可用时自动回退到内置 AND+EXCLUDE 逻辑。

### 锁重入修复

`v6op_server` 的 `_push_event()` 使用 `_state_lock`。初版代码在 `with _state_lock:` 块内调用 `_push_event()`，造成非可重入锁死锁。修复：所有 `_push_event()` 调用必须在 `with _state_lock:` 块外执行。

---

## 13. 需要 v6-op 架构师审阅的点

1. **fetch_planner 失败率逻辑**：当前 `readiness=aborted` 条件是历史失败率（从 `prefetch_report.json` 读取）>20%。对于 demo 的 3 只股票中 1 只失败（33%），会标为 aborted，但仍然继续执行。是否应在 aborted 时直接返回错误，还是保持当前"警告但继续"的行为？

2. **SMC strict 模式命中率**：阶段 1 测试时 strict 模式会大幅减少命中（可能只有真正有 BOS/ChoCH 信号的股票）。建议在阶段 3 前先用 50 只股票跑一次 strict 模式，确认命中率合理。

3. **Wave 弱信号处理**：当前 `expression_auto_generator` 检测 `no_top` verdict 后标注，但不减少 wave 的权重。如果 simple_hybrid 路径中 wave 是 K_OF_N 的一票，弱信号是否应该算半票？

4. **SSE 实现**：当前 `/api/stream` 是 JSON 轮询，不支持 EventSource API。如果阶段 3 前端需要实时推送，建议切换到 Flask + `stream_with_context` 实现 true SSE，或保持轮询并在前端用 `setInterval`。

5. **execution_result.json 过大**：包含完整 `producer_results`（含所有 evidence），对 50 只股票可能超过 1MB。建议讨论是否需要一个精简版（只含 final_hit_codes、explanations、warnings）和完整版两个文件。

---

## 14. 下一步建议

- **阶段 3**：单页操盘台前端（React/Vue + `/api/run` + `/api/stream` 轮询）
- **true SSE**：如前端需要，可换 Flask + `stream_with_context`
- **数据覆盖扩展**：当前 demo 使用 3 只手动代码；可用 `--demo all_a_small`（20只）测试更大规模
- **SMC strict 验证**：在 50 只缓存股票上跑 strict 模式，确认命中率和证据质量
- **Wave 参数调优**：降低 `fib_tolerance` 或增加 `no_top_required` 参数，减少弱信号放行

---

## 15. 文件清单（阶段 2 新增/修改）

```
F:\v.6\v6-op\
├── scripts\
│   ├── source_resolver.py              (NEW) 三来源统一解析
│   ├── fetch_planner.py                (NEW) 数据预热规划，动态读 prefetch_report
│   ├── strategy_graph_builder.py       (NEW) 策略图构建，三种路径
│   ├── expression_auto_generator.py    (NEW) MaskExpression 自动生成
│   ├── execution_engine.py             (NEW) 8步执行引擎
│   ├── explanation_builder.py          (NEW) 中文解释构建
│   ├── run_report.py                   (NEW) JSON+MD 报告
│   ├── v6op_server.py                  (NEW) stdlib HTTP API 服务器
│   └── producers\
│       └── landmine_producer.py        (MODIFIED) 动态 prefetch_report 读取
├── tests\
│   ├── test_phase2_execution.py        (NEW) 47 项阶段 2 测试
│   ├── test_v6op_server.py             (NEW) 18 项服务器测试
│   └── test_phase1_producers.py        (MODIFIED) 适配 landmine 动态加载
└── output\current\
    ├── execution_result.json           (NEW 运行输出)
    ├── run_report.json                 (NEW 运行输出)
    └── run_report.md                   (NEW 运行输出)
```
