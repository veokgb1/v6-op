# V6OP-029 实施报告：问财板块联动 · 收藏 · 中止

**日期**：2026-05-06  
**执行人**：Claude Sonnet 4.6  
**状态**：✅ 完成，验证通过

---

## 一、任务边界（来自 V6OP-029 命令文档）

| 编号 | 要求 | 状态 |
|------|------|------|
| 1 | P1-P6 预设策略（来自 V5 PRESET_QUERIES） | ✅ |
| 2 | `v6op_wencai_favorites` localStorage 问财收藏 | ✅ |
| 3 | `v6op_sector_favorites` localStorage 板块收藏 | ✅ |
| 4 | 个股模式 / 板块联动模式切换 | ✅ |
| 5 | `POST /api/scan_sectors`——独立查询，不启动管道 | ✅ |
| 6 | Phase B 板块模式：构建 `属于{sectors}板块，且{phaseB}` | ✅ |
| 7 | "运行" → "启动管道"（底层仍是 `/api/run`） | ✅ |
| 8 | 真实中止：`POST /api/abort` → `execution_engine` 步骤边界检查 | ✅ |
| 9 | "查看当前报告" → `window.open('/api/result')` | ✅ |
| 10 | "清空屏幕日志" → DOM only，提示"磁盘文件未删除" | ✅ |
| 11 | Wave 整理：移除 `isWeak`/`has_weak_signal`，保留文本警告 | ✅ |

**本轮明确排除**：断点续跑、清理缓存、删除磁盘日志、历史报告选择器。

---

## 二、文件变更清单

### `scripts/execution_engine.py`（改）
- 新增 `import threading`
- 新增模块级变量 `_abort_requested: bool`、`_abort_lock: threading.Lock`
- 新增异常类 `AbortRequested`
- 新增函数 `request_abort()` / `reset_abort()` / `is_abort_requested()` / `_check_abort()`
- `execute()` 入口调用 `reset_abort()`
- 在 sequential / parallel_and / simple_hybrid 三种路径的每个 producer 调用前插入 `_check_abort()`
- 步骤 1/2/3/4/6 边界各插入一次 `_check_abort()`

### `scripts/sources/sector_scan_source.py`（新建）
- Phase A 独立板块扫描，不调用 `execution_engine.execute()`
- `scan(sector_query, top_n)` → `{sectors, count, query, error, elapsed_s}`
- 依赖检查：`pywencai` 未安装 → 中文错误，不崩溃
- API Key 检查：`IWENCAI_API_KEY` 缺失 → 中文错误
- 板块名提取：优先字段名列表，fallback 启发式中文字符串
- 所有失败路径均返回 `error: "清晰中文描述"` + `sectors: []`

### `scripts/v6op_server.py`（改）
- `_run_state` 增加 `"abort_requested": False` 字段
- `_run_execution_background` 新增 `except execution_engine.AbortRequested` 分支 → `status="aborted"`
- `POST /api/run` 重置 `abort_requested: False`
- 新增路由 `POST /api/abort`：检查状态、设标志、调 `execution_engine.request_abort()`
- 新增路由 `POST /api/scan_sectors`：调 `sector_scan_source.scan()`，error 返回 400

### `web/index.html`（完全重写）
- `all-a-limit`：`<input type=number>` → `<select>`（SAFE 100 / STABLE 300 / TEST 500 / PRO 1000 / PRO 2000 / PRO 5000）
- `src-wencai` 面板：
  - 模式切换行（`wm-btn-stock` / `wm-btn-sector`）
  - `phase-a-panel`（hidden）：板块收藏栏 / sector-query textarea / sector-top-n select / 扫描按钮 / checklist / 确认行 / 已确认 chips
  - `phase-b-panel`：P1-P6 预设按钮行 / 问财收藏栏 / wencai-query input / wencai-limit select
