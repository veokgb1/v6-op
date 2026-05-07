# V6-OP 数据源入口治理方案

日期：2026-05-07  
范围：只适用于 `F:\v.6\v6-op`，不修改 `v6` / `v5.10` 参考目录。

## 1. 为什么必须治理

当前 V6-OP 已经能跑，但数据入口存在混用风险：

- 官方问财技能声明指向 `openapi.iwencai.com`。
- 当前代码实际通过 `pywencai` 访问 `www.iwencai.com` 网页接口。
- K线行情数据又使用 `baostock / akshare / yfinance`。
- 问财板块在 `sector / zhishu` 之间 fallback。
- 技能计算阶段读取本地 K线，但报告里必须清楚说明这些 K线来自哪里。

如果不统一治理，后续会出现：

- 同一功能今天走 A 入口、明天走 B 入口。
- 报告无法解释数据事实来自哪里。
- 问财失败时误判为语法失败。
- K线缺失时误判为策略失败。
- 后续新增技能时重复造入口，系统越来越乱。

本文件用于把入口、备用、失败、报告、测试全部对齐。

## 2. 当前真实入口

### 2.1 问财选 A 股

当前代码：

- `scripts/sources/wencai_source.py`
- `query_lab/scripts/adapters/wencai_astock_adapter.py`

当前实际入口：

```text
www.iwencai.com
```

当前调用链：

```text
pywencai.get(query=..., query_type="stock")
  -> http://www.iwencai.com/customized/chart/get-robot-data
  -> http://www.iwencai.com/gateway/urp/v7/landing/getDataList
```

当前认证现实：

```text
.env 中有 IWENCAI_API_KEY
但当前 pywencai 路径并不把 api_key 作为官方 OpenAPI 参数传入
实际依赖 pywencai / iwencai 网页 session、cookie、hexin-v token
```

风险：

- 不是官方 SkillHub OpenAPI 链路。
- session 可能耗尽。
- 接口可能限速。
- 返回字段可能变化。
- timeout 不等于语义错误。

### 2.2 问财选板块

当前代码：

- `scripts/sources/sector_scan_source.py`
- `query_lab/scripts/adapters/wencai_sector_adapter.py`

当前实际入口：

```text
www.iwencai.com
```

当前 fallback：

```text
pywencai.get(query=..., query_type="sector")
如果失败或空结果：
pywencai.get(query=..., query_type="zhishu")
```

风险：

- `sector` / `zhishu` 的返回字段不同。
- 板块名称字段提取不稳定。
- 需要把“实际命中的 backend”写入报告。

### 2.3 手动输入股票代码

当前代码：

- `scripts/source_resolver.py`

当前入口：

```text
用户手动输入代码
```

处理逻辑：

```text
000001 -> 000001.SZ
600000 -> 600000.SH
北交所 8/4 开头 -> BJ
```

风险：

- 输入格式不标准时需要明确提示。
- 手动代码池不应访问问财。

### 2.4 全 A 股

当前代码：

- `scripts/source_resolver.py`

当前入口：

```text
data/ashare_codes.txt
```

风险：

- 这不是实时问财。
- 文件更新频率必须被报告记录。
- 全量跑时不能再假装来自问财。

### 2.5 K线 / 行情数据

当前代码：

- `scripts/ohlcv_provider.py`
- `scripts/data_prefetch.py`

当前入口顺序：

```text
1. 本地新鲜缓存
2. baostock
3. akshare
4. yfinance
5. 本地过期缓存
6. 全部失败
```

快速全量模式：

```text
FAST_FULL_SCAN=true:
1. 本地新鲜缓存
2. baostock
3. 失败就跳过
```

风险：

- baostock 不支持或不稳定的代码要明确标记。
- akshare / yfinance 是备用，不应静默切换。
- 技能计算只应读本地 K线，不应自己直接访问外部接口。

## 3. 官方目标入口

用户提供的同花顺官方截图显示：

```text
IWENCAI_BASE_URL=https://openapi.iwencai.com
IWENCAI_API_KEY=...
SkillHub 技能：hithink-astock-selector
```

因此目标应该是：

```text
问财选 A 股主入口：openapi.iwencai.com 官方 SkillHub / OpenAPI
问财选板块主入口：openapi.iwencai.com 官方 SkillHub / OpenAPI，如官方存在对应板块技能
```

当前 `pywencai / www.iwencai.com` 不应继续伪装成官方 OpenAPI。

## 4. 目标统一规则

### 4.1 股票池入口

| 来源类型 | 主入口 | 备用入口 | 失败策略 |
|---|---|---|---|
| 手动输入 | 用户输入代码 | 无 | 格式错误则提示，不伪造 |
| 全 A 股 | `data/ashare_codes.txt` | 无 | 文件缺失则报错 |
| 问财选 A 股 | `openapi.iwencai.com` 官方 SkillHub | `www.iwencai.com / pywencai` | 明确报错，不伪造 |
| 问财选板块 | `openapi.iwencai.com` 官方 SkillHub | `pywencai sector -> zhishu` | 明确报错，不伪造 |

### 4.2 K线入口

| 数据类型 | 主入口 | 备用入口 | 失败策略 |
|---|---|---|---|
| 日线 K线 | 本地缓存 | baostock -> akshare -> yfinance | 失败标记 missing |
| 技能计算 | 本地 K线 | 无 | 不允许技能自己访问外部 |
| 报告解释 | execution_result / run_report | 无 | 必须写明 provider |

### 4.3 禁止行为

