# V6OP-025 第一阶段总纲收口 Delta 包 报告

> 指令发出：Codex / V6OP 新架构师
> 执行对象：Claude / V6OP 新代码师
> 工作目录：`F:\v.6\v6-op`
> 报告路径：`F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-025_first_stage_total_closure_delta_report.md`
> 执行日期：2026-05-05

---

## 一、修改文件清单

| 文件 | 变更类型 | 说明 |
|---|---|---|
| `scripts/verify_prefetch_300.py` | 修改 | 修正 total 统计公式，移除 recovered_count 重复计入 |
| `tests/test_v6op023_verify_prefetch.py` | 修改 | 新增 TestVerifyPrefetch300RecoveredFormula 4 项测试 |
| `docs/claude_v6op/current_status.md` | 修改 | 从 V6OP-022 升至 V6OP-025，补正拓扑执行口径，记录完整进度 |
| `docs/claude_v6op/latest_report.md` | 修改 | 从 V6OP-022 升至 V6OP-025，新增 15 条验收矩阵更新版 |
| `docs/claude_v6op/commands/V6OP-024_first_stage_total_closure_mega_pack.md` | 新建 | 补正点1：恢复缺失命令文件 |
| `output/verification/v6op025_v6_asset_alignment.json` | 生成 | V6 资产继承矩阵 JSON |
| `output/verification/v6op025_prefetch_smoke.json` | 生成 | 20 只预热 smoke JSON |
| `output/verification/v6op025_prefetch_300.json` | 生成 | 300 只预热验收 JSON |
| `output/verification/v6op025_browser_smoke.json` | 生成 | 浏览器状态 JSON（browser_unavailable） |

---

## 二、6 个大项逐项状态

V6OP-025 命令文件将本轮任务分为 6 大项（大项 1-4 与 V6OP-024 延续，大项 5-6 为本轮主体）。

### 大项 1：技能 catalog 总纲口径闭合

**状态：DONE ✓（V6OP-024 已完成，本轮确认维持）**

```
v6_total=22  declared_total=27  missing_asset_count=5  mapped=5  gray=17  live=6
```

6 个 live 能力：
- `landmine`（v6-op 原生）
- `wave`（V6: elliott-wave-engine）
- `czsc`（V6: chan-pattern-recognition）
- `smc`（V6: smart-money-concepts）
- `kline`（V6: candlestick-pattern-recognition）
- `wencai`（V6: hithink-astock-selector → source-tier live 能力）

缺失 5 张（v6-missing-asset-01 ~ v6-missing-asset-05）进入 missing_assets 字段，可机器检测。

灰色 17 张（V6 JSON 中未映射的卡片，前端 disabled，不可执行）。

### 大项 2：内容寻址 Mask cache 严格闭合

**状态：DONE ✓（V6OP-024 已完成，本轮确认维持）**

- fingerprint 使用 SHA256（64 位 hex）
- 5 个 live producer 文件均定义 `ALGO_VERSION = "1.0.0"`
- mask_cache.py 动态 importlib 读取 ALGO_VERSION
- prefetch_triggered=False 时 data_date 通过 compute_scope_data_time_max 真实读取 .pkl DatetimeIndex
- 5 维度 miss 测试全覆盖

**V6 mask_store.py 接入判断（第一阶段只读参考）**：

mask_store.py 依赖 V6 内部的数据库连接配置，引入会带来环境依赖；v6-op 当前使用文件系统 fingerprint 缓存（`output/mask_cache/{fingerprint}.json`），已满足内容寻址语义。第一阶段不接入，原因：低价值高风险，避免引入 V6 DB 依赖。后续接入点：第二阶段 mask 存储统一时评估。

### 大项 3：V6 后台资产继承矩阵与最小接入

**状态：DONE ✓（V6OP-024 已完成，本轮验证 JSON 输出）**

`scripts/v6_asset_alignment.py` 输出：

