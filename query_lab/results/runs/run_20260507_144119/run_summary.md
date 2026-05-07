# QueryLab 运行报告 — run_20260507_144119

**生成时间**: 2026-05-07 14:41:47  
**路由**: astock  
**分组**: A1_basic  
**总条数**: 5  

## 状态统计

| 状态 | 数量 |
|------|------|
| stable / 稳定 | 4 |
| unstable / 不稳定 | 0 |
| risky / 高风险 | 0 |
| failed / 失败 | 1 |
| forbidden / 禁用 | 0 |
| invalid_query | 0 |
| pending | 0 |

## 失败类型分布

- `empty_result`: 1 条

## A股查询结果

| query_id | 状态 | 失败类型 | 结果数 | 耗时ms | query_text |
|----------|------|---------|--------|--------|------------|
| A1-001 | stable | none | 100 | 2572 | 今日涨幅大于3% |
| A1-002 | stable | none | 100 | 1545 | 今日涨幅大于5% |
| A1-003 | stable | none | 100 | 1804 | 今日涨幅大于3%，非ST |
| A1-004 | stable | none | 100 | 1492 | 今日成交额大于3亿 |
| A1-005 | failed | empty_result | 0 | 5292 | 今日成交额大于5亿 |

## 失败与非法案例

- **[A1-005]** `今日成交额大于5亿` → `empty_result` [empty_result] 问财返回0条结果，条件可能过严或字段不被识别
