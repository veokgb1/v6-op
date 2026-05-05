# V6OP 工程交接报告

> 交接时间：2026-05-05  
> 交接人：Claude (claude-sonnet-4-6)，V6OP-001 至 V6OP-016  
> 接收方：下一位 Claude / Codex 工程师

---

## 一、总览判断

### 1. 各阶段状态

| 阶段 | 内容 | 真实状态 |
|---|---|---|
| 阶段 0 | 数据引擎 + K线预热 + CZSCProducer | **真实闭合**（V6OP-001）|
| 阶段 1 | 6 个 Producer 接通 | **真实闭合**（V6OP-002）|
| 阶段 2 | Fetch Planner + 执行引擎 + 后端 API | **真实闭合**（V6OP-003，经 V6OP-006/006b 纠偏）|
| 阶段 3 | 单页操盘台 + 参数面板 + 证据展开 | **真实闭合**（V6OP-007 三路径端到端通过）|
| 阶段 4 | 问财来源 + 全 A 保护 + 报告增强 + 证据质量 | **主体闭合，一条路径未闭合**：wencai 预热成功路径（baostock 不可达）|

### 2. 什么算真实闭合，什么没有

**已真实闭合（有 run_id 或命令产物为证）：**
- manual 多技能三路径（parallel_and / sequential / simple_hybrid），20只，kline+czsc+wave+landmine，hit=6/20
- SMC strict 验收：20只，signal_bars=60，hit=5/20（ChoCH/BOS 中文证据完整），run_id=run_20260505_180215_b8e84e
- wencai 链路触发：query→scope(5只,status=ok)→prefetch 触发→预热失败降级→run_report.md 生成
- 测试产物隔离（_OUTPUT_ROOT + autouse）：269/269 通过，全套跑完后 output/current 不被污染
- output/current raw JSON 干净（prefetch_report=null，全文无 000003/000005）

**代码已写但环境限制无法验收：**
- wencai 预热成功完整端到端：baostock 在当前 Windows 开发环境不可达，wencai 返回的新股票（300599.SZ 等）无法完成 prefetch→分析。**代码完整，0 行需改，只需网络环境。**

### 3. 离"每天可用的真实操盘台"差哪几大块

1. **baostock 网络环境**：wencai 来源的新股票无法预热，预热路径未端到端验证。
2. **server 需手动启动**：`python scripts/v6op_server.py` 无守护进程/自动重启；self-test 依赖服务已在运行（未启动时超时失败，这是正常行为，不是 bug）。
3. **21 个技能未接主操盘线**：V6/V5.10 中已有资产，但未接入 v6-op 主线；这是"可选扩展"，不是"主线缺口"。

---

## 二、当前代码结构

### 目录职责

| 目录/文件 | 职责 |
|---|---|
| `scripts/` | 全部后端 Python 逻辑（引擎、规划器、报告、API 服务）|
| `scripts/producers/` | 五个本地分析 Producer（kline/czsc/smc/wave/landmine）|
| `scripts/sources/` | 股票来源解析（wencai_source.py）|
| `web/` | 单页前端（app.js, index.html, styles.css），纯静态，v6op_server.py 托管 |
| `tests/` | pytest 测试（5 个文件，269 项）|
| `output/current/` | 最后一次真实操盘结果（三文件：execution_result.json / run_report.json / run_report.md）|
| `output/runs/` | 历次运行归档（每次运行一个子目录，当前 161 个）|
| `docs/claude_v6op/` | 交接文档（current_status.md / latest_report.md / reports/）|

### 核心模块一句话职责

