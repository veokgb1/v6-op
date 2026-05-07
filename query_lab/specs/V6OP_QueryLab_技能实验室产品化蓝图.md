# V6OP QueryLab 技能实验室产品化蓝图

## 定位

`query_lab` 后续必须从“零散测试脚本”升级成 V6-OP 的独立软件块：技能实验室。

它负责管理每个技能的：

- 为什么要测
- 怎么测
- 当前测试状态
- 地板问法
- 天花板问法
- 标准输入格式
- 间接/拆分输入格式
- 禁问/风险表达
- 返回对象契约
- 当前法典
- 历史证据和回滚记录

这个软件块以后要能随主程序迁移，不能散在临时报告、聊天记录、output 里。

## 总目录建议

现有 `query_lab` 可以保留，但要明确每层职责：

```text
query_lab/
  registry/                 技能登记表：有哪些技能、中文名、英文 key、状态
  cases/                    每个技能的测试用例 CSV
  scripts/                  测试器、guard、adapter、analyzer、canon 工具
  results/                  每次实测原始结果，按 run_id 留痕
  reports/                  人能读的阶段报告、交接报告、法典摘要
  canon/                    正式说法典、候选变更、冲突、版本
  specs/                    给 Claude/Codex/后来者的工单、协议、蓝图
  tests/                    离线单元测试和回归测试
```

后续不要新增散乱根目录。任何技能评测材料都要归到上面七类之一。

## 每个技能必须有一张技能卡

建议在 `query_lab/registry/skills.csv` 或 JSON 中登记：

```text
skill_key
skill_name_zh
route
source_backend
status
owner
purpose_zh
input_object_type
output_object_type_expected
return_contract_status
canon_status
last_verified_run_id
last_verified_at
notes
```

示例：

```text
astock,问财选A股,astock,iwencai_openapi,testing,QueryLab,用中文条件筛选A股,自然语言条件,stock_code/stock_name,needs_recheck,draft,...
sector,问财选板块,sector,iwencai_openapi,testing,QueryLab,用中文条件扫描板块,自然语言条件,sector/stock/mixed/text,testing,draft,...
```

## 每个技能至少三类测试

### 1. 地板测试

回答：

- 最短稳定问法是什么？
- 单字段能不能稳定返回？
- 最低可用输入格式是什么？

例：

```text
问财选A股：今日涨幅大于3%
问财选板块：今日涨幅排名前10的板块
```

### 2. 天花板测试

回答：

- 条件最多能叠几层？
- 哪些字段组合后会超时、吞条件、返回空？
- 哪些复杂问法必须拆分？

例：

```text
今日涨幅大于3%，今日成交额大于50亿，今日主力净流入为正的板块
```

### 3. 返回契约测试

回答：

- 返回的是股票代码、股票名称、板块名称、混合表格，还是纯文本？
- 返回对象能不能直接进入下一段 pipeline？
- 如果不能，应该接人工审阅、二次拆分，还是本地技能？

这是目前漏得最严重的一层。

## 返回契约是强制字段

每个技能都必须定义 `return_object_type`，不能只写 stable/failed。

通用候选：

```text
stock_code
stock_name
stock_table
sector_name
sector_table
mixed_sector_stock
indicator_value
quote_value
text_explanation
table_unknown
empty_or_error
```

对 `问财选A股` 的补测要求：

前期我们默认它返回股票代码，但这只是想当然。后续必须补一次返回契约复查：

- 是否返回股票代码
- 是否返回股票简称
- 是否返回股票代码 + 名称
- 是否返回其他列
- 是否可能返回文本说明
- 是否可能返回混合表

这不是重跑 A1-A15，而是补 `A_return_contract` 小组。

## 每个技能的文件落点

以 `问财选板块` 为例：

```text
cases/sector_问财选板块/
  S1_basic.csv
  S2_synonym.csv
  S3_combo.csv
  S4_risky.csv
  S5_return_contract.csv

reports/
  sector_ceiling_report.md
  sector_return_contract_report.md
  SECTOR_QUERY_CANON_HANDOFF.md

canon/skills/sector_问财选板块/
  canon.csv
  canon.md
  evidence_index.jsonl
  changelog.md
  versions/
```

以 `问财选A股` 为例，后续要补：

```text
cases/astock_问财选A股/
  A_return_contract.csv

reports/
  astock_return_contract_report.md

canon/skills/astock_问财选A股/
  canon.csv
  canon.md
  evidence_index.jsonl
```

## 技能状态流转

每个技能必须有明确状态：

```text
not_started       未开始
scaffolded        骨架已建
floor_testing     地板测试中
ceiling_testing   天花板测试中
return_testing    返回契约测试中
canon_draft       法典草案
canon_review      等人工审阅
canon_active      法典可引用
needs_retest      需要补测
deprecated        暂停/废弃
```

## 法典引用等级

每条法典不能只有“能用/不能用”，还要标注系统能不能自动引用：

```text
strong    强引用：系统可自动生成
weak      弱引用：系统可建议，用户可绕过
manual    只给人工看
pending   待测
risky     高风险
forbidden 禁止自动生成
```

## 21 个技能的扩展节奏

不要一次性测 21 个技能。

每个技能都走同一模板：

```text
技能卡登记
-> 地板测试
-> 天花板测试
-> 返回契约测试
-> 法典候选
-> 冲突检查
-> 人工确认
-> 正式法典
```

当前优先级：

1. 问财选A股：已完成 A1-A15，但要补返回契约。
2. 问财选板块：正在摸地板、天花板、返回契约。
3. 后续日线/行情/技术指标：必须沿用同一模板。

## 对策略台/输入工坊的意义

QueryLab 最终不是为了写报告，而是为了让产品少痛苦：

- 输入工坊用法典生成字段矩阵。
- 用户自然语言先过法典过滤。
- P1-P6 不再是死按钮，而是法典引用。
- 策略台知道每个 Query 返回什么对象。
- pipeline 知道该接 Phase B、本地技能、人工审阅还是禁止运行。

## 后续必须补的短板

### 问财选A股返回契约补测

原因：

前期主要测试了“怎么问”和“能否返回股票池”，但没有系统确认它到底返回哪些字段。

补测目标：

```text
问财选A股返回股票代码？
返回股票简称？
返回股票代码 + 股票简称？
返回附加指标列？
返回文本说明？
返回混合表？
```

### 问财选板块返回契约

原因：

板块返回可能不是单一对象，可能是：

```text
板块名
A股股票
板块 + 股票混合
指数/概念说明
文本理由
空结果
```

这决定后续接法：

```text
sector_name -> Phase B / 问财选A股
stock_code/stock_name -> 本地技能
mixed -> 拆分审阅
text -> 人工参考
empty/error -> 禁止继续
```

## 结论

QueryLab 要作为 V6-OP 的独立基础设施长期维护。

它不是临时测试目录，而是以后 21 个技能的共同入口：

```text
技能登记
测试用例
实测证据
返回契约
说法典
冲突治理
产品引用
```

后续所有 Claude/Codex 工单都必须先看本蓝图，再决定新技能应该放在哪里、怎么测、怎么入法典。
