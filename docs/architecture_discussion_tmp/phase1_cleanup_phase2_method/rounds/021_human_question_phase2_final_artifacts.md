# Round 007: 第二阶段最终交付物收口

本轮讨论输入文件：

```text
F:\v.6\v6-op\docs\architecture_discussion_tmp\phase1_cleanup_phase2_method\rounds\021_human_question_phase2_final_artifacts.md
```

请 Claude 分析员把正式回复写入：

```text
F:\v.6\v6-op\docs\architecture_discussion_tmp\phase1_cleanup_phase2_method\rounds\022_claude_analyst_response_phase2_final_artifacts.md
```

## 给 Claude 分析员

请先读取：

```text
F:\v.6\v6-op\docs\architecture_discussion_tmp\phase1_cleanup_phase2_method\rounds\020_claude_analyst_response_phase2_full_scope_development_plan.md
```

必要时参考：

```text
F:\v.6\v6-op\docs\architecture_discussion_tmp\phase1_cleanup_phase2_method\rounds\015_claude_analyst_response_phase2_scope_goals_alignment.md
F:\v.6\v6-op\docs\architecture_discussion_tmp\phase1_cleanup_phase2_method\rounds\012_claude_analyst_response_phase1_architecture_summary.md
F:\v.6\v6-op\v6-op_full_rescue_charter.md
```

本轮是第二阶段架构讨论的收口轮。请不要继续展开新讨论，不要新增新目标，不要写代码。

你需要基于 `020` 输出三类最终交付物：

1. **第二阶段升级大纲**
2. **给代码执行 Claude 的具体升级提示词**
3. **检测依据 / 验收依据**

输出完成后，请明确写：

```text
Claude 分析员本轮讨论任务完成，可以退出。
```

## 一、请输出《V6OP 第二阶段升级大纲》

这份大纲要像第一阶段原始大纲一样，用来给后续所有开发和第三阶段交接对齐。

请包含：

1. 第二阶段总宗旨。
2. 第二阶段为什么存在。
3. 第二阶段要解决的用户问题。
4. 第二阶段不是什么。
5. 第二阶段 8 个大目标。
6. Pass 1 / Pass 2 / Pass 3 的关系。
7. 主操盘台动线原则。
8. 管理中心边界。
9. Bridge Capability 定义。
10. Data Provenance 定义。
11. 分层问题定位解释器定义。
12. 第二阶段完成后，第三阶段才能接什么。

要求：

- 不要写成技术 bug 清单。
- 要写成能作为阶段章程的大纲。
- 但每个关键判断要能追溯到 `020` 的目标与验收。

## 二、请输出“给代码执行 Claude 的具体升级提示词”

这不是泛泛计划，而是可以复制给代码执行 Claude 的完整提示词。

要求：

- 一次性给足第二阶段完整范围。
- 明确按 `020` 的 Pass 1 / Pass 2 / Pass 3 检查点推进。
- 明确不能砍目标、不能缩范围。
- 明确 G8 图执行器如果出现严重回归，允许作为 Pass 3 单独修，但不能永久后置。
- 明确要改哪些模块。
- 明确要产出哪些报告字段。
- 明确前端要出现哪些区域。
- 明确必须跑哪些验收。

请把提示词写成一个完整代码块，标题为：

```text
给代码执行 Claude 的第二阶段升级提示词
```

## 三、请输出“检测依据 / 验收依据”

请回答：第二阶段完成后，我们凭什么判断它真的完成了？

请不要只写“测试通过”。请按以下结构列清楚：

1. 验收依据来自哪里：
   - 原始大纲；
   - 第一阶段风险审计；
   - `020` 的 8 个大目标；
   - 用户真实事故：问财跑空、scope 为 0、命中 0 不可解释。

2. 每个目标的检测依据：
   - 需要看哪个页面变化；
   - 需要看哪个报告字段；
   - 需要看哪个日志；
   - 需要运行哪个典型场景；
   - 什么结果算通过；
   - 什么结果算失败。

3. 必须覆盖这些场景：
   - 问财返回 0；
   - 问财返回少量，例如 45；
   - 问财接近上限或触发截断；
   - 全A 5000；
   - days=365 与 days=730；
   - K线本地已有 / 新拉 / 失败 / 旧数据；
   - 技能筛空；
   - 顺序路径筛空；
   - 并行交集为空；
   - 排雷剔除；
   - Bridge constrained mode；
   - Bridge second-pass mode；
   - abort；
   - 分层缓存清理；
   - 历史记录恢复参数；
   - G8 三路径统一后无回归。

4. 请输出一张总验收表：

```text
验收项 | 检测方式 | 通过标准 | 对应目标 | 失败时说明
```

## 四、请最后给出你的收口判断

请回答：

1. `020` 的开发计划是否可以作为第二阶段开发依据？
2. 这轮输出的升级大纲、升级提示词、检测依据是否足以交给代码执行 Claude？
3. 是否还需要继续架构讨论？

如果你认为还缺东西，请只列“缺什么”，不要展开新方案。

最后请明确写：

```text
Claude 分析员本轮讨论任务完成，可以退出。
```
