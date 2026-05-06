# V6OP-030 全链路逻辑风险审计

日期：2026-05-06

范围：只读审计。未改业务代码，目标是把当前 V6OP 的来源、取数、K线库、技能过滤、路径组合、报告与前端解释一次性摊开，避免“遇到一个问题修一个问题”。

## 一句话结论

当前截图里的失败首先不是缠论、K线、SMC、波浪、排雷造成的，而是问财来源阶段返回了空池：

- 当前 query：`非ST，今日收盘价站上20日均线，近5日主力资金净流入，按近5日主力资金净流入降序`
- 当前 limit：`5000`
- 当前结果：`source status = empty_result`，`scope_count = 0`
- 执行结果：管道在第 1 步来源解析后中止，后面的技能没有真正开始过滤。

所以这一轮不能再只改某个技能参数。需要先把“问财来源是否真实取数、5000 的含义、K线库是否新鲜、路径组合是否和报告一致”这几个根问题查清楚。

## 端到端链路地图

V6OP 当前链路大致是：

1. 前端 `web/app.js`
   - 组装 `strategy.source`：`manual` / `all_a` / `wencai`
   - 组装 `selected_skills`、每个技能参数、执行路径 `sequential` / `parallel_and` / `simple_hybrid`
   - 调 `/api/run`

2. 服务端 `scripts/v6op_server.py`
   - `/api/run` 开后台线程执行
   - `/api/stream` 输出日志
   - `/api/result` 读 `output/current/run_report.json`，没有则回落到 `execution_result.json`
   - `/api/abort` 只设置中止标记，等待执行器在步骤边界检查

3. 来源解析 `scripts/source_resolver.py`
   - `manual`：手动代码
   - `all_a`：本地 A 股代码清单，按 limit 截断
   - `wencai`：调用 `scripts/sources/wencai_source.py`

4. K线准备
   - `scripts/fetch_planner.py` 判断本地 K线是否够
   - `scripts/data_prefetch.py` 缺 K线时补取
   - `scripts/ohlcv_provider.py` 实际读写 K线库

5. 技能运行
   - 缠论：`scripts/producers/czsc_producer.py`
   - K线形态：`scripts/producers/kline_producer.py`
   - SMC：`scripts/producers/smc_producer.py`
   - 波浪：`scripts/producers/wave_producer.py`
   - 排雷：`scripts/producers/landmine_producer.py`

6. 组合与报告
   - 路径组合在 `scripts/execution_engine.py`
   - 表达式报告在 `scripts/expression_auto_generator.py`
   - 中文解释和 Markdown 报告在 `scripts/explanation_builder.py`、`scripts/run_report.py`

## 关键代码证据

这些不是推测，是本轮读代码看到的直接证据：

- `scripts/sources/wencai_source.py:147` 调 `pywencai.get(...)`，但没有看到 `api_key` 被传入调用参数。
- `scripts/execution_engine.py:359` 和 `scripts/execution_engine.py:449` 调 `fetch_planner.plan(...)`，没有把本轮技能最大回看天数传进去。
- `scripts/execution_engine.py:426-437` 预取 K线时才计算 `prefetch_days`，这和前面的 readiness 判断不是同一个入口。
- `scripts/execution_engine.py:473` 调 `compute_scope_data_time_max(...)`，没有传本轮 days。
- `scripts/producers/czsc_producer.py:199` 缠论直接 `fetch_ohlcv(code, days=365, ...)`，存在忽略 UI 回看天数的风险。
- `scripts/data_prefetch.py:197` 启动 worker subprocess，`scripts/data_prefetch.py:207` 直接 `proc.wait()`，未见超时/强杀。
- `scripts/ohlcv_provider.py:341-352` `FAST_FULL_SCAN` 模式只走 baostock，失败后返回 None，不走 akshare/yfinance 降级。

## 高风险问题清单

### 1. 问财 Key 被检查了，但没有真正传给 pywencai

