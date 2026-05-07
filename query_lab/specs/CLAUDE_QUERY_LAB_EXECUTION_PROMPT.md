# 给 Claude 的执行工单：V6OP QueryLab 与技能说法典

## 0. 项目边界

正式项目只允许修改：

```text
F:\v.6\v6-op
```

禁止修改：

```text
F:\v.6\v6
F:\v.6\v5.10
F:\New.V5.10\Old.V5
```

旧 V5/V6 只能作为参考，不是正式改动目标。

## 1. 任务定位

这是 V6OP 的重要 OP 基础设施，不是一次性测试脚本。

目标是建立一个长期可扩展的 `query_lab`，用于反测并沉淀：

```text
中文金融自然语言
-> 稳定问财 Query
-> 实测证据
-> 技能说法典
-> P1-P6 / 输入工坊 / 策略台 / 自然语言过滤器可引用规则
```

核心问题：

1. 问财选A股到底怎么问最稳？
2. 问财选板块到底怎么问最稳？
3. 返回对象是什么？
4. 哪些表达稳定、哪些危险、哪些禁止？
5. 后续新增 KD、KDJ、MACD、JMA、BOLL、资金、板块、行情、日线等条件时，如何追加测试、留证据、更新法典？

## 2. 必须先读的规格文件

实现前必须先读：

```text
F:\v.6\v6-op\query_lab\specs\CLAUDE_QUERY_LAB_WORK_ORDER.md
F:\v.6\v6-op\query_lab\specs\中文问财Query种子清单.md
F:\v.6\v6-op\query_lab\specs\V6OP_QueryLab_长期扩展协议.md
F:\v.6\v6-op\query_lab\specs\V6OP_技能说法典_更新治理协议.md
F:\v.6\v6-op\query_lab\specs\V6OP_已知问财语法注意事项.md
```

这些文件是约束，不是参考建议。

## 3. 中文 Query 硬约束

所有实际发送给同花顺问财的 `query_text` 必须是中文金融自然语言。

禁止：

```text
A-shares with market cap between 3 and 15 billion
```

允许：

```text
流通市值在30亿到150亿之间，近30日振幅小于15%的A股
```

英文只能用于：

```text
代码字段、目录名、文件名、枚举值、测试编号
```

允许的中文金融缩写：

```text
A股、ST、MACD、KDJ、KD、PE、PB、ROE、ETF、BOLL、JMA
```

程序必须有中文 Query 预检：

1. `query_text` 必须包含中文字符。
2. 不得出现英文整句。
3. 除白名单缩写外，英文单词要标记为 `invalid_query`，不得请求问财。
4. 报告中必须保留原始中文 `query_text`。

## 4. 两步实施

### 第一步：先把程序全部建立起来并跑通

先搭 QueryLab 框架、配置、测试器、报告器、法典治理器。这个阶段不追求大量真实问财测试，重点是程序结构正确、离线测试通过、目录和数据流闭环。

必须完成：

```text
query_lab/
  README.md
  registry/
    skills_registry.csv
    fields_registry.csv
    query_templates.csv
    status_rules.yaml
  cases/
    astock_问财选A股/
    sector_问财选板块/
    daily_kline_日线/
    quote_行情/
    extensions/
  scripts/
    run_query_lab.py
    query_runner.py
    result_analyzer.py
    report_writer.py
    canon_manager.py
    canon_linter.py
    canon_diff.py
    canon_promote.py
    canon_rollback.py
    validators/
      chinese_query_validator.py
      schema_validator.py
    adapters/
      wencai_astock_adapter.py
      wencai_sector_adapter.py
      daily_kline_adapter.py
      quote_adapter.py
  results/
    runs/
    latest/
  reports/
  canon/
    skills/
    review_queue/
    manual_overrides/
    conflicts/
```

程序入口必须支持：

```text
--dry-run
--route astock|sector|all
--group A1_basic|A2_synonym|S1_basic 等
--limit
--repeat
--sleep-ms
--replay-failed
```

法典治理必须支持：

```text
canon propose
canon lint
canon diff
canon promote
canon rollback
```

第一步验收：

1. 离线 pytest 通过。
2. `--dry-run` 能列出将要跑的中文 Query。
3. 英文 Query 会被 `invalid_query` 拦截。
4. A股和板块能分路由、分目录、分报告。
5. 测试器不会把结果写进普通 `output/current`。
6. 测试结果只能先进入 candidate/review，不得自动覆盖正式法典。

建议运行：

```powershell
Set-Location F:\v.6\v6-op
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py --dry-run --route all --limit 20
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py canon lint
```

### 第二步：按中文金融字段分层实测，形成技能说法典

