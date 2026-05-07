# 给 Claude 的命令：先诊断问财选A股为什么慢，不要继续盲跑

当前只处理：

```text
workspace = F:\v.6\v6-op
skill_type = astock
skill_name_zh = 问财选A股
```

禁止碰：

```text
F:\v.6\v6
F:\v.6\v5.10
F:\New.V5.10\Old.V5
```

## 背景

`A1_basic Limit 10` 已经成功：

```text
run_20260507_141044
10 queries
10 stable
RUN_COMPLETE confirmed
```

随后启动 `A1_basic Limit 20`：

```text
run_20260507_141605
```

它跑到第 11 条后停住：

```text
A1-011  流通市值在80亿到300亿之间  stable  result_count=1580  elapsed_ms=32418.6
```

下一条应该是：

```text
A1-012  总市值在50亿到300亿之间
```

之后 jsonl 没再增长。

## 关键怀疑

请先检查程序设计，不要直接继续长跑。

重点看：

```text
query_lab/scripts/query_runner.py
query_lab/scripts/adapters/wencai_astock_adapter.py
query_lab/scripts/query_lab_guard.ps1
```

目前有一个重大怀疑：

```text
run_query_lab.py --limit 20
```

这里的 `--limit 20` 只是“跑 20 条 CSV 用例”，不是“每条问财只取 20 / 100 / 300 只股票”。

而 `WencaiAstockAdapter.query(query_text, limit=0)` 默认 `limit=0` 时：

```text
perpage = 100
max_pages = 100
```

这意味着每一条 Query 都可能翻页最多 100 页去抓股票代码。对“市值范围”这种大池子查询，可能非常慢，甚至像卡死。

这不符合 QueryLab 当前目的。当前目的不是完整取股池，而是快速验证：

```text
这句中文问法能不能被问财稳定识别
返回是否非空
大致返回数量级
耗时是否可接受
是否适合进入说法典
```

## 你要先回答的问题

请先给 Codex/用户一个明确判断：

```text
1. A1_basic Limit 20 卡在第 12 条，根因更可能是什么？
2. 是问财 session/API 问题，还是 adapter 翻页取数策略问题，还是 query_text 语义问题？
3. QueryLab “摸天花板”阶段是否应该抓全量股票代码？
4. 是否应该区分：
   - case_limit：跑多少条测试用例
   - fetch_limit：每条问财最多取多少只股票/多少页
   - query_timeout_sec：单条 Query 最大等待多久
5. 你建议的最快、最准、风险最低的跑法是什么？
```

## 修复方向

如果你的判断确认当前适配器不适合快速天花板测试，请修改程序，但不要大改架构。

建议最小修复：

```text
1. 给 run_query_lab.py 增加 --fetch-limit，默认 300 或 500。
2. 给 run_query_lab.py 增加 --query-timeout-sec，默认 60 或 90。
3. QueryRunner 调用 astock_adapter.query(query_text, limit=fetch_limit)。
4. WencaiAstockAdapter 不要在 QueryLab 默认模式下无限翻页到 max_pages=100。
5. 每条 Query 开始前写 current_query.json，包含 query_id/query_text/start_at。
6. 单条 Query 超时后写入 analyzed_results.jsonl，failure_type=timeout 或 session_error，然后继续下一条。
7. 只有完整跑完才写 RUN_COMPLETE。
```

注意：如果 Python 线程/pywencai 无法被安全中断，你也要明确说明，给出 Windows 下更可靠的 subprocess per query 方案或保守方案。

## 验证方式

修完后不要直接跑全量。

先跑离线：

```powershell
.\.venv\Scripts\python.exe -m pytest query_lab\tests\test_query_lab.py -q
```

再跑一个极小实测：

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action start -Route astock -Group A1_basic -Limit 1 -Repeat 1 -SleepMs 3000
```

确认：

```text
query_results.jsonl 有增长
analyzed_results.jsonl 有增长
RUN_COMPLETE 存在
stdout/stderr log 可看
```

然后只跑到 Limit 5。不要直接 Limit 20。

## 输出报告必须包含

```text
1. 根因判断
2. 修改了哪些文件
3. 新增参数说明：case_limit / fetch_limit / query_timeout_sec
4. A1-012 是否是语义慢、取数慢、session慢，还是未知
5. 最小验证结果
6. 下一步建议跑法
```

这一步目标是先把跑测机制变聪明，不是继续硬跑。