文件：

- `scripts/sources/wencai_source.py`
- `scripts/sources/sector_scan_source.py`

现象：

- 代码会读取 `IWENCAI_API_KEY`，也会在没有 key 时报错。
- 但实际调用 `pywencai.get(...)` 时，没有把 `api_key` 传进去。

风险：

- 页面顶部显示“变量名有 IWENCAI_API_KEY”，用户会以为问财 API 正在授权访问。
- 实际能不能访问，取决于 `pywencai` 自己的环境、cookie、默认配置或接口状态。
- 一旦 pywencai 没吃到 key，就会出现“有 key 但问财返回 None/空”的假象。

Claude 需要查：

- 当前 pywencai 版本到底如何传 key。
- 如果 pywencai 不支持 key 参数，要把 UI/日志文案改掉，不能显示成“key 已生效”。
- 增加一个最小 live smoke：固定宽松 query，确认返回 raw rows、提取 codes、分页数量。

### 2. `PRO 5000` 只是最多取 5000，不是保证 5000，更不是全 A

文件：

- `web/app.js`
- `scripts/source_resolver.py`
- `scripts/sources/wencai_source.py`

现状：

- 问财模式下，`PRO 5000` 表示最多接收 5000 条问财结果。
- 如果问财只返回 45 条，V6OP 当前就只有 45 条来源池。
- 如果问财返回 0 条，V6OP 当前就中止。
- 它不是“全 A 5000”，也不是“不够 5000 自动换全 A”。

风险：

- 用户会把 “PRO 5000” 理解为“全量跑 A 股”。
- 实际它是“问财返回多少用多少，最多截到 5000”。
- 45 条几秒出结果，可能是正常的窄 query，也可能是 query 语法、权限、分页、字段提取有问题。现在无法从报告里看清 raw row。

建议命名：

- 问财档位：`问财最多 5000`
- 全 A 档位：`本地A股最多 5000`
- 不要把两个都叫 `PRO 5000`，否则认知会混。

### 3. 问财 query 语法很脆，当前空结果很可能是来源语句过硬

当前失败 query：

```text
非ST，今日收盘价站上20日均线，近5日主力资金净流入，按近5日主力资金净流入降序
```

更稳的压力测试 query 建议分层：

```text
非ST，收盘价大于20日均线，按成交额降序
```

```text
非ST，近5日主力资金净流入，按主力资金净流入降序
```

```text
非ST，收盘价大于20日均线，近5日主力资金净流入，按主力资金净流入降序
```

风险：

- `今日收盘价站上20日均线` 可能比 `收盘价大于20日均线` 更难被问财识别。
- `按近5日主力资金净流入降序` 可能字段名不稳定。
- 问财返回 None 时，当前日志只显示“视为空结果”，缺少原始响应摘要。

Claude 需要做：

- 建立 5 到 10 条固定问财 smoke query。
- 每条记录：raw rows、提取出的代码数、分页页数、耗时、是否有异常。
- 把空结果区分成：
  - 真的无股票
  - 问财接口失败
  - 字段解析失败
  - 权限/key/session 失败

### 4. K线回看天数没有端到端一致

文件：

- `scripts/execution_engine.py`
- `scripts/fetch_planner.py`
- `scripts/mask_cache.py`
- `scripts/producers/czsc_producer.py`

发现：

- 前端允许每个技能设置 `回看天数`。
- `execution_engine.py` 做预取时会计算技能里的最大 days。
- 但 `fetch_planner.plan(...)` 没有拿到这个最大 days，默认还是 365。
- `compute_scope_data_time_max(...)` 也默认 365。
- 缠论 producer 内部 `fetch_ohlcv(code, days=365)` 是硬编码，可能忽略 UI 传入的回看天数。

风险：

- UI 上改了 180 / 730 天，报告和技能缓存可能以为参数变了，但实际 K线检查仍按 365。
- K线库可能显示“够用”，但对某个技能实际不够。
- 技能结果库的指纹日期可能取错。
- 缠论参数显示和真实计算可能不一致。

