# V6OP-029 问财板块联动 + 两套收藏 + 启动管道基础整理

> 指令发出：Codex / V6OP 架构协同  
> 执行对象：Claude / V6OP 前端与最小后端实现  
> 工作目录：`F:\v.6\v6-op`  
> 审计依据：`F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-028_sector_linkage_audit_report.md`  
> V5 对照：`F:\v.6\v5.10\web\index.html`、`F:\v.6\v5.10\web_server.py`、`F:\v.6\v5.10\scripts\step1_wencai_merged.py`

---

## 一、执行结论

V6OP-028 审计结论通过：板块联动可以接入，但必须保持：

```text
Phase A 板块扫描 = 独立查询/预览
Phase B 最终运行 = 普通 wencai source
source_resolver 不知道 sector
execution_engine 不知道 sector
```

本轮进入实现，但只做安全范围。

---

## 二、本轮必须实现

### 1. P1-P6 预设策略

从 V5 复制 P1-P6 文案：

```text
F:\v.6\v5.10\web\index.html
PRESET_QUERIES
```

要求：

1. V6OP 左侧问财区域能选择 P1-P6；
2. 选择后自动切到 `问财选股`；
3. 在个股模式下填入 Phase B / 问财个股语句；
4. 不触发运行。

### 2. 两套收藏

实现两个互相独立的 localStorage 收藏：

```text
v6op_wencai_favorites   = Phase B 问财个股选股语句
v6op_sector_favorites   = Phase A 板块扫描提示词
```

要求：

1. 均支持保存、选择回填、删除；
2. 不混用 V5 的 `openclaw_v5_*` key；
3. 可以读取 V5 旧 key 做一次性导入按钮，但不是必需；
4. 收藏只存 query 文本和 label，不存股票结果、不存板块扫描结果。

### 3. 个股模式 / 板块联动模式

在问财来源区域内增加类似 V5 的模式切换：

```text
个股模式
板块联动
```

个股模式：

```text
只显示 Phase B 问财个股语句 + 问财收藏
最终 source = { type: "wencai", query, limit }
```

板块联动：

```text
Phase A 板块扫描语句 + 板块收藏 + 取前 N 个 + 扫描按钮
扫描结果 checklist
确认后的板块 tag/chips
Phase B 问财个股语句 + 问财收藏
```

运行前必须：

```text
confirmed_sectors -> 构造成最终 wencai query
```

推荐拼接：

```text
属于{板块1、板块2、板块3}板块，且{Phase B 问财个股语句}
```

最终仍然发送：

```json
{
  "source": {
    "type": "wencai",
    "query": "属于xxx板块，且...",
    "limit": 300
  }
}
```

可以附带 metadata 便于报告调试，但不能改 source type：

```json
"source": {
  "type": "wencai",
  "query": "...",
  "limit": 300,
  "sector_linkage": {
    "enabled": true,
    "confirmed_sectors": ["半导体", "人工智能"],
    "phase_a_query": "...",
    "phase_b_query": "..."
  }
}
```

`source_resolver.py` 会忽略这些额外字段，不要为了 metadata 修改它。

### 4. Phase A 扫描端点

新增独立后端端点：

```text
POST /api/scan_sectors
```

参考 V5：

```text
F:\v.6\v5.10\web_server.py
api_scan_sectors()

F:\v.6\v5.10\scripts\step1_wencai_merged.py
run_sector_phase_a_debug()
_extract_sector_names()
```

实现要求：

1. 只做查询，不启动管道；
2. 不写 output；
3. 不改 `_run_state`；
4. 不调用 `execution_engine.execute()`；
5. 不改 `source_resolver.py`；
6. key 缺失、依赖缺失、查询失败时返回清楚中文错误；
7. 前端错误提示必须清楚，不能伪造板块。

可以把最小板块扫描逻辑放到新文件，例如：

```text
scripts/sources/sector_scan_source.py
```

如果 V6OP 当前没有 V5 的 SkillHub CLI 安装路径或 `hithink-sector-selector` 不可用，端点应返回：

```json
{
  "error": "板块扫描依赖未安装或不可用",
  "sectors": []
}
```

不要返回假板块。

### 5. 扫描档位

把 V5 的扫描档位带入 V6OP 问财/全 A 的 limit 控制：

```text
SAFE   100 只（轻量测试）
STABLE 300 只（推荐）
TEST   500 只
PRO    1000 只
PRO    2000 只
PRO    5000 只（完整扫描）
```

要求：

1. 默认 STABLE 300；
2. 档位最终写入 `source.limit`；
3. 保留大范围确认保护；
4. 若问财实际只能返回较少结果，前端只显示实际返回，不伪造成完整档位数量；
5. 版面不要挤，档位可用 select。

### 6. 启动管道与安全操作按钮

当前 V6OP 已有 `POST /api/run`，所以基础启动不需要再审计。

本轮可以做：

