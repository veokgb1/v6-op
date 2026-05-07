# V6OP QueryLab 长期扩展协议

## 定位

`query_lab` 是 V6OP 的长期 OP 基础设施，不是一次性脚本。

它负责把模糊的中文金融想法，逐步沉淀成可验证、可复测、可对表的问财 Query 知识库。

核心链路：

```text
用户自然语言
-> 待测语义记录
-> 中文 Query 候选
-> 问财实测
-> 结果分类
-> 稳定表达字典 / 风险表达字典
-> P1-P6 / 输入工坊 / 策略台可引用规则
```

## 为什么必须做成库

V6OP 后续会不断遇到新问题：

- 问财选A股到底怎么问最稳
- 问财选板块到底怎么问最稳
- KD、KDJ、JMA、MACD、BOLL、均线等技术指标能不能叠加
- 资金、题材、板块、风险排除条件能不能组合
- 用户一句自然语言到底应该改写成哪条稳定 Query

这些问题不能靠临时猜测，也不能靠一次对话解决。每一次新增、失败、修正，都必须进入同一个实验库，后续可以复盘、复测、对照。

## 追加规则

未来新增任何中文金融语义时，必须先进入待测队列：

```text
query_lab/configs/extensions/pending_queries.csv
```

待测项必须记录：

```text
pending_id
op_domain
op_topic
skill_type
skill_name_zh
user_phrase
candidate_query_text
normalized_intent
source_origin
source_note
risk_tags
created_at
status
notes
```

示例：

```text
pending_id: EXT-KDJ-001
op_domain: technical_indicator
op_topic: KDJ
skill_type: astock
skill_name_zh: 问财选A股
user_phrase: KDJ金叉
candidate_query_text: 今日KDJ金叉
normalized_intent: KDJ 指标今日形成金叉
source_origin: user_added
source_note: 用户后续希望把 KDJ 技术条件叠加进策略
risk_tags: technical_indicator
status: pending
```

## 技术指标扩展候选

以下不是稳定结论，只是后续可测候选。没有测试前不得进入自动策略。

### KDJ / KD

- 今日KDJ金叉
- 今日KDJ死叉
- KDJ指标金叉
- K值大于D值
- KDJ处于低位金叉
- KDJ超卖区金叉

### MACD

- 今日MACD金叉
- 今日MACD死叉
- MACD红柱放大
- MACD绿柱缩短
- DIF上穿DEA
- MACD零轴上方金叉

### JMA

JMA 不是问财常见标准字段，必须作为高风险扩展项处理。

- 收盘价站上JMA均线
- JMA均线向上
- JMA趋势向上
- JMA拐头向上

默认：

```text
risk_level = high
recommended_usage = pending
```

### BOLL

- 收盘价突破布林线上轨
- 收盘价跌破布林线下轨
- 收盘价站上布林线中轨
- 布林线开口放大

### 均线

- 今日收盘价大于5日均线
- 今日收盘价大于20日均线
- 5日均线大于20日均线
- 5日均线上穿20日均线
- 均线多头排列

## 状态流转

任何新增语义必须按下面状态流转：

```text
pending / 待测
-> testing / 测试中
-> stable / 稳定
-> unstable / 不稳定
-> risky / 高风险
-> failed / 失败
-> forbidden / 禁用
```

只有 `stable / 稳定` 可以进入：

- P1-P6 候选
- 输入工坊推荐模板
- 自动 normalizer 改写规则
- 策略台默认快捷项

`risky / 高风险` 只能进入手动提示和风险说明。

`forbidden / 禁用` 只能作为反例。

## 对表要求

每次实测后必须能回答：

1. 这句话是问 A 股还是问板块？
2. 实际调用的是 stock、sector 还是 zhishu？
3. 返回对象是什么？
4. 返回数量是否正常？
5. 是否出现 None、empty、error、timeout？
6. 条件是否疑似被吞？
7. 是否适合进入 P1-P6？
8. 是否适合自然语言自动改写？
9. 如果失败，是哪个字段或哪个组合导致？

## 报告追加要求

长期报告必须保留历史，不要覆盖掉证据。

建议每次运行生成：

```text
query_lab/results/runs/run_YYYYMMDD_HHMMSS/
  query_results.jsonl
  failed_replay.jsonl
  run_summary.md
```

同时更新：

```text
query_lab/reports/stable_dictionary.md
query_lab/reports/risk_dictionary.md
query_lab/reports/parser_boundary_report.md
query_lab/reports/query_normalizer_rules.md
```

## Claude 实施提醒

不要为了“看起来完整”自行发明英文 Query。

如果用户提出一个新技术词，例如 JMA，而当前无法确认问财是否支持，必须：

1. 记录到 pending 队列。
2. 生成中文候选问法。
3. 小批量实测。
4. 标记风险。
5. 报告中说明它是否适合自动化。

不能直接把它放进 P1-P6 或默认策略。