这是高优先级，因为它会造成“看起来能跑，实际不是按用户设置跑”。

### 5. V6OP 全量补 K线没有继承 V5 的三源降级

文件：

- `scripts/data_prefetch.py`
- `scripts/ohlcv_provider.py`
- `v6-op_full_rescue_charter.md`

V5/章程目标：

```text
baostock -> akshare -> yfinance -> stale cache
```

当前风险：

- `FAST_FULL_SCAN=true` 时，`ohlcv_provider.py` 主要走 baostock。
- baostock 失败后，不一定继续 akshare/yfinance。
- worker 子进程输出没有完整流到 UI，用户看不到 V5 那种瀑布式取数过程。

结果：

- 大规模取数时，可能很快返回，但不是因为真的完整取完，而是复用旧 K线或只走了一小段逻辑。
- 用户看到“几秒完成”会怀疑是对的。

Claude 需要核对：

- full scan 是否必须恢复 V5 三源降级。
- UI 是否显示“本轮重新取 K线 X、本地已有 Y、失败 Z、最新交易日 D”。
- worker 是否有超时、取消和日志回传。

### 6. K线库是否“够用”不能只看文件存在

文件：

- `scripts/fetch_planner.py`
- `scripts/ohlcv_provider.py`

现状：

- readiness 主要看对应 pickle 文件是否存在。
- 旧 K线判断更多依赖文件 mtime，不完全等于真实最后一根 K线日期。
- 当前报告出现过：K线最新日期 `2026-04-30`，距离当前 `6` 个自然日。

风险：

- UI 说“★★ K线数据库已够用”，用户会理解为行情最新。
- 实际可能只是本地有文件，但最后一根 K线偏旧。

建议：

- “K线数据库已够用”旁必须显示“最新K线日期”。
- 只要数据日期过旧，就用黄色提示。
- 帮助里明确：够用 = 文件能支持本轮计算；不等于行情一定最新。

### 7. 执行路径有三套手写逻辑，容易和报告表达式漂移

文件：

- `scripts/execution_engine.py`
- `scripts/strategy_graph_builder.py`
- `scripts/expression_auto_generator.py`

现状：

- `sequential`、`parallel_and`、`simple_hybrid` 在 execution engine 里各自手写。
- 同时又生成 expression steps 给报告使用。
- 对 sequential / hybrid 来说，最终结果不完全靠 expression runner，而是靠 engine 手动组合。

风险：

- 页面显示“路径=并行/漏斗/混合”，报告表达式可能与真实执行细节不完全一致。
- 后续加入问财板块、P1-P6、打分制、抗压排名时，三套路由会越来越难维护。

建议：

- 后续统一成一个 canonical execution graph。
- UI 路径只是生成 graph 的模式，不要再有多套最终合并逻辑。

### 8. 中止运行不是强中止

文件：

- `scripts/v6op_server.py`
- `scripts/execution_engine.py`
- `scripts/data_prefetch.py`

现状：

- `/api/abort` 设置 abort flag。
- engine 在步骤边界检查。
- Wencai 调用、prefetch worker、某个 producer 内部长循环，不能保证立刻停。
- prefetch worker 是 subprocess，父进程 `wait()` 没有明显超时和 kill。

风险：

- 用户点“中止运行”，UI 可能要等很久。
- 子进程可能继续跑，后续 run 的状态和日志可能混。

这不是不能做，而是要做成“真中止”：能取消网络请求最好，至少能终止 worker 并标记本轮 aborted。

### 9. output/current 里可能残留上一轮文件，容易造成认知混乱

文件：

- `scripts/execution_engine.py`
- `scripts/run_report.py`
- `output/current/*`

观察：