在第一步跑通后，再开始真实问财测试。不要一次性猛跑。按由简单到复杂的顺序执行：

1. 基础测：单字段、单条件。
2. 同义测：同一个意思不同中文说法。
3. 单位测：亿、万、百分比、排名、区间。
4. 时间测：今日、近5日、近20日、近60日、过去N个交易日。
5. 排除测：非ST、非停牌、非新股、非北交所等。
6. 交叉测：字段组合、条件顺序变化。
7. 复杂测：条件数量阶梯。
8. 危险词测：强势股、龙头、资金关注、热门板块等。
9. 失败回放：None、empty、error、timeout、异常结果复测。
10. 法典生成：只把有证据的稳定说法提为候选。

重点技能：

```text
astock / 问财选A股 / 返回股票
sector / 问财选板块 / 返回板块
```

后续占位技能：

```text
daily_kline / 日线
quote / 行情
technical_indicator / 技术指标
capital_flow / 资金
```

第二步验收：

1. 每次运行生成独立 run 目录。
2. 每条结果保留 `run_id`、`query_id`、`skill_type`、`skill_name_zh`、`query_text`、返回数量、错误类型。
3. 生成 `stable / unstable / risky / failed / forbidden / invalid_query` 分类。
4. 生成候选技能说法典，但不静默覆盖正式法典。
5. 生成冲突报告。
6. 生成中文总结报告。

建议小批量开始：

```powershell
Set-Location F:\v.6\v6-op
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py --route astock --group A1_basic --limit 20 --repeat 1 --sleep-ms 1500
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py --route sector --group S1_basic --limit 10 --repeat 1 --sleep-ms 1500
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py canon propose
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py canon lint
```

## 5. 每个技能必须有英文名 + 中文名

所有技能必须进入总注册表：

```text
query_lab/registry/skills_registry.csv
```

字段示例：

```text
skill_id,skill_key,skill_name_zh,domain,input_type,output_type,adapter,status
wencai_astock,astock,问财选A股,wencai_query,中文Query,股票列表,wencai_astock_adapter,active
wencai_sector,sector,问财选板块,wencai_query,中文Query,板块列表,wencai_sector_adapter,active
daily_kline,daily_kline,日线,market_data,股票代码,K线序列,daily_kline_adapter,pending
quote,quote,行情,market_data,股票代码,行情快照,quote_adapter,pending
```

未来 21 个技能都要按这个方式登记，不能散落在代码里。

## 6. 技能说法典

每个技能最终要形成自己的说法典：

```text
query_lab/canon/skills/astock_问财选A股/
  canon.csv
  canon.md
  evidence_index.jsonl
  changelog.md
  versions/

query_lab/canon/skills/sector_问财选板块/
  canon.csv
  canon.md
  evidence_index.jsonl
  changelog.md
  versions/
```

法典项必须能说明：

```text
这个语义是什么？
标准中文问法是什么？
允许哪些变体？
哪些变体危险？
哪些说法禁用？
证据来自哪些 run_id / query_id？
是否允许 strong / weak / manual 引用？
最近一次验证是什么时候？
能否进入 P1-P6 或输入工坊？
```

## 7. 法典更新规则

测试器不能直接覆盖正式法典。

自动测试只能写：

```text
query_lab/canon/review_queue/candidate_changes.jsonl
```

人工覆盖只能写：

```text
query_lab/canon/manual_overrides/manual_overrides.csv
```

正式发布必须经过：

```text
candidate -> lint -> diff -> manual review -> promote -> changelog -> version snapshot
```

冲突必须写入：

```text
query_lab/canon/conflicts/conflict_items.jsonl
query_lab/canon/conflicts/conflict_report.md
```

## 8. 最终报告

最后必须给出中文验收报告，至少包含：

1. 已建立的目录结构。
2. 已实现的程序入口。
3. 已跑通的离线测试。
4. 已实测的 A股 Query 数量与板块 Query 数量。
5. stable / risky / failed / forbidden 统计。
6. 问财选A股的初步稳定说法。
7. 问财选板块的初步稳定说法。
8. 失败案例和原因。
9. 冲突报告。
10. 技能说法典候选更新。
11. 下一轮建议测试项。

## 9. 不允许做的事

1. 不要用英文金融语句请求问财。
2. 不要把实验报告混进普通 output。
3. 不要静默覆盖正式法典。
4. 不要把 pending/risky 直接放进 P1-P6。
5. 不要修改旧 V5/V6。
6. 不要一次性无节制请求问财。

## 10. 交付后请明确说明

请在最终回复里明确：

```text
第一步是否完成
第二步跑到了哪一层
有哪些文件新增/修改
如何运行测试器
如何查看报告
如何查看候选法典
如何继续追加新技能或新中文问法
```