| V6 资产 | 状态 | 证据 |
|---|---|---|
| contracts.py | adapted | ContractBase / ContractType 导入，已用于 expression_runner 接口定义 |
| expression_runner.py | adapted | ExpressionRunner 已在 expression_engine.py 中使用 |
| mask_store.py | read_only_reference | 第一阶段不接 V6 DB 依赖；文件缓存等价 |
| io_utils.py | read_only_reference | 标准 json+Path 等价；不引入额外依赖 |
| universe_provider.py | read_only_reference | scope 以 code list 处理；Universe 推迟 |
| secret_masking.py | adapted | wencai_source 用 env 变量读取 API Key，不落盘日志；等价脱敏 |
| live_recapture.py | read_only_reference | wencai_source 已可用；live_recapture 推迟 |
| selection_condition.py | read_only_reference | 第一阶段无条件编辑器需求 |
| mask_expression_executor.py | read_only_reference | ExpressionRunner 已满足；底层 executor 不重复接入 |
| report_group_summary.py | read_only_reference | 第一阶段单次运行报告；分组摘要推迟 |

**汇总：adapted=3，read_only_reference=7，V6 scripts 目录可访问，逐项给出证据。**

### 大项 4：执行图 / 拓扑排序 / Fetch Planner / aborted 语义收敛

**状态：DONE ✓（V6OP-024 已完成，本轮补正拓扑口径措辞）**

#### 4a. Fetch Planner 去硬编码（V6OP-023/024）

`fetch_planner.py` 已移除 `_KLINE_SKILLS` 硬编码，替换为：

```python
def _get_kline_skills() -> frozenset[str]:
    from skill_registry import SKILL_REGISTRY
    return frozenset(s["skill_id"] for s in SKILL_REGISTRY if s.get("data_requirement") == "kline_daily")
```

新增技能只需在 skill_registry 声明 `data_requirement=kline_daily` 即可自动纳入。

#### 4b. readiness=aborted 提前返回（V6OP-023/024）

`readiness=aborted` → 写 aborted execution_result.json → 立即返回，`producer_results=[]`，不继续执行 Producer 冒充完整分析。

#### 4c. execution_plan + topological_order（V6OP-024）

`strategy_graph_builder.build()` 新增两个可检查字段：
- `execution_plan`：按依赖顺序排列的节点列表（含 exec_order / input_scope）
- `topological_order`：节点 ID 的拓扑序列表

**拓扑执行口径（补正点3 — 本轮明确）**：

> `execution_plan` 和 `topological_order` 是**附加的可检查结构**，用于报告和测试验证。
>
> `execution_engine.py` 本轮仍保留三路径业务分支（sequential / parallel_and / simple_hybrid）。**完全统一的图节点执行器属于第二阶段**，第一阶段**不声明"拓扑执行完全闭合"**。

### 大项 5：验收脚本与真实验收

**状态：DONE ✓（所有命令已运行，结果见第八、九节）**

### 大项 6：状态文档与最终签收预备

**状态：DONE ✓**

- `docs/claude_v6op/current_status.md`：从 V6OP-022 升至 V6OP-025，记录完整进度，补正拓扑口径
- `docs/claude_v6op/latest_report.md`：从 V6OP-022 升至 V6OP-025，输出 15 条验收矩阵更新版

---

## 三、6 个 live 能力清单

| live 能力 | V6 来源 | 类型 | 说明 |
|---|---|---|---|
| `czsc` | chan-pattern-recognition | V6 映射 | 缠论选股 |
| `smc` | smart-money-concepts | V6 映射 | 聪明钱 |
| `kline` | candlestick-pattern-recognition | V6 映射 | K 线形态 |
| `wave` | elliott-wave-engine | V6 映射 | 波浪理论 |
| `landmine` | 无（v6-op 原生） | 原生 | 排雷扫描 |
| **`wencai`** | **hithink-astock-selector** | **V6 映射（source-tier）** | **问财选股** |

wencai 为 source-tier live 能力（决定股票池），不在前端 SKILL_META 5 个过滤技能中，在 skill_catalog.py live_count=6 中计入。

---

## 四、22/27/缺失 5 的机器检测结果

```
v6_total=22        ← V6 JSON 实际卡片数（skill_connection_cards.json 22 条）
declared_total=27  ← 总纲声称总数
missing_asset_count=5  ← 缺口 = 27 - 22
live_count=6           ← 已接通
gray_count=17          ← V6 JSON 中未映射，灰色 disabled
```

