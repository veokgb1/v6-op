# V6OP-023 总纲缺口闭合开发包

> 指令发出：Codex / V6OP 新架构师  
> 执行对象：Claude / V6OP 新代码师  
> 工作目录：`F:\v.6\v6-op`  
> 报告路径：`F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-023_charter_gap_closure_development_report.md`

---

## 一、任务背景

V6OP-022 已按《v6-op_full_rescue_charter.md》第十三节完成第一阶段 15 条签收矩阵。但这不等于整篇总纲全部落地。Codex 复核总纲正文和当前代码后确认，仍有几块“总纲正文要求 / 实现原则 / 日常操盘体验”没有充分闭合。

本轮不是写报告轮，而是开发闭合轮。请优先修改代码和测试，只在最后写报告。

所有实现仍落在当前主链：

```text
source -> fetch_plan -> prefetch -> producer -> expression -> report
```

禁止引入 V5 Slot/漏斗旧架构，禁止照搬 V5.10；只复用其真实数据闭环经验。

---

## 二、本轮必须完成的 5 个开发项

### 1. 技能卡资产对齐：保留未接通技能，不能只显示 5 个本地技能

总纲第七章要求技能工具箱保留 V6 技能卡资产：已接通技能绿色可用，未接通技能灰色保留，metadata 完整保留。

当前现状：

- `scripts/skill_registry.py` 只有 6 个核心能力；
- `web/app.js` 的 `SKILL_META` 只显示 `czsc/smc/kline/wave/landmine`；
- V6 资产文件可见于：
  - `F:\v.6\v6\data\raw_skill_sample_cards.json`
  - `F:\v.6\v6\data\skill_connection_cards.json`
- Codex 初核发现这两个 JSON 当前可读条数为 22，不是总纲写的 27。不要假装 27 已存在，必须查明差异。

要求：

1. 新增或扩展 v6-op 的技能 metadata 装载层，不破坏现有 6 个核心能力执行逻辑。
2. 从 V6 技能卡资产中读取技能名称、状态、参数、命中方向、数据需求等可用 metadata。
3. 前端技能工具箱显示：
   - 已接通核心能力：可勾选、绿色/可用状态；
   - 未接通技能：灰色、不可勾选、标明“暂未接通”；
   - 不允许未接通技能进入执行 payload。
4. 若 V6 资产实际只有 22 条，报告中写清楚：总纲 27 与当前资产 22 的差异、缺少哪些、后续如何补资产。
5. 加测试确认：核心技能仍可执行；灰色技能不可执行；UI 不再只有 5 个技能卡。

### 2. 参数回显：上次使用值必须回到页面

总纲第十一章写明：“参数区不需要用户每次手动重填（上次使用的值默认回显）”。

当前 `web/app.js` 看不到 `localStorage/sessionStorage` 等参数保存机制。

要求：

1. 前端保存最近一次运行的：
   - source 类型；
   - wencai query/limit；
   - manual codes；
   - path type；
   - selected skills；
   - 各 skill 参数值。
2. 页面加载时自动回显上次使用值。
3. 提供“恢复默认参数”能力，避免旧参数困住用户。
4. 报告仍记录本次实际参数，不得记录默认值冒充实际值。
5. 加测试覆盖保存、回显、恢复默认、payload 使用回显后的真实值。

### 3. 内容寻址 Mask 复用：实现最小可用层

总纲第十章将内容寻址缓存定义为实现原则，不是后续页面功能。当前只有 `mask_id`，没有基于 `skill_id + scope_codes + params + data_date + algo_version` 的复用判断。

要求：

1. 给每个已接通 producer 增加稳定 `algo_version`。
2. 在 producer 执行前计算稳定 fingerprint：
   - `skill_id`
   - 排序后的 `scope_codes`
   - 排序序列化后的 `params`
   - `data_date` / `data_time_max`
   - `algo_version`
3. 增加最小持久化 Mask 缓存目录，例如 `output/mask_cache/` 或现有合理路径。
4. 命中缓存时可跳过 producer 重算，并在日志和 run_report 中显示 `mask_cache_hit=true`。
5. 数据日期、参数、代码池、算法版本任一变化时必须 miss。
6. 加测试覆盖 hit/miss/参数变化/data_time_max 变化/algo_version 变化。

注意：不要为了这个功能新建一套账本体系；它只是执行层内部复用能力。

### 4. 大样本预热验收：至少补齐 300 只性能/稳定性验收

总纲对象接力表写过：300 只股票能在 60 秒内完成预热（含缓存命中），并输出 `cache_hit/fetched_ok/failed`。

当前有 all_a 保护和小样本真实 wencai run，但没有看到 300 只真实/半真实大样本验收。

要求：

1. 增加一个可手动运行的验收脚本，例如 `scripts/verify_prefetch_300.py`。
2. 脚本支持：
   - 默认 limit=300；
   - workers=8；
   - 输出耗时、cache_hit、fetched_ok、recovered_count、failed、data_time_max；
   - 失败率和超时判断；
   - JSON 输出到 `output/verification/`。
3. 如果当前网络/baostock 环境无法稳定完成，不能伪造通过；要输出明确环境失败归因。
4. 单元测试只测脚本结构和小样本 dry-run，不强迫 CI 每次跑 300 网络请求。
5. 报告中必须区分“脚本能力已实现”和“本机真实 300 验收是否跑过、结果如何”。

### 5. 浏览器级操盘台验收：不要只靠静态 JS 检查

V6OP-022 的前端验收主要是静态测试和后端结果。总纲要求的是用户打开页面完成操盘。

要求：

1. 增加浏览器级 smoke 验收（Playwright 或项目中已有等价工具均可）。
2. 启动本地 `v6op_server.py`，打开 `web/index.html` 或服务首页。
3. 至少验证：
   - 技能工具箱渲染；
   - 灰色未接通技能不可勾选；
   - 参数回显生效；
   - 点击运行后日志区域实时出现“准备数据/预热/分析”类事件；
   - 运行完成后右侧结果区、预热摘要、失败/stale 区域可见。
4. 网络型 wencai 可作为可选验收；基础 smoke 可以用 manual 小股票池，避免环境不稳定。
5. 将截图或文字证据写入报告。

---

## 三、验收命令

完成后至少运行：

```powershell
pytest -q
node --check web/app.js
python scripts/verify_prefetch_300.py --limit 20 --workers 2 --json-out output/verification/v6op023_prefetch_smoke.json
```

如浏览器 smoke 需要单独命令，请在报告中写明完整命令和结果。

如果能跑真实 300，再额外运行：

```powershell
python scripts/verify_prefetch_300.py --limit 300 --workers 8 --json-out output/verification/v6op023_prefetch_300.json
```

不能跑真实 300 时，不准写“已通过 300 验收”，只能写“脚本已就绪，当前环境未完成真实 300”并给原因。

---

## 四、报告要求

报告必须写到：

```text
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-023_charter_gap_closure_development_report.md
```

报告必须包含：

1. 修改文件清单；
2. 5 个开发项逐项状态；
3. 总纲对应章节；
4. 测试命令与结果；
5. 真实 300 预热是否完成及证据；
6. V6 技能卡资产到底是 22 还是 27 的核对结论；
7. 剩余不能本轮闭合的事项，必须说明是否属于第一阶段、阶段 5+，或资产缺失。

签名：

```text
Claude / V6OP 新代码师
V6OP-023 总纲缺口闭合开发包
```
