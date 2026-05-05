# V6OP 监督与协作规则

> 文档作者角色：v6-op 架构师（Codex）
> 面向对象：用户 / Claude / 后续新对话
> 文档状态：active
> 最后更新时间：2026-05-05

## 1. 角色分工

Codex 在 V6OP 中主要负责监督，不抢主开发：

- 拆阶段、定边界、写 Claude 命令
- 核对 V5/V6 资产是否存在、路径是否准确
- 审阅 Claude 交付结果
- 跑验收命令，查污染、查密钥、查报告口径
- 做小补丁、文档修正、GitHub 上传

Claude 负责主开发代码：

- 数据引擎
- Producer
- 执行引擎
- 后端 API
- 前端主页面

用户负责：

- 把 Codex 给出的完整命令复制给 Claude
- 确认阶段方向和业务取舍
- 需要真实 API / 密钥 / 付费接口时拍板

## 2. 命令制度

给 Claude 的每轮任务必须有命令编号，例如：

```text
V6OP-001
V6OP-002
V6OP-003
```

命令文件放在：

```text
docs/claude_v6op/commands/
```

每条命令必须写清：

- 目标
- 背景
- 必读文件
- 允许修改
- 禁止修改
- 具体任务
- 输出要求
- 验收命令
- 报告落点
- 完成后回复格式

## 3. 报告制度

Claude 每轮完成后必须更新：

```text
docs/claude_v6op/latest_report.md
docs/claude_v6op/current_status.md
docs/claude_v6op/reports/<COMMAND_ID>_<short_name>_report.md
```

Codex 审阅后如需写签收报告，另写：

```text
docs/claude_v6op/reports/<COMMAND_ID>_codex_review.md
```

不要把 Claude 原始报告和 Codex 审阅混成一份。

## 4. V5 / V6 复用边界

V5.10 是只读能力库，不是工程模板。

允许：

- 只读参考算法、缓存、预热、报告格式、失败经验
- 提取思路后在 V6OP 自己目录内重写
- 复制纯数据文件 `ashare_codes.txt`

禁止：

- 修改 `F:\v.6\v5.10`
- 复制 `.env`
- 复制 `.venv`
- 复制整个 `var` / `output` / 历史缓存目录
- 直接 import 或运行 V5 脚本作为 V6OP 主路径
- 继承旧 Slot / 线性漏斗池 / 旧页面结构

V6 是后台能力库。

允许：

- 直接引用稳定模型与工具，如 `contracts.py`、`expression_runner.py`、`mask_store.py`
- 适配包装已有表达式执行、条件执行、Universe 构建能力

禁止：

- 继续扩张现有 V6 workbench 多页面
- 新增 V6 账本目录或 schema 文件作为 V6OP 第一阶段主线
- 修改 `F:\v.6\v6` 文件，除非用户明确要求

## 5. 环境规则

V6OP 可以建立自己的 Python 环境。

当前机器可见 Python：

```text
Python 3.13.3
```

Claude 可以在 `F:\v.6\v6-op` 下自行创建 `.venv`，并按阶段 0 需要安装依赖。

硬边界：

- 不复制 V5/V6 `.venv`
- 不复制 V5/V6 `.env`
- 不把真实 key 写入代码、测试、报告或 Git
- 依赖安装失败时，必须在报告里说明阻断点和替代方案

## 6. 高速推进规则

本轮 V6OP 目标是 4-5 小时内快速跑通。

每条 Claude 命令要大步幅推进，但仍严格对应 charter 阶段：

1. 阶段 0：数据引擎 + 预热 + 首个 Producer
2. 阶段 1：六个核心 Producer
3. 阶段 2：Fetch Planner + 执行引擎 + 后端 API
4. 阶段 3：单页操盘台

每轮不做散碎小任务，除非是验收返修。

## 7. Git / 上传规则

Claude 正在主开发时，Codex 不推送。

Claude 完成后，Codex 才做：

```text
git status
稳定窗口检查
显式 git add 文件名
敏感串扫描
测试 / 验收
commit
push
```

当前 `F:\v.6\v6-op` 尚未初始化 Git。是否单独建仓或并入现有仓库，等第一轮代码成形后由 Codex 向用户确认。

## 8. 前端中文表达规则

V6OP 的主页面首先是给用户每天操盘使用，不是给工程师展示内部术语。

硬性要求：

- 面板标题、按钮、表单标签、提示文案、告警文案、空状态文案必须以中文为主。
- 中文要轻松、直接、可理解，避免晦涩术语堆叠。
- 英文技术名可以保留，但只能作为小字、括号、等宽补充或 tooltip 补充，例如 `parallel_and`、`strict`、`soft_filter`。
- 极专业且不适合硬翻译的英文名可以保留，但附近必须有中文解释。
- 用户不应被迫理解 Mask、ScopeRef、ExecutionDraft 等 V6 内部术语才能完成操作。
- Codex 审阅前端时必须检查中文可读性，不能只检查功能是否跑通。