缺失资产（机器可检测）：
- v6-missing-asset-01
- v6-missing-asset-02
- v6-missing-asset-03
- v6-missing-asset-04
- v6-missing-asset-05

---

## 五、Mask cache SHA256 / ALGO_VERSION / V6 mask_store 结论

| 项目 | 状态 | 证据 |
|---|---|---|
| fingerprint 使用 SHA256 | ✅ 已闭合 | `hashlib.sha256(payload.encode()).hexdigest()`，64 位 hex |
| 5 个 producer 定义 ALGO_VERSION | ✅ 已闭合 | czsc/smc/kline/wave/landmine 均有 `ALGO_VERSION = "1.0.0"` |
| mask_cache.py 动态读取 ALGO_VERSION | ✅ 已闭合 | `_get_algo_version()` 用 importlib 导入，有 cache |
| data_date 不依赖 prefetch_triggered | ✅ 已闭合 | `compute_scope_data_time_max()` 独立读 .pkl DatetimeIndex |
| V6 mask_store.py | read_only_reference | 第一阶段不接 V6 DB 依赖；文件系统缓存等价；后续接入点：第二阶段 |

---

## 六、V6 资产继承矩阵

（详见大项 3，及 `output/verification/v6op025_v6_asset_alignment.json`）

```
V6 资产继承审计  total=10
  adapted            : 3  (contracts.py / expression_runner.py / secret_masking.py)
  read_only_reference: 7  (mask_store / io_utils / universe_provider / live_recapture /
                            selection_condition / mask_expression_executor / report_group_summary)
V6 scripts 目录可访问: True
```

---

## 七、execution plan / topological sort / Fetch Planner / aborted 代码证据

### Fetch Planner（fetch_planner.py）

```python
def _get_kline_skills() -> frozenset[str]:
    from skill_registry import SKILL_REGISTRY
    return frozenset(s["skill_id"] for s in SKILL_REGISTRY if s.get("data_requirement") == "kline_daily")
```

硬编码 `_KLINE_SKILLS` 已移除。

### readiness=aborted（execution_engine.py）

```python
if fetch["readiness"] == "aborted":
    _log("ERROR", "readiness=aborted：失败率超 20%，中止执行，不继续运行 Producer")
    aborted_result = {
        "status": "aborted",
        "producer_results": [],
        "final_hit_codes": [],
        "final_hit_count": 0,
        "prefetch_triggered": False,
        ...
    }
    # writes execution_result.json then returns immediately
    return aborted_result
```

### execution_plan + topological_order（strategy_graph_builder.py）

```python
return {
    ...existing keys...,
    "execution_plan": [
        {"node_id": "czsc", "exec_order": 0, "input_scope": "scope", ...},
        {"node_id": "merge", "exec_order": 1, "input_scope": "parallel_and_result", ...},
    ],
    "topological_order": ["czsc", "smc", "merge", "exclude"],
}
```

**注意**：这是可检查结构，execution_engine.py 本轮仍保留三路径业务逻辑，图节点统一执行器属第二阶段。

### verify_prefetch_300.py 统计公式（补正点2）

**旧（错误）：**
```python
total = cache_hit + fetched_ok + recovered + failed  # 重复计入 recovered
```

**新（正确）：**
```python
# recovered is already folded into fetched_ok by data_prefetch._apply_recovery;
# adding it again would double-count. recovered_count is kept as an informational field only.
total = cache_hit + fetched_ok + failed
```

---

## 八、300 预热 JSON 摘要（统计不重复计数）

### 20 只 Smoke

```
python scripts\verify_prefetch_300.py --limit 20 --workers 2 --json-out output\verification\v6op025_prefetch_smoke.json
```

| 字段 | 值 |
|---|---|
| status | pass |
| actual_code_count | 20 |
| cache_hit | 20 |
| fetched_ok | 0 |
| recovered_count | 0 |
| failed | 0 |
| failure_rate | 0.0 |
| data_time_max | 2026-04-30 |
| elapsed_seconds | 1.94 |

### 300 只预热

```
python scripts\verify_prefetch_300.py --limit 300 --workers 8 --timeout 240 --json-out output\verification\v6op025_prefetch_300.json
```

