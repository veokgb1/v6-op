# V6OP-024 V6OP-023 验收偏差修正包

> 指令发出：Codex / V6OP 新架构师  
> 执行对象：Claude / V6OP 新代码师  
> 工作目录：`F:\v.6\v6-op`  
> 报告路径：`F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-024_v6op023_acceptance_fixes_report.md`

---

## 一、任务性质

这轮不是新增功能，也不是写报告轮，是修正 V6OP-023 的验收偏差。

请完成以下 5 项：

1. 技能 catalog 必须从 V6 JSON 真实装载，不再手写灰卡。
2. Mask cache 必须在 `prefetch_triggered=False` 时也使用真实 K 线数据日期。
3. `verify_prefetch_300` 必须支持 timeout、partial JSON、worker 清理，并重新跑 20 和 300。
4. HTTP smoke 只能叫 HTTP smoke，补真实浏览器 smoke；不可用就输出 `browser_unavailable`，不能冒充通过。
5. 清理 pytest 的 Windows GBK 子进程 warning。

---

## 二、报告要求

完成后报告写到：

```text
F:\v.6\v6-op\docs\claude_v6op\reports\V6OP-024_v6op023_acceptance_fixes_report.md
```

报告必须列出：

1. 修改文件；
2. 五项修正逐项状态；
3. 20/300 预热结果；
4. 浏览器 smoke 状态；
5. pytest / node 结果。

签名：

```text
Claude / V6OP 新代码师
V6OP-024 V6OP-023 验收偏差修正包
```
