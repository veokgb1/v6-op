# V6OP-021 指令：真实进度、Prefetch 口径一致、参数重跑验收

> 指令来源：Codex / V6OP 新架构师  
> 执行对象：Claude / V6OP 新代码师  
> 执行目录：`F:\v.6\v6-op`  
> 报告输出：`F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-021_realtime_progress_prefetch_parity_and_rerun_acceptance_report.md`

---

## 一、总目标

本轮不是写报告轮，是开发闭合轮。

目标：继续推进 v6-op 当前主架构：

`source -> fetch_plan -> prefetch -> producer -> expression -> report`

不要复制 V5/V5.10 的 Slot 漏斗，不要新增页面，不要做 DAG，不要接入其余 21 个技能，不要修改 `F:\v.6\v5.10` 或 `F:\v.6\v6`。

你要吸收三类教训：

- V5 的优点是单页、真实数据、能每天跑；缺点是固定漏斗，不是 v6-op 目标。
- V5.10 的优点是真实数据闭环、worker 预热、失败归因、数据新鲜度和恢复 pass；缺点是仍然围绕 Slot/管道/本地 fallback，不能照搬。
- V6 的优点是 Mask/MaskExpression/技能卡资产；缺点是概念页、账本和 fixture 过多，用户无法每天打开就得到真实选股结果。

本轮要把 V5.10 的真实工程坑，压进 v6-op 单页操盘主线里。

---

## 二、开工前必须读取

先读这些文件，不要凭记忆改：

1. `v6-op_full_rescue_charter.md`
2. `docs/claude_v6op/reports/V6OP-020_real_data_loop_and_daily_usability_report.md`
3. `docs/claude_v6op/reports/V6OP-019_charter_acceptance_matrix_report.md`
4. `docs/claude_v6op/current_status.md`
5. `scripts/data_prefetch.py`
6. `scripts/execution_engine.py`
7. `scripts/v6op_server.py`
8. `scripts/run_report.py`
9. `web/app.js`
10. 只读参考：`F:\v.6\v5.10\scripts\prefetch_kline_cache.py`
11. 只读参考：`F:\v.6\v5.10\scripts\pipeline_orchestrator.py`

---

## 三、任务 1：Prefetch 并行口径和 CLI 口径补齐

V6OP-020 已经补了 `run_prefetch()` 路径，但我核代码发现还有两个口径缺口：

1. `data_prefetch._run_coordinator()` 汇总 worker 报告时，没有汇总每个 worker 的 `data_time_max`，所以 workers=8 的主路径可能无法在最终 `prefetch_report.json` 里显示 K 线最新日期。
2. `data_prefetch.py` 命令行入口 `main()` 没有调用 `_apply_recovery(stats, args.days)`，也没有把 `failed_codes_raw / recovered_codes / recovered_count / data_time_max` 写进 CLI 产出的 `prefetch_report.json`。

请修复：

- worker 汇总时收集各 worker 的 `data_time_max`，最终取 max。
- CLI 顺序和并行两路都必须经过 `_apply_recovery()`。
- CLI 写出的 report schema 与 `run_prefetch()` 写出的核心字段一致。
- 不破坏现有 `run_prefetch()` API。
- 不污染 `output/current` 的现有真实 run，测试必须继续使用 tmp_path 或可控 report_dir。

必须新增/调整测试：

- workers=2 或 workers=8 路径能在最终 report 中保留 `data_time_max`。
- CLI/report helper 路径包含 `failed_codes_raw / recovered_codes / recovered_count / data_time_max`。
- recovery 成功时 `failed` 和 `fetched_ok` 计数仍与 V5.10 一致。

---

## 四、任务 2：运行中真实进度，而不是完成后回灌日志

我核到 `scripts/v6op_server.py` 目前是后台 `execution_engine.execute(strategy)` 返回后，才把 `execution_engine.get_log_events()` 灌入 `_run_state["events"]`。这会导致页面轮询时可能只看到 pending/running/完成，而不是运行中逐步看到 source、fetch_plan、prefetch、producer、expression、report。

这不符合总纲“中间：运行进度日志实时滚动”的主目标。

请实现最小改法：