| 字段 | 值 |
|---|---|
| status | **pass** |
| actual_code_count | 300 |
| cache_hit | 300 |
| fetched_ok | 0 |
| recovered_count | 0 |
| failed | 0 |
| failure_rate | 0.0 |
| data_time_max | 2026-04-30 |
| elapsed_seconds | 4.05 |

**统计口径（补正点2 已修正）**：`total = cache_hit + fetched_ok + failed = 300`，`failure_rate = 0/300 = 0.0`。recovered_count=0，即使非零也不计入 total（只作为信息字段）。

---

## 九、浏览器 JSON 摘要

```
python scripts\browser_smoke_playwright.py --json-out output\verification\v6op025_browser_smoke.json
```

```json
{
  "status": "browser_unavailable",
  "reason": "playwright 未安装（pip install playwright && playwright install chromium）",
  "base_url": "http://127.0.0.1:7749",
  "verified_at": "2026-05-05T21:54:42.893439",
  "note": "报告不得写'真实浏览器已通过'——Playwright 未安装"
}
```

Playwright 不可用，输出 `browser_unavailable`。HTTP smoke ≠ 真实浏览器验收，两者不混淆。真实浏览器验收属第二阶段。

---

## 十、pytest / node 结果

### pytest

```
481 passed, 3817 warnings in 15.74s
```

新增测试：`TestVerifyPrefetch300RecoveredFormula`（4 项，全部通过）。

3817 warnings 均为已知 DeprecationWarning（czsc_producer cxt_third_bs_V230318 + importlib u-type code），非 pytest 失败，不影响验收。GBK 子进程解码 warning 已在前序版本修复，本轮无新增 GBK warning。

### node --check

```
node --check web/app.js  → （无输出，退出 0）
```

web/app.js 语法检查通过。

---

## 十一、current_status / latest_report 更新摘要

| 文件 | 更新前 | 更新后 |
|---|---|---|
| `docs/claude_v6op/current_status.md` | "最后更新：V6OP-022 最终签收" | "最后更新：V6OP-025 补正收口" |
| `docs/claude_v6op/latest_report.md` | "最后更新：V6OP-022 最终签收" | "最后更新：V6OP-025 补正收口" |

新增内容：
- V6OP-023/024/025 完整进度记录
- 拓扑执行口径明确（execution_plan = 可检查结构，图节点统一执行属第二阶段）
- 技能 catalog 当前口径表
- 15 条验收矩阵更新版（含 V6OP-024/025 补全项）
- 属于第二阶段的事项明确列出（不再与第一阶段混淆）

---

## 十二、哪些内容仍属于后续阶段

以下**不属于第一阶段**，不在本轮声明：

| 项目 | 阶段 | 原因 |
|---|---|---|
| 图节点统一执行器（替换三路径分支） | 第二阶段 | 不大改 UI 语义前提下推迟 |
| 全部灰色技能（17 个 V6 映射）真实执行 | 第二阶段 | 逐个接入，须先审计 V6 资产 + V5.10 历史 |
| Playwright 真实浏览器 DOM/localStorage 验收 | 第二阶段 | 当前环境 Playwright 未安装 |
| mask_store.py V6 接入 | 第二阶段 | 第一阶段文件缓存等价，避免 V6 DB 依赖 |
| DAG 编辑器 | 明确不做 | 禁止事项 |

---

## 十三、下一轮判断

V6OP-025 补正 4 个补正点全部闭合：

1. ✅ 命令文件断链修复
2. ✅ recovered_count 统计公式修正（+4 新测试）
3. ✅ 拓扑执行口径明确（不声明"完全闭合"）
4. ✅ 状态文档升至 V6OP-025 级别

**pytest 481/0 通过，node --check 通过，300 只预热 PASS，V6 资产矩阵已生成，技能 catalog live_count=6（含 wencai）。**

若 Codex 复核通过，本批可标记为**第一阶段总纲结构缺口 delta 全部闭合**。下一轮视 Codex 复核结论，可进入：
- 第二阶段技能接入（优先逐个审计 V6 灰色技能卡 + V5.10 历史）
- 或最终签收（若无新发现缺口）

---

签名：

```
Claude / V6OP 新代码师
V6OP-025 第一阶段总纲收口 Delta 包
2026-05-05
```
