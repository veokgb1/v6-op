# QueryLab 运行报告 — run_20260507_115634

**生成时间**: 2026-05-07 11:58:03  
**路由**: sector  
**分组**: S1_basic  
**总条数**: 10  

## 状态统计

| 状态 | 数量 |
|------|------|
| 稳定 stable | 0 |
| 不稳定 unstable | 0 |
| 高风险 risky | 0 |
| 失败 failed | 10 |
| 禁用 forbidden | 0 |
| 非法查询 invalid_query | 0 |
| 待测 pending | 0 |

## 板块查询结果 (问财选板块)

| query_id | 状态 | 结果数 | 耗时ms | query_text |
|----------|------|--------|--------|------------|
| S1-001 | failed | 0 | 0 | 今日涨幅大于3%的板块 |
| S1-002 | failed | 0 | 0 | 今日涨幅大于5%的板块 |
| S1-003 | failed | 0 | 0 | 今日成交额大于50亿的板块 |
| S1-004 | failed | 0 | 0 | 今日成交额大于100亿的板块 |
| S1-005 | failed | 0 | 0 | 今日主力净流入大于1亿的板块 |
| S1-006 | failed | 0 | 0 | 今日主力净流入为正的板块 |
| S1-007 | failed | 0 | 0 | 近5日涨幅最大的板块 |
| S1-008 | failed | 0 | 0 | 近20日涨幅大于10%的板块 |
| S1-009 | failed | 0 | 0 | 今日换手率大于3%的板块 |
| S1-010 | failed | 0 | 0 | 今日量比大于1.5的板块 |

## 失败与非法案例

- **[S1-001]** `今日涨幅大于3%的板块` → `empty_result`: 执行失败: empty_result  error=sector 和 zhishu 均无结果
- **[S1-002]** `今日涨幅大于5%的板块` → `empty_result`: 执行失败: empty_result  error=sector 和 zhishu 均无结果
- **[S1-003]** `今日成交额大于50亿的板块` → `empty_result`: 执行失败: empty_result  error=sector 和 zhishu 均无结果
- **[S1-004]** `今日成交额大于100亿的板块` → `empty_result`: 执行失败: empty_result  error=sector 和 zhishu 均无结果
- **[S1-005]** `今日主力净流入大于1亿的板块` → `empty_result`: 执行失败: empty_result  error=sector 和 zhishu 均无结果
- **[S1-006]** `今日主力净流入为正的板块` → `empty_result`: 执行失败: empty_result  error=sector 和 zhishu 均无结果
- **[S1-007]** `近5日涨幅最大的板块` → `empty_result`: 执行失败: empty_result  error=sector 和 zhishu 均无结果
- **[S1-008]** `近20日涨幅大于10%的板块` → `empty_result`: 执行失败: empty_result  error=sector 和 zhishu 均无结果
- **[S1-009]** `今日换手率大于3%的板块` → `empty_result`: 执行失败: empty_result  error=sector 和 zhishu 均无结果
- **[S1-010]** `今日量比大于1.5的板块` → `empty_result`: 执行失败: empty_result  error=sector 和 zhishu 均无结果
