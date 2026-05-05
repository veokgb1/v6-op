# V6OP-024 V6OP-023 验收偏差修正包报告

**日期**: 2026-05-05  
**执行者**: Claude / V6OP 新代码师  
**命令来源**: `docs/claude_v6op/commands/V6OP-024_v6op023_acceptance_fixes.md`  
**复核依据**: `docs/claude_v6op/reports/V6OP-023_codex_architect_review.md`

---

## 一、修改文件清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `scripts/skill_catalog.py` | 新建 | Fix 1：从 V6 JSON 真实装载技能目录 |
| `scripts/v6op_server.py` | 修改 | Fix 1：新增 `/api/skill_catalog` 端点 |
| `web/app.js` | 修改 | Fix 1：移除硬编码 SKILL_CATALOG_GRAY，改为 fetch /api/skill_catalog |
| `scripts/mask_cache.py` | 修改 | Fix 2：新增 `compute_scope_data_time_max()` |
| `scripts/execution_engine.py` | 修改 | Fix 2：无条件从 pkl 计算 data_time_max |
| `scripts/verify_prefetch_300.py` | 改写 | Fix 3：线程超时 + partial JSON + psutil 清理 |
| `scripts/browser_smoke_playwright.py` | 新建 | Fix 4：真实浏览器 smoke（Playwright 不可用时输出 browser_unavailable） |
| `scripts/browser_smoke.py` | 保留 | Fix 4：HTTP smoke（保留，命名已明确为 HTTP smoke） |
| `tests/test_v6op023_skill_catalog.py` | 改写 | Fix 1：测试改为验证 skill_catalog 模块，含 18 灰卡计数 |
| `tests/test_v6op023_verify_prefetch.py` | 改写 | Fix 3+5：新增 timeout 测试，所有 subprocess.run 加 encoding=utf-8 |
| `tests/test_v6op024_mask_cache_data_date.py` | 新建 | Fix 2：14 个集成测试，含 prefetch_triggered=False 路径 |
| `output/verification/v6op024_prefetch_smoke.json` | 产物 | limit=20 smoke |
| `output/verification/v6op024_prefetch_300.json` | 产物 | limit=300 真实验收 |
| `output/verification/v6op024_browser_smoke.json` | 产物 | browser_unavailable 证据 |

---

## 二、5 项修正逐项状态

### Fix 1 — 技能 catalog 从 V6 JSON 真实装载

**状态**: DONE ✓

**实现**：
- `scripts/skill_catalog.py` 新建，从以下两个 V6 JSON 只读装载：
  - `F:\v.6\v6\data\skill_connection_cards.json` — 22 条权威 skill_id 列表
  - `F:\v.6\v6\data\raw_skill_sample_cards.json` — cn_name 补充（部分 ID 匹配）
- `V6_TO_V6OP` 映射表（4 条）：chan-pattern-recognition→czsc、smart-money-concepts→smc、candlestick-pattern-recognition→kline、elliott-wave-engine→wave
- landmine 标注为 `v6_skill_id=None`（v6-op 原生能力，不来自 V6 JSON）
- 返回 `{"live": [...5...], "gray": [...18...], "v6_total": 22, "v6_mapped": 4, "gray_count": 18, "live_count": 5}`

**v6op_server.py**：新增 `/api/skill_catalog` GET 端点，调用 `skill_catalog.get_catalog()`

**app.js**：
- 移除手写 `SKILL_CATALOG_GRAY` 数组（18 条硬编码）
- 改为 `let SKILL_CATALOG_GRAY = [];`（初始空）
- `DOMContentLoaded` 改为 `async`，先 `fetch('/api/skill_catalog')` 再 `buildSkillList()`
- 灰卡禁用逻辑不变：`cb.disabled = true`，`LIVE_SKILL_IDS.has()` 双重防守

**口径统一**：22 - 4 = 18 灰卡，无 17/18 矛盾

**测试**：`test_v6op023_skill_catalog.py` 改写为 52 个测试，含专门的 `TestV6OP023SkillCatalogModule` 验证 skill_catalog.py 输出

---

### Fix 2 — 修正 Mask cache 的 data_date

**状态**: DONE ✓

**问题根源**：旧代码 `if _prefetch_triggered: ... _data_time_max = prefetch_report.data_time_max`，缓存充足不触发 prefetch 时 `_data_time_max=""` → fingerprint 无差异 → 可能错误复用旧 Mask。

**新增**：`mask_cache.compute_scope_data_time_max(codes, cache_dir, days)`
- 读取 `{cache_dir}/{CODE}_{days}d.pkl` 的 DatetimeIndex，取 scope 内最大日期
- 返回 `'YYYY-MM-DD'` 字符串，无 pkl 时返回 `""`
- 不依赖 prefetch 是否触发

