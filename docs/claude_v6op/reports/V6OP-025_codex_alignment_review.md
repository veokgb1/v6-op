# V6OP-025 Codex 对齐复核

> 复核时间：2026-05-05  
> 复核者：Codex / V6OP 新架构师  
> 对齐对象：命令、Claude 报告、当前代码、验收产物、总纲位置  

---

## 一、先对齐编号和报告事实

当前已完成并有 Claude 报告的是：

```text
命令：docs/claude_v6op/commands/V6OP-024_v6op023_acceptance_fixes.md
报告：docs/claude_v6op/reports/V6OP-024_v6op023_acceptance_fixes_report.md
Codex 复核：docs/claude_v6op/reports/V6OP-024_codex_architect_review.md
```

结论：V6OP-024 五项验收偏差修正与 Claude 报告对齐，可以按五项命令签收。

当前存在的下一条命令是：

```text
docs/claude_v6op/commands/V6OP-025_first_stage_total_closure_delta.md
```

截至本次复核，报告目录没有发现：

```text
docs/claude_v6op/reports/V6OP-025_first_stage_total_closure_delta_report.md
```

所以 V6OP-025 不能签收为已完成，只能签“当前代码已有部分推进，缺正式 Claude 报告和若干闭合项”。

---

## 二、当前代码对 V6OP-025 六大项的真实完成度

| V6OP-025 大项 | 当前代码证据 | 验收结论 |
|---|---|---|
| 1. 技能 catalog 总纲口径闭合 | `python scripts\skill_catalog.py` 输出 `v6_total=22, declared_total=27, missing_asset_count=5, mapped=5, gray=17, live=6`，live 含 `wencai`，`hithink-astock-selector -> wencai`。 | **代码已闭合** |
| 2. 内容寻址 Mask cache 严格闭合 | `mask_cache.py` 已改为 SHA256；5 个 producer 文件均有 `ALGO_VERSION = "1.0.0"`；`mask_cache.py` 动态读取 producer `ALGO_VERSION`。但 `verify_prefetch_300.py` 仍有 `total = cache_hit + fetched_ok + recovered + failed`，`recovered_count` 被重复计入 total/failure_rate。 | **部分闭合，统计公式未闭合** |
| 3. V6 后台资产继承矩阵 | `scripts/v6_asset_alignment.py` 存在且可运行；Codex 复跑输出 total=10，`adapted=3`，`read_only_reference=7`。 | **矩阵已出现，需 Claude 报告解释 7 项只读原因** |
| 4. 执行图、拓扑、Fetch Planner、aborted | `fetch_planner.py` 已从 `skill_registry.data_requirement` 推导 K 线需求，不再见 `_KLINE_SKILLS = frozenset`；`execution_engine.py` 对 `readiness=aborted` 已返回 aborted，不继续 producer；`strategy_graph_builder.py` 输出 `execution_plan/topological_order`。但 `execution_engine.py` 仍保留 `if path_type == "sequential" / elif simple_hybrid / else parallel_and` 三路径 producer 执行业务大分支。 | **部分闭合，执行引擎尚未完全统一到 plan 执行** |
| 5. 验收脚本与真实验收 | Codex 复跑：`pytest -q` 为 `477 passed, 3816 warnings`；`node --check web/app.js` 通过；20 只预热 smoke 通过；浏览器为 `browser_unavailable` 且 exit code 2。未发现 V6OP-025 官方 300 产物。 | **部分闭合，缺 V6OP-025 官方 300 和 Claude 报告汇总** |
| 6. 状态文档与最终签收预备 | `current_status.md` 和 `latest_report.md` 最后更新时间仍停在 V6OP-022 口径，未记录 V6OP-023/024/025 的真实位置。 | **未闭合** |

---

## 三、Codex 复跑结果

```text
pytest -q
=> 477 passed, 3816 warnings
```

说明：功能测试全部通过；warning 仍是 `czsc_producer.py` 上游弃用警告，不是 GBK warning。

```text
node --check web/app.js
=> exit code 0
```

```text
python scripts\verify_prefetch_300.py --limit 20 --workers 2 --json-out output\verification\codex_v6op025_prefetch_smoke_recheck.json
=> status=pass, cache_hit=20, failed=0, data_time_max=2026-04-30
```

```text
python scripts\browser_smoke_playwright.py --json-out output\verification\codex_v6op025_browser_recheck.json
=> status=browser_unavailable, LASTEXITCODE=2
```

```text
python scripts\v6_asset_alignment.py --json-out output\verification\codex_v6op025_v6_asset_alignment_recheck.json
=> total=10, adapted=3, read_only_reference=7
```

---

## 四、不能签收的原因

V6OP-025 目前不能签收，不是因为“没做”，而是因为缺以下事实闭环：

1. 没有 Claude 的 `V6OP-025_first_stage_total_closure_delta_report.md`；
2. `verify_prefetch_300.py` 的 recovered 统计公式仍重复计数；
3. `execution_engine.py` 仍是三路径 producer 大分支，没有完全改成按 `execution_plan` 执行；
4. 没有 V6OP-025 官方 300 预热 JSON；
5. `current_status.md` / `latest_report.md` 仍停在 V6OP-022 旧签收口径；
6. V6 资产矩阵虽然有，但还需要 Claude 在报告中解释 7 项 read-only 的原因和后续接入点。

---

## 五、给 Claude 的正确后续口径

不要重做 V6OP-024，也不要重新打开泛化大包。

Claude 应继续完成当前 V6OP-025，并只补未闭合项：

1. 修正 `verify_prefetch_300.py` 的 total/failure_rate 公式；
2. 将 `execution_engine.py` 的三路径 producer 执行收敛到 `execution_plan`，或在报告中证明为何当前只是 plan 可检查但尚未主链执行；
3. 运行 V6OP-025 官方 300 预热；
4. 更新 `current_status.md` 和 `latest_report.md`；
5. 写出 `docs/claude_v6op/reports/V6OP-025_first_stage_total_closure_delta_report.md`；
6. 报告中逐项签 6 大项，不能把“测试通过”替代“总纲闭合”。

---

## 六、签名

```text
Codex / V6OP 新架构师
V6OP-025 对齐复核
结论：V6OP-025 代码已部分推进，但未形成报告闭环，暂不能签收
```
