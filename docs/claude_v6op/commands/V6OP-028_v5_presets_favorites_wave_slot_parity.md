# V6OP-028 V5 预设/收藏/波浪 Slot 参数对齐

> 指令发出：Codex / V6OP 架构协同  
> 执行对象：Claude / V6OP 前端与联调工程师  
> 工作目录：`F:\v.6\v6-op`  
> 对照旧版：`F:\v.6\v5.10\web\index.html`  
> 建议报告：`F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-028_v5_presets_favorites_wave_slot_parity_report.md`

---

## 零、用户最新补充：以本节为准

### 执行模式修正：先审计，不要直接硬搬

用户当前担心：V5 的问财板块联动如果“硬生生拉进来”，可能绕开 V6OP 已经建立好的来源解析、技能门禁、readiness、缓存、报告和执行链路。

因此本任务第一步必须改为：

```text
先做只读审计和接入方案，不直接写代码。
```

Claude 第一轮只允许：

1. 阅读 V5 的板块联动逻辑；
2. 阅读 V6OP 的来源解析和执行链路；
3. 判断板块联动应该接在 V6OP 哪一层；
4. 给出最小安全实现方案；
5. 列出需要改哪些文件、哪些接口、哪些测试；
6. 写审计报告。
7. 一并审计 V5 的扫描档位和启动区操作按钮，判断哪些能直接映射到 V6OP，哪些需要新增后端接口。

第一轮禁止：

```text
不要直接迁移 V5 代码
不要直接新增 /api/scan_sectors
不要直接改 source_resolver / execution_engine
不要改现有运行链路
不要把板块联动做成绕过 V6OP 主链的旁路
不要只复制 V5 按钮外观而不接真实动作
```

审计报告写到：

```text
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-028_sector_linkage_audit_report.md
```

等用户和 Codex 看完审计报告后，再决定是否进入实现阶段。

### 扫描档位与启动区也要纳入审计

用户补充：V6OP 现在的“最多只数 500”不符合真实选股习惯。V5 不是随手填 500，而是用扫描档位控制规模：

```text
SAFE   100 只（轻量测试）
STABLE 300 只（推荐）
TEST   500 只
PRO    1000 只
PRO    2000 只
PRO    5000 只（完整扫描）
```

Claude 需要审计并说明：

1. V6OP 的 `all_a` / `wencai` 是否都应该改为 V5 这种扫描档位；
2. `wencai` 的真实 API 返回是否支持 1000/2000/5000，是否存在服务端硬上限；
3. “完整扫描”应该如何提示风险、如何要求用户确认；
4. 扫描档位最终应如何写入 `strategy.source.limit`；
5. 是否保留手动数字输入，还是改为档位选择 + 高级自定义。

V5 启动区按钮也要审计：

```text
启动管道
断点续跑
中止运行
查看报告
清理缓存
清空日志
```

当前 V6OP 已有：

```text
POST /api/run
GET  /api/result
GET  /api/stream
```

但当前 V6OP 未发现这些 V5 等价接口：

```text
/api/resume
/api/clear/cache
/api/clear/logs
/api/abort 或 /api/stop
/api/reports 历史报告列表
```

第一轮审计必须判断：

1. 哪些按钮可以纯前端实现；
2. 哪些按钮需要新增后端接口；
3. 哪些按钮需要 execution_engine 支持合作式中止；
4. 断点续跑是否应复用上一轮 `source` 股票池，再从技能漏斗开始；
5. 清理缓存具体应清理哪些目录，不能误删用户文件；
6. 清空日志是否只清屏，还是同时删除 `logs/`；
7. 查看报告是打开当前 `run_report.md`，还是做 V5 那样的历史报告选择器。

本轮仍然先审计，不直接实现这些按钮。

本轮主目标调整为：优先把 V5 的 `Slot 1 - 问财联动漏斗` 搬回 V6OP。

### 波浪纠偏：本轮不要改波浪展开逻辑

用户已确认：波浪这块不要做固定参数块，不要改后端算法，不要改参数调用。

保持当前逻辑即可：

```text
勾选波浪 -> 展开参数
不勾选波浪 -> 不展开参数
```

这和 SMC、缠论等技能一致，当前交互是可以接受的。

本轮对波浪只允许做一个小 UI 修正：

