# QueryLab 运行报告 — run_20260507_152032

**生成时间**: 2026-05-07 15:22:09  
**路由**: astock  
**分组**: A4_risky  
**总条数**: 8  

## 状态统计

| 状态 | 数量 |
|------|------|
| stable / 稳定 | 0 |
| unstable / 不稳定 | 0 |
| risky / 高风险 | 2 |
| failed / 失败 | 1 |
| forbidden / 禁用 | 5 |
| invalid_query | 0 |
| pending | 0 |

## 失败类型分布

- `api_error`: 1 条

## A股查询结果

| query_id | 状态 | 失败类型 | 结果数 | 耗时ms | query_text |
|----------|------|---------|--------|--------|------------|
| A4-001 | risky | none | 100 | 3130 | 今日换手率大于近5日平均换手率的1.5倍 |
| A4-002 | failed | api_error | 0 | 45000 | 今日成交额大于近5日平均成交额的1.5倍 |
| A4-003 | forbidden | none | 14 | 1885 | 强势股 |
| A4-004 | forbidden | none | 100 | 1950 | 放量上涨股票 |
| A4-005 | forbidden | none | 100 | 1343 | 短线龙头股 |
| A4-006 | forbidden | none | 19 | 2144 | 明天可能上涨的股票 |
| A4-007 | forbidden | none | 0 | 7590 | 有可能涨停的股票 |
| A4-008 | risky | none | 100 | 1837 | 收盘价站上JMA均线 |

## 失败与非法案例

- **[A4-002]** `今日成交额大于近5日平均成交额的1.5倍` → `api_error` [api_error] 问财 API 接口异常（session 耗尽 / 网络 / 认证失败）
