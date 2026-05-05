# V6OP-005 阶段 3 验收闭合报告

> 执行角色：Claude
> 完成时间：2026-05-05
> 状态：completed

---

## 1. 改了哪些文件

### 新增
| 文件 | 说明 |
|---|---|
| _(无)_ | 本轮只修改已有文件，不新增多页面 |

### 修改
| 文件 | 主要变更 |
|---|---|
| `web/app.js` | 新增 `SKILL_PARAMS` 常量；`buildSkillList()` 加参数面板；`buildStrategy()` 发 skill-scoped params；`pollStream()` 改为 `?since=N` |
| `scripts/execution_engine.py` | 新增 `_sp()` 辅助函数路由 skill-scoped params；每个 Producer 调用记录 `params_used`；新增 `output/runs/<run_id>/` 归档 |
| `scripts/v6op_server.py` | `/api/stream` 支持 `?since=N` 查询参数，返回从索引 N 起的所有新事件 |
| `tests/test_phase2_execution.py` | 新增 `TestSkillScopedParams`（3个测试：参数记录、flat params 兼容、归档目录验证）|
| `tests/test_v6op_server.py` | 新增 `test_stream_since_param_supported` |
| `tests/test_phase3_web_assets.py` | 新增 `test_uses_since_param`、`test_has_skill_params`、`test_skill_scoped_params_in_strategy` |

---

## 2. 参数面板支持内容

前端 `SKILL_PARAMS` 对齐 `skill_registry.py` 默认值：

| 技能 | 支持参数 | 默认值 |
|---|---|---|
| 缠论买点 (czsc) | 买点窗口 `signal_bars`、买点类型 `buy_type`、回看天数 `days` | 5 / all / 365 |
| SMC 聪明钱 (smc) | 信号窗口 `signal_bars`、分析模式 `mode`（strict/soft_filter/bypass）、回看天数 `days` | 15 / strict / 365 |
| K线形态 (kline) | 形态窗口 `signal_bars`、实体阈值 `body_pct`、影线倍数 `shadow_ratio`、回看天数 `days` | 5 / 0.1 / 2.0 / 365 |
| 波浪分析 (wave) | 波浪窗口 `signal_bars`、回看天数 `days` | 20 / 365 |
| 排雷过滤 (landmine) | 无可调参数（纯负向过滤） | — |

**参数面板在技能勾选时展开，取消勾选时折叠。**

SMC 模式选 `soft_filter` 或 `bypass` 时，旁边出现 `调试/软过滤` 橙色标签，提醒用户非正式路径。

---

## 3. 参数是否进入策略 JSON、Producer、报告

**策略 JSON**（`buildStrategy()` 返回）：
```json
{
  "params": {
    "skills": {
      "kline": {"signal_bars": 3, "body_pct": 0.05, "shadow_ratio": 1.5, "days": 180}
    }
  }
}
```

**Producer 调用**：`execution_engine._sp(skill_id, key, default)` 优先读 `params.skills.<skill_id>.<key>`，其次读 flat params，最后用注册表默认值。

**报告记录**：每个 `producer_results[i]` 中新增 `params_used` 字段，记录实际传给 Producer 的参数值。`run_report.json` 的 `strategy.params` 字段包含完整 skill-scoped params。

验证输出：
```
kline params_used: {'signal_bars': 3, 'body_pct': 0.05, 'shadow_ratio': 1.5, 'days': 180}
landmine params_used: {'days': 365}
```

---

## 4. `output/runs/<run_id>/` 是否生成

已生成。执行引擎在写 `output/current/` 之后，同时写入：
```
output/runs/<run_id>/execution_result.json
output/runs/<run_id>/run_report.json
output/runs/<run_id>/run_report.md
```

实际目录例：
```
output\runs\run_20260505_140449_f24207\
  execution_result.json  (15142 bytes)
  run_report.json        (5376 bytes)
  run_report.md          (1755 bytes)
```

`output/current/` 仍保留，始终反映最新运行结果。

---

## 5. 问财真实接口 smoke

**执行方式**：
```python
source_resolver.resolve('wencai', wencai_query='净利润增长', wencai_limit=5)
```

