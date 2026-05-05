# V6OP-005 Codex 架构审阅报告

> 审阅角色：v6-op 架构师（Codex）  
> 审阅时间：2026-05-05  
> 对象：Claude `V6OP-005_phase3_acceptance_closure_report.md`

## 1. 结论

V6OP-005 基本完成 charter 阶段 3 的验收闭合：单页操盘台、技能参数面板、skill-scoped params、运行归档、问财真实入口 smoke、`/api/stream?since=N`、中文界面表达均已形成可验收状态。

Codex 审阅时发现并已修补几处边界问题。修补后，本轮可以视为“第一阶段主线工程闭合”，剩余项属于正式使用前的数据预热、移动端视觉确认和后续运维策略。

## 2. Codex 已执行验证

```powershell
cd F:\v.6\v6-op
node --check web\app.js
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts\execution_engine.py --demo manual
.venv\Scripts\python.exe scripts\v6op_server.py --self-test --port 8878
```

结果：

- `node --check web\app.js`：通过。
- `pytest -q`：173 passed，2544 warnings。warnings 来自 CZSC 第三方 deprecated 函数，不阻断。
- `execution_engine.py --demo manual`：completed，final_hits=2，写入 `output/current/*` 与 `output/runs/<run_id>/*`。
- `v6op_server.py --self-test --port 8878`：15 通过 / 0 失败。
- 静态入口 smoke：`GET /`、`GET /app.js`、`GET /styles.css`、`GET /api/health` 均为 200。
- 问财 smoke：`status=ok`，`scope_count=5`。仅输出状态和数量，未输出 key。
- 敏感串扫描：`scripts/`、`web/`、`tests/`、`docs/` 未发现真实 key 字面量。

## 3. Codex 已做的小修补

文件：

- `.gitignore`
- `scripts/execution_engine.py`
- `scripts/run_report.py`
- `scripts/v6op_server.py`
- `web/app.js`
- `tests/test_phase2_execution.py`
- `tests/test_phase3_web_assets.py`
- `tests/test_v6op_server.py`

修补内容：

1. `.gitignore` 增加 `output/runs/`，避免运行归档误入 Git。
2. `execution_engine.py` 每次 `execute()` 开始清空本轮日志事件，避免 server 多次运行时把旧运行日志带入新 run。
3. `execution_engine.py` 补齐每个 Producer 的 `skill_id`、`skill_name`、`hit_semantics`，避免报告里出现 `None`。
4. `execution_engine.py` 将已注册但前端原本未完整传递的参数贯通到 Producer：
   - SMC：`swing_length`、`close_break`
   - K线：`pass_neutral`
   - 波浪：`swing_window`、`fib_tolerance`
   - 排雷：`params_used` 补齐 `min_bars`
5. `run_report.py` 将每个 Producer 的 `params_used` 写入 `run_report.json` 和 Markdown 的“实际参数”列。
6. `v6op_server.py` 将 `/api/stream?since=N` 改为基于单次 run 的累计 `event_count` 游标，避免依赖数组长度造成游标错位。
7. `web/app.js` 补齐缺失参数输入，并用中文标签表达；布尔参数显示为“是/否”。
8. 新增/更新测试覆盖上述修补点。

## 4. 对 Claude 报告中待审点的回答

1. `wencai` 是来源而非可勾选技能：接受。第一阶段 UI 中问财应作为股票来源入口，`skill_registry.py` 保留其 metadata 作为资产登记，不要求作为 Producer 勾选项重复出现。
2. SMC 高级参数未暴露：Codex 已补齐 `swing_length` 和 `close_break`。
3. run archive 无清理机制：第一阶段不阻断；后续可做 retain-N 或按日期清理。
4. 正式使用前需全量预热：确认。当前 demo 的 `readiness=aborted` 来自缓存不足，真实操盘前应先跑 `data_prefetch.py`。
5. 移动端真实设备未验证：仍是残余风险，不阻断阶段 3 工程验收。

## 5. 中文表达审阅

页面主文案以中文为主，按钮、标签、状态、空状态、失败区、参数说明均可读。

英文保留情况可接受：

- `strict`、`soft_filter`、`bypass` 作为 SMC 模式专业值保留，但带中文解释。
- `sequential`、`parallel_and`、`simple_hybrid` 作为路径类型技术名保留，但旁边有中文标签。
- `hfq`、`JSON` 等技术词保留为辅助说明。

未发现 Mask、ScopeRef、ExecutionDraft 等 V6 内部术语暴露为用户必须理解的操作项。

## 6. 对照大纲

已闭合：

- 阶段 0：数据引擎 + K 线预热 + CZSCProducer。
- 阶段 1：6 个核心能力接通。
- 阶段 2：Fetch Planner + 执行引擎 + 后端 API。
- 阶段 3：单页操盘台 + 参数面板 + 运行归档 + 问财入口 smoke。

仍不进入 Phase 4。下一步应是最终总验收和真实数据预热演练，而不是扩张 21 张技能或新增页面。

## 7. 残余风险

1. 正式操盘前必须先做更完整的 K 线预热，否则 `readiness=aborted` 会持续出现。
2. 移动端真实设备/浏览器 DevTools 视口尚未做截图验收。
3. `output/runs/` 已忽略但会持续增长，后续需要清理策略。
4. pywencai 调用过程中 Node 会输出 `punycode` deprecation warning，不影响本轮功能，但后续可关注依赖更新。