```text
把“运行”按钮改成“启动管道”
把按钮区域整理成 V5 风格但不堆得过挤
保留现有 run_id / 状态 / spinner
增加“中止运行”
增加“查看当前报告”
增加“清空屏幕日志”
```

#### 6.1 中止运行必须是真中止

“中止运行”本轮允许做，而且建议做。

但必须是真中止，不允许只改 UI 状态。

推荐最小安全方案：

```text
POST /api/abort
```

行为：

1. 如果当前没有 running/pending 任务，返回清楚提示；
2. 如果有任务，设置 abort_requested 标志；
3. 前端显示“已请求中止，等待当前步骤收尾”；
4. 后台执行在步骤边界检查 abort 标志；
5. 中止后状态进入 aborted/user_aborted，并写清楚原因。

允许对 `execution_engine.py` 做有限改动：

```text
execute(strategy, should_abort=None)
```

只在这些边界检查：

```text
source_resolver 后
fetch_plan 后
prefetch 前/后
每个 producer 前/后
expression 合并前
report 写入前
```

不要强杀 Python 线程，不要用危险的进程级 kill。

如果当前步骤正在网络请求或 K 线预热，中止可以不是毫秒级立即停止，但必须能在当前步骤结束后停止后续流程。

#### 6.2 查看当前报告

可以做。

先实现“查看当前报告”即可：

```text
读取 /api/result
或复用现有右侧 execution_result.json / run_report.md 链接
```

本轮不要求历史报告选择器。

#### 6.3 清空屏幕日志

可以做纯前端：

```text
只清空当前页面 log-box
不删除磁盘文件
不删除 output
不删除 K 线缓存
```

#### 6.4 本轮仍不要实现的按钮

这些不是永远不做，而是不和“问财板块联动”混在同一轮：

```text
断点续跑
清理缓存
清空日志后端删除
历史报告选择器
```

原因：

1. 断点续跑需要定义“复用哪一轮 source/scope、从哪一步恢复、报告如何标记”，不能用 V5 slots 直接套；
2. 清理缓存需要白名单目录和运行中保护，尤其不能误删用户文件；
3. 清空磁盘日志需要明确只删 `logs/`，且运行中禁止；
4. 历史报告选择器需要 `/api/reports` 和删除报告接口，属于报告体系扩展。

如果为了版面对齐需要显示这些按钮，必须 disabled，并标注“待接后端”，不要让用户误以为可用。

### 7. 波浪只清理标签

不要改波浪算法、参数、展开逻辑。

只允许：

```text
去掉“辅助”
去掉黄色/橙色辅助标签
不要再显示“弱信号”
```

---

## 三、禁止事项

禁止：

1. 新增 `sector` source_type；
2. 修改 `source_resolver.py` 的 source 类型；
3. 修改 `execution_engine.py` 的 Step 1 主链；
4. 把 V5 slots 格式搬进 V6OP；
5. 用假板块、假股票、假成功结果兜底；
6. 把 Phase A scan 结果直接变成 codes 绕过问财 source；
7. 直接实现断点续跑/清理缓存/磁盘清日志这些需要单独白名单和恢复协议的按钮。
8. 用强杀线程/进程的方式实现中止运行。

---

## 四、建议修改文件

```text
web/index.html
web/app.js
web/styles.css
scripts/v6op_server.py
scripts/sources/sector_scan_source.py   （如需要）
tests/test_phase3_web_assets.py
```

如新增后端端点，请补轻量测试。

---

## 五、验收

至少运行：

```powershell
node --check web/app.js
pytest tests/test_phase3_web_assets.py
```

如新增 `/api/scan_sectors`：

```powershell
pytest tests/test_phase2_execution.py
```

手工验收：

1. P1 能回填问财个股语句；
2. 问财收藏可保存/选择/删除；
3. 板块收藏可保存/选择/删除；
4. 板块联动模式下，未扫描/未确认板块时不能启动；
5. 扫描失败时显示真实错误；
6. 确认板块后启动，最终请求仍是 `source.type="wencai"`；
7. 后续技能漏斗照常运行；
8. “启动管道”按钮仍能调用 `/api/run`；
9. “中止运行”能调用 `/api/abort`，且不会启动新任务或破坏输出目录；
10. “清空屏幕日志”只清页面日志，不删磁盘；
11. “查看当前报告”能看到当前结果或报告路径；
12. 没有出现“弱信号/辅助”波浪标签。

---

## 六、报告

完成后写：

```text
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-029_wencai_sector_favorites_safe_impl_report.md
```

报告必须包含：

1. 修改文件；
2. 是否新增 `/api/scan_sectors`；
3. Phase A scan 的依赖是否可用；
4. 两套 localStorage key；
5. 板块联动如何转换为普通 wencai source；
6. 中止运行如何实现，检查点在哪里；
7. 哪些 V5 按钮本轮没有做，原因是什么；
8. 测试结果。
