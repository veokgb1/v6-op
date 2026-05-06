# V6OP-027 报告：页面布局拖拽与 V6 灰色资产折叠

> 执行：Claude / V6OP 新代码师  
> 日期：2026-05-05  
> 状态：✅ 完成

---

## 一、修改文件清单

| 文件 | 变更类型 | 说明 |
|---|---|---|
| `web/index.html` | 修改 | 新增两个 resizer div |
| `web/styles.css` | 修改 | 布局改 flex，新增 resizer / 灰卡折叠样式 |
| `web/app.js` | 修改 | 新增 `initResizers()`，改造 `buildSkillList()` 灰卡段 |
| `tests/test_v6op027_resizable_and_collapsible.py` | 新增 | 26 条静态验收测试 |

---

## 二、三栏拖拽实现说明

### HTML 结构变化

在三个 `<section class="panel">` 之间各插入一个分隔条：

```html
<div class="resizer" id="resizer-left"></div>   <!-- 左栏与中栏之间 -->
<div class="resizer" id="resizer-right"></div>  <!-- 中栏与右栏之间 -->
```

### CSS 布局变化

`.console-layout` 从 `display: grid` 改为 `display: flex; height: calc(100vh - 41px); overflow: hidden;`

左栏和右栏设为 `flex: none`（固定像素宽度），中栏保持 `flex: 1 1 0`（自动填充剩余空间），不需要三栏宽度同时存储。

### JS 拖拽逻辑（`initResizers()`）

- 鼠标 `mousedown` 记录起始 X 和起始宽度
- `mousemove` 实时更新左栏或右栏宽度（最小宽度保护：左 160px，中 180px，右 160px）
- `mouseup` 调用 `saveWidths()` 写入 localStorage，并清除事件监听
- 拖拽期间设置 `document.body.style.userSelect = 'none'` 防止选中文字，松开后恢复
- 分隔条拖拽中添加 `.dragging` 类触发高亮

### 窗口 resize 后的可用性

中栏是 `flex: 1`，窗口缩放后中栏自动伸缩，左右栏保持用户设定的像素宽度，始终可用。

---

## 三、localStorage 键名

| 键名 | 用途 | 格式 |
|---|---|---|
| `v6op_layout_columns` | 三栏宽度持久化 | `[leftPx, rightPx]`（两个整数） |
| `v6op_v6_assets_collapsed` | 灰卡折叠状态 | `"true"` 或 `"false"` |

---

## 四、V6 灰卡折叠状态说明

- 默认折叠（首次打开显示标题 + 数量，如 `▶ V6 技能资产（暂未接通） 17`）
- 点击标题切换展开/折叠，状态写入 `localStorage`，刷新后恢复
- 展开后：`▼ V6 技能资产（暂未接通）`，所有灰卡可见
- 折叠后：显示技能数量角标 `<span class="v6-gray-count">N</span>`
- 灰卡 `cb.disabled = true` 保持不变，`data-gray="true"` 标记保持不变
- 已接通 live 技能（czsc / smc / kline / wave / landmine）不受折叠影响，始终可见可选
- `SKILL_CATALOG_GRAY` 仍来自 `/api/skill_catalog`，前端不手写灰卡列表

---

## 五、验收测试结果

### node --check

```
web/app.js  → OK（无语法错误）
```

### pytest -q

```
508 passed, 3817 warnings in 15.49s
```

新增测试文件：`tests/test_v6op027_resizable_and_collapsible.py`（26 条）

覆盖：
- `resizer-left` / `resizer-right` 存在且位置正确
- `initResizers` 函数存在并在 DOMContentLoaded 中调用
- `v6op_layout_columns` 键名 + localStorage 读写逻辑
- `v6op_v6_assets_collapsed` 键名
- `v6-gray-toggle` / `v6-gray-body` 元素创建
- `collapsed` 类操作
- `v6-gray-count` 数量显示
- 灰卡 `disabled = true` 仍存在
- `SKILL_CATALOG_GRAY` 仍来自 `/api/skill_catalog`
- 拖拽事件（mousedown / mousemove / mouseup）存在
- 最小宽度保护存在
- `display: flex` 布局
- `.resizer` 样式 / `col-resize` 光标 / hover 高亮
- `.v6-gray-toggle` / `.v6-gray-body.collapsed` / `.v6-gray-count` CSS 类存在

---

## 六、页面访问地址

- `http://127.0.0.1:7749/`
- `http://10.10.10.186:8900/`（如果服务仍在运行）

---

```
Claude / V6OP 新代码师
V6OP-027 页面布局拖拽与 V6 灰色资产折叠
```