- "启动管道"区段：`btn-run "▶ 启动管道"` / `btn-abort "⏹ 中止运行" disabled` / `btn-view-report` / `btn-clear-log` / `btn-reset-params`

### `web/app.js`（完全重写）
- `API`：新增 `abort` / `scanSectors`
- `PRESET_QUERIES`：P1-P6 六条完整语句（来自 V5）
- `FAV_KEY_WENCAI` / `FAV_KEY_SECTOR`：两个独立 key，与 V5 `openclaw_v5_*` 不冲突
- `SKILL_META.wave`：移除 `isWeak: true`，更新 note（不含"辅助放行"）
- 问财板块联动：`_wencaiMode` 状态 / `_confirmedSectors` 数组 / `setWencaiMode` / `scanSectors` / `confirmSectors` / `renderConfirmedChips`
- `buildStrategy()` wencai 分支：sector 模式构建合成查询 + `source.sector_linkage` metadata
- `renderHits()`：移除 `h.has_weak_signal` 判断和 yellow tag 推送
- `renderWarnings()`：保留文字警告（`weak_signal_skills` 文本），无 tag
- `setRunningState()`：统一管理 btn-run/btn-abort/spinner
- `pollStream()`：terminal states 含 `'aborted'`
- `bindAbortButton` / `bindViewReportButton` / `bindClearLogButton`：新增三个按钮绑定
- `all-a-limit` 改为 `'change'` 事件（select 元素）

### `web/styles.css`（追加）
新增以下样式类：
`.wencai-mode-row` / `.mode-btn` / `.mode-btn.active` / `.sub-section-title` / `.preset-row` / `.preset-label` / `.preset-btn` / `.fav-bar` / `.fav-chip` / `.fav-chip-label` / `.fav-chip-del` / `.sector-checklist-title` / `.sector-check-group` / `.sector-check-item` / `.sector-confirmed-chips` / `.confirmed-chip` / `.btn-danger`

### `tests/test_phase3_web_assets.py`（追加）
新增 `TestV6OP029WencaiSectorFavorites`（38 个测试方法），覆盖：
P1-P6 / 收藏 key / CRUD / Phase A/B UI / scan_sectors / abort / 查看报告 / 清空日志 / 启动管道文字 / Wave 整理 / CSS 新样式 / execution_engine 中止支持

---

## 三、关键设计决策

### 协作式中止（非 force-kill）
`execution_engine._check_abort()` 仅在步骤边界被调用（never inside `_run_one()`），避免宽泛 `except Exception` 吞掉异常。`AbortRequested` 会原路传播至 `_run_execution_background` 的专用 `except` 分支，将 `status` 置为 `"aborted"`，触发 UI 的 `badge-aborted` 样式。

### sector_linkage metadata 透传
`source_resolver.py` 仅读取 `source.type` / `.codes` / `.query` / `.limit`，未知字段自然被忽略。因此 `source.sector_linkage` 这个调试元数据字段无需任何后端改动即可透传至结果 JSON。

### Phase A/B 边界严格
`/api/scan_sectors` 完全独立：不调用 `source_resolver`，不调用 `execution_engine.execute()`，不改 `_run_state`。只调用 `sector_scan_source.scan()`，把结果 JSON 返回给前端。

### localStorage key 命名空间隔离
使用 `v6op_wencai_favorites` / `v6op_sector_favorites` 前缀，与 V5 的 `openclaw_v5_*` 完全隔离，不会相互污染。

---

## 四、验证结果

```
node --check web/app.js
# (无输出 = 语法通过)

pytest tests/test_phase3_web_assets.py -v
# 119 passed in 0.54s
```

- 所有 81 个原有测试全部通过（无回归）
- 新增 38 个 V6OP-029 测试全部通过
- JS 语法检查零错误

---

## 五、未做事项（按命令文档明确排除）

- 断点续跑（resume from checkpoint）
- 清理缓存 API
- 删除磁盘日志
- 历史报告选择器