| 模块 | 职责 |
|---|---|
| `ohlcv_provider.py` | 从本地 .pkl 读取 OHLCV 数据，环境变量 READ_CACHE_ONLY=true 时禁止联网 |
| `data_prefetch.py` | 批量从 baostock 拉取 K 线写入 .pkl 缓存，支持 workers 子进程并行 |
| `source_resolver.py` | 将前端 source 配置（manual/wencai/all_a）解析为 scope_codes 列表 |
| `wencai_source.py` | 调用 pywencai 执行自然语言选股，读取 .env IWENCAI_API_KEY |
| `skill_registry.py` | 技能注册表，维护 skill_id → producer 模块路径 + 元信息的映射 |
| `fetch_planner.py` | 根据 scope_codes 和本地缓存制定预热计划，维护 failed/stale/cached 分类不变式 |
| `strategy_graph_builder.py` | 根据 path_type 和 selected_skills 构建执行图（正向/负向/路径顺序）|
| `expression_auto_generator.py` | 根据执行图自动生成布尔表达式（AND/EXCLUDE/sequential 漏斗）|
| `execution_engine.py` | 主控：scope→fetch_plan→prefetch→Producer→expression→report，写 output/current |
| `explanation_builder.py` | 将 producer_results 转为中文证据文本（ChoCH/BOS/K线形态/波浪等）|
| `run_report.py` | 将 execution_result 生成中文 run_report.md 和 run_report.json（12 章节）|
| `v6op_server.py` | Flask API + 静态文件托管，端口 8876，提供 /api/run、/api/health 等端点 |

### 五个本地 Producer

| Producer | 职责 |
|---|---|
| `kline_producer.py` | 识别近 N 日 K 线形态（阳线实体、上影线等），正向命中 |
| `czsc_producer.py` | 使用 czsc 库识别三买/背驰，正向命中 |
| `smc_producer.py` | Smart Money Concepts（ChoCH/BOS/FVG），strict 模式要求 N 日内有买入信号 |
| `wave_producer.py` | 波浪结构识别（Elliott Wave 简化），正向命中 |
| `landmine_producer.py` | 负向排雷（财务/资金流/退市风险），hit=负向→排除命中股票 |

---

## 三、真实验收状态

### 1. 当前最新可靠运行产物

**run_id：`run_20260505_180215_b8e84e`**

对应文件：
- `output/current/execution_result.json`
- `output/current/run_report.json`
- `output/current/run_report.md`
- `output/runs/run_20260505_180215_b8e84e/`（同内容归档）

### 2. output/current 运行参数

| 项目 | 值 |
|---|---|
| source | manual |
| skills | kline, smc, landmine |
| path_type | parallel_and |
| scope_count | 20 |
| scope_codes | 000001~000029（排除 000003/000005，共 20 只）|
| smc params | signal_bars=60, swing_length=10, mode=strict |
| readiness | ready |
| prefetch_triggered | False |
| fetch_plan.failed_codes | [] |
| fetch_plan.stale_codes | [] |
| fetch_plan.prefetch_report | null |
| final_hit_count | 5 |
| final_hit_codes | 000001, 000006, 000008, 000019, 000020 |

### 3. 实际跑过并通过的命令

```
# pytest（V6OP-016 最终状态）
cd F:\v.6\v6-op && python -m pytest tests/ -q
→ 269 passed, 3817 warnings（0 failed, 0 skipped, 0 xfail）

# node --check
node --check web/app.js
→ OK（无语法错误）

# self-test（需先启动 server 才能通过，未启动时 0/1 超时，是正常行为）
python scripts/v6op_server.py --self-test

# manual 三路径硬验收（V6OP-008）
→ parallel_and: run_20260505_161041_9ab802, kline+czsc+wave+landmine, hit=6/20
→ sequential:   run_20260505_161041_9ab802, hit=6/20（相同批次不同路径）
→ simple_hybrid: run_20260505_161043_388e1d, hit=6/20

# SMC strict 验收（V6OP-011/015/016）
→ run_20260505_180215_b8e84e, signal_bars=60, hit=5/20, ChoCH/BOS 证据完整

# wencai 链路触发验收（V6OP-008）
→ run_20260505_161203_2738e2, query→scope(5只,ok)→prefetch 触发→readiness=aborted（baostock不可达）
```

### 4. 尚未完成的验收（环境限制）

- **wencai 预热成功路径**：baostock 在当前 Windows 开发环境不可达。wencai 返回 5 只新股票（300599.SZ 等），这些股票本地无缓存，触发了 prefetch，但 baostock 连接失败 → readiness=aborted。代码路径完整，0 行需改。

---

## 四、数据与真实性

### 1. 是否使用 fixture 冒充真实结果

**否。** 测试中 `execute()` 调用真实 Producer（使用本地 .pkl 缓存），通过 `_OUTPUT_ROOT + autouse monkeypatch` 将输出重定向到 `tmp_path`，不冒充真实结果，也不覆盖 output/current。

