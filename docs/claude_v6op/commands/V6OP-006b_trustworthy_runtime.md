# V6OP-006b 可信运行层纠偏命令

> 下发角色：v6-op 架构师（Codex）
> 执行对象：Claude
> 任务性质：小范围纠偏，不是阶段 4，不是新增功能
> 时间：2026-05-05

---

## 0. 本轮判断

V6OP-006 已经把自动预热、sequential、simple_hybrid、证据展开、前端/API 契约这五个方向拉回来了，但不能宣布最小可用验收闭合。

当前阻断点不是功能缺失，而是可信运行层仍有硬风险：

1. Fetch Planner 判断缓存的文件名和真实缓存文件名不一致。
2. data_prefetch 的 worker report 会混入旧报告，导致 prefetch_report 数字不自洽。
3. READ_CACHE_ONLY 在同一进程两阶段运行时可能受模块导入时机影响。
4. run_report.md 仍把全链路写成“未访问 baostock / akshare / yfinance”，没有区分数据准备阶段和本地分析阶段。
5. strategy_graph_builder.py 文件头注释仍残留 simple_hybrid = K_OF_N。

本轮只修这五项。不要进入阶段 4。

---

## 1. 必读文件

请先阅读：

```text
F:\v.6\v6-op\v6-op_full_rescue_charter.md
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-006_completion_report.md
F:\v.6\v6-op\docs\claude_v6op\current_status.md
F:\v.6\v6-op\docs\claude_v6op\latest_report.md
F:\v.6\v6-op\output\current\prefetch_report.json
F:\v.6\v6-op\output\current\run_report.md
```

重点代码：

```text
scripts/fetch_planner.py
scripts/ohlcv_provider.py
scripts/data_prefetch.py
scripts/execution_engine.py
scripts/run_report.py
scripts/strategy_graph_builder.py
```

---

## 2. 修复一：缓存命名必须统一

当前问题：

`fetch_planner.py` 用：

```text
cache_dir / f"{code}.pkl"
```

但真实缓存由 `ohlcv_provider.cache_path(code, days)` 写出，文件名类似：

```text
000001_SZ_365d.pkl
```

这会导致缓存已经存在时，Fetch Planner 仍判断 missing，进而误触发预热、误判 readiness。

要求：

- `fetch_planner` 不得自己拼缓存文件名。
- 必须复用 `ohlcv_provider` 的缓存路径规则，或抽出一个共同 helper。
- 如修改 helper，必须保证 `ohlcv_provider` 写缓存和 `fetch_planner` 查缓存使用同一函数。
- 最好同时考虑 `lookback_days` 和缓存新鲜度，不能只看裸文件是否存在。

验收：

- 对 `000001.SZ`、`000002.SZ` 这类已有 `000001_SZ_365d.pkl` 缓存的代码，`fetch_planner.plan(..., lookback_days=365)` 应识别为 cached，不应再放入 missing。

---

## 3. 修复二：worker report 必须按本轮隔离

当前问题：

`output/current/prefetch_report.json` 出现过：

```text
total_codes = 3
fetched_ok = 13
failed = 7
```

这不可能。说明 `_run_coordinator` 可能读取了旧的 `prefetch_worker_*_report.json`，或 worker report 没有按本次运行隔离。

要求：

- 每次 `run_prefetch()` 开始前，必须清理或隔离本轮 worker report。
- 推荐使用本轮独立目录，例如 `output/current/prefetch_workers/<prefetch_run_id>/`。
- 每个 worker report 必须带本轮 `prefetch_run_id`、`worker_id`、`total_codes`、`run_at`。
- coordinator 汇总时只能读取本轮 worker 产生的报告。
- 如果 worker 退出码非 0、报告缺失、run_id 不匹配，不允许读取旧报告顶替。
- worker 失败时，应把该 worker 分配到的 codes 计入失败，或在报告中明确标注 worker_failed_codes，不能让总数失真。

验收：

- `cache_hit + fetched_ok + stale_used + failed + bj_skipped` 必须等于 `total_codes`，除非报告明确给出 worker_failed_codes 且总数仍可解释。
- 连续运行两次不同小股票池，第二次 prefetch_report 不得混入第一次的 worker 结果。

---

## 4. 修复三：READ_CACHE_ONLY 两阶段隔离必须可靠

当前风险：

`execution_engine` 在同一进程里调用 `data_prefetch.run_prefetch()`，然后设置：

```text
os.environ["READ_CACHE_ONLY"] = "true"
```

但 `ohlcv_provider.py` 里的 `_READ_CACHE_ONLY` 是模块导入时读取环境变量得到的全局值。如果模块已经导入，后续切换环境变量不一定生效。

要求：

- Producer 阶段必须证明只读缓存，不能访问 baostock / akshare / yfinance。
- 预热阶段必须允许网络拉取。
- 推荐修法：`ohlcv_provider.fetch_ohlcv()` 每次调用时动态读取 `READ_CACHE_ONLY` 和 `FAST_FULL_SCAN`，不要依赖导入时固定的全局布尔值。
- 如果采用子进程隔离，也必须新增测试证明 Producer 阶段不走网络。

