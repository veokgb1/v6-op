# V6OP-021 Codex 架构师验收报告

> 验收时间：2026-05-05  
> 验收者：Codex / V6OP 新架构师  
> 被验收报告：`V6OP-021_realtime_progress_prefetch_parity_and_rerun_acceptance_report.md`  
> 结论：功能验收通过；文档状态有旧句残留，需最终收口清理。

---

## 一、总纲位置

本轮对应总纲主链：

`source -> fetch_plan -> prefetch -> producer -> expression -> report`

V6OP-021 主要收口三处此前部分闭合项：

1. `prefetch`：并行 worker `data_time_max` 聚合、CLI 与 API report schema 对齐。
2. `report/UI`：执行日志实时推送、单页显示本轮预热摘要。
3. `source -> report`：wencai 真实链路与参数重跑验收。

本轮没有复制 V5/V5.10 Slot 漏斗，没有新增页面，没有接 21 个后续技能，没有改动 `F:\v.6\v5.10` 或 `F:\v.6\v6`。

---

## 二、代码抽查

已抽查以下文件：

- `scripts/data_prefetch.py`
- `scripts/execution_engine.py`
- `scripts/v6op_server.py`
- `web/index.html`
- `web/app.js`
- `scripts/verify_wencai_e2e.py`
- `tests/test_phase2_execution.py`
- `tests/test_phase3_web_assets.py`

确认结果：

- `_run_coordinator()` 已收集 worker report 的 `data_time_max` 并取全局 max。
- CLI `main()` 已调用 `_apply_recovery(stats, args.days)`，report 含 `failed_codes_raw / recovered_codes / recovered_count / data_time_max`。
- `execution_engine._log()` 已支持 `_log_sink`，`v6op_server` 在执行前注入 `_push_event`，旧的完成后 `get_log_events()` 批量回灌逻辑已移除。
- 前端已新增 `prefetch-box` 与 `renderPrefetch(r)`，能区分 `prefetch_triggered=false` 和本轮真实预热。

---

## 三、独立验证

### 1. 全量测试

```powershell
cd F:\v.6\v6-op
.\.venv\Scripts\python.exe -m pytest -q
```

结果：

```text
299 passed, 3816 warnings
```

### 2. 前端语法

```powershell
node --check .\web\app.js
```

结果：通过，无输出。

### 3. wencai 辅助验收脚本

```powershell
.\.venv\Scripts\python.exe .\scripts\verify_wencai_e2e.py --query "净利润增速大于20%" --limit 10 --json-out .\output\wencai_verify\codex_verify_v6op021.json
```

结果摘要：

- `IWENCAI_API_KEY` 存在，未打印值。
- wencai `status=ok`，返回 10 只。
- 预热样本 5 只：`cache_hit=5`，`fetched_ok=0`，`failed=0`。
- `data_time_max=2026-04-30`。

说明：Claude 报告中的辅助脚本闭合了 `wencai source + prefetch availability`，但该次是缓存命中，不是新拉成功。

### 4. Codex 追加完整主链验收

为按总纲严格验收，我追加运行了完整策略：

```json
{
  "source": {"type": "wencai", "query": "净利润增速大于20%", "limit": 5},
  "skills": ["kline", "landmine"],
  "path_type": "parallel_and",
  "params": {"skills": {"kline": {"signal_bars": 5, "days": 365}}}
}
```

结果：

- `run_id=run_20260505_200356_9bafd7`
- `status=completed`
- `source_status=ok`
- `scope_count=5`
- `prefetch_triggered=True`
- `readiness=ready`
- `cache_hit=0`
- `fetched_ok=5`
- `prefetch_failed=0`
- `data_time_max=2026-04-30`
- `producer_count=2`
- `final_hit_count=3`

这次完整覆盖：

`wencai -> fetch_plan -> prefetch -> producer(kline/landmine) -> expression -> report`

因此条 2 可以按更严格口径闭合。

---

## 四、output/current 状态

`output/current` 当前已被 Codex 追加的完整 wencai 主链验收更新为：

`run_20260505_200356_9bafd7`

这不是测试污染；它是一个真实 wencai 操盘链路 run，比 V6OP-021 报告里的参数重跑 current 更适合作为当前签收样本。

`output/current/run_report.md` 已确认包含：

- 来源类型：问财选股
- 触发自动预热
- 新拉取成功：5
- 拉取失败：0
- K 线数据最新日期：2026-04-30
- 最终命中：3

---

## 五、发现的问题

### P1：`current_status.md` 有旧状态残留

文件中仍有几处与 V6OP-021 结论冲突的旧句：

- 阶段 4 行仍写：`wencai 预热路径待网络环境`
- 已验收列表仍写：`预热成功路径未闭合`
- 阶段 4 子任务仍写：`wencai 链路触发验证...预热成功路径未闭合`

同一文件后文又写 V6OP-021 已闭合 wencai 完整端到端，所以目前文档自相矛盾。

这不影响代码验收，但影响最终签收文件可信度。建议 V6OP-022 只做最终状态收口与签收，不再新增功能。

---

## 六、验收结论

V6OP-021 功能验收通过。

按总纲第一阶段 15 条验收标准，条 2、条 6、条 11 已具备闭合证据；结合此前 V6OP-001 至 V6OP-020，第一阶段主链已可进入最终签收。

下一步建议：

- 不进入 21 技能扩张。
- 不做新页面。
- 不做 DAG。
- 先执行 V6OP-022：最终状态文档清理 + 全量验收矩阵重签 + Codex/Claude 双签收。

— Codex / V6OP 新架构师
