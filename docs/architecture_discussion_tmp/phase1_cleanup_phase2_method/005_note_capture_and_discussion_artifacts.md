# 笔记、截图与讨论材料整理规则

## 1. 本文件目的

讨论区不只保存文字结论，也要保存讨论过程中的关键材料。

这些材料包括：

- 人类口语化问题。
- Codex / codext 清理后的问题。
- Claude 分析师回复。
- Codex 独立判断。
- 人类贴出的截图。
- Claude 生成的 Markdown 图、树形图、目录图。
- 运行日志截图。
- 页面问题截图。
- 阶段性签收或否决意见。

## 2. Markdown 能放什么

Markdown 可以放：

- 普通文字。
- 表格。
- 代码框。
- Mermaid 图。
- 树形目录。
- 本地图片链接。

如果图片已经保存到本地，可以使用：

```markdown
![说明文字](F:/v.6/v6-op/docs/architecture_discussion_tmp/phase1_cleanup_phase2_method/assets/example.png)
```

如果图片只出现在聊天窗口、没有本地文件，则 Codex / codext 先记录：

- 图片来自哪一轮。
- 图片显示了什么。
- 用户用箭头指出了什么。
- 这张图对应哪个问题。

后续如需正式保留，再把图片另存到本讨论区的 `assets/` 目录。

## 3. 建议的材料目录

如果后续图片和图表变多，可建立：

```text
phase1_cleanup_phase2_method/
  assets/
    001_user_screenshot_wencai_source.png
    002_claude_tree_network_path.png
  rounds/
```

当前先不强制创建 `assets/`，需要时再建。

## 4. 每轮笔记格式

每轮讨论建议使用：

```markdown
# Round N: 主题

## 人类原始问题

原文或摘要。

## 附图/截图说明

- 图1：说明什么。
- 图2：说明什么。

## codext 清理后的问题

整理成 Claude 分析师可以回答的问题。

## Claude 分析师回答

引用或链接 Claude 写入的文件。

## codext 独立见解

- 同意什么。
- 不同意什么。
- 哪些缺代码证据。
- 哪些需要后续进入开发计划。

## 人类签收/追问

记录人类是否认可，是否继续追问。
```

## 5. 重要规则

- 不把聊天窗口里的散答当正式结论。
- 不把没有证据的图示当代码事实。
- 不把 Claude 或 Codex 的推断当签收结果。
- 所有重要结论必须能追到文件、代码、运行结果、人类需求或截图说明。