- 问财失败时禁止伪造股票池。
- K线失败时禁止用空数据继续当成功。
- 技能 producer 禁止绕过 `ohlcv_provider` 自己访问外部接口。
- 报告禁止只写“问财”，必须写实际入口。
- `IWENCAI_API_KEY` 存在但未用于官方 OpenAPI 时，报告必须说明。

## 5. 改造计划

### Phase G1：入口盘点与报告透明

目标：不立刻大改业务，只先让每次运行说清楚“实际用了谁”。

任务：

1. 新增统一入口登记表，例如：

```text
scripts/data_source_registry.py
```

2. 每个 source 返回：

```text
provider_family: wencai / kline / local
provider_name: openapi_iwencai / pywencai_www / baostock / akshare / yfinance / cache
endpoint_host: openapi.iwencai.com / www.iwencai.com / local_file / baostock
endpoint_path: ...
auth_mode: api_key / session_cookie / none
fallback_level: primary / fallback_1 / fallback_2
```

3. `run_report.py` 必须展示：

```text
股票池来源实际入口
问财实际 backend
K线实际 provider
是否发生 fallback
是否用了过期缓存
```

验收：

- 手动输入报告显示 `manual / no external source`。
- 全 A 股报告显示 `local file / data/ashare_codes.txt`。
- 问财报告显示 `www.iwencai.com / pywencai` 或未来 `openapi.iwencai.com`。
- K线报告显示 `cache / baostock / akshare / yfinance`。

### Phase G2：官方 OpenAPI 接入验证

目标：验证 `openapi.iwencai.com` 是否能替代当前 `pywencai`。

任务：

1. 新增官方 OpenAPI adapter，不能覆盖当前 pywencai。
2. 使用最小 5 条 A 股 query 做对照：

```text
今日涨幅大于3%
今日成交额大于3亿
流通市值在30亿到150亿之间
今日主力净流入为正
今日收盘价大于5日均线
```

3. 同一 query 对比：

```text
openapi_iwencai result_count
pywencai_www result_count
交集代码数量
耗时
错误类型
字段完整度
```

验收：

- 官方 OpenAPI 能返回 A 股代码。
- 返回结果可解析为统一 `000001.SZ` 格式。
- 失败时能明确区分认证失败、空结果、接口错误。

### Phase G3：问财板块入口验证

目标：确认官方 OpenAPI 是否支持板块扫描；如果不支持，明确 pywencai 板块 fallback 的规则。

测试 query：

```text
今日主力资金净流入排名前10的行业板块
近3日涨幅排名前10的概念板块
半导体相关概念板块
人工智能相关概念板块
今日成交额放大的行业板块
```

验收：

- 板块名称可稳定提取。
- `sector` 和 `zhishu` 结果要分别记录。
- 不能把指数名称、股票名称误当板块名称。

### Phase G4：K线数据源治理

目标：让 baostock / akshare / yfinance 不再“暗中切换”。

任务：

1. `ohlcv_provider.py` 每次返回必须写：

```text
df.attrs["source"]
df.attrs["fallback_level"]
df.attrs["cache_status"]
df.attrs["fetch_error"]
```

2. 报告写清楚：

```text
本轮使用缓存多少只
baostock 成功多少只
akshare 成功多少只
yfinance 成功多少只
三源失败多少只
```

3. FAST_FULL_SCAN 模式必须在报告中显式说明：

```text
快速全量模式只使用 cache + baostock，不启用 akshare/yfinance
```

验收：

- 随机 10 只股票可追溯 K线 provider。
- 北交所失败必须被标记，不能静默吞掉。
- 技能报告里能看到每个技能用了多少有效 K线。

### Phase G5：统一入口测试矩阵

目标：把入口治理纳入固定测试，防止以后改乱。

测试分组：

```text
DG1_manual_source
DG2_all_a_source
DG3_wencai_astock_openapi
DG4_wencai_astock_pywencai_fallback
DG5_wencai_sector
DG6_kline_provider_fallback
DG7_report_traceability
```

每组至少验证：

```text
入口是否正确
fallback 是否可见
失败是否明确
报告是否可追溯
是否禁止伪造结果
```

## 6. 今天必须完成的落地项

今天至少完成：

1. 本治理文件确认。
2. 梳理现状入口与目标入口。
3. 决定问财主入口是否切到 `openapi.iwencai.com`。
4. 如果切，先做官方 OpenAPI 最小验证，不直接替换生产路径。
5. 新建入口测试矩阵任务单。
6. 后续任何问财法典测试报告，都必须写明实际入口：

```text
official_openapi_iwencai
或
pywencai_www_iwencai
```

## 7. 后续 Claude 执行要求草案

给 Claude 的执行原则：

```text
你只操作 F:\v.6\v6-op。
先不要替换现有生产入口。
先新增 data source governance / registry / diagnostics。
所有外部入口必须命名、记录、报告。
官方 openapi.iwencai.com 与当前 pywencai/www.iwencai.com 必须分开测试。
不要把 pywencai 叫成官方 OpenAPI。
不要在问财失败时伪造股票池。
不要让技能 producer 自己访问外部行情。
每一条测试都要输出实际 endpoint_host、auth_mode、fallback_level。
```

## 8. 当前结论

现在的系统不是完全错，但入口边界不够干净。

当前可继续用 `pywencai / www.iwencai.com` 做问财语法摸底，但在正式架构上必须改成：

```text
官方 OpenAPI 优先
pywencai 网页接口备用
baostock/akshare/yfinance 只负责 K线行情
技能只读本地 K线
报告必须全链路可追溯
```

