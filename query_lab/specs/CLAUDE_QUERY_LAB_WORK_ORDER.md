# Claude 工单：同花顺问财 Query 实验体系

## 项目边界

正式项目只允许修改：

```text
F:\v.6\v6-op
```

不要修改：

```text
F:\v.6\v6
F:\v.6\v5.10
F:\New.V5.10\Old.V5
```

旧 V5/V6 只能作为参考。

## 核心目标

建立一个独立的 `query_lab` 实验体系，用于系统测试同花顺问财 Query 的中文解析规律。

当前阶段不要改 P1-P6，不要改主策略台业务流程，不要把实验报告混进普通运行报告。

这不是一次临时测试脚本，而是 V6OP 的重要 OP 基础设施。它要成为后续所有“问财中文语义 -> 稳定 Query -> 实测证据 -> 可复用规则”的长期知识库。

以后用户继续增加 KD、KDJ、JMA、MACD、BOLL、均线、资金、板块、题材、风险排除等技术标准时，必须能追加到这个体系里复测、归档、出报告，而不是重新靠人工猜问法。

## 必须先读

先读这个中文种子清单，再生成测试用例：

```text
F:\v.6\v6-op\query_lab\specs\中文问财Query种子清单.md
```

这个文件是中文金融语义白名单。实际发送给问财的 `query_text` 必须来自这里，或基于这里的中文表达扩展。

同时必须遵守长期扩展协议：

```text
F:\v.6\v6-op\query_lab\specs\V6OP_QueryLab_长期扩展协议.md
```

还必须阅读前期已经踩过的问财语法注意事项：

```text
F:\v.6\v6-op\query_lab\specs\V6OP_已知问财语法注意事项.md
```

还必须遵守技能说法典更新治理协议：

```text
F:\v.6\v6-op\query_lab\specs\V6OP_技能说法典_更新治理协议.md
```

## 中文 Query 硬约束

1. 所有实际发送给同花顺问财的 `query_text` 必须是中文金融自然语言。
2. 禁止把问财查询语句翻译成英文。
3. 英文只能用于代码标识、文件名、字段名、枚举值、测试编号。
4. 允许保留中文金融语境里的缩写：A股、ST、MACD、KDJ、PE、PB、ROE、ETF、BOLL。
5. 报告必须保留原始中文 `query_text`。
6. 如果发现英文整句 query，必须标记为 `invalid_query`，不得请求问财。

正确示例：

```text
skill_type = astock
skill_name_zh = 问财选A股
query_text = 流通市值在30亿到150亿之间，近30日振幅小于15%的A股
```

错误示例：

```text
query_text = A-shares with circulating market cap between 3 and 15 billion
```

## 技能路由

必须严格分两路：

```text
astock / 问财选A股 / 返回股票
sector / 问财选板块 / 返回板块
```

两者不能混测、不能混表、不能混统计。

注意：板块测试需要记录底层实际尝试的问财类型，例如 `sector`、`zhishu`。因为当前 V6-OP 已经发现部分板块 Query 可能需要 `zhishu` fallback。

## 目录

请建立或补全：

```text
F:\v.6\v6-op\query_lab\
  README.md
  configs\
    astock\
    sector\
    shared\
    extensions\
  scripts\
  results\
    query_results.jsonl
    failed_replay.jsonl
    runs\
  reports\
    stable_dictionary.md
    risk_dictionary.md
    parser_boundary_report.md
    p1_p6_recommendation.md
    query_normalizer_rules.md
  canon\
    skills\
    review_queue\
    manual_overrides\
    conflicts\
  specs\
    中文问财Query种子清单.md
    CLAUDE_QUERY_LAB_WORK_ORDER.md
    V6OP_QueryLab_长期扩展协议.md
    V6OP_技能说法典_更新治理协议.md
```

不要把实验结果写到普通 `output/current` 或普通策略运行报告里。

## 测试表统一字段

每条测试必须包含：

```text
query_id
skill_type
skill_name_zh
actual_query_backend
op_domain
op_topic
source_origin
source_note
version
test_group
category
query_text
normalized_intent
condition_count
field_atoms
expression_type
time_window
unit_type
operator_type
order_variant
risk_tags
run_count
success_count
none_count
error_count
empty_count
avg_result_count
min_result_count
max_result_count
avg_latency_ms
status
risk_level
recommended_usage
notes
```

字段补充说明：

```text
op_domain：OP 领域，例如 wencai_query、technical_indicator、sector_query、capital_flow
op_topic：具体主题，例如 MACD、KDJ、JMA、板块涨幅、主力净流入
source_origin：来源，例如 user_added、seed_spec、failed_case、v5_reference、v6op_runtime
source_note：为什么新增这条测试，例如 用户以后要叠加 JMA 条件
version：实验规则版本，例如 v1、v2
```

## 运行能力

实验程序需要支持：

```text
--dry-run
--route astock|sector|all
--group A1_basic|A2_synonym|S1_basic 等
--limit
--repeat
--sleep-ms
--replay-failed
```

默认不要全量猛跑。默认应当安全、可暂停、可复跑。

## 状态分类

报告需要分类为：

```text
stable / 稳定
unstable / 不稳定
risky / 高风险
failed / 失败
forbidden / 禁用
invalid_query / 非法查询
```

只有 `stable / 稳定` 才能进入未来 P1-P6 候选。

`risky / 高风险` 和 `forbidden / 禁用` 只能作为反例和 normalizer 警告依据。

## 交付要求

1. 生成 query_lab 实验程序。
2. 生成初始中文测试用例 CSV。
3. 生成结果分类器。
4. 生成报告写入器。
5. 增加 README 使用说明。
6. 增加离线 pytest，保证不调用真实问财也能测试 CSV 读取、中文 Query 校验、结果分类、报告生成。
7. 不改主策略台 P1-P6。
8. 不修改旧 V5/V6。
9. 增加可追加扩展机制：未来新增 KD、JMA、MACD、板块问法、资金问法时，可以追加测试项并保留历史结果。
10. 增加 pending/unknown 队列：用户提出但暂未验证的中文金融语义，先进入待测队列，不允许直接进入 P1-P6 或自动策略。
11. 增加技能说法典治理功能：测试结果不得直接覆盖正式法典，必须先进入 candidate/review 队列，经人工确认后才能 promote。
12. 增加冲突检测：同一语义多种标准说法、同一句话多个语义、strong 与 forbidden 冲突、A股/板块路由冲突、人工覆盖与测试证据冲突，都必须报告。
13. 增加版本与回滚：每次法典变更必须有 version、changelog、evidence run_id、reviewer、reason，旧条目只能 deprecate，不能静默删除。

## 验收标准

1. `query_text` 全部是中文金融表达。
2. `astock / 问财选A股` 和 `sector / 问财选板块` 完全分开。
3. 结果只进入 `query_lab/results` 和 `query_lab/reports`。
4. 报告能告诉我们：
   - 哪些中文表达稳定
   - 哪些中文表达不稳定
   - 哪些中文表达危险
   - 哪些中文表达禁止自动生成
   - P1-P6 应该从哪些稳定表达里候选
   - 用户自然语言应该如何被改写成稳定问财 Query
5. 能解释每个字段/技术指标/板块问法的测试证据来自哪里，未来新增条件时能继续复测和对表。
6. 能输出技能说法典候选变更、冲突报告、人工覆盖记录，并能回滚到上一版法典。