验收：

- 新增测试：在 `READ_CACHE_ONLY=true` 且缓存缺失时，mock/monkeypatch baostock、akshare、yfinance fetcher 为“一旦调用即失败”，Producer 阶段应返回缓存未命中，而不是触发这些网络 fetcher。
- 新增测试：`run_prefetch()` 在调用前即使环境里有 `READ_CACHE_ONLY=true`，预热阶段仍能进入允许网络的模式。

---

## 5. 修复四：报告必须区分数据准备阶段和本地分析阶段

当前问题：

`run_report.md` 边界声明仍写：

```text
未访问 baostock / akshare / yfinance（仅读缓存）。
```

但同一轮已经发生自动预热，这句话会误导用户和验收。

要求：

报告必须分成两段写：

```text
数据准备阶段：
- 是否触发自动预热；
- 是否访问网络数据源；
- 预热代码数、缓存命中、新拉成功、失败、stale、BJ跳过；
- 如能取得来源统计，写明 baostock / akshare / yfinance 的使用情况。

本地分析阶段：
- Producer 是否强制 READ_CACHE_ONLY；
- Producer 是否未访问 baostock / akshare / yfinance；
- 缓存缺失或旧缓存如何处理。
```

禁止继续笼统写“未访问 baostock / akshare / yfinance（仅读缓存）”覆盖整个链路。

---

## 6. 修复五：清理 K_OF_N 残留注释

`strategy_graph_builder.py` 文件头仍写：

```text
simple_hybrid : 正向技能 K_OF_N（过半数），负向技能 EXCLUDE
```

请修正为：

```text
simple_hybrid : 前 2 个正向技能并线 AND，后续正向技能顺序过滤，负向技能 EXCLUDE
```

这只是注释修正，但必须做，避免后续维护者被误导。

---

## 7. 本轮禁止事项

禁止：

- 进入阶段 4；
- 接入问财新能力；
- 接入 21 个灰色技能；
- 新增页面；
- 做任意 DAG；
- 重写整个系统；
- 修改 `F:\v.6\v5.10`；
- 复制 `.env` / `.venv`；
- 打印、写入、泄露任何 API key；
- 用 fixture 冒充真实结果。

---

## 8. 必须新增或更新测试

至少覆盖：

1. `fetch_planner` 使用真实缓存命名，能识别 `000001_SZ_365d.pkl`。
2. `run_prefetch()` 连续两轮运行不会混入旧 worker report。
3. prefetch_report 统计自洽，总项数关系合理。
4. `READ_CACHE_ONLY=true` 时 Producer 阶段不会调用网络 fetcher。
5. `run_report.md` 同时出现“数据准备阶段”和“本地分析阶段”的边界说明。
6. `strategy_graph_builder.py` 不再残留 `simple_hybrid = K_OF_N` 文件头说明。

---

## 9. 验收命令

必须执行：

```powershell
cd F:\v.6\v6-op
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts\v6op_server.py --self-test --port 8878
```

还必须执行一次小股票池端到端运行，并在报告里写清：

```text
scope_codes:
prefetch_report:
- total_codes
- cache_hit
- fetched_ok
- failed
- stale_used
- bj_skipped
- 是否自洽

fetch_planner:
- cached_codes
- missing_codes
- failed_codes
- readiness

报告口径：
- 数据准备阶段是否访问网络
- Producer 分析阶段是否只读缓存
```

如果真实网络或数据源阻断，必须写清阻断原因和阶段，不允许说成通过。

---

## 10. 输出要求

完成后必须写唯一总报告：

```text
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-006b_trustworthy_runtime_report.md
```

同时更新：

```text
F:\v.6\v6-op\docs\claude_v6op\latest_report.md
F:\v.6\v6-op\docs\claude_v6op\current_status.md
```

报告必须包含：

1. V6OP-006b 完成 / 未完成。
2. 五项修复逐条说明。
3. 修改文件清单。
4. 测试命令和结果。
5. 端到端运行样例。
6. prefetch_report 数字是否自洽。
7. Producer 阶段只读缓存证明。
8. 是否修改 V5.10：必须明确写“没有”。
9. 是否泄露密钥：必须明确写“没有泄露”。
10. 是否用 fixture 冒充真实结果：必须明确写清。

---

## 11. 完成后回复格式

```text
V6OP-006b 已完成 / 未完成

五项可信运行纠偏：
1. 缓存命名统一：
2. worker report 隔离：
3. READ_CACHE_ONLY 两阶段隔离：
4. 报告口径修正：
5. K_OF_N 注释清理：

验收：
- pytest:
- self-test:
- 小股票池端到端:
- prefetch_report 自洽性:
- Producer 只读缓存证明:

报告路径：
- ...

风险：
- ...
```
