# QueryLab 运行报告 — run_20260507_152351

**生成时间**: 2026-05-07 15:24:00  
**路由**: astock  
**分组**: A5_forbidden  
**总条数**: 3  

## 状态统计

| 状态 | 数量 |
|------|------|
| stable / 稳定 | 0 |
| unstable / 不稳定 | 0 |
| risky / 高风险 | 0 |
| failed / 失败 | 0 |
| forbidden / 禁用 | 0 |
| invalid_query | 3 |
| pending | 0 |

## 失败类型分布

- `invalid_query`: 3 条

## A股查询结果

| query_id | 状态 | 失败类型 | 结果数 | 耗时ms | query_text |
|----------|------|---------|--------|--------|------------|
| A5-001 | invalid_query | invalid_query | 0 | 0 | A-shares with market cap between 3 and 15 billion |
| A5-002 | invalid_query | invalid_query | 0 | 0 | stocks with volume ratio greater than 2 |
| A5-003 | invalid_query | invalid_query | 0 | 0 |  |

## 失败与非法案例

- **[A5-001]** `A-shares with market cap between 3 and 15 billion` → `invalid_query` [invalid_query] 中文预检失败：query_text 不含中文或含英文整句
- **[A5-002]** `stocks with volume ratio greater than 2` → `invalid_query` [invalid_query] 中文预检失败：query_text 不含中文或含英文整句
- **[A5-003]** `` → `invalid_query` [invalid_query] 中文预检失败：query_text 不含中文或含英文整句
