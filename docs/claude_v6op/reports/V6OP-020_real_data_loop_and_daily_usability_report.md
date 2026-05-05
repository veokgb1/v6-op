# V6OP-020 V5.10 真实数据闭环经验对齐报告

> 执行日期：2026-05-05
> 执行者：Claude 新代码师 (claude-sonnet-4-6)
> 指令来源：Codex / V6OP 新架构师
> 等待：Codex / V6OP 新架构师验收签收

---

## 概述

本轮任务调整为：**"V5.10 真实数据闭环经验对齐到 v6-op"**。

先读取 V5.10 已完成实现中的 7 个核心文件，分析已踩过的坑，再将关键机制最小迁移到 v6-op。不盲测真实数据链路，不绕过现有测试，不新增页面，不接入 21 技能。

前置修正：V6OP-019 报告小计"已闭合 11 条"→ **已闭合 12 条**（同步修正 latest_report.md）。

---

## 一、V5.10 参考文件阅读摘要

| 文件 | 关键发现 |
|---|---|
| `prefetch_kline_cache.py` | `_recovery_pass` + `_apply_recovery`：并行后单线程补拉，产出 `failed_codes_raw / recovered_codes / recovered_count / failed_codes`（最终）；`data_time_max` 字段 |
| `pipeline_orchestrator.py` | READ_CACHE_ONLY **仅在** prefetch returncode==0 后设置；`SKIP_PREFETCH` 跳过机制 |
| `step1_wencai_merged.py` | 区分 `WencaiAuthError`（401）/ 一般 Exception / 本地 fallback；`used_fallback` 字段 |
| `step6_final_report.py` | `latest_bar_date / earliest_bar_date / stale_days / source_publish_time`；`_staleness_note()` 警告机制 |
| `test_prefetch_v511.py` | 8 项离线验证：serial/4workers/8workers退化/BJ跳过/空文件/READ_CACHE_ONLY静态/块文件清理/超半数失败退出1 |
| `DATA_SOURCE_ROUTING_AND_FALLBACK_MODEL.md` | intended_source/actual_source/fallback_type 完整 schema |
| `10_ashare_daily_ohlcv_bridge_design.md` | 桥接层应 fail-open，唯一起点 `fetch_ohlcv()`，不引入新数据源 |

---

## 二、Gap 分析与修复决策

### 2.1 Prefetch Recovery Pass（缺失 → 已迁移）

**V5.10 有，v6-op 无**：并行阶段结束后单线程补拉 pass，区分首次失败与最终失败。

**修复**：在 `scripts/data_prefetch.py` 新增 `_recovery_pass()` + `_apply_recovery()`，在 `run_prefetch()` 并行/串行两路后统一调用。

新增字段（prefetch_report.json + run_prefetch() 返回值）：
- `failed_codes_raw`：首次失败列表（进入 recovery 前）
- `recovered_codes`：补拉恢复的代码
- `recovered_count`：恢复数量
- `failed_codes`：最终仍失败列表

不变式：`len(failed_codes_raw) == recovered_count + len(failed_codes)`

**当前环境**：baostock 不可达，recovered_count=0，结构正确，环境可达时自动生效。

### 2.2 `data_time_max` 字段（缺失 → 已迁移）

**V5.10 有，v6-op 无**：`_fetch_loop` 收集每只成功股票的最新 bar 日期，取 max 后写入报告。

**修复**：`_fetch_loop` 增加 `bar_maxes` 列表，成功时 `bar_maxes.append(str(df.index[-1])[:10])`，返回 `data_time_max: max(bar_maxes) if bar_maxes else None`。`prefetch_report.json` 含此字段。

### 2.3 READ_CACHE_ONLY 门控（部分缺失 → 已修复）

**V5.10 模式**：prefetch returncode==0 → 设置 READ_CACHE_ONLY；失败不设置。

**v6-op 现状**：`execution_engine.py` 在步骤 5 始终无条件设置 `READ_CACHE_ONLY=true`。但有隐患：若预热抛出异常（步骤 3 except 块），`fetch` 未重规划，`missing_codes` 中的代码不在 `failed_codes` 中，会被错误地传给 Producer，Producer 读不到缓存文件、静默产出无数据。

**修复**：在 `_prefetch_exception_missing: set[str] = set()` 声明后，在 except 块内赋值 `set(fetch.get("missing_codes", []))`；在步骤 5 `_failed_set` 中 `| _prefetch_exception_missing`，确保预热异常时 missing_codes 不进入 producer_scope。

### 2.4 问财失败归因（粗分 → 已细化）

**V5.10 有**：`WencaiAuthError` 明确区分 401；`used_fallback` 字段。

**v6-op 旧**：`"blocked"`（既表示 pywencai 未安装，也表示 401）/ `"error"`（所有其他错误）。

