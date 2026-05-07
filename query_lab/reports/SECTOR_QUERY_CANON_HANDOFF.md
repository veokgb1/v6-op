# SECTOR_QUERY_CANON_HANDOFF

> 问财选板块 查询法典交接文件

**实测日期**: 2026-05-07  
**纳入 run_id**:
- S1: run_20260507_184927
- S2: run_20260507_185040
- S3: run_20260507_185133
- S4: run_20260507_185212
- S5: run_20260507_185404
- S6: run_20260507_185451
- S7: run_20260507_185554
- S8: run_20260507_185649
- S9: run_20260507_193519

---

## 1. 各组结论摘要

| 组别 | 条数 | 结论 |
|------|------|------|
| S1_basic | 10 | **全部 stable**。涨幅/成交额/净流入/换手率/量比/近5日/近20日涨幅 均可用 |
| S2_synonym | 7 | **全部 stable**。今日/今天/板块前置/超过=大于/主力资金=主力净流入 均等价 |
| S3_combo | 5 | **全部 stable**。1→5 条件组合均稳定，条件天花板 ≥5 |
| S4_risky | 4 | **全部 forbidden**。热门/强势→空；主线/可能爆发→返回但不可信 |
| S5_emotion | 6 | **5 stable 1 risky**。上涨家数/涨停家数/情绪组合可用；连板字段 risky |
| S6_two_step | 6 | **4 failed 2 risky**。板块内股票查询全部失败；must_split=true |
| S7_low_reversal | 5 | **4 stable 1 failed**。低位回流组合可用；同字段双窗口比较不支持 |
| S8_contract | 8 | **3 stable 2 risky 3 failed**。TOP-N 稳定；龙头股/最强/板块内股票失败 |
| S9_return_enrichment | 11 | **3 stable 4 risky 4 failed**。上涨原因不可返回；指数字段默认包含；`领涨股`可触发股票名 |

---

## 2. 最短稳定问法（地板）

```text
今日涨幅大于3%的板块
今日成交额大于50亿的板块
今日主力净流入为正的板块
今日涨幅排名前10的板块
今日涨停家数大于3的板块
```

---

## 3. stable 清单摘要

**基础字段**（均稳定）：
- 今日涨幅、成交额、主力净流入、换手率、量比
- 近5日涨幅、近20日涨幅、近60日涨幅（配合今日条件）
- 今日涨停家数、上涨家数

**组合条件**：中文逗号分隔，1-5条均稳定

**同义词**（均等价）：今日=今天，大于=超过，主力净流入=主力资金净流入，板块前后置均可

**情绪指标**：上涨家数排名前N、涨停家数排名前N、涨停家数大于N、换手率+涨停双排名

**低位回流**：近60日涨幅<N% + 今日涨幅/净流入/成交额（跨窗口两字段组合均稳定）

---

## 4. risky 清单摘要

| 问法 | 风险点 |
|------|-------|
| 连板股最多的板块 | 非标准字段，结果不可信 |
| 主线板块 | 有返回但是全市场默认，不代表市场主线 |
| 可能爆发的板块 | 有返回但语义不可预期 |
| 今日最强 / 值得关注 | 返回模糊默认列表 |
| 条件+中的龙头股 | sector 忽略"龙头股"，仍返回板块列表 |

---

## 5. forbidden 清单摘要

**truly_forbidden**（直接返回空）：
```
热门板块  强势板块  最强板块
X板块龙头股  X板块中的股票
```

**semantic_forbidden**（有返回但不可信）：
```
主线板块  可能爆发的板块  哪些板块值得关注
```

**must_split**（需要拆成两步）：
```
X板块中今日涨幅排名前N的股票
X板块中今日成交额排名前N的股票
今日最强板块中的前排股
```

---

## 6. sector vs zhishu backend 实际表现

| backend | 结果 |
|---------|------|
| sector（pywencai sector 路由） | **从未独立返回结果**。所有成功查询均由 zhishu 路由完成 |
| zhishu（pywencai zhishu 路由） | 所有 38 条成功查询的实际后端 |
| sector+zhishu_fallback | 13 条失败查询（两者均无结果） |

**结论**：adapter 的 sector→zhishu fallback 策略正确且必要。zhishu 是问财选板块的真实工作路由。

---

## 7. 返回内容分类统计

| return_object_type | S1-S8 数量 | S9 数量 | pipeline 接法 |
|-------------------|------------|---------|--------------|
| sector_only | 38 | 0 | sector_to_phase_b（接入问财选A股） |
| sector_with_index_fields | 0 | 7 | sector_to_phase_b（含指数代码/行情字段，可接 Phase B） |
| sector_with_reason | 0 | 0 | sector_to_phase_b（含原因列，理论上存在） |
| empty_or_error | 13 | 4 | failed（记录，不进入 pipeline） |
| stock_only | 0 | 0 | （理论）stock_to_local_skill |
| mixed_sector_stock | 0 | 0 | （理论）review + 拆分 |

**注意**：S9 的 7 条 `sector_with_index_fields` 结果，实际数据结构与 S1-S8 的 `sector_only` 相同（zhishu 始终返回指数字段）。S1-S8 使用旧版 adapter，未检测 index fields；S9 使用新版 adapter（Step 0 修复后），正确分类为 `sector_with_index_fields`。

