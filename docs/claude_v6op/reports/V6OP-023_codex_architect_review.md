# V6OP-023 Codex 架构复核

> 复核时间：2026-05-05  
> 复核者：Codex / V6OP 新架构师  
> 被复核报告：`docs/claude_v6op/reports/V6OP-023_charter_gap_closure_development_report.md`

---

## 一、总体判断

V6OP-023 不是空转报告轮，确实完成了实质开发：

- 新增灰色技能卡展示；
- 新增参数 localStorage 回显；
- 新增 `scripts/mask_cache.py`；
- 新增 `scripts/verify_prefetch_300.py`；
- 新增 HTTP smoke 脚本；
- 测试从此前约 299 项增加到 389 项。

但本轮不能签为“总纲缺口全部闭合”。按总纲严格验收，V6OP-023 是 **大部分完成，三项部分闭合，一项未完成真实验收**。

---

## 二、Codex 复跑结果

### 1. pytest

```text
389 passed, 3819 warnings in 12.95s
```

说明：

- 功能测试全部通过；
- 但 `tests/test_v6op023_verify_prefetch.py` 有 3 条 `PytestUnhandledThreadExceptionWarning`，原因是子进程输出在 Windows GBK 解码时触发 `UnicodeDecodeError`。这不是主功能失败，但需要清理。

### 2. node --check

```text
node --check web/app.js
exit code 0
```

### 3. 20 只预热 smoke

Codex 复跑：

```powershell
python scripts\verify_prefetch_300.py --limit 20 --workers 2 --json-out output\verification\codex_v6op023_prefetch_smoke.json
```

结果：

```json
{
  "status": "pass",
  "limit": 20,
  "actual_code_count": 20,
  "workers": 2,
  "cache_hit": 20,
  "fetched_ok": 0,
  "failed": 0,
  "failure_rate": 0.0,
  "data_time_max": "2026-04-30",
  "elapsed_seconds": 1.56
}
```

### 4. 300 只真实预热

Codex 追加尝试：

```powershell
python scripts\verify_prefetch_300.py --limit 300 --workers 8 --json-out output\verification\codex_v6op023_prefetch_300.json
```

结果：

- 运行超过 244 秒，被工具层超时终止；
- 没有生成 `codex_v6op023_prefetch_300.json`；
- 终止后残留 8 个 `data_prefetch.py` worker 和 1 个 `verify_prefetch_300.py` 父进程；
- Codex 已按命令行确认并清理这些残留进程。

结论：**300 只真实预热验收未闭合**。当前只能签 `limit=20 smoke pass`，不能签 300。

---

## 三、逐项复核结论

### Task 1：技能卡资产对齐

状态：**部分闭合**

已完成：

- `web/app.js` 增加 `SKILL_CATALOG_GRAY`；
- 灰卡 `disabled=true`；
- `LIVE_SKILL_IDS` 过滤可防 DOM 篡改；
- 当前 V6 资产文件确认为 22 条：
  - `F:\v.6\v6\data\raw_skill_sample_cards.json`
  - `F:\v.6\v6\data\skill_connection_cards.json`

未完全闭合：

- 当前实现是把 18 张灰卡手写进 `web/app.js`，不是从 V6 技能卡 JSON 动态装载；
- 没有新增 v6-op 的技能 metadata 装载层；
- 报告中“未接通 17”和实际 `js_gray_skill_count=18` 有口径矛盾；
- UI 现在实际是 5 个已接通操盘技能 + 18 个灰卡；V6 JSON 22 条中有 4 条映射到已接通能力，`landmine` 是 v6-op 自身新增能力，不在 V6 JSON 中。

需要 V6OP-024 修正：建立真实 catalog loader / endpoint / 前端装载，避免继续手写静态列表。

### Task 2：参数回显

状态：**基本闭合**

已完成：

- `PARAMS_STORE_ID = 'v6op_last_params'`；
- `saveParams()` / `restoreParams()` / `resetParams()`；
- 页面加载回显；
- 运行时保存；
- “恢复默认参数”按钮。

需要后续注意：

- 当前测试主要是静态 JS 检查，真实浏览器 localStorage 行为还需 Task 5 的真正浏览器 smoke 覆盖。

### Task 3：内容寻址 Mask 复用

状态：**部分闭合**

已完成：

- `scripts/mask_cache.py` 存在；
- fingerprint 包含 `skill_id/scope_codes/params/data_date/algo_version`；
- `execution_engine.py` 接入 cache_get/cache_put；
- `execution_result` 有 `mask_cache_hits/misses`。

关键缺口：

`execution_engine.py` 当前只在 `_prefetch_triggered=True` 时设置 `_data_time_max`：

```python
_data_time_max: str = ""
if _prefetch_triggered:
    pr = fetch.get("prefetch_report") or {}
    _data_time_max = str(pr.get("data_time_max", ""))[:10]
```

这会导致常见的“缓存充足、跳过预热”路径里，Mask fingerprint 的 `data_date` 为空字符串。结果是：如果本地 K 线缓存后来更新，但这一轮没有触发预热，同一代码池和参数仍可能命中旧 Mask 缓存。

这不符合总纲第十章“data_date = K 线缓存最新数据日期”的要求。

需要 V6OP-024 修正：无论是否触发 prefetch，都必须从当前 producer 实际读取的缓存文件中计算数据日期或缓存签名。

### Task 4：verify_prefetch_300.py

状态：**脚本存在，20 smoke 闭合；300 未闭合**

已完成：

- 脚本结构完整；
- 20 只 smoke 通过；
- JSON 输出正常。

未闭合：

- Claude 未跑真实 300；
- Codex 追加跑 300 超时 244 秒；
- 脚本在外部超时后没有留下 partial JSON；
- `data_prefetch.py` worker 会残留，需要更强的超时/清理机制。

### Task 5：浏览器级 smoke

状态：**部分闭合**

已完成：

- HTTP API smoke 可用；
- 能验证 `/api/health`、静态文件、`/api/run`、`/api/stream`、`/api/result`。

未闭合：

- 这不是实际浏览器渲染；
- 没有真实 DOM 操作；
- 没有真实验证 localStorage 回显；
- 没有真实点击灰色技能、运行按钮、结果区渲染。

需要 V6OP-024 补：Playwright 或等价真实浏览器 smoke。若环境没有 Playwright，可以输出 `browser_unavailable`，但不能把 HTTP smoke 写成“浏览器级已闭合”。

---

## 四、当前签收状态

| 项 | 状态 |
|---|---|
| V6OP-023 有效开发 | 通过 |
| pytest / node / 20 smoke | 通过 |
| 技能卡资产真实装载 | 未完全闭合 |
| 参数回显 | 基本闭合 |
| Mask 内容寻址 | 未完全闭合 |
| 300 只真实预热 | 未闭合 |
| 真实浏览器 smoke | 未闭合 |

---

## 五、架构结论

V6OP-023 方向正确，但还不能作为总纲缺口最终收口。下一轮 V6OP-024 不应扩张新功能，应专门修正 V6OP-023 的验收偏差：

1. 技能 catalog 从 V6 JSON 真实装载，不再手写灰卡；
2. Mask cache 的 data_date 在无预热路径也必须真实计算；
3. 300 预热脚本必须有超时、partial JSON、worker 清理能力，并重新验收；
4. 补真实浏览器 smoke；
5. 清理 Windows GBK 子进程解码 warning。

---

## 六、签名

```text
Codex / V6OP 新架构师
V6OP-023 架构复核
结论：有效开发，但不完全签收，需 V6OP-024 修正收口
```
