# QueryLab 中文验收报告

**生成时间**: 2026-05-07  
**执行人**: Claude (run_query_lab.py)  
**环境**: F:\v.6\v6-op  Python 3.13.3  pywencai 0.13.1

---

## 1. 已建立的目录结构

```
query_lab/
  README.md
  registry/
    skills_registry.csv      6个技能登记（2个active，4个pending）
    fields_registry.csv      25个字段（F001-F020 A股，S001-S005 板块）
    query_templates.csv      10个模板
    status_rules.json        7种状态定义 + 流转规则
  cases/
    astock_问财选A股/
      A1_basic.csv           20条  基础单字段/时间/排除/技术
      A2_synonym.csv         15条  同义表达测试
      A3_combo.csv           7条   组合阶梯（1-7条件）
      A4_risky.csv           8条   高风险/危险词/JMA
      A5_forbidden.csv       3条   英文查询/空查询禁止案例
    sector_问财选板块/
      S1_basic.csv           10条  板块基础测试
      S2_synonym.csv         7条   板块同义表达
      S3_combo.csv           5条   板块组合阶梯
      S4_risky.csv           4条   板块危险词
    extensions/
      pending_queries.csv    7条   KDJ/MACD/JMA/BOLL/MA 待测队列
  scripts/
    run_query_lab.py         主入口
    query_runner.py          执行器
    result_analyzer.py       分类器
    report_writer.py         报告器
    canon_manager.py         法典管理
    canon_linter.py          法典 Linter
    canon_diff.py            法典 Diff
    canon_promote.py         法典发布
    canon_rollback.py        法典回滚
    validators/              中文预检 + Schema 校验
    adapters/                astock / sector / daily_kline / quote
  results/runs/              每次运行独立目录
  reports/                   稳定字典/风险字典/P1-P6/改写规则
  canon/                     法典骨架（空，等待 promote）
  tests/
    test_query_lab.py        49 个离线 pytest 测试
```

---

## 2. 已实现的程序入口

```powershell
# 离线测试（49个，全部通过）
.\.venv\Scripts\python.exe -m pytest query_lab\tests\test_query_lab.py -q

# 干跑列出将要跑的中文 Query
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py --dry-run --route all --limit 20

# 实测 A股
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py --route astock --group A1_basic --limit 20 --sleep-ms 1500

# 实测板块
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py --route sector --group S1_basic --limit 10 --sleep-ms 2000

# 法典治理
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py canon propose
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py canon lint
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py canon diff
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py canon promote --skill astock --reviewer "user" --reason "初次发布"
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py canon rollback --skill astock
```

---

## 3. 已跑通的离线测试

**49 个 pytest 测试，全部通过（49 passed in 0.08s）**

测试覆盖：
- `TestChineseQueryValidator`（9个）：中文预检、白名单缩写、英文整句拦截
- `TestSchemaValidator`（5个）：必须字段、skill_type、status 枚举
- `TestCaseFiles`（10个）：CSV 读取、中文 Query 校验、A股/板块分离、query_id 唯一性
- `TestResultAnalyzer`（8个）：stable/failed/risky/forbidden/invalid_query 分类
- `TestRegistry`（5个）：注册表文件、状态规则、白名单
- `TestCanonFiles`（6个）：法典文件、headers、目录结构
- `TestDryRun`（6个）：路由过滤、limit、group、adapter dry_run

---

## 4. 实测的 A股 Query 数量与板块 Query 数量

### A股实测（run_20260507_114221 + run_20260507_115402）

| 批次 | 组别 | 条数 | ok | api_error/empty | 备注 |
|------|------|------|-----|-----------------|------|
| run_20260507_114221 | A1_basic | 20 | 20 | 0 | 全部成功 |
| run_20260507_115402 | A2_synonym | 15 | 1 | 14 | session 耗尽后退化 |

**A股实测合计：35条，21条 ok，14条 api_error**

### 板块实测（run_20260507_115634）

| 批次 | 组别 | 条数 | ok | empty_result | 备注 |
|------|------|------|-----|--------------|------|
| run_20260507_115634 | S1_basic | 10 | 0 | 10 | 板块名称字段提取为空 |

**板块实测合计：10条，0条 ok，10条 empty_result**

---

## 5. stable / risky / failed / forbidden 统计

### A股（A1_basic 批次，20条全部 ok）

| 状态 | 数量 |
|------|------|
| stable / 稳定 | 20 |
| failed / 失败 | 0 |
| risky / 高风险 | 0 |
| forbidden / 禁用 | 0 |
| invalid_query | 0 |

### A股（A2_synonym 批次）

| 状态 | 数量 |
|------|------|
| stable / 稳定 | 1 |
| failed / 失败 | 14 |

### 板块（S1_basic 批次）

| 状态 | 数量 |
|------|------|
| failed / 失败（empty_result） | 10 |

---

## 6. 问财选A股的初步稳定说法

以下 20 条基础表达均在 A1_basic 中稳定返回（run_20260507_114221）：