**修复**：`wencai_source._query_wencai()` 细化为：
| 新状态码 | 含义 |
|---|---|
| `"blocked"` | pywencai 库未安装（ImportError）|
| `"auth_failed"` | API Key 无效（401 Unauthorized）|
| `"empty_result"` | API 正常但返回 0 只股票 |
| `"network_error"` | ConnectionError / TimeoutError |
| `"api_error"` | 其他 API 级别错误 |

同步更新：`source_resolver.py` 白名单、`_make_scope_json` note 字段、3 处测试断言。

### 2.5 报告数据新鲜度（缺失 → 已最小补充）

**V5.10 有**：`run_report.md` 展示 `latest_bar_date / stale_days / source_publish_time`。

**修复**：`run_report.py` 的"五、数据准备阶段"在有预热时额外显示：
- `K线数据最新日期`（来自 `prefetch_report.data_time_max`）
- `数据延迟天数`（stale_days = today - data_time_max）
- 若 stale_days ≥ 1 则附带警告行（对齐 V5.10 `_staleness_note`）

---

## 三、修改文件清单

| 文件 | 变更类型 | 说明 |
|---|---|---|
| `scripts/data_prefetch.py` | 功能扩展 | `_fetch_loop` 加 `bar_maxes/data_time_max`；新增 `_recovery_pass()` + `_apply_recovery()`；`run_prefetch()` 调用 recovery，report 加新字段，空列表早返回含新字段 |
| `scripts/execution_engine.py` | 门控修复 | 声明 `_prefetch_exception_missing`；except 块内收集 `missing_codes`；`_failed_set` 合并 |
| `scripts/sources/wencai_source.py` | 归因细化 | `_query_wencai` 返回 `auth_failed/empty_result/network_error/api_error`；`_make_scope_json` note 枚举 |
| `scripts/source_resolver.py` | 白名单同步 | `_known_fail` 集合含全部新状态码；error 消息改用 `note` 字段 |
| `scripts/run_report.py` | 报告增强 | `data_time_max / stale_days / stale_note` 计算；预热统计表加 `recovered` / `K线数据最新日期` / `数据延迟天数` 行 |
| `tests/test_phase1_producers.py` | 测试同步 | wencai 状态码断言含新状态 |
| `tests/test_phase2_execution.py` | guard 测试 | 2 处 wencai 状态码断言扩展；新增 `TestV6OP020PrefetchAlignV510`（7 项） |

---

## 四、新增测试（TestV6OP020PrefetchAlignV510，7 项）

| 测试名 | 验证内容 |
|---|---|
| `test_recovery_fields_present_workers_1` | workers=1 时 run_prefetch 返回含 `failed_codes_raw/recovered_codes/recovered_count` |
| `test_recovery_fields_self_consistent` | `len(failed_codes_raw) == recovered_count + len(failed_codes)` |
| `test_sum_self_consistent_workers_1` | `cache_hit + fetched_ok + stale_used + failed + bj_skipped == len(codes)`（workers=1）|
| `test_sum_self_consistent_workers_2` | 同上（workers=2）|
| `test_data_time_max_in_prefetch_report_json` | prefetch_report.json 含 `data_time_max / failed_codes_raw / recovered_count` |
| `test_read_cache_only_gate_static_check` | execution_engine.py 含 `_prefetch_exception_missing` + 门控合并逻辑 |
| `test_wencai_status_codes_expanded` | wencai_source.py 含 4 个新状态码字符串 |

---

## 五、pytest 结果

```
279 passed, 3817 warnings in 7.68s
（基线 272 → +7，全部通过，0 failed，0 skipped）
```

## node --check

```
node --check web/app.js → OK
```

---

## 六、output/current 污染检查

```
run_id: run_20260505_180215_b8e84e（未变）
000003.SZ in execution_result.json: False
000005.SZ in execution_result.json: False
```

**output/current 未被污染。** 所有测试写入 tmp_path（conftest.py autouse fixture 保护）。

---

## 七、未迁移项（有意不做）

| 项 | 原因 |
|---|---|
| `used_fallback` + 本地 fallback 兜底 | v6-op 明确不伪造结果；key_missing/blocked 直接返回空，不用 ashare_codes.txt 兜底 |
| V5.10 Data Freshness per-step audit | V5.10 有 pipeline 多步骤，v6-op 是单次 execute；最小补充顶层 `data_time_max` 已足够 |
| `source_publish_time` | baostock 不提供发布时间戳（V5.10 同样标注 unknown） |
| orchestrator-level READ_CACHE_ONLY 完全门控 | v6-op 是 in-process 执行，无 subprocess returncode；已通过 `_prefetch_exception_missing` 覆盖实际缺口 |
| `SKIP_PREFETCH` 环境变量 | 当前执行路径已有 `prefetch_required` flag 控制 |

---

## 八、安全声明

- 未修改 `F:\v.6\v5.10` 或 `F:\v.6\v6`
- 未读取或泄露 .env / API key
- 未使用 fixture 冒充真实结果
- 未新增页面，未接入 21 技能，未做 DAG

---

## 等待 Codex / V6OP 新架构师验收签收

— Claude 新代码师 (claude-sonnet-4-6)，2026-05-05