- 让 `execution_engine._log()` 支持可选 log sink/callback，或提供等价机制，使 server 能在执行过程中实时收到日志。
- `v6op_server.py` 在后台执行期间把这些事件即时推入 `/api/stream`。
- 避免重复事件，避免 completed 状态先于详细日志导致前端停止轮询。
- 保持 `/api/stream?since=N` 语义不变。
- 不引入新框架，不强行改成复杂 SSE；JSON 轮询可以继续，但必须是真运行中可见。

必须新增/调整测试：

- server 源码或行为测试能证明详细执行事件不是 execute 完成后才批量灌入。
- `/api/stream?since=N` 继续可用。
- 完成状态不会丢最后一批日志。

---

## 五、任务 3：操盘台展示 Prefetch 真实摘要

当前右侧数据覆盖只显示 cached/missing/failed/stale，V6OP-020 新增的真实预热字段没有在操盘台充分显性化。

请在现有单页里补齐，不新建页面：

- 如果本轮 `prefetch_triggered=true`，前端显示：
  - 命中缓存
  - 新拉成功
  - 补拉恢复
  - 最终失败
  - stale 降级
  - K 线最新日期 `data_time_max`
  - 数据延迟提示（如后端已有）
- 如果 `prefetch_triggered=false`，明确显示“本轮未触发预热，使用已有缓存”，不要读历史 prefetch_report 误导用户。
- 保持用户语言，不暴露 Mask/ScopeRef/ExecutionDraft 术语。

必须新增/调整测试：

- `test_phase3_web_assets.py` 或等价测试覆盖这些展示字段。
- `node --check web/app.js` 通过。

---

## 六、任务 4：参数改后重跑验收闭合

V6OP-019 条 11 仍是“部分闭合”：后端已证明参数有效，但缺少同一操盘流程里“改参数 -> 重新运行 -> 结果变化”的验收证据。

请用当前已有缓存和当前架构做一次不依赖网络的验收闭合：

- 使用 manual 来源，固定一组已有缓存股票。
- 选择 SMC strict，至少跑两组参数，例如 `signal_bars=60` 和 `signal_bars=15`。
- 记录两个 run_id、两组 params、两组 hit_codes/final_hit_count。
- 若结果确实不同，条 11 可闭合。
- 若结果碰巧相同，不要硬写闭合；换一组可解释参数或说明原因。

验收产物可以写入 V6OP-021 报告，但不要用 fixture 冒充结果。

---

## 七、任务 5：真实 wencai 端到端验收脚本/命令准备

条 2 的真正缺口是：

`wencai -> scope(ok) -> prefetch 成功至少 1 只 -> READ_CACHE_ONLY producer -> report`

当前环境可能 baostock 不可达，所以本轮不要求你伪造成功。但要把验收命令整理成可重复执行的真实检查：

- 检查 `IWENCAI_API_KEY` 是否存在，但不打印 key。
- 检查问财 source 是否返回 `status=ok`。
- 检查 prefetch 是否至少成功 1 只或明确输出环境阻塞原因。
- 成功时写清 run_id、prefetch_triggered、fetched_ok/cache_hit/recovered_count/final_hit_count。
- 失败时写清是 `auth_failed / network_error / api_error / baostock 不可达 / 0 结果` 哪一类。
- 不使用本地 fallback 冒充问财成功。

这一步可以是脚本、测试 helper 或报告中的可执行命令，但必须方便下一轮在网络可达环境直接跑。

---

## 八、验收命令

至少运行：

```powershell
cd F:\v.6\v6-op
.\.venv\Scripts\python.exe -m pytest -q
node --check .\web\app.js
```

如修改了 server 流，请额外跑相关 server 测试。

如做了参数重跑验收，请报告两个 run_id 和差异。

---

## 九、报告要求

报告必须写到：

`F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-021_realtime_progress_prefetch_parity_and_rerun_acceptance_report.md`

同时更新：

- `docs/claude_v6op/current_status.md`
- `docs/claude_v6op/latest_report.md`

报告必须列出：

1. 修改文件清单
2. 每个任务是否完成
3. 测试结果
4. `output/current` 是否被污染
5. 若 wencai 未能真实闭合，必须写明环境阻塞原因，不得写“已完成”

签名：

`Claude / V6OP 新代码师`

