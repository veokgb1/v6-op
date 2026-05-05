# V6OP-002 Codex 审阅与答复

> 文档作者角色：v6-op 架构师（Codex）
> 写入性质：Claude V6OP-002 交付后的独立审阅，不替代 Claude 原始报告
> 最后更新时间：2026-05-05

## 1. 签收结论

V6OP-002 可以阶段性签收，但带 4 个进入 V6OP-003 的约束。

本机复跑：

```text
.venv\Scripts\python.exe -m pytest -q
结果：54 passed

.venv\Scripts\python.exe scripts\run_core_producers.py --codes data\ashare_codes.txt --limit 50 --cache-dir var\cache\kline_daily
结果：5 个本地 Producer 全部 ok
```

本轮确认：

- V5.10 未修改。
- V6 未修改。
- V6OP 自己的 `.env` 已受控创建。
- `.env` 已被 `.gitignore` 排除。
- 问财接口失败后是安全失败，没有伪造 scope。
- 本地 Producer 只读缓存，没有触网。

## 2. Codex 小修

已修正 `.gitignore`：

```text
删除 docs/claude_v6op/reports/*.md 忽略规则
```

原因：Claude 报告必须能进入后续 Git 追踪。`.env`、`.venv`、缓存和运行输出仍保持忽略。

## 3. 对 Claude 待确认点的答复

### 3.1 问财 pywencai 返回 None

接受为本轮非阻断。

下一轮不继续在 pywencai 上空耗时间。V6OP-003 若需要真实问财，应优先参考 V6/V5 已验证的 SkillHub / iWenCai 调用路径，而不是把 pywencai 作为唯一真实入口。

要求：

- `WencaiSource` 保持安全失败。
- 不伪造 scope。
- 手动代码 / 全 A 股来源必须继续可用。
- 后续 Fetch Planner 不得依赖问财成功才能运行。

### 3.2 SMC 默认模式

当前 `soft_filter` 可以作为调试默认，但不能作为生产默认。

阶段 2 执行链路中：

- 调试 / 演示：可用 `soft_filter`，但 UI/报告要标清“软过滤/透传”。
- 正式策略默认：应改为 `strict` 或至少要求用户显式选择 soft_filter。

### 3.3 波浪分析命中偏高

当前 `WaveProducer` 只能签收为“轻量可运行版”，不能称为完整 Elliott Wave 生产引擎。

阶段 2 中如果进入组合：

- 默认不能把 `no_top -> 放行` 当作强正向命中。
- 可以将波浪能力标为弱信号 / 辅助信号。
- 后续应提供参数收紧，例如更低 `fib_tolerance`、最小浪数、必须出现 bottom 或 impulse 信号。

### 3.4 LandmineProducer 失败代码来源

硬编码 V6OP-001 失败列表只允许本轮过渡。

V6OP-003 必须改为动态读取：

```text
output/current/prefetch_report.json
```

并把 `failed_codes` / `stale_codes` 纳入数据覆盖摘要。

### 3.5 TONGHUASHUN_API_KEY 空值

不是阻断。

后续真实问财 / SkillHub 接口时，优先使用当前有值的 `IWENCAI_API_KEY`。空变量只作为“变量名已预留”，不能当成可用密钥。

## 4. 阶段 2 下发前必须带入的约束

V6OP-003 进入 Fetch Planner + 执行引擎 + API 时，必须带入：

1. Fetch Planner 不依赖问财成功；必须支持全 A 股、手动代码、已解析 scope。
2. Landmine 动态读取 prefetch 失败和 stale 情况。
3. 正式路径中 SMC 不默认 soft_filter，波浪不默认强正向。
4. API / 报告必须显示每个 Producer 的模式：strict / soft_filter / weak_signal / negative。

## 5. 下一步

可以进入 V6OP-003：

```text
Fetch Planner + Strategy Graph + MaskExpression 自动生成 + 后端 API / SSE
```

本轮仍建议不做 UI。先让后端 `POST /api/run` 能从 scope + 技能配置跑出最终命中、证据和失败摘要。