- 当前 source empty 的 run 正确写出了新的 `execution_result.json` 和 `run_report.json`。
- 但旧的 `prefetch_report.json` 仍可能留在 `output/current`。
- engine 现在不再把旧 prefetch report 附到当前报告里，这是好事。
- 但用户或工具直接看目录时，会以为当前失败 run 也做过 K线预取。

建议：

- 每次新 run 开始时，清理或重命名 run-scoped current 文件。
- 或者所有 current 文件都必须带 run_id，UI 只读取匹配 run_id 的文件。

### 10. 报告里缺少完整问财来源证据

文件：

- `scripts/source_resolver.py`
- `scripts/run_report.py`

现状：

- `execution_result.json` 里有 query。
- `run_report.json` 的 `strategy.source` 主要有 type、status、limit、scope_count。
- 问财的 `query_hash`、elapsed、raw row 统计、分页页数等没有完整进入报告。

风险：

- 事后只能看到“问财返回 45/0”，看不出是哪句话、哪次接口、哪一页停了。
- 排查“假 5000 / 真 5000 / 45 从哪来”很困难。

建议：

- 来源报告必须包含：
  - query 原文
  - limit 档位
  - 实际返回数
  - 页数
  - query_hash
  - api_called
  - env_key_present
  - raw_status / error

## 中风险问题清单

### 11. scope_id 只取前 30 个代码生成

文件：`scripts/source_resolver.py`

风险：

- 两个不同股票池，如果前 30 个一样，scope_id 可能一样。
- 技能缓存本身有 full scope fingerprint，结果大概率不乱。
- 但报告追踪和用户识别会误导。

建议：

- scope_id 用完整 sorted codes 或至少加总数、全量 hash。

### 12. Wencai 代码提取和分页需要真实样本校验

文件：`scripts/sources/wencai_source.py`

现状：

- 优先从 `股票代码/证券代码/代码/symbol/code` 字段取。
- 不行就从所有字段里 regex 6 位数字。
- 如果某一页没有新增 code，就停止分页。

风险：

- 问财字段名一变，就可能少提取、提前停止。
- 某些非代码数字可能被误抓。

建议：

- 对 raw DataFrame columns 做日志摘要。
- 固定 query 存一份 sample schema 用测试保护。

### 13. 板块扫描 Phase A 是独立新接口，需要和主链路保持隔离

文件：`scripts/sources/sector_scan_source.py`

现状：

- `/api/scan_sectors` 只是辅助查询板块，不应该直接成为新的 source_type。
- 正确逻辑是：板块扫描出板块名，人工勾选后注入 Phase B 问财语句。

风险：

- 如果以后把 sector 当 source，会破坏 source_resolver/readiness/report 的主链路。

建议：

- 保持 sector_scan 独立。
- 报告里记录“Phase A 板块扫描语句”和“注入到 Phase B 的板块名”。

### 14. SMC 默认模式不一致

文件：

- `scripts/skill_registry.py`
- `scripts/producers/smc_producer.py`
- `scripts/execution_engine.py`
- `web/app.js`

现状：

- registry / producer 默认可能是 `soft_filter`。
- UI / engine 默认展示和实际常用是 `strict`。

风险：

- 用户没显式选模式时，报告、缓存参数、实际运行可能出现理解偏差。

建议：

- 统一默认值。
- 在报告里明确写：`SMC 模式 = strict / soft_filter / bypass`。

### 15. 环境变量是进程全局状态，跨 run 有污染风险

文件：

- `scripts/execution_engine.py`
- `scripts/data_prefetch.py`
- `scripts/ohlcv_provider.py`

现状：

- 执行时会设置 `READ_CACHE_ONLY`、`KLINE_CACHE_DIR`、`FAST_FULL_SCAN`。
- 有些地方会 pop，有些地方依赖全局环境。

风险：

- 一轮运行异常中断后，下一轮可能继承错误环境。

建议：

- 用上下文管理器封装环境变量，finally 里恢复。
- 或者不要用环境变量传内部执行模式，改成显式参数。