```text
去掉“辅助”两个字
去掉波浪旁边的黄色/橙色辅助标签
不要再显示“弱信号”
```

除此之外，后文凡是提到“波浪固定参数块”“Slot 6 固定波浪参数”的要求均作废，不执行。

必须包含：

1. `个股模式` / `板块联动` 两个模式；
2. P1-P6 预设策略；
3. Phase A 板块扫描语句；
4. Phase A 板块提示词收藏；
5. Phase A 扫描热点板块按钮；
6. Phase A 扫出 1-10 个左右板块后，用户可勾选确认其中若干个；
7. Phase B 个股筛选语句，板块名自动前置或注入；
8. Phase B 问财选股提示词收藏；
9. 已确认板块必须能向下传给后续技能漏斗；
10. 逻辑和 V5 保持一致，不只是页面长得像。

V5 参考点：

```text
F:\v.6\v5.10\web\index.html
setSlot1Mode('sector')
scanSectors()
selectAllSectors()
confirmSectors()
openclaw_v5_favorites
openclaw_v5_sector_favorites
```

执行前必须先读 V5 这一段逻辑，不要凭想象重写：

```text
F:\v.6\v5.10\web\index.html
约 710-820 行：P1-P6、个股模式/板块联动、Phase A/Phase B 页面结构
约 1118-1180 行：PRESET_QUERIES、SLOT_OPTIONS、初始化
约 1329-1468 行：setSlot1Mode、scanSectors、selectAllSectors、confirmSectors
约 1490-1540 行：运行前 params 注入 confirmed_sectors
约 2199-2388 行：问财收藏、板块提示词收藏
```

可以照抄 V5 的行为逻辑，但不要机械照抄拥挤版面。V6OP 页面更窄，布局要略微优化。

版面要求：

1. `个股模式 / 板块联动` 用清晰的双按钮或 segmented control；
2. Phase A 和 Phase B 分成两个小节，标题短，输入框不要太高；
3. 收藏下拉、收藏按钮、删除按钮尽量放一行；
4. “取前 N 个”与“扫描热点板块”放在同一操作区；
5. 扫描结果 checklist 可以折叠或限制高度滚动，避免把后面的技能漏斗挤没；
6. 已确认板块用一行 chips/tag 展示，太多时换行或省略；
7. 不要新增大段解释文字，保留必要标签即可。

本轮优先级改为：

```text
板块联动 Phase A/B > 两套收藏 > P1-P6 > 方案保存 > 去掉波浪辅助标签
```

波浪说明：

```text
波浪算法和后端调用本轮不用改。
波浪参数仍保持勾选后展开。
只去掉“辅助/弱信号/黄色标签”这类误导性显示。
```

---

## 一、先给结论

这轮不是重写选股主链，也不是接第二阶段灰色技能。

目标是把 V6OP 左侧操作区向 V5 的可操作习惯对齐：

1. 波浪分析的 V5 三个调参项要像 V5 一样明确显示，不能让用户以为没有接上；
2. P1-P6 预设策略要放进 V6OP；
3. 问财语句收藏要放进 V6OP；
4. 技能顺序、技能选择、常用参数要继续可保存；
5. 如果能低风险实现，再补“技能收藏/方案收藏”，让用户不用每次重新勾选。

---

## 二、原因分析

### 1. 波浪不是没有正确引用

V5 里波浪过滤是：

```text
BUILTIN-WAVE = 艾略特波浪过滤（内置）
```

V5 传给波浪过滤的三个参数是：

```text
wave-swing -> swing_window
wave-fib   -> fib_tolerance
wave-bars  -> signal_bars
```

V6OP 当前已经有同名后端参数：

```text
params.skills.wave.swing_window
params.skills.wave.fib_tolerance
params.skills.wave.signal_bars
```

并且后端会从 `scripts/execution_engine.py` 传给 `scripts/producers/wave_producer.py`。

所以问题不是“波浪 filter 没接上”，而是 UI 展示方式和 V5 差太远。

### 2. 图一为什么看不到三个参数

V6OP 当前做法是“技能卡片内联参数”：

```text
波浪分析没有勾选 -> 参数面板隐藏
波浪分析勾选     -> 参数面板才显示
```

V5 做法是“Slot 固定参数区”：