| query_text | 返回数量 | 语义 |
|-----------|---------|------|
| 今日涨幅大于3% | 833 | 涨幅>3% |
| 今日涨幅大于5% | 368 | 涨幅>5% |
| 今日涨幅大于3%，非ST | 796 | 涨幅>3%且非ST |
| 今日成交额大于3亿 | 1325 | 成交额>3亿 |
| 今日成交额大于5亿 | 885 | 成交额>5亿 |
| 今日换手率大于5% | 700 | 换手率>5% |
| 今日换手率大于10% | 182 | 换手率>10% |
| 今日量比大于1.5 | 1442 | 量比>1.5 |
| 今日量比大于2 | 622 | 量比>2 |
| 流通市值在30亿到150亿之间 | 3036 | 流通市值30~150亿 |
| 流通市值在80亿到300亿之间 | 1578 | 流通市值80~300亿 |
| 总市值在50亿到300亿之间 | 2805 | 总市值50~300亿 |
| 今日主力净流入大于5000万 | 286 | 净流入>0.5亿 |
| 今日主力净流入大于1亿 | 149 | 净流入>1亿 |
| 今日主力净流入为正 | 2700 | 净流入>0 |
| 近5日涨幅大于10% | 694 | 近5日涨幅>10% |
| 近20日涨幅大于20% | 1185 | 近20日涨幅>20% |
| 非ST，非停牌 | 5241 | 排除ST和停牌 |
| 上市超过60天，非ST，非停牌 | 5212 | 排除ST停牌和新股 |
| 今日收盘价大于5日均线 | 4108 | 收盘>MA5 |

**初步结论：使用 `今日XX大于/小于/在...之间` 格式稳定。**

---

## 7. 问财选板块的初步稳定说法

**当前状态：全部 empty_result，无稳定说法。**

**失败分析**：
- 板块适配器先尝试 `query_type="sector"`，再 fallback `query_type="zhishu"`
- 两者均返回非空行但名称字段提取失败（~7秒响应）
- 问题可能在于 pywencai 0.13.1 的板块接口返回字段格式变化

**建议下一步**：
1. 手动检查 pywencai.get(query="今日涨幅大于3%的板块", query_type="sector") 的原始返回结构
2. 更新 `_extract_sector_names` 中的 `_NAME_FIELDS` 列表以匹配实际字段名
3. 增加原始返回行的 debug 日志

---

## 8. 失败案例和原因

### A2_synonym api_error（14条）

**根本原因**：pywencai session 在连续多次请求后耗尽。A1_basic 20条运行后，A2-002 开始的 46秒超时表明 session 正在刷新，之后退化为 3秒极速 api_error。

**处置建议**：
- 两批测试之间等待 5-10 分钟让 session 恢复
- 或在 adapter 中增加 session 重试逻辑
- 下次按照 A2 组单独运行，间隔 2-3 分钟每条

### S1_basic empty_result（10条）

**根本原因**：板块名称字段提取失败，pywencai 返回板块数据但字段名不匹配。

**处置建议**：
- 调试获取原始 rows 的字段名
- 更新 `wencai_sector_adapter._NAME_FIELDS`

---

## 9. 冲突报告

运行 `canon lint` 结果：**0 errors，0 warnings**

冲突文件：`canon/conflicts/conflict_report.md`（空）

---

## 10. 技能说法典候选更新

运行 `canon propose` 后，`canon/review_queue/candidate_changes.jsonl` 中共有：

**21 条候选变更（全部 change_type=add，skill=astock）**

候选条目（均来自 A1_basic 稳定实测）：
- 今日涨幅大于3%（×2，两次实测均通过）
- 今日涨幅大于5%
- 今日涨幅大于3%，非ST
- 今日成交额大于3亿 / 5亿
- 今日换手率大于5% / 10%
- 今日量比大于1.5 / 2
- 流通市值在30亿到150亿之间 / 80亿到300亿之间
- 总市值在50亿到300亿之间
- 今日主力净流入大于5000万 / 1亿 / 为正
- 近5日涨幅大于10%
- 近20日涨幅大于20%
- 非ST，非停牌
- 上市超过60天，非ST，非停牌
- 今日收盘价大于5日均线

**等待人工 `canon promote` 正式发布到 canon.csv。**

**板块法典**：当前无候选（sector 实测全部 empty_result）。

---

## 11. 下一轮建议测试项

### 优先修复

1. **板块 adapter 调试**：打印 pywencai 返回的原始字段名，修复 `_extract_sector_names`
2. **Session 管理**：A2_synonym 分批测试（每批 3-5 条，间隔 3 分钟）

### 下一层测试顺序

1. **A3_combo 组合阶梯**：从 1 条到 7 条逐步定位问财解析边界
2. **A1_basic 重跑 repeat=2**：验证稳定性（成功率 ≥ 80% 才能 promote 为 strong）
3. **A2_synonym 分批续跑**：确认哪些同义说法等价，哪些触发差异
4. **板块 S1_basic（修复后）**：验证板块基础问法
5. **A4_risky（危险词）**：确认模糊词实测行为

### 法典发布

在确认 A1_basic 两次以上稳定后，执行：

```powershell
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py canon promote --skill astock --reviewer "user" --reason "A1_basic 20条单次实测全部ok，pending正式发布"
```

### 追加新技能或新中文问法

1. 在 `cases/extensions/pending_queries.csv` 添加行（KDJ/MACD/JMA 已有7条占位）
2. 待测后移到对应 `cases/astock_问财选A股/AX_xxx.csv`
3. 运行 → 分析 → `canon propose` → `canon promote`
