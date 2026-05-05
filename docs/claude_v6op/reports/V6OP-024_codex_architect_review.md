# V6OP-024 Codex 架构复核

> 复核时间：2026-05-05  
> 复核者：Codex / V6OP 新架构师  
> 被复核命令：`docs/claude_v6op/commands/V6OP-024_v6op023_acceptance_fixes.md`  
> 被复核报告：`docs/claude_v6op/reports/V6OP-024_v6op023_acceptance_fixes_report.md`

---

## 一、纠正说明

Codex 前一版复核把后续总纲收口要求倒扣到了 V6OP-024 上，这是错误的。

V6OP-024 当时下发给 Claude 的命令就是五项验收偏差修正：

1. 技能 catalog 从 V6 JSON 真实装载；
2. Mask cache 在 `prefetch_triggered=False` 时使用真实 K 线数据日期；
3. `verify_prefetch_300` 支持 timeout、partial JSON、worker 清理，并重跑 20 和 300；
4. HTTP smoke 只能叫 HTTP smoke，补真实浏览器 smoke；不可用输出 `browser_unavailable`；
5. 清理 pytest Windows GBK 子进程 warning。

因此本报告只按这五项对命令、报告、代码和产物逐项核对。总纲后续缺口另列为“命令之外的后续项”，不再混判为 V6OP-024 未执行。

---

## 二、命令-报告-证据逐项对照

| 命令项 | Claude 报告内容 | Codex 复核证据 | 结论 |
|---|---|---|---|
| 1. 技能 catalog 从 V6 JSON 真实装载，不再手写灰卡 | 新建 `scripts/skill_catalog.py`；新增 `/api/skill_catalog`；前端移除硬编码 `SKILL_CATALOG_GRAY`，改为 fetch；报告口径为 V6 22 条、映射 4 条、灰卡 18 条、live 5 条。 | 报告内容与命令一致。`web/app.js` 确实从 `/api/skill_catalog` 装载灰卡，灰卡 checkbox disabled。当前代码已被后续推进到 live=6，但 V6OP-024 报告本身签的是 live=5，这不违反当时五项命令。 | **通过** |
| 2. Mask cache 在 `prefetch_triggered=False` 时也用真实 K 线数据日期 | 新增 `mask_cache.compute_scope_data_time_max()`；`execution_engine.py` 无条件从本地 pkl 计算 `_data_time_max`，只在缺失时回退 prefetch_report。 | `tests/test_v6op024_mask_cache_data_date.py` 报告 14 项通过；Codex 复核代码中仍能看到 `compute_scope_data_time_max()` 被 execution engine 调用。 | **通过** |
| 3. `verify_prefetch_300` 支持 timeout / partial JSON / worker 清理，并重跑 20 和 300 | `verify_prefetch_300.py` 改写为线程 timeout；超时写 `status=timeout, partial=true, workers_cleaned=true`；产出 `v6op024_prefetch_smoke.json` 和 `v6op024_prefetch_300.json`。 | `output/verification/v6op024_prefetch_300.json` 为 `status=pass, actual_code_count=300, failed=0, elapsed_seconds=82.08, data_time_max=2026-04-30`。20 smoke 报告为 pass。 | **通过** |
| 4. HTTP smoke 只能叫 HTTP smoke；补真实浏览器 smoke；不可用输出 `browser_unavailable`，不能冒充通过 | 新建 `scripts/browser_smoke_playwright.py`；Playwright 不可用时输出 `browser_unavailable`；HTTP smoke 保留但不冒充浏览器级。 | `output/verification/v6op024_browser_smoke.json` 为 `status=browser_unavailable`，reason 是 Playwright 未安装；脚本对该状态返回 exit code 2。报告没有写真实浏览器已通过。 | **通过，环境限制未签真实浏览器通过** |
| 5. 清理 pytest Windows GBK 子进程 warning | `tests/test_v6op023_verify_prefetch.py` 所有 `subprocess.run` 增加 `encoding="utf-8"`；报告称 GBK warning 为 0。 | Codex 复跑 `pytest -q`：`429 passed, 3816 warnings`；剩余 warning 为 `czsc_producer.py` 上游弃用警告，不是 GBK warning。 | **通过** |

---

## 三、V6OP-024 可签结论

按当时 V6OP-024 五项命令，Claude 的报告是对齐的。

可签：

- 五项验收偏差修正基本完成；
- 20/300 预热已跑并有 JSON 产物；
- 浏览器 smoke 框架已补，当前环境只能签 `browser_unavailable`，不能签真实浏览器通过；
- pytest GBK warning 已清理。

不能把 V6OP-024 判成“未按命令执行”。前一版复核这样写是 Codex 的错误。

---

## 四、命令之外仍要进入后续的事项

以下内容不是 V6OP-024 五项命令的失败，而是对照总纲后续仍需推进的结构性事项：

1. 第一阶段 catalog 总口径应最终成为 6 个 live：`wencai/czsc/smc/kline/wave/landmine`，并保留 22/27/缺失 5 的机器检测口径。
2. Mask cache 总纲口径应继续收严到 SHA256、producer `ALGO_VERSION`、V6 `mask_store.py` 接入或拒绝说明。
3. `verify_prefetch_300.py` 的统计公式需要修正：`recovered_count` 已计入 `fetched_ok` 后，不应再次加入 total/failure_rate。
4. V6 后台资产继承要形成逐项矩阵。
5. 执行图、拓扑排序、Fetch Planner metadata 推导、`aborted` 不继续跑 producer，这些属于后续总纲收口，不属于 V6OP-024 五项修正命令。

---

## 五、后续命令口径

V6OP-025 可以继续作为总纲 delta 收口命令，但它的性质应写清楚：

```text
V6OP-024 已按五项验收偏差命令完成；
V6OP-025 是总纲结构缺口继续推进，不是纠正 Claude 上轮跑偏。
```

---

## 六、签名

```text
Codex / V6OP 新架构师
V6OP-024 架构复核
结论：V6OP-024 五项命令与 Claude 报告对齐；后续总纲缺口进入 V6OP-025
```