```text
Slot 6 - 波浪参数一直在下面
用户天然知道 Swing窗口 / Fib容差 / 波浪回看 是波浪过滤的参数
```

用户截图里波浪分析未勾选，所以 V6OP 没显示参数。这是可用性问题，不是算法引用问题。

### 3. V6OP 还多了两个参数

V6OP 当前波浪参数比 V5 多：

```text
min_wave_bars = 每浪最少K线
days          = K线回看
```

建议默认界面先对齐 V5 三件套：

```text
Swing窗口
Fib容差
波浪回看
```

`每浪最少K线` 和 `K线回看` 可以放到“高级参数”里，或者先保留在展开区域，但不要挤乱 V5 用户熟悉的主操作区。

---

## 三、必须完成

### 1. 加回 P1-P6 预设策略

在 V6OP 左侧股票来源区域上方或问财区域内增加：

```text
预设策略 select
```

选项必须包括：

```text
P1 核心中军（半导体/AI主线）
P2 超跌错杀（右侧反转）
P3 试盘先锋（长上影试盘线）
P4 威科夫SOS底部建仓
P5 弹簧突破（波动率收缩）
P6 AI/低空经济核心中军
```

选择某个 P 后，应自动填入 V6OP 的问财输入框 `#wencai-query`，并自动切到“问财选股”来源。

P1-P6 文案从 V5 复制，来源：

```text
F:\v.6\v5.10\web\index.html
PRESET_QUERIES
```

### 2. 加回问财收藏

参考 V5：

```text
openclaw_v5_favorites
```

V6OP 建议新 key：

```text
v6op_wencai_favorites
```

要求：

1. 可以保存当前问财语句；
2. 可以从下拉框选择收藏并回填；
3. 可以删除收藏；
4. 收藏内容用 localStorage，不需要后端；
5. 若检测到 V5 收藏 `openclaw_v5_favorites`，可以做一次只读迁移或提供“导入 V5 收藏”按钮。

### 3. 波浪参数改成 V5 可见结构

当前 V6OP 的波浪参数不要只藏在勾选后的卡片里。

请在左侧技能选择区域下方增加一个固定参数块，风格参考 V5：

```text
波浪参数
Swing窗口     默认 10
Fib容差       默认 0.15
波浪回看      默认 20
```

要求：

1. 波浪参数块默认可见；
2. 如果波浪分析未勾选，参数块可以置灰，但仍然可见；
3. 勾选波浪分析后，`buildStrategy()` 必须读取这个固定参数块；
4. 提交给后端的字段仍然是：

```text
params.skills.wave.swing_window
params.skills.wave.fib_tolerance
params.skills.wave.signal_bars
```

5. 不要破坏现有后端参数；
6. `min_wave_bars` 和 `days` 保留，但可以放到高级区域或沿用当前内联参数。

### 4. 波浪命名对齐

把用户可见名称从：

```text
波浪分析
```

调整为更接近 V5 的：

```text
艾略特波浪过滤
```

说明文字建议：

```text
辅助过滤：ABC底可放行，5浪顶可拦截；无顶部风险时不拦截
```

不要再显示“弱信号”这种容易让用户误会为“没用/不准”的词。

### 5. 技能方案收藏

低风险实现一个“方案收藏”，保存当前：

```text
股票来源
问财语句
limit
已勾选技能
技能顺序
执行路径
已接通技能参数
```

建议 key：

```text
v6op_strategy_favorites
```

要求：

1. 可以保存当前方案；
2. 可以选择方案并恢复；
3. 可以删除方案；
4. 不要覆盖现有 `v6op_last_params`；
5. 方案恢复后页面状态和 `buildStrategy()` 输出一致。

如果时间不够，优先级如下：

```text
P1-P6 > 问财收藏 > 波浪固定参数块 > 方案收藏
```

### 6. 板块联动入口要谨慎对齐

V5 有：

```text
个股模式
板块联动
板块语句收藏
```

V6OP 第一阶段当前主来源以：

```text
手动输入代码
全 A 股 limit
问财选股
```

为主。如果后端没有完整 `sector` / `板块联动` source，不要只做一个看起来能点、实际不能跑通的按钮。

要求：