**execution_engine.py 修改**：
```python
# 无条件从 pkl 计算（不依赖 _prefetch_triggered）
_data_time_max = _mask_cache.compute_scope_data_time_max(
    codes=scope_codes, cache_dir=cache_dir
)
# 备选：prefetch_triggered 时从 prefetch_report 补充
if not _data_time_max and _prefetch_triggered:
    pr = fetch.get("prefetch_report") or {}
    _data_time_max = str(pr.get("data_time_max", ""))[:10]
```

**测试**：`test_v6op024_mask_cache_data_date.py`，14 个测试，全部通过：
- pkl 文件读取正确日期
- 不同 data_date 产生不同指纹
- 相同 data_date 产生相同指纹（cache hit）
- 修改 pkl 日期后必须 cache miss
- prefetch_triggered=False 路径有效

---

### Fix 3 — verify_prefetch_300 增加超时/partial JSON/worker 清理

**状态**: DONE ✓

**新机制**：
- `run_verification()` 将 `data_prefetch.run_prefetch()` 放入 daemon 线程
- 主线程 `_done.wait(timeout=timeout_seconds)` 等待完成
- 超时时调用 `_kill_prefetch_workers()`（via psutil，已安装 7.2.2）终止所有子进程
- 超时 JSON：`{"status": "timeout", "partial": true, "workers_cleaned": true, "workers_killed": N, ...}`
- exit code：timeout=1（不再是无 JSON 被外部杀死）

**--dry-run JSON** 也新增 `timeout_seconds` 字段。

**测试**：`test_v6op023_verify_prefetch.py` 改写为 17 个测试，含 4 个专门测试 timeout 路径。

---

### Fix 4 — 补真实浏览器 smoke，HTTP smoke 只作 fallback

**状态**: DONE（Playwright 未安装，按要求输出 browser_unavailable）

**browser_smoke_playwright.py** 新建：
- 尝试 `from playwright.sync_api import sync_playwright`
- 若可用：驱动 Chromium headless，验证 DOM 渲染、灰卡 disabled、localStorage 回显、日志区、结果区
- 若不可用：返回 `{"status": "browser_unavailable", "reason": "playwright 未安装…"}`，exit code 2

**当前环境**：Playwright 未安装，输出：
```json
{
  "status": "browser_unavailable",
  "reason": "playwright 未安装（pip install playwright && playwright install chromium）",
  "note": "报告不得写'真实浏览器已通过'——Playwright 未安装"
}
```

**结论**：真实浏览器 smoke 环境不满足，exit code 2（环境限制，非测试失败）。  
**HTTP smoke**（`browser_smoke.py`）保留，已在文档中明确标注为"HTTP 层等价验收"，不冒充浏览器级。

---

### Fix 5 — 清理 Windows GBK 子进程解码 warning

**状态**: DONE ✓

**修复**：`test_v6op023_verify_prefetch.py` 所有 `subprocess.run(...)` 调用均补充 `encoding="utf-8"`。

**验证**：`pytest -q` 输出中不再出现 `PytestUnhandledThreadExceptionWarning`，仅剩 czsc_producer 的 `DeprecationWarning`（与本次修正无关）。

---

## 三、V6 JSON 22 条与前端 catalog 精确映射表

| V6 skill_id | 映射到 v6-op | 状态 | 说明 |
|---|---|---|---|
| chan-pattern-recognition | czsc | **已接通（V6 映射）** | 缠论买点选股 |
| smart-money-concepts | smc | **已接通（V6 映射）** | SMC 聪明钱 |
| candlestick-pattern-recognition | kline | **已接通（V6 映射）** | K 线形态 |
| elliott-wave-engine | wave | **已接通（V6 映射）** | 波浪分析 |
| *(不来自 V6 JSON)* | landmine | **已接通（v6-op 原生）** | 排雷过滤 |
| hithink-finance-query | — | 灰卡 | 暂未接通 |
| hithink-market-query | — | 灰卡 | 暂未接通 |
| hithink-basicinfo-query | — | 灰卡 | 暂未接通 |
| hithink-event-query | — | 灰卡 | 暂未接通 |
| hithink-astock-selector | — | 灰卡 | 暂未接通 |
| hithink-sector-selector | — | 灰卡 | 暂未接通 |
| hithink-zhishu-query | — | 灰卡 | 暂未接通 |
| announcement-search | — | 灰卡 | 暂未接通 |
| news-search | — | 灰卡 | 暂未接通 |
| research-report-search | — | 灰卡 | 暂未接通 |
| equity-research | — | 灰卡 | 暂未接通 |
| minute-data-analysis | — | 灰卡 | 暂未接通 |
| sector-rotation-monitor | — | 灰卡 | 暂未接通 |
| market-sentiment-analysis | — | 灰卡 | 暂未接通 |
| market-sentiment-deviation | — | 灰卡 | 暂未接通 |
| geopolitical-risk-analysis | — | 灰卡 | 暂未接通 |
| social-media-intelligence | — | 灰卡 | 暂未接通 |
| anonymous-project-teaser | — | 灰卡 | 暂未接通 |