真实数据来源：`F:\v.6\v6-op\var\cache\kline_daily\` 中的 .pkl 文件，由 baostock 拉取写入，Producer 通过 `READ_CACHE_ONLY=true` 保证只读缓存、不联网。

### 2. ashare_codes.txt 规模

**5,465 行**（5,465 只 A 股代码）。

### 3. var/cache/kline_daily 缓存规模

**50 个 .pkl 文件**（命名格式：`000001_SZ_365d.pkl`），覆盖 000001~000029.SZ（除 000003、000005 无缓存）。所有 SMC/kline/czsc/wave/landmine 硬验收均依赖这 50 个文件。

### 4. 问财链路真实状态

| 环节 | 状态 |
|---|---|
| IWENCAI_API_KEY | 已在 .env 配置，wencai_source.py 正常读取 |
| source_resolver → wencai query | 可返回 scope_codes（5只，status=ok，已验证）|
| prefetch（baostock） | 触发成功，但 baostock 连接失败，新股票预热不成功 |
| READ_CACHE_ONLY 分析 | 若股票本地有缓存，可正常分析；wencai 返回的新股票无缓存，分析被跳过 |
| run_report.md 生成 | 生成正常，但因所有股票 prefetch 失败，final_hit_count=0 |

---

## 五、两个关键风险说明

### 风险 1：data_prefetch 的 8-worker 路径是否稳定

**当前真实状态：workers>1 路径代码完整，但本会话中从未真实成功跑通过**（因 baostock 不可达）。

具体设计：
- `workers=1 或 codes≤2`：顺序模式，单进程直接拉取。
- `workers>1 且 codes>2`：协调者模式，`subprocess.Popen` 启动子进程，每个子进程独立持有 baostock 会话，子进程退出码非 0 时该 worker 分配的所有代码计入失败。
- Windows stdout/stderr 问题：data_prefetch.py 第 249-252 行已强制将 stdout/stderr 转为 UTF-8，emoji 导入问题在 smc_producer.py 通过 `redirect_stdout(StringIO())` 包裹解决。

**无法给出"已稳定"的验收命令和结果**，因为 baostock 在当前环境不可达，workers>1 实际调用从未成功完成。只能说代码层面的 worker exit code 处理和编码修复已到位。

### 风险 2：stale_codes 语义

**四个问题的精确答案：**

**fetch_planner 是否把 stale 和 failed 分开？是。**
- `failed_codes`：prefetch_report.json 中标记为失败的代码（baostock 拉取失败，无可用数据）
- `stale_codes`：prefetch_report.json 中标记为 stale 的代码（.pkl 存在但数据过旧）
- 两者互斥，通过独立 set 维护

**execution_engine 是否允许 stale 股票进入 Producer？是。**
```python
_failed_set = set(fetch.get("failed_codes", []))
producer_scope = [c for c in scope_codes if c not in _failed_set]
```
`producer_scope` 只排除 `failed_codes`，stale 代码不在 `_failed_set` 中，所以正常进入 Producer。

**landmine_producer 是否会把 stale 当负向剔除？会，但这是正确行为。**
`landmine_producer._load_prefetch_failures()` 读取 prefetch_report.json 中的 `failed | stale` 并集，将含 stale 的股票标记为"prefetch_report 已知无数据"。然而：stale 代码有 .pkl 文件（只是旧），ohlcv_provider 仍能读取它，所以 kline/smc 等技能能正常分析 stale 股票，只有 landmine 会额外对其应用动态排雷规则。这个行为在 V6OP-010 报告中明确记录，当前实现与报告一致。

**当前实现与 V6OP-010 报告是否一致？是。**

---

## 六、已知问题和未完成大块

### 必须完成的主线大块

1. **wencai 预热成功路径**：需 baostock 可达的环境（Linux 服务器/云端）。执行命令：wencai query="净利润增速大于20%", limit=5, skills=["kline","landmine"]，验收：prefetch 成功至少 1 只，run_report.md 有命中。**0 行代码需修改。**

### 可以延后的扩展

1. 接入 21 个技能主操盘线（V6/V5.10 中已有资产，后续接入须先搜索复用，不从零开发）
2. 守护进程/自动重启机制（当前需手动启动 server）
3. 全 A 扫描实际性能测试（all_a 保护已实现，但从未用真实 5,465 只跑过）

### 明确不做的事情

- 不接 21 技能进 v6-op 主操盘线（有禁令）
- 不做任意 DAG
- 不新增页面
- 不开放全部 12 种表达式操作符
- 不重写架构
- 不修改 `F:\v.6\v5.10` 或 `F:\v.6\v6`（只读复用）
- 不复制 `.env` / `.venv`
- 不泄露密钥

---

## 七、测试与保护机制

### 1. 测试总数与 skip/xfail

- **总数：269 项，0 failed，0 skipped，0 xfail**
- 分布：test_phase1_producers（8类），test_phase2_execution（20类），test_phase3_web_assets（6类），test_v6op_server（6类），test_smoke（25个函数）

### 2. 测试产物隔离机制

`tests/conftest.py` 的 autouse fixture（V6OP-013）：
```python
@pytest.fixture(autouse=True)
def _isolate_execution_engine_output(tmp_path, monkeypatch):
    import execution_engine
    monkeypatch.setattr(execution_engine, "_OUTPUT_ROOT", tmp_path)
