# 第一阶段清理与第二阶段开发方法建立

这是 V6OP 的临时架构讨论工作区。

本区用途：

- 清理第一阶段真实完成情况。
- 梳理用户实际痛点和需求。
- 讨论第一阶段大纲、实现、用户体验之间的差距。
- 建立第二阶段开发宗旨、开发方法和开发计划。
- 在形成共识前，不向代码执行方下达施工命令。

本区不是：

- 不是正式开发命令区。
- 不是代码修改区。
- 不是最终签收报告区。
- 不是 Claude 或 Codex 自由发挥的聊天草稿区。

正式参考材料只读，不在本区改写：

```text
F:\v.6\v6-op\v6-op_full_rescue_charter.md
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-026_final_first_stage_signoff_report.md
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-030_full_logic_risk_audit.md
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-031_phase1_work_summary_report.md
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-032_code_alignment_guidelines_report.md
```

目录结构：

```text
phase1_cleanup_phase2_method/
  000_discussion_workspace_readme.md
  001_roles_and_response_protocol.md
  002_evidence_and_code_reading_rules.md
  003_required_and_forbidden_scope.md
  004_reference_materials_index.md
  005_note_capture_and_discussion_artifacts.md
  rounds/
```

讨论文件命名规则：

```text
rounds/001_human_question_<topic>.md
rounds/002_claude_analyst_response_<topic>.md
rounds/003_codex_architect整理_<topic>.md
rounds/004_human_signoff_or_followup_<topic>.md
```

每一轮必须能看出：

- 人类提出了什么问题。
- Claude 分析师如何回答。
- Codex 架构师如何整理、质疑、归类。
- 人类是否签收、追问或否决。

特殊称呼规则：

- 当人类在对话中用 `codext` 作为前缀或称呼时，Codex 的职责进入“架构整理者”模式。
- `codext` 不直接下达代码施工命令，除非人类明确要求。
- `codext` 的主要工作是清理人类语言、形成可交给 Claude 分析师的问题、发表独立见解、整理讨论笔记，并为后续开发任务做准备材料。
