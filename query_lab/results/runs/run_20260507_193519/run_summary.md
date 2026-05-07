# QueryLab 运行报告 — run_20260507_193519

**生成时间**: 2026-05-07 19:37:11  
**路由**: sector  
**分组**: S9_return_enrichment  
**总条数**: 11  

## 状态统计

| 状态 | 数量 |
|------|------|
| stable / 稳定 | 3 |
| unstable / 不稳定 | 0 |
| risky / 高风险 | 4 |
| failed / 失败 | 4 |
| forbidden / 禁用 | 0 |
| invalid_query | 0 |
| pending | 0 |

## 失败类型分布

- `empty_result`: 4 条

## 失败与非法案例

- **[S9-001]** `今日涨幅排名前10的板块，上涨原因是什么` → `empty_result` [empty_result] 问财返回0条结果，条件可能过严或字段不被识别
- **[S9-009]** `军工板块领涨股` → `empty_result` [empty_result] 问财返回0条结果，条件可能过严或字段不被识别
- **[S9-010]** `军工板块中今日涨幅排名前10的股票` → `empty_result` [empty_result] 问财返回0条结果，条件可能过严或字段不被识别
- **[S9-011]** `今日涨幅排名前5的板块，然后查询每个板块中的今日涨幅排名前3股票` → `empty_result` [empty_result] 问财返回0条结果，条件可能过严或字段不被识别
