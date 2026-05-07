# QueryLab 运行报告 — run_20260507_185649

**生成时间**: 2026-05-07 18:58:01  
**路由**: sector  
**分组**: S8_return_contract  
**总条数**: 8  

## 状态统计

| 状态 | 数量 |
|------|------|
| stable / 稳定 | 3 |
| unstable / 不稳定 | 0 |
| risky / 高风险 | 2 |
| failed / 失败 | 3 |
| forbidden / 禁用 | 0 |
| invalid_query | 0 |
| pending | 0 |

## 失败类型分布

- `empty_result`: 3 条

## 失败与非法案例

- **[S8-004]** `今日最强板块` → `empty_result` [empty_result] 问财返回0条结果，条件可能过严或字段不被识别
- **[S8-005]** `军工板块龙头股` → `empty_result` [empty_result] 问财返回0条结果，条件可能过严或字段不被识别
- **[S8-006]** `军工板块中今日涨幅排名前10的股票` → `empty_result` [empty_result] 问财返回0条结果，条件可能过严或字段不被识别