1. 先检查 V6OP 后端 `/api/run` 的 source schema 是否支持板块联动；
2. 如果已经支持，则把 V5 板块联动入口和板块收藏迁移进来；
3. 如果暂未支持，则可以先放“板块联动（未接通）”的禁用入口，或只保留任务说明，不要让用户误以为可运行；
4. 板块收藏建议 key：

```text
v6op_sector_favorites
```

5. 如做 V5 导入，读取旧 key：

```text
openclaw_v5_sector_favorites
```

### 7. Phase A / Phase B 的真实运行逻辑

这一段是本轮最重要的验收点。

V5 逻辑不是简单“问财选股 + 文本框”，而是：

```text
Phase A：问财扫描板块
  -> 返回若干热点板块
  -> 用户勾选确认 1 个或多个板块
  -> 把已确认板块注入 Phase B

Phase B：问财个股筛选
  -> 自动带上板块条件
  -> 生成股票池
  -> 股票池继续进入后续技能漏斗
```

V6OP 需要对齐这个行为：

1. 点击“板块联动”后显示 Phase A 和 Phase B 两段输入；
2. Phase A 有独立收藏，下拉选择后填入板块扫描语句；
3. Phase A 有 `取前 N 个热点板块注入 Phase B`，默认 5，可调；
4. 点击扫描后调用板块扫描接口，返回板块列表；
5. 返回后显示 checklist，用户可以全选、全不选、手动勾选；
6. 用户确认后保存为 `confirmed_sectors`；
7. Phase B 问财语句有独立收藏；
8. 最终运行时，如果处于板块联动模式，必须把 `confirmed_sectors` 和 Phase B 语句一起发给后端；
9. 如果未确认板块，运行按钮应提示先扫描并确认板块，不要静默继续；
10. 最终命中的股票要继续向下进入 `czsc / smc / kline / wave / landmine` 漏斗。

若 V6OP 后端当前没有 `/api/scan_sectors` 或等价接口，本轮需要从 V5 迁移或补齐最小可用接口；不要只做前端空壳。

---

## 四、禁止事项

禁止：

1. 改后端选股主链；
2. 改 `wave_producer.py` 的核心算法；
3. 接通灰色 V6 技能；
4. 删除现有 localStorage 恢复能力；
5. 把波浪参数做成只有运行后才看得见；
6. 因为 V5 有 Slot UI 就把 V6OP 整体重写成 V5。
7. 在后端不支持时伪装“板块联动”已经可运行。

---

## 五、验收标准

板块联动必须额外满足：

1. 切到“板块联动”后能看到 Phase A 板块扫描语句、Phase A 收藏、取前 N 个、扫描按钮；
2. Phase A 扫描后能显示板块 checklist；
3. 用户可以勾选部分板块并确认；
4. 确认后的板块能显示在界面上；
5. Phase B 问财语句有独立收藏；
6. 运行时能把已确认板块注入 Phase B，并最终生成股票池；
7. 股票池继续进入后续技能漏斗；
8. 未确认板块时不能假装运行成功。

至少满足：

1. 刷新 `http://10.10.10.186:8900/` 后能看到 P1-P6 预设策略；
2. 选择 P1 后，问财输入框出现 P1 语句，并切到问财选股；
3. 可以保存、选择、删除问财收藏；
4. 左侧能直接看到“波浪参数”固定块；
5. 勾选艾略特波浪过滤后运行，`execution_result.json` 里能看到 wave 参数进入策略；
6. 不勾选波浪时，不应把 wave 加进 skills；
7. `node --check web/app.js` 通过；
8. `pytest tests/test_phase3_web_assets.py` 通过；
9. 如改到参数构造逻辑，补跑 `pytest tests/test_phase2_execution.py`。

---

## 六、建议修改文件

主要文件：

```text
web/index.html
web/app.js
web/styles.css
tests/test_phase3_web_assets.py
```

必要时增加前端静态测试，不要让这轮变成大范围后端改造。

---

## 七、完成报告

完成后写：

```text
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-028_v5_presets_favorites_wave_slot_parity_report.md
```

报告包含：

1. 修改文件清单；
2. P1-P6 来源与填充逻辑；
3. 问财收藏 localStorage key；
4. 技能方案收藏 localStorage key；
5. 波浪参数 UI 与后端字段映射；
6. 测试命令和结果；
7. 未完成项或风险。
