# V6OP-009 状态口径修正与数据一致性报告

> 执行日期：2026-05-05
> 执行者：Claude (claude-sonnet-4-6)

---

## 概述

V6OP-009 完成三件事：

1. **修正 current_status 和 latest_report**：纠正 V6OP-008 中过度声明的"阶段 4 全部闭合"，写清真实验收口径
2. **修复数据覆盖口径矛盾**：消除 `failed_codes` 与 `cached_codes` 同时包含同一股票的不变式违反，Producer 不再分析已知失败的股票
3. **给出下一步最短补齐路径**：wencai 完整端到端 + SMC 缺口修复

---

## 一、状态口径修正

### 修正前（V6OP-008 错误表述）

| 项目 | 错误表述 |
|---|---|
| wencai | "完整链路验收通过" |
| SMC | 未提及是缺口 |
| 阶段 4 | "完成闭合" |

### 修正后（真实状态）

| 项目 | 真实状态 |
|---|---|
| manual 多技能三路径 | **硬验收通过**（kline+czsc+wave+landmine，20只真实 A 股，三路径） |
| wencai 链路 | **链路触发验证通过，预热成功路径未闭合**（baostock 在当前环境不可达，预热失败是环境问题而非链路代码问题；但"wencai 完整端到端"的定义要求预热成功路径也通过）|
| SMC | **未验收通过，是核心缺口**（Windows/GBK 编码缺陷 + ohlcv 数据格式缺陷，两个独立问题未修复）|
| 阶段 4 整体 | **已启动并完成部分验收**，不是"全部闭合"|

---

## 二、数据覆盖口径矛盾修复

### 问题描述

在 V6OP-008 的 wencai 链路运行中，执行日志显示：

```
步骤 2/8: 规划数据预热
  readiness=partial  cached=0  missing=5  failed=0
步骤 3/8: 准备数据 — 检查缓存
  缓存缺失 5 只，启动真实预热…
  Worker-0~4 退出码 1（所有 worker 失败）
  重规划后 readiness=aborted  cached=5  missing=0   ← 矛盾！
步骤 5/8: 运行 Producer
  kline: hit=2  miss=3（kline 分析了这 5 只）
  landmine: [排雷] 300599.SZ 原因: prefetch_report 已知无数据
           [排雷] 301002.SZ ... （全部 5 只被排雷）
```

**矛盾**：`prefetch_report` 记录所有 5 只为 `failed_codes`，但 `fetch_planner` 第二次规划时发现它们有旧的 `.pkl` 文件，报告 `cached=5`。同时 kline 正常分析了这 5 只（命中 2 只），而 landmine 因读取 `prefetch_report` 正确排除了全部 5 只。最终命中 0，但 kline 输出 2 只命中的信息泄漏到日志。

**根因一（fetch_planner.py）**：
```python
# 旧代码：只要 .pkl 存在就进 cached_codes
if cache_file.exists():
    cached_codes.append(code)
elif code not in known_unavailable:
    missing_codes.append(code)
```
`known_unavailable = failed_codes | stale_codes`，但 `cached_codes` 没有排除 `failed_codes`。若某股票有旧 `.pkl` 且被 prefetch 标为 failed，它会同时出现在 `cached_codes` 和 `failed_codes`。

**根因二（execution_engine.py）**：
Producer 输入使用 `scope_codes`（所有股票），而非 `available_codes`（排除 failed 后的可用股票）。kline 拿到包含 failed 股票的输入，读取旧缓存后正常返回命中结果。

### 修复内容

**`scripts/fetch_planner.py`**：

```python
# 修复：failed 股票不计入 cached，不变式：cached ∩ failed = ∅
failed_codes_set = set(failed_codes)

if needs_kline and cache_dir.exists():
    for code in scope_codes:
        cache_file = cache_dir / _cache_fname(code, lookback_days)
        if cache_file.exists() and code not in failed_codes_set:   # ← 新增过滤
            cached_codes.append(code)
        elif code not in known_unavailable:
            missing_codes.append(code)
```

**`scripts/execution_engine.py`**：

```python
# 修复：排除 failed_codes 后才给 Producer
_failed_set = set(fetch.get("failed_codes", []))
producer_scope = [c for c in scope_codes if c not in _failed_set]
if len(producer_scope) < len(scope_codes):
    _log("INFO", f"  排除已知失败代码 {len(scope_codes) - len(producer_scope)} 只，"
                 f"Producer 实际输入 {len(producer_scope)} 只")
```

所有路径（parallel_and / sequential / simple_hybrid）的 Producer 初始输入改用 `producer_scope`，负向技能（landmine 等）也改用 `producer_scope`（因为 failed 股票已在排雷中被排除，再排一遍无效且迷惑）。

