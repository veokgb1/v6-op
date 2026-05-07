# Claude 执行单：A12 代码池复问修复专项

## 0. 目标

只修一个问题：`问财选A股` 是否支持“指定股票代码池后再问条件”。

第三阶段 A12 的结论是：把代码池直接写进中文句子里，基本失败。现在不要直接宣布放弃，必须再做 3 类最小压力测试：

1. 中文 query 写法修复。
2. `pywencai.get(..., find=代码列表)` 专项测试。
3. 如果问财仍不支持，确认 pipeline 方案：应用层 intersection。

补充要求：同时做少量“非代码池缩圈对照”，验证失败到底来自代码池复问，还是来自“近5日平均成交额 1.5 倍”这一类相对字段本身。

只操作：

```powershell
F:\v.6\v6-op
```

不要修改 V5/V6。不要 promote 法典。

## 1. 先读已有结论

先读取：

```text
F:\v.6\v6-op\query_lab\reports\astock_ceiling_report.md
F:\v.6\v6-op\query_lab\cases\astock_问财选A股\A12_code_pool_requery.csv
F:\v.6\v6-op\query_lab\results\runs\run_20260507_163617\analyzed_results.jsonl
```

确认 A12 原失败方式：

```text
在以下股票代码中，哪些...
```

这类问法失败，不代表所有代码池复问都失败。

## 2. 测试一：中文写法修复

新增一个专项 CSV：

```text
F:\v.6\v6-op\query_lab\cases\astock_问财选A股\A12R_code_pool_repair.csv
```

沿用现有 CSV 表头，UTF-8 with BOM。

只做少量，最多 8 条。重点是不同写法，不要扩大范围。

建议 query：

```text
股票代码为000060或603399，今日成交额大于近5日平均成交额1.5倍
证券代码为000060或603399，今日成交额大于近5日平均成交额1.5倍
000060或603399，今日成交额大于近5日平均成交额1.5倍
科创板，今日成交额大于近5日平均成交额1.5倍
股票代码是000060、603399、600519、000858，今日成交额大于近5日平均成交额1.5倍
股票简称为中金岭南或抚顺特钢，今日成交额大于近5日平均成交额1.5倍
股票代码为000060，今日成交额大于近5日平均成交额1.5倍
股票代码为603399，今日成交额大于近5日平均成交额1.5倍
股票代码为600519，今日成交额大于近5日平均成交额1.5倍
军工板块，今日成交额大于近5日平均成交额1.5倍
军工板块，今日成交额大于近5日平均成交额1.5倍，MACD金叉
军工板块，今日成交额大于近5日平均成交额1.5倍，KDJ金叉
军工板块，今日成交额大于近5日平均成交额1.5倍，MACD在零轴之上
```

注意：

- `000060` 和 `603399` 是前面 A11 已经命中过的示例代码。
- `600519`、`000858` 作为对照。
- 如果“股票简称”写法可用，也要记录，但不优先推荐，因为简称会重名。
- `科创板 / 军工板块` 是非代码池缩圈对照；如果它们成功而代码池失败，说明问题集中在代码池复问，不是相对成交额字段。
- 技术指标对照只做 MACD/KDJ/零轴，目的只是最后确认“缩圈 + 相对成交额 + 技术指标”能否问，不要扩展成新一轮技术指标大测。

运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\query_lab\scripts\query_lab_guard.ps1 -Action start -Route astock -Group A12R_code_pool_repair -Limit 0 -SleepMs 3000 -FetchLimit 100 -QueryTimeoutSec 45
```

## 3. 测试二：pywencai find 参数专项

这一步不要通过 CSV runner 硬塞，因为现有 QueryRunner 不支持 `find` 字段。

新建一个最小专项脚本：

```text
F:\v.6\v6-op\query_lab\scripts\test_wencai_find_code_pool.py
```

脚本只做这件事：

```python
import pywencai

codes = ["000060", "603399", "600519", "000858", "600036", "601318", "000333", "600276", "000001", "600000"]
query = "今日成交额大于近5日平均成交额1.5倍"

result = pywencai.get(
    query=query,
    query_type="stock",
    find=codes,
    perpage=100,
    page=1,
)
```

然后再测：

```python
query = "今日收盘价大于5日均线"
query = "近10日有涨停"
query = "今日成交额大于近5日平均成交额1.5倍，今日收盘价大于5日均线"
```

必须输出：

```text
query
find_codes
returned_codes
result_count
elapsed_ms
raw_columns
status
raw_error
```

输出目录：

```text
F:\v.6\v6-op\query_lab\results\code_pool_repair\
```

必须保存：

```text
find_test_results.jsonl
find_test_report.md
```

判定：

- 如果 `find=` 能尊重代码池并返回命中代码，说明要改 QueryRunner / adapter 支持 `find_codes`。
- 如果 `find=` 也失败，说明当前 pywencai 网页接口不适合代码池复问。
- 如果返回了代码池外股票，判定为不可用。

## 4. 测试三：应用层 intersection 方案确认

如果测试一和测试二失败，给出 pipeline 收口方案：

```text
不要再让问财做代码池复问。
先问财全局/缩圈得到候选股票池。
然后在 V6-OP 应用层用 set intersection 与已有代码池取交集。
后续 K线条件全部走本地 K线技能。
```

必须回答：

```text
1. 问财代码池复问是否支持？
2. 支持的是哪一种方式：中文 query / pywencai find / 都不支持？
3. 如果支持，应该怎么改 adapter？
4. 如果不支持，pipeline 应该怎么收口？
5. A12 法典最终标记：strong / weak / forbidden / app_layer_only？
6. 科创板/军工板块缩圈下，相对成交额 1.5 倍是否仍可用？
7. 军工板块 + 相对成交额 + MACD/KDJ/零轴 是否可作为弱引用或必须拆问？
```

## 5. 验收报告

完成后给出：

```text
新增/修改文件
A12R run_id
find 专项脚本输出目录
每种写法结果
最终建议
```

不要继续跑 A13/A14/A15。不要自动入正式法典。