---

## 8. 每种返回类型的 pipeline 接法

### sector_only / sector_with_index_fields → Phase B（推荐）

两种类型接法相同。zhishu backend 始终含指数字段；adapter 版本决定分类标签。

```text
Step 1 sector:
  问法: "今日涨幅排名前5的板块"
  返回: ["通信线缆及配套", "机床工具", "激光设备", "光纤概念", "小红书概念"]

Step 2 astock（对每个板块）:
  问法: "通信线缆及配套板块，今日收盘价大于5日均线，主力净流入大于0的股票"
  返回: A股代码列表 → 进入本地技能
```

**注意**：Phase B 的 astock 查询中，板块名作为前缀条件，不是再次调用 sector。

### sector_with_index_fields + 领涨股 → 含领涨股名的板块列表

```text
Step 1 sector（含领涨股）:
  问法: "今日涨幅排名前5的板块及其领涨股"
  返回:
    板块名: ["通信线缆及配套", "机床工具", "激光设备", ...]
    领涨股简称: ["通鼎互联", "宇环数控", "大族激光", ...]（每板块1只）

Step 2 可选-astock（按领涨股名查询）:
  问法: "通鼎互联，今日涨幅、主力净流入"
  返回: 该股数据（注意简称可能重名，建议验证代码）
```

**限制**：只有1只领涨股/板块；只有`领涨股`能触发（`龙头股`无效）；指定板块名+领涨股直接失败。

### empty_or_error → failed

不进入 pipeline。记录失败原因后，可以：
1. 简化条件重试
2. 拆成两步
3. 手动跳过

### stock_only（未出现，理论接法）

直接进入本地技能：kline / smc / wave / landmine。  
**不可**再送回问财选A股（A12 已确认代码池复问不支持）。

### mixed_sector_stock（未出现，理论接法）

拆开：板块名进 Phase B，股票代码进本地技能。标记 review，不自动运行完整 pipeline。

---

## 9. 推荐给策略台/输入工坊的标准板块 Query 生成格式

```text
格式：{时间窗口}{字段}{运算符}{阈值或排名}的板块[，{条件2}，...]

示例：
  今日涨幅大于3%的板块
  今日成交额排名前10的板块
  今日主力净流入为正，今日涨幅大于2%的板块
  近60日涨幅小于20%，今日涨幅大于3%的板块
  今日涨停家数大于3的板块，今日主力净流入为正
```

**分隔符**：中文逗号（，）推荐

**不建议自动生成的说法**：
```text
热门板块  强势板块  主线板块  最强板块
龙头（作为 sector 内条件，不触发领涨股列）
板块中的股票（需走 astock）
值得关注  可能爆发  未来
上涨原因是什么（KILLS QUERY，返回空）
原因是什么  资金流入原因是什么（reason_query_ignored，无意义）
指定板块名+领涨股（如"军工板块领涨股"，直接失败）
两步嵌套（如"TOP5板块，然后查询每个板块中的TOP3股票"，直接失败）
```

---

## 10. 后续新增板块问法操作指引

- **新增稳定问法** → 修改 `query_lab/cases/sector_问财选板块/S1_basic.csv` 或对应主题 CSV
- **新增同义词测试** → 修改 `S2_synonym.csv`
- **新增组合测试** → 修改 `S3_combo.csv`
- **新增风险词测试** → 修改 `S4_risky.csv`
- **新增情绪/涨停类** → 修改 `S5_emotion_style.csv`
- **新增必须拆分的问题** → 修改 `S6_two_step.csv`
- **新增低位回流结构** → 修改 `S7_low_reversal.csv`
- **新增返回类型验证** → 修改 `S8_return_contract.csv`
- **新增返回增强补测（原因/指数字段/领涨股）** → 修改 `S9_return_enrichment.csv`

运行命令（以 S1 为例）：
```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 `
  -Action start -Route sector -Group S1_basic -Limit 0 `
  -SleepMs 3000 -FetchLimit 20 -QueryTimeoutSec 45
```

先看报告：`query_lab/reports/sector_ceiling_report.md`

---

## 验收确认

- [x] S1-S4 全部有完整 run
- [x] S5-S8 全部有完整 run
- [x] S9 return_enrichment 有完整 run（run_20260507_193519，11 条）
- [x] return_object_type 字段已落盘（sector_adapter 修复后）
- [x] 每条结果有耗时、返回数量、backend、板块名样例、股票代码样例（均空）、返回对象类型
- [x] 明确区分"返回板块"（sector_only/sector_with_index_fields）和"返回股票"（未出现）
- [x] 明确：sector_only/sector_with_index_fields 接 Phase B，stock_only 接本地技能，mixed 需拆分审阅
- [x] 不把 A 股代码（88xxxx 指数代码）误判成板块字段（已修复过滤）
- [x] 上涨原因类查询行为已验证：`上涨原因是什么` KILLS QUERY；`原因是什么` reason_query_ignored
- [x] `领涨股`触发 `指数@领涨股简称` 列已验证（S9-007 实测：通鼎互联/宇环数控/大族激光）
- [x] `龙头股` 无效，不触发领涨股列（S9-008 实测）
- [x] 不自动 promote
- [x] 最终报告能让用户直接知道：板块扫描提示词怎么写、哪些不要写、返回后接哪里