### 16. 缓存写入失败被静默吞掉

文件：`scripts/ohlcv_provider.py`

风险：

- 取数成功但写盘失败，报告可能还显示成功。
- 下次运行又缺 K线。

建议：

- 写缓存失败要进入 prefetch_report 的 `failed_codes` 或 `warnings`。

### 17. producer JSON 时间不完全统一 CST

文件：

- `scripts/producers/*.py`
- `scripts/expression_auto_generator.py`

风险：

- 人类 Markdown 报告已经在往 CST 收敛。
- 但机器 JSON 里仍有 naive `datetime.now().isoformat()`。
- 后续历史报告、排序、跨天对账容易混乱。

建议：

- 所有生成时间统一走 `scripts/time_utils.py`。

## V5 对齐缺口

V5 已有但 V6OP 仍未完全对齐或需要确认的能力：

1. V5 的问财/板块来源有更成熟的瀑布式日志。
2. V5 有 Phase A 板块扫描 + Phase B 个股问财注入。
3. V5 有两套收藏：问财选股收藏、板块提示词收藏。
4. V5 有 P1-P6 预设。
5. V5 有报告历史、查看报告、清屏日志、清理缓存、续跑、中止等完整操作。
6. V5 的报告格式曾经专门修过，V6OP 不能退回杂乱 txt / 时间错位 / 数据源不明。
7. V5 设计里有三源取数降级，V6OP full scan 当前要重点核对。

注意：这些功能可以分批做，但不能再用“前端按钮先拉进来”替代后端真实语义。尤其是续跑、清缓存、强中止，必须先定义会影响哪些目录和 run_id。

## 用户当前最容易被误导的词

建议前端统一替换或加帮助：

| 当前词 | 建议词 | 解释 |
|---|---|---|
| scope 总数 | 来源总数 | 本轮股票池里实际有多少只 |
| 缓存 | 本地保存 | 不要泛泛叫缓存，说明是问财快照、K线数据库、还是技能结果库 |
| 预热 | 本轮补K线 | 如果只是检查本地已有 K线，不要叫预热 |
| K线数据库已够用 | 本地K线可计算 | 还要显示最新K线日期 |
| Stale | 旧K线 | 文件存在但行情日期偏旧 |
| PRO 5000 | 问财最多5000 / 本地A股最多5000 | 区分问财来源和全A来源 |

建议星级标记继续保留：

- `★ 问财来源快照`：本轮问财/手动/全A拿到的股票池，下一轮可能覆盖。
- `★★ K线数据库`：本地保存的日K线，重启电脑仍可复用。
- `★★★ 技能结果库`：同股票池、同参数、同日期下的技能计算结果，可复用。

## 压力测试建议顺序

不要一开始全技能全路径 PRO 5000。建议这样测：

### A. 问财来源单测

只开问财，不开任何技能，或者只走最轻的排雷：

```text
非ST，收盘价大于20日均线，按成交额降序
```

预期：

- 来源总数应该明显大于 45。
- 报告要显示问财实际返回数、limit、分页数、耗时。

### B. 本地K线压力

用 A 的来源池，开 K线形态或缠论一个技能。

预期：

- 如果缺 K线，应显示本轮补 K线。
- 如果复用本地，应显示最新 K线日期。

### C. 单技能正确性

分别跑：

- 缠论 + 排雷
- K线 + 排雷
- SMC + 排雷
- 波浪 + 排雷

预期：

- 每个技能报告里都能看出命中数、未命中数、耗时、参数。

### D. 路径对比

同一个来源池、同一组技能，分别跑：

- 顺序漏斗
- 并行取交集
- 简单混合

预期：

- 来源总数一致。
- K线数据库复用。
- 技能结果库能复用时必须显示复用。
- 三种路径的区别只体现在组合方式，不应该重新拉问财，除非用户改了问财语句或来源模式。

### E. 大档位测试