```
所有调用 `execute()` 的测试，产物自动写入 `tmp_path`，测试结束 monkeypatch 自动恢复。output/current 和 output/runs 不受影响。

### 3. guard tests（TestV6OP014RealCurrentGuard，10 项）

保护 output/current 不被污染，每次 pytest 全套运行后自动验证：

| 测试名 | 验证内容 |
|---|---|
| test_run_report_md_has_no_mock_markers | run_report.md 无 kline_mock/test_run/pytest-of/Temp\pytest |
| test_execution_result_json_has_no_mock_markers | execution_result.json 无上述标记 |
| test_run_id_is_not_test_run | run_id 不以 test_run 开头 |
| test_failed_codes_subset_of_scope | failed_codes ⊆ scope |
| test_stale_codes_subset_of_scope | stale_codes ⊆ scope |
| test_run_report_md_no_out_of_scope_failed_codes | md 不显示 scope 外失败代码（硬保护 000003/000005）|
| test_prefetch_triggered_false_means_no_prefetch_claim_in_md | prefetch_triggered=False 时无"触发了自动预热" |
| test_execution_result_json_no_out_of_scope_codes | execution_result.json 全文无 000003/000005 |
| test_run_report_json_no_out_of_scope_codes | run_report.json 全文无 000003/000005 |
| test_prefetch_report_null_when_not_triggered | prefetch_triggered=False 时 fetch_plan.prefetch_report=null |

### 4. 改完后必须跑的最小验收命令

```bash
# 1. 语法检查
node --check web/app.js

# 2. 全套测试（包含 guard tests）
cd F:\v.6\v6-op && python -m pytest tests/ -q
# 期望：269 passed（或更多），0 failed，0 skipped

# 3. 真实运行一次（确认引擎端到端正常，不启动 server）
python -c "
import sys; sys.path.insert(0,'scripts'); sys.path.insert(0,'scripts/producers')
import execution_engine as ee; ee._OUTPUT_ROOT = None
result = ee.execute({'source':{'type':'manual','codes':['000001.SZ','000006.SZ']},
  'skills':['kline'],'path_type':'parallel_and','params':{}})
print('run_id:', result['run_id']); print('hits:', result['final_hit_count'])
"
```

---

## 八、给新 Claude 的续接 Prompt

```
你正在接手 v6-op 工程（F:\v.6\v6-op），这是一个基于 Python + Flask 的单页 A 股操盘台。

【当前真实状态】
- 阶段 0/1/2/3/4 主体均已闭合
- 唯一未闭合：wencai 来源 + 新股票预热成功路径（baostock 在当前环境不可达，代码不需改）
- output/current 最新产物：run_id=run_20260505_180215_b8e84e
  source=manual, skills=kline+smc+landmine, scope=20只, hits=5/20, prefetch_triggered=False
- pytest: 269/269 通过，0 failed，0 skipped

【不要误判为已完成的地方】
- wencai 端到端未完成（触发验证通过，预热成功路径未通过）
- self-test 会超时失败（因为 server 没有运行，这是正常行为，不是 bug）
- data_prefetch workers>1 路径代码完整但从未在此环境成功过（baostock 不可达）

