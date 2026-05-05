# V6OP-022 指令：最终收口与签收

> 指令来源：Codex / V6OP 新架构师  
> 执行对象：Claude / V6OP 新代码师  
> 执行目录：`F:\v.6\v6-op`  
> 报告输出：`F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-022_final_acceptance_signoff_report.md`

---

## 一、总目标

本轮是最终收口签收轮，不是新增功能轮。

总纲主链已经跑通：

`source -> fetch_plan -> prefetch -> producer -> expression -> report`

V6OP-021 后，Codex / V6OP 新架构师已追加完整主链验收：

- `run_id=run_20260505_200356_9bafd7`
- source：wencai
- source_status：ok
- scope_count：5
- prefetch_triggered：true
- fetched_ok：5
- failed：0
- readiness：ready
- producer：kline + landmine
- final_hit_count：3
- run_report.md 已生成

本轮目标：清理文档矛盾，重跑最终验收，输出最终签收报告。

不要做：

- 不新增功能
- 不新增页面
- 不接入 21 个后续技能
- 不做 DAG
- 不改 V5.10 / V6
- 不改 `.env` / `.venv`
- 不泄露 key
- 不用 fixture 冒充真实结果

---

## 二、开工前必须读取

1. `v6-op_full_rescue_charter.md`
2. `docs/claude_v6op/reports/V6OP-021_realtime_progress_prefetch_parity_and_rerun_acceptance_report.md`
3. `docs/claude_v6op/reports/V6OP-021_codex_architect_review.md`
4. `docs/claude_v6op/current_status.md`
5. `docs/claude_v6op/latest_report.md`
6. `output/current/execution_result.json`
7. `output/current/run_report.md`

---

## 三、任务 1：清理状态文档矛盾

`current_status.md` 目前有旧状态残留，和 V6OP-021 后的真实状态冲突。

必须修正：

- 阶段 4 不再写 `wencai 预热路径待网络环境`
- 已验收列表不再写 `预热成功路径未闭合`
- 阶段 4 子任务不再写 `wencai 链路触发验证...预热成功路径未闭合`
- 统一写为：wencai 完整端到端已闭合，最终以 `run_20260505_200356_9bafd7` 为 Codex 追加主链验收样本

`latest_report.md` 也同步清理旧状态。

---

## 四、任务 2：重签 15 条验收矩阵

对照总纲第十三节 15 条验收标准，重新列最终矩阵。

要求：

- 15 条全部给出状态
- 状态只能是：已闭合 / 不适用
- 如果写“已闭合”，必须给证据：代码文件、报告文件、run_id 或测试名
- 不允许再出现“部分闭合”
- 不允许把后续 21 技能扩张混进第一阶段签收

重点证据：

- manual 三路径验收：V6OP-008
- output/current 污染防卫：V6OP-016
- V5.10 闭环经验对齐：V6OP-020
- wencai 完整主链验收：Codex 追加 `run_20260505_200356_9bafd7`
- 参数重跑：V6OP-021，`signal_bars=60 hit=6` vs `signal_bars=15 hit=0`
- 实时进度：V6OP-021 `_log_sink`
- 前端预热摘要：V6OP-021 `renderPrefetch`

---

## 五、任务 3：最终验收命令

必须运行：

```powershell
cd F:\v.6\v6-op
.\.venv\Scripts\python.exe -m pytest -q
node --check .\web\app.js
```

必须读取并报告：

```powershell
output/current/execution_result.json
output/current/run_report.md
```

检查当前样本是否仍为：

- `run_id=run_20260505_200356_9bafd7`
- `source=wencai`
- `prefetch_triggered=true`
- `readiness=ready`
- `fetched_ok=5`
- `failed=0`
- `final_hit_count=3`

如果 current 已被测试覆盖，要说明原因，并优先恢复或重跑真实 wencai 主链，不允许最终 current 指向 fixture/test run。

---

## 六、任务 4：最终签收报告

创建：

`docs/claude_v6op/reports/V6OP-022_final_acceptance_signoff_report.md`

报告必须包括：

1. 当前总纲位置
2. 15 条验收矩阵最终状态
3. 当前 `output/current` 摘要
4. 测试结果
5. 修改文件清单
6. 明确剩余边界：后续是阶段 5 的 21 技能逐步接入，不属于本次第一阶段签收
7. Claude 签名

同时更新：

- `docs/claude_v6op/current_status.md`
- `docs/claude_v6op/latest_report.md`

签名：

`Claude / V6OP 新代码师`

---

## 七、完成后回报

完成后告诉 Codex / V6OP 新架构师：

- 报告绝对路径
- 测试结果
- `output/current` run_id
- 修改过的文件列表
- 是否存在任何未闭合项

