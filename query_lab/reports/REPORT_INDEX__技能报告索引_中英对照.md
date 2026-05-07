# QueryLab Report Index / 技能报告索引

这个索引用来解决“报告文件名看不出对应哪个技能”的问题。

原则：

- 根目录下保留原英文文件，避免破坏旧引用和程序路径。
- 人看的报告放进技能目录，文件名统一为 `英文技能名_中文技能名__英文用途_中文用途`。
- 以后新增报告也按这个方式落盘。

## 问财选A股 / ASTOCK

目录：

```text
query_lab/reports/ASTOCK_问财选A股/
```

主要文件：

```text
ASTOCK_问财选A股__QUERY_CANON_HANDOFF_法典交接.md
ASTOCK_问财选A股__CEILING_REPORT_地板天花板.md
ASTOCK_问财选A股__A1_A10_CONSOLIDATED_阶段整理.md
ASTOCK_问财选A股__A1_A10_CLEAN_DICTIONARY_干净法典候选.csv
ASTOCK_问财选A股__A1_A10_CLEAN_DICTIONARY_干净法典候选.json
ASTOCK_问财选A股__RETURN_CONTRACT_返回契约.md    ← 新增（2026-05-07）
```

用途：

- 看最终结论：先看 `QUERY_CANON_HANDOFF_法典交接`
- 看地板/天花板：看 `CEILING_REPORT_地板天花板`
- 看 A1-A10 阶段整理：看 `A1_A10_CONSOLIDATED_阶段整理`
- 看结构化候选：看 `CLEAN_DICTIONARY_干净法典候选`
- 看返回字段（代码/名称/价格/因子）：看 `RETURN_CONTRACT_返回契约`

## 问财选板块 / SECTOR

目录：

```text
query_lab/reports/SECTOR_问财选板块/
```

主要文件：

```text
SECTOR_问财选板块__FLOOR_CEILING_FINAL_SUMMARY_地板天花板最终摘要.md
SECTOR_问财选板块__QUERY_CANON_HANDOFF_法典交接.md
SECTOR_问财选板块__RETURN_CONTRACT_返回契约.md
SECTOR_问财选板块__S9_RETURN_ENRICHMENT_返回增强.md
SECTOR_问财选板块__CEILING_REPORT_地板天花板.md
SECTOR_问财选板块__STABLE_DICTIONARY_稳定问法字典.md
SECTOR_问财选板块__RISK_DICTIONARY_风险问法字典.md
SECTOR_问财选板块__FORBIDDEN_DICTIONARY_禁问字典.md
```

用途：

- 看最终收口：先看 `FLOOR_CEILING_FINAL_SUMMARY_地板天花板最终摘要`
- 看交接给后续开发/Claude：看 `QUERY_CANON_HANDOFF_法典交接`
- 看返回了什么：看 `RETURN_CONTRACT_返回契约`
- 看原因/指数/领涨股补测：看 `S9_RETURN_ENRICHMENT_返回增强`
- 看稳定/风险/禁问清单：看三个 dictionary 文件

## 命名规则

以后所有技能报告建议命名：

```text
{EN_SKILL}_{中文技能名}__{EN_PURPOSE}_{中文用途}.md
```

示例：

```text
QUOTE_实时行情__RETURN_CONTRACT_返回契约.md
DAILY_KLINE_日线行情__CEILING_REPORT_地板天花板.md
MACD_MACD指标__STABLE_DICTIONARY_稳定问法字典.md
```

## 根目录报告 / Root Reports

```text
query_lab/reports/astock_return_contract_report.md   ← 问财选A股返回契约（2026-05-07）
query_lab/reports/ASTOCK_QUERY_CANON_HANDOFF.md
query_lab/reports/astock_ceiling_report.md
query_lab/reports/stable_dictionary.md
query_lab/reports/risk_dictionary.md
query_lab/reports/forbidden_dictionary.md
query_lab/reports/SECTOR_QUERY_CANON_HANDOFF.md
query_lab/reports/sector_return_contract_report.md
query_lab/reports/sector_s9_return_enrichment_report.md
```

## 注意

当前目录里的双语文件是给人看的归档副本。程序和旧工单仍可继续引用根目录英文文件。