最后再跑 `问财最多 5000` 或 `本地A股最多 5000`。

预期：

- 问财 5000：实际数量可能小于 5000。
- 本地A股 5000：当前清单超过 5000 时截断到 5000，不是无上限全量。

## Claude 处理建议

请不要先改 UI 文案。先做链路证据。

### 第一批：来源真实性和报告证据

目标：

- 确认 `IWENCAI_API_KEY` 是否真正参与 pywencai 请求。
- 区分问财空结果、接口失败、字段解析失败。
- 报告里保留 query 原文、limit、实际返回、分页、raw schema 摘要。

必须新增/更新测试：

- Wencai source smoke 可 mock。
- source empty 时 run_report 不引用旧 prefetch_report。
- `PRO 5000` 文案和数据语义一致。

### 第二批：K线 days 端到端一致

目标：

- execution_engine 计算本轮 max_lookback_days。
- fetch_planner、prefetch、compute_scope_data_time_max、producer 都使用一致 days。
- 修复缠论 producer hardcoded 365。

必须新增/更新测试：

- 修改缠论 days 后，producer 调用 fetch_ohlcv 的 days 变化。
- 修改波浪/SMC days 后，fetch planner 检查对应 days 文件。
- data_time_max 对应本轮最大回看天数。

### 第三批：全量取数和 V5 三源降级

目标：

- 明确 full scan 是否恢复 baostock -> akshare -> yfinance -> 旧K线。
- worker 有超时、中止、日志回传。
- UI 展示本轮新取/复用/失败/旧K线数量。

必须新增/更新测试：

- baostock 失败时进入下一源。
- worker 卡住时 abort 能退出。
- 写缓存失败能进入失败报告。

### 第四批：路径统一和报告一致

目标：

- 明确一个 canonical graph / execution plan。
- sequential / parallel_and / simple_hybrid 只生成不同 graph，不再各自维护最终组合真相。
- 报告表达式必须等于真实执行逻辑。

必须新增/更新测试：

- 同一输入下，三路径的最终 hits 与表达式解释一致。
- 负向排雷永远是排除逻辑，不被当作正向命中。

## 给 Claude 的可复制指令

```text
请做 V6OP 全链路逻辑审计与修复设计，不要只修一个表面问题。

先读：
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-030_full_logic_risk_audit.md
F:\v.6\v6-op\v6-op_full_rescue_charter.md
F:\v.6\v6-op\scripts\execution_engine.py
F:\v.6\v6-op\scripts\source_resolver.py
F:\v.6\v6-op\scripts\sources\wencai_source.py
F:\v.6\v6-op\scripts\sources\sector_scan_source.py
F:\v.6\v6-op\scripts\fetch_planner.py
F:\v.6\v6-op\scripts\data_prefetch.py
F:\v.6\v6-op\scripts\ohlcv_provider.py
F:\v.6\v6-op\scripts\mask_cache.py
F:\v.6\v6-op\scripts\producers\czsc_producer.py
F:\v.6\v6-op\scripts\run_report.py
F:\v.6\v6-op\web\app.js

请先输出一份修复设计，不要直接大改：
1. 当前问财空结果到底是 query 语法、key/session、分页、字段解析，还是正常无结果。
2. PRO 5000 在问财和全A下分别代表什么，前端和报告如何避免误导。
3. K线回看天数如何从 UI 传到 fetch_planner、prefetch、producer、mask_cache，指出所有不一致。
4. full scan 是否恢复 V5 三源降级，以及 abort 如何真正终止 worker。
5. sequential / parallel_and / simple_hybrid 是否能统一成一个 graph，报告表达式是否等于真实执行。
6. 哪些改动本轮做，哪些只给设计，不要把 V5 的续跑/清缓存/历史报告等大功能和来源修复混成一锅。

输出要求：
- 先给风险清单和优先级。
- 再给文件级修改方案。
- 最后给测试清单。
- 没有证据不要说“已修复”。
```
