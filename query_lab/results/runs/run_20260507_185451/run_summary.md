# QueryLab 运行报告 — run_20260507_185451

**生成时间**: 2026-05-07 18:55:48  
**路由**: sector  
**分组**: S6_two_step  
**总条数**: 6  

## 状态统计

| 状态 | 数量 |
|------|------|
| stable / 稳定 | 0 |
| unstable / 不稳定 | 0 |
| risky / 高风险 | 2 |
| failed / 失败 | 4 |
| forbidden / 禁用 | 0 |
| invalid_query | 0 |
| pending | 0 |

## 失败类型分布

- `empty_result`: 4 条

## 失败与非法案例

- **[S6-001]** `人工智能板块龙头股` → `empty_result` [empty_result] 问财返回0条结果，条件可能过严或字段不被识别
- **[S6-004]** `人工智能板块中今日涨幅排名前10的股票` → `empty_result` [empty_result] 问财返回0条结果，条件可能过严或字段不被识别
- **[S6-005]** `人工智能板块中今日成交额排名前10的股票` → `empty_result` [empty_result] 问财返回0条结果，条件可能过严或字段不被识别
- **[S6-006]** `人工智能板块中今日主力净流入排名前10的股票` → `empty_result` [empty_result] 问财返回0条结果，条件可能过严或字段不被识别