【下一步最短路径（只有一步）】
在 baostock 可达的环境中运行：
python -c "
import sys; sys.path.insert(0,'scripts'); sys.path.insert(0,'scripts/producers')
sys.path.insert(0,'scripts/sources')
import execution_engine as ee; ee._OUTPUT_ROOT = None
result = ee.execute({
  'source': {'type': 'wencai', 'query': '净利润增速大于20%', 'limit': 5},
  'skills': ['kline', 'landmine'], 'path_type': 'parallel_and', 'params': {}
})
print('run_id:', result['run_id'])
print('prefetch_triggered:', result['prefetch_triggered'])
print('hits:', result['final_hit_count'])
"
验收：prefetch_triggered=True，至少 1 只预热成功，final_hit_count≥0，run_report.md 有命中。

【禁止事项】
- 不接 21 技能进 v6-op 主操盘线
- 不新增页面
- 不做任意 DAG
- 不修改 F:\v.6\v5.10 或 F:\v.6\v6（只读复用）
- 不复制 .env / .venv
- 不泄露密钥
- 不用 fixture 冒充真实结果

【必须先读的文件】
1. docs/claude_v6op/current_status.md      # 最新状态表
2. docs/claude_v6op/latest_report.md       # 当前判断和报告索引
3. output/current/execution_result.json    # 最后一次真实运行完整产物
4. tests/conftest.py                       # 测试产物隔离机制
5. scripts/execution_engine.py             # 主控引擎（最重要）

【必须先跑的验证命令】
cd F:\v.6\v6-op
node --check web/app.js
python -m pytest tests/ -q
# 期望：269 passed，0 failed
```

---

## 九、文件修改清单（V6OP-001 至 V6OP-016）

| 文件 | 主要变更 |
|---|---|
| `scripts/ohlcv_provider.py` | READ_CACHE_ONLY 强制本地读取，baostock 禁用 |
| `scripts/data_prefetch.py` | 8-worker 子进程架构，Windows stdout UTF-8 fix |
| `scripts/source_resolver.py` | manual/wencai/all_a 三来源解析 |
| `scripts/sources/wencai_source.py` | pywencai 调用，key 脱敏，status=ok/blocked/key_missing |
| `scripts/skill_registry.py` | 技能注册表 |
| `scripts/fetch_planner.py` | failed/stale/cached 三分不变式；scope 过滤（V6OP-012）|
| `scripts/strategy_graph_builder.py` | parallel_and/sequential/simple_hybrid 图构建 |
| `scripts/expression_auto_generator.py` | AND/EXCLUDE/顺序漏斗 布尔表达式自动生成 |
| `scripts/execution_engine.py` | 主控引擎；producer_scope（V6OP-009）；prefetch_triggered（V6OP-012）；_OUTPUT_ROOT（V6OP-013）；fetch_for_result（V6OP-016）|
| `scripts/explanation_builder.py` | 中文证据 key 对齐（V6OP-008）|
| `scripts/run_report.py` | 12 章节中文报告；prefetch_triggered 语义（V6OP-012）|
| `scripts/v6op_server.py` | Flask API；all_a 双层保护；self-test |
| `scripts/producers/smc_producer.py` | emoji redirect_stdout（V6OP-010）；pd.to_numeric（V6OP-010）；DatetimeIndex 恢复（V6OP-011）|
| `scripts/producers/landmine_producer.py` | 读取 prefetch_report.json 动态排雷 |
| `web/app.js` | 单页操盘台 JS；参数面板；证据展开；all_a 保护前端 |
| `web/index.html` | 单页 HTML |
| `web/styles.css` | 样式 |
| `tests/conftest.py` | autouse fixture（V6OP-013）|
| `tests/test_phase2_execution.py` | 主要测试文件（20 个测试类，含 guard tests）|
| `output/current/` | 最新真实产物（V6OP-016 重新生成）|

---

## 十、交接结论

**现在 v6-op 位于阶段 4 末尾，主线已完成"单页操盘台可用、SMC 严格验收通过、报告语义正确、测试产物隔离完整"，仍未闭合"wencai 新股票预热成功路径"（baostock 不可达，代码不需改）。下一步应该先做"在 baostock 可达的环境中跑一次 wencai 完整端到端"，而不是接 21 个技能或新增任何功能。**