# QueryLab 运行报告 — run_20260507_185554

**生成时间**: 2026-05-07 18:56:42  
**路由**: sector  
**分组**: S7_low_reversal  
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

## 失败与非法案例

- **[S7-004]** `近5日主力净流入小于0，今日主力净流入大于0的板块` → `empty_result` [empty_result] 问财返回0条结果，条件可能过严或字段不被识别