**修复后 wencai 失败场景的正确行为**：
- `cached=0, missing=0, failed=5`（无重叠）
- `producer_scope = []`（没有可分析的股票）
- Producer 输入为空 → 0 命中 → run_report 如实显示 5 只 failed
- 逻辑一致，无矛盾

### 新增测试（4 项）

**`TestV6OP009DataConsistency`**（`tests/test_phase2_execution.py`）：

| 测试 | 验证内容 |
|---|---|
| `test_fetch_planner_no_overlap_failed_and_cached` | failed∩cached=∅，不变式 |
| `test_fetch_planner_failed_code_not_in_cached` | .pkl 存在但 prefetch failed → 只在 failed_codes |
| `test_fetch_planner_cached_excludes_failed_preserves_fresh` | 未失败的 .pkl 正常进 cached_codes |
| `test_execution_engine_failed_codes_excluded_from_producers` | failed 股票不传给 Producer |

### 存量测试隔离修复

`TestV6OP006Corrections` 中两个 mock 测试（`test_sequential_second_skill_receives_first_output`、`test_simple_hybrid_execution_semantics`）使用代码 `000001.SZ~000006.SZ`，但当前 `output/current/prefetch_report.json` 包含 `000003.SZ`、`000005.SZ` 为 failed（来自之前 demo run 的遗留）。新的 `producer_scope` 过滤导致这两个 mock 测试收到 4 只输入而非 6 只。

修复：为这两个测试增加 `mock.patch.object(fetch_planner, "plan", return_value=clean_plan)` 隔离，`clean_plan` 中 `failed_codes=[]`。这是正确做法——测试 execution semantics 不应依赖系统的真实 prefetch 状态。

---

## 三、下一步最短补齐路径

### 补齐路径一：wencai 预热成功路径

**条件**：baostock 在当前 Windows 开发环境不可达。需在 baostock 可访问时执行。

**步骤**：
1. 启动 `v6op_server.py`
2. POST `/api/run`：`source.type=wencai`，`query="净利润增速大于20%"`，`limit=5`，`skills=["kline","landmine"]`
3. 验收标准：wencai 返回 scope_count≥1，prefetch 成功至少 1 只（fetched_ok≥1），kline 分析，run_report.md 包含命中或有理有据的 0 命中

**不需要**：修改任何代码（链路代码已完整），只需网络可达。

---

### 补齐路径二：SMC 缺口修复

SMC 有两个独立缺陷，需分别修复：

**缺陷一：编码缺陷（优先级高）**

`smartmoneyconcepts/__init__.py` 在导入时 print 了 ⭐（U+2B50）到 stdout，在 Windows GBK 终端报 `UnicodeEncodeError`。

修复方案（`scripts/producers/smc_producer.py`）：
```python
import contextlib, io

# 导入时捕获 stdout，防止 emoji 打印到 GBK 终端
with contextlib.redirect_stdout(io.StringIO()):
    import smartmoneyconcepts as _smc
```

**缺陷二：数据格式缺陷（依赖缺陷一修复后才能测试）**

`bad operand type for unary -: 'str'` 出现在 SMC 内部计算。根因是 ohlcv_provider 返回的 DataFrame 中某些列（OHLCV）可能是字符串类型（baostock 常见问题，已知的数据清洗缺口）。

修复方案（`scripts/producers/smc_producer.py`）：
```python
# 在传给 smartmoneyconcepts 前强制转换数值列
for col in ["open", "high", "low", "close", "volume"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
df = df.dropna(subset=["open", "high", "low", "close"])
```

**验收**：`manual`，20 只缓存股票（000001.SZ~000029.SZ），`skills=["kline","smc","landmine"]`，parallel_and，smc `hit_count > 0`，无 UnicodeEncodeError，无 `bad operand type` 错误。

---

## 四、修改文件清单

| 文件 | 变更类型 | 说明 |
|---|---|---|
| `scripts/fetch_planner.py` | 修复 | 不变式：failed_codes 中的股票不计入 cached_codes |
| `scripts/execution_engine.py` | 修复 | 引入 producer_scope，排除 failed_codes 后给 Producer |
| `tests/test_phase2_execution.py` | 新增类+修复 | TestV6OP009DataConsistency（4项）；两个 mock 测试加 fetch_planner 隔离 |
| `docs/claude_v6op/current_status.md` | 修正 | 阶段 4 状态改为"已启动并完成部分验收"；明确 SMC 缺口和 wencai 未闭合 |
| `docs/claude_v6op/latest_report.md` | 修正 | 同上；增加下一步最短补齐路径 |

---

## 五、测试结果

```
238 passed, 3816 warnings in 17.42s
```

（V6OP-009 新增：TestV6OP009DataConsistency 4 项；修复 2 项存量 mock 测试隔离）

---

## 六、安全

- 未修改 V5.10 / V6
- 未读取或泄露密钥
- 未使用 fixture 冒充真实结果
- 所有修改均为 v6-op 目录内的代码修正