**汇总**：V6 JSON 22 条，映射接通 4 条，灰卡 18 条，v6-op 原生 1 条（landmine），总计 live=5。

---

## 四、Mask cache prefetch_triggered=False 下 data_date 生效的测试证据

测试文件：`tests/test_v6op024_mask_cache_data_date.py`，14 个测试全部通过。

关键证据（`TestExecutionEngineDataDate`）：
- `test_compute_scope_data_time_max_used_in_engine`：确认 `execution_engine.py` 中存在 `compute_scope_data_time_max` 调用
- `test_data_time_max_not_conditional_on_prefetch_only`：确认调用不依赖 `_prefetch_triggered` 条件
- `test_execution_uses_real_pkl_date`：构造 pkl（2026-04-28），验证读取 `2026-04-28`；更新 pkl（2026-04-30），验证读取 `2026-04-30`；不同日期产生不同指纹

---

## 五、300 只验收结果

**结论：PASS**

```json
{
  "status": "pass",
  "limit": 300,
  "actual_code_count": 300,
  "workers": 8,
  "cache_hit": 44,
  "fetched_ok": 256,
  "recovered_count": 124,
  "failed": 0,
  "failure_rate": 0.0,
  "data_time_max": "2026-04-30",
  "elapsed_seconds": 82.08,
  "timeout_seconds": 240,
  "verified_at": "2026-05-05T21:15:17.427517"
}
```

命令：`python scripts/verify_prefetch_300.py --limit 300 --workers 8 --timeout 240 --json-out output/verification/v6op024_prefetch_300.json`

300 只全部完成，0 失败，耗时 82.08s（< 240s timeout），data_time_max=2026-04-30。

limit=20 smoke 也通过（`v6op024_prefetch_smoke.json`，1.68s，cache_hit=20/20）。

---

## 六、浏览器 smoke 结果

**结论：browser_unavailable（环境限制）**

```json
{
  "status": "browser_unavailable",
  "reason": "playwright 未安装（pip install playwright && playwright install chromium）",
  "base_url": "http://127.0.0.1:7749",
  "note": "报告不得写'真实浏览器已通过'——Playwright 未安装"
}
```

命令：`python scripts/browser_smoke_playwright.py --json-out output/verification/v6op024_browser_smoke.json`  
Exit code：2（环境限制，非测试失败）

真实浏览器 smoke 框架已实现（`scripts/browser_smoke_playwright.py`），安装 Playwright 后可立即运行：
```bash
pip install playwright
playwright install chromium
python scripts/browser_smoke_playwright.py --start-server --port 7752 \
  --json-out output/verification/v6op024_browser_smoke_real.json
```

---

## 七、pytest GBK warning 状态

**结论：已清除**

`pytest -q` 输出（2026-05-05）：
```
===================== 429 passed, 3816 warnings in 28.24s =====================
```

3816 条 warning 均为 czsc_producer.py 的 `DeprecationWarning`（`cxt_third_bs_V230318` 已废弃），与 GBK 无关，且为预存问题。

`PytestUnhandledThreadExceptionWarning`（GBK 来源）：**0 条**。

修复位置：`test_v6op023_verify_prefetch.py` 所有 `subprocess.run` 调用补充 `encoding="utf-8"`。

---

## 八、验收命令汇总

```
pytest -q
  → 429 passed, 0 failed, 无 GBK warning ✓

node --check web/app.js
  → exit:0 ✓

python scripts/verify_prefetch_300.py --limit 20 --workers 2 \
  --json-out output/verification/v6op024_prefetch_smoke.json
  → status=pass, cache_hit=20/20, elapsed=1.68s ✓

python scripts/verify_prefetch_300.py --limit 300 --workers 8 --timeout 240 \
  --json-out output/verification/v6op024_prefetch_300.json
  → status=pass, failed=0, elapsed=82.08s ✓

python scripts/browser_smoke_playwright.py \
  --json-out output/verification/v6op024_browser_smoke.json
  → status=browser_unavailable, exit=2 ✓（环境限制，非失败）
```

---

```text
Claude / V6OP 新代码师
V6OP-024 V6OP-023 验收偏差修正包
```
