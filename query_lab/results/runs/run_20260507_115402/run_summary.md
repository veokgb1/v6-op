# QueryLab 运行报告 — run_20260507_115402

**生成时间**: 2026-05-07 11:56:10  
**路由**: astock  
**分组**: A2_synonym  
**总条数**: 15  

## 状态统计

| 状态 | 数量 |
|------|------|
| 稳定 stable | 1 |
| 不稳定 unstable | 0 |
| 高风险 risky | 0 |
| 失败 failed | 14 |
| 禁用 forbidden | 0 |
| 非法查询 invalid_query | 0 |
| 待测 pending | 0 |

## A股查询结果 (问财选A股)

| query_id | 状态 | 结果数 | 耗时ms | query_text |
|----------|------|--------|--------|------------|
| A2-001 | stable | 833 | 18279 | 今日涨幅大于3% |
| A2-002 | failed | 0 | 0 | 今天涨幅大于3% |
| A2-003 | failed | 0 | 0 | 涨幅大于3% |
| A2-004 | failed | 0 | 0 | 涨幅超过3% |
| A2-005 | failed | 0 | 0 | 涨幅高于3% |
| A2-006 | failed | 0 | 0 | 今日涨幅超过3% |
| A2-007 | failed | 0 | 0 | 今日涨幅3%以上 |
| A2-008 | failed | 0 | 0 | 今天上涨超过3% |
| A2-009 | failed | 0 | 0 | 今日成交额大于3亿 |
| A2-010 | failed | 0 | 0 | 今日成交金额大于3亿 |
| A2-011 | failed | 0 | 0 | 今日成交额超过3亿 |
| A2-012 | failed | 0 | 0 | 今日成交额3亿以上 |
| A2-013 | failed | 0 | 0 | 今日主力净流入为正 |
| A2-014 | failed | 0 | 0 | 主力资金净流入为正 |
| A2-015 | failed | 0 | 0 | 今日主力资金流入 |

## 失败与非法案例

- **[A2-002]** `今天涨幅大于3%` → `api_error`: 执行失败: api_error  error='NoneType' object has no attribute 'get'
- **[A2-003]** `涨幅大于3%` → `api_error`: 执行失败: api_error  error='NoneType' object has no attribute 'get'
- **[A2-004]** `涨幅超过3%` → `api_error`: 执行失败: api_error  error='NoneType' object has no attribute 'get'
- **[A2-005]** `涨幅高于3%` → `api_error`: 执行失败: api_error  error='NoneType' object has no attribute 'get'
- **[A2-006]** `今日涨幅超过3%` → `api_error`: 执行失败: api_error  error='NoneType' object has no attribute 'get'
- **[A2-007]** `今日涨幅3%以上` → `api_error`: 执行失败: api_error  error='NoneType' object has no attribute 'get'
- **[A2-008]** `今天上涨超过3%` → `api_error`: 执行失败: api_error  error='NoneType' object has no attribute 'get'
- **[A2-009]** `今日成交额大于3亿` → `api_error`: 执行失败: api_error  error='NoneType' object has no attribute 'get'
- **[A2-010]** `今日成交金额大于3亿` → `api_error`: 执行失败: api_error  error='NoneType' object has no attribute 'get'
- **[A2-011]** `今日成交额超过3亿` → `api_error`: 执行失败: api_error  error='NoneType' object has no attribute 'get'
- **[A2-012]** `今日成交额3亿以上` → `api_error`: 执行失败: api_error  error='NoneType' object has no attribute 'get'
- **[A2-013]** `今日主力净流入为正` → `api_error`: 执行失败: api_error  error='NoneType' object has no attribute 'get'
- **[A2-014]** `主力资金净流入为正` → `api_error`: 执行失败: api_error  error='NoneType' object has no attribute 'get'
- **[A2-015]** `今日主力资金流入` → `api_error`: 执行失败: api_error  error='NoneType' object has no attribute 'get'