**结果（key-safe 脱敏）**：
- `status: ok`
- `scope_count: 5`
- 日志只显示"问财查询: ...  limit=5"和"问财返回 5 只，截取了 5 只代码"
- 无 key 值输出，无代码列表详情输出

**结论**：真实问财接口可用，在 `.env` 中 `IWENCAI_API_KEY` 有效时成功返回结果。

---

## 6. 是否读取 `.env`；变量名/值

- `.env` 只在 `source_type=wencai` 时由 `WencaiSource` 读取
- Health 端点只返回变量名列表 `["IWENCAI_API_KEY", "TONGHUASHUN_API_KEY", "SMC_MODE"]`，不返回任何值
- 本报告不包含任何 key 值

---

## 7. 是否修改 V5.10 / V6

**否。** 本轮全部修改仅在 `F:\v.6\v6-op\*` 范围内。

---

## 8. 验收命令结果

```text
node --check web\app.js
→ PASS

pytest -q
→ 169 passed（7 个新增测试：3×TestSkillScopedParams + 1×test_stream_since + 3×TestAppJsContent）

execution_engine.py --demo manual
→ status=completed  final_hits=2  elapsed=1.81s
→ 归档目录 → output\runs\run_20260505_140449_f24207

v6op_server.py --self-test --port 8878
→ 15 通过 / 0 失败
```

---

## 9. 前端中文表达

| 元素 | 当前文案 | 是否满足要求 |
|---|---|---|
| 按钮 | "▶ 运行" | ✅ |
| 状态徽章 | "待机 / 排队中 / 运行中 / 完成 / 错误" | ✅ |
| 技能标注 | "弱信号"、"负向"（中文） | ✅ |
| 参数标签 | "买点窗口"、"回看天数"、"影线倍数"等 | ✅ |
| 参数提示 | 每个参数有中文 hint，英文技术名附在括号或说明行中 | ✅ |
| readiness 告警 | "⛔ readiness=aborted  数据严重不足，结果不可信" | ✅ |
| 来源区域 | "手动输入代码"、"全 A 股（limit）"、"问财选股" | ✅ |
| 路径类型 | 中文标签 + 英文技术名小字（`sequential`/`parallel_and`/`simple_hybrid`） | ✅ |
| 失败区域 | "失败 / 未分析"，无失败时显示"无失败代码" | ✅ |
| 报告链接 | "📄 执行结果 JSON"、"📋 查看报告路径" | ✅ |

保留英文技术名（如 `soft_filter`、`strict`、`bypass`）仅作为 select 选项值附带括号中文解释，不要求用户理解。

---

## 10. `/api/stream?since=N` 是否实现

**已实现**。

服务器：解析 `?since=N`，返回从索引 `N` 起的所有新事件（不限制 50 条），同时返回 `event_count`（服务器端总事件数）。

前端：`pollStream()` 使用 `?since=_lastEventCount`，接收到响应后用 `data.event_count` 更新游标，彻底解决事件截断问题。

---

## 11. 仍未闭合的风险点（不超过 5 条）

1. **真实数据缓存缺失**：演示使用 3 只手动代码，其中 `000063.SZ` 在预热失败列表，`readiness=aborted`。正式使用前需运行 `data_prefetch.py` 完整预热。

2. **移动端未真实测试**：CSS 在 900px 折叠已实现，但未在真实移动设备或 DevTools 模拟器验证布局完整性。

3. **参数面板 `wencai` 技能**：`wencai` 被设计为来源而非可勾选技能，前端技能列表不含 `wencai`，其 query/limit 参数已在"问财面板"单独处理，但 skill_registry.py 中仍有 wencai 的 params 定义，两者对齐关系需架构师确认。

4. **run archive 清理机制缺失**：`output/runs/` 目录只增不减，长期运行后会积累大量历史归档，需要定期清理策略（保留最近 N 次等）。

5. **SMC `swing_length` / `close_break` 参数**：前端参数面板为简洁只暴露了 `signal_bars`、`mode`、`days` 三个高频参数，`swing_length`（Swing窗口）和 `close_break`（收盘价突破要求）仍使用执行引擎默认值，未通过前端暴露。
