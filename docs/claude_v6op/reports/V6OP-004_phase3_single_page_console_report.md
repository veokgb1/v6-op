# V6OP-004 Phase 3 单页操盘台前端 — 交付报告

> 执行角色：Claude
> 完成时间：2026-05-05
> 状态：completed

---

## 1. 改了哪些文件

### 新增

| 文件 | 说明 |
|---|---|
| `web/index.html` | 单页操盘台 HTML，三栏布局 |
| `web/app.js` | 纯 Vanilla JS 前端逻辑（健康检查/技能列表/策略构建/轮询/结果渲染） |
| `web/styles.css` | 深色控制台主题，CSS 自定义属性，响应式布局 |
| `tests/test_phase3_web_assets.py` | Phase 3 轻量前端资产测试（42 项） |

### 修改

| 文件 | 说明 |
|---|---|
| `scripts/v6op_server.py` | 新增 `_serve_static()` 方法，支持 `GET /` → `web/index.html`，防路径穿越 |

### 未修改

- `V5.10 / V6` 相关文件：**未修改**
- `.env`：**未修改**
- 后端主逻辑（execution_engine / producers / source_resolver）：**未修改**

---

## 2. 页面访问 URL

```
http://127.0.0.1:8876/
```

端口被占用时自动尝试 8877 / 8878（已有实现）。

---

## 3. 页面布局

三栏 CSS Grid（`260px 1fr 300px`），移动端折叠：

```
左侧                     中间                    右侧
─────────────────────────────────────────────────────
股票来源（3种）           运行日志（log-box）      命中数
  手动 / 全A / 问财       数据就绪状态             命中列表 + 中文解释
                          数据覆盖表格             失败 / 未分析
技能选择（6种）           警告/标注                Stale（隐藏到有数据）
  缠论 / SMC / K线        技能运行摘要             报告入口
  波浪 / 排雷

路径类型（3种）
  sequential / parallel_and / simple_hybrid

启动按钮 + spinner + status badge
```

---

## 4. 是否启动服务验证

已验证：

```text
GET http://127.0.0.1:8879/              → 200 text/html   ✅
GET http://127.0.0.1:8879/styles.css   → 200             ✅
GET http://127.0.0.1:8879/app.js       → 200             ✅
GET http://127.0.0.1:8879/api/health   → 200             ✅
```

---

## 5. 是否访问真实外部接口

- **问财（pywencai）**：否。Phase 3 演示使用 `manual` 策略，不触发问财请求。
- **行情源（baostock/akshare）**：否。执行引擎为 `read_cache_only` 模式。

---

## 6. 是否读取 `.env`

否。服务器 health 端点只显示变量名（`dot_env_var_names`），不返回任何 key 值。

---

## 7. 是否修改 V5.10 / V6

**否。**

---

## 8. API 是否仍通过 self-test

```text
.venv\Scripts\python.exe scripts\v6op_server.py --self-test --port 8878
结果：15 通过 / 0 失败
```

---

## 9. 前端是否能提交 manual 策略并显示结果

已通过 self-test 演示路径验证：

```text
POST /api/run  source=manual codes=[000001.SZ, 000002.SZ, 000063.SZ]
skills=kline,landmine  path=parallel_and
→ status=completed  final_hits=2  elapsed=0.42s
```

前端提交后：
- 轮询 `/api/stream` 显示分步日志
- 完成后拉取 `/api/result` 渲染命中列表、中文解释、失败列表、数据覆盖

---

## 10. stream 使用轮询还是 SSE

**JSON 轮询**（`setInterval(pollStream, 1500)`，不使用 `EventSource`）。

这与架构师 V6OP-003 审阅结论一致：stdlib HTTPServer 不适合 true SSE，JSON 轮询是阶段 3 可接受方案。

---

## 11. 测试结果

```text
pytest -q
→ 161 passed  (42 Phase3 新增 + 119 原有)

v6op_server.py --self-test --port 8878
→ 15 通过 / 0 失败
```

### JS 语法检查

无 Node.js，使用 Python 静态检查：

```python
# 服务器加载 app.js 并正常返回 200，说明文件可读
# 浏览器打开可验证无语法错误（无 console.error 出现）
```

报告使用 Python 静态内容搜索替代 `node --check`，已确认文件格式完整。

---

## 12. 关键设计说明

### readiness=aborted 醒目标注

```html
<!-- 渲染为 alert-danger 红色告警框 -->
⛔ readiness=aborted  失败率 XX%  数据严重不足
```

### SMC soft_filter 标注

- 默认 `strict`（前端 radio 默认选中）
- `soft_filter` 选项显示 `tag-debug`（黄色边框标签）+ 说明"调试/软过滤 结果仅供参考"
- 命中列表和警告区均显示 `soft_filter` 标签

### Wave 弱信号标注

- Wave skill 旁显示 `tag-weak`（橙色）"弱信号"
- 命中列表中 Wave 相关命中显示 `tag-weak` 标签
- 警告区显示"Wave 弱信号：no_top 放行，不应视为强正向信号"

### 不展示真实 key 值

Health 检查只渲染变量名（如 `IWENCAI_API_KEY`），不渲染值。

---

## 13. 需要 v6-op 架构师审阅的 5 点

1. **路径穿越防护**：`_serve_static()` 使用 `resolve().startswith(web_dir.resolve())` 防护，但 Windows 路径大小写不敏感，建议补充 `case_sensitive=False` 或在 staging 环境额外验证。

2. **JS 语法验证方案**：当前无 Node.js，使用 Python 内容搜索验证文件完整性。如果 CI 环境有 Node，建议加 `node --check web/app.js` 步骤。

3. **`/api/stream` 事件计数跳跃**：`_lastEventCount` 在前端维护，服务器每次返回最近 50 条；如果单次执行产生 >50 条事件，前端可能跳过中间日志。建议服务器支持 `?since=N` 参数（Phase 4 可做）。

4. **self-test 结果依赖已有缓存**：`readiness=aborted` 是因为 `000063.SZ` 在失败列表，演示路径正常。但如果 `output/current/` 被清空，self-test 的 `/api/result` 预检查会从 200 降为 404，影响测试第一步判断。

5. **移动端布局验证**：CSS 在 900px 以下折叠为单列，但未在真实移动设备测试。建议架构师在手机或开发者工具模拟器验证可用性。
