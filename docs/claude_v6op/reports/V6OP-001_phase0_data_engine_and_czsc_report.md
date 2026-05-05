# V6OP-001 阶段 0 执行报告

> 命令：V6OP-001_phase0_data_engine_and_czsc.md
> 执行角色：Claude（claude-sonnet-4-6）
> 执行日期：2026-05-05
> 状态：COMPLETED ✓

---

## 1. 执行摘要

阶段 0 目标全部完成：

```
真实 K 线预热 ✓ → 本地 pickle 缓存 ✓ → CZSCProducer 只读缓存 ✓ → 输出 V6 Mask JSON ✓
```

---

## 2. 改了哪些文件

**新增（全部在 F:\v.6\v6-op 内）：**

| 文件 | 说明 |
|---|---|
| `requirements.txt` | 阶段 0 最小依赖 |
| `.env.example` | 环境变量模板 |
| `.gitignore` | 排除 .env/.venv/cache |
| `pytest.ini` | pytest 配置 |
| `data/ashare_codes.txt` | 从 V5 复制（纯数据，无密钥） |
| `scripts/__init__.py` | 包初始化 |
| `scripts/ohlcv_provider.py` | OHLCV 数据层（重写自 V5 shared_data.py） |
| `scripts/data_prefetch.py` | K线预热协调者/工作者（重写自 V5 prefetch_kline_cache.py） |
| `scripts/v6_compat.py` | V6 合约引用层 |
| `scripts/producers/__init__.py` | 包初始化 |
| `scripts/producers/czsc_producer.py` | CZSC Producer（重写自 V5 step2_czsc_analysis.py） |
| `tests/__init__.py` | 包初始化 |
| `tests/conftest.py` | pytest conftest |
| `tests/test_smoke.py` | 20 项 smoke tests |
| `.venv/` | Python 3.13.3 虚拟环境（V6OP 自建） |
| `var/cache/kline_daily/` | K线缓存目录（运行后有 42 只股票 pickle） |
| `output/current/prefetch_report.json` | 真实预热报告 |
| `output/current/czsc_mask.json` | CZSC Mask JSON 输出 |
| `docs/claude_v6op/latest_report.md` | 最新报告 |
| `docs/claude_v6op/current_status.md` | 当前状态 |
| `docs/claude_v6op/reports/V6OP-001_phase0_data_engine_and_czsc_report.md` | 本报告 |

**V6OP 自建 .venv 的 Python 路径：**
```
F:\v.6\v6-op\.venv\Scripts\python.exe
```

---

## 3. 没碰哪些敏感文件

| 文件/目录 | 状态 |
|---|---|
| `F:\v.6\v5.10\*` | 未修改，只读参考 |
| `F:\v.6\v6\*` | 未修改，通过 v6_compat.py 动态 import |
| `F:\v.6\v5.10\.env` | 未复制 |
| `F:\v.6\v5.10\.venv` | 未复制 |
| `F:\v.6\v6\.env` | 未复制 |
| `F:\v.6\v6\.venv` | 未复制 |
| `F:\v.6\v5.10\var` | 未复制 |
| `F:\v.6\v5.10\output` | 未复制 |

---

## 4. 安全与合规确认

| 检查项 | 结果 |
|---|---|
| 是否复制 `.env` | 否 |
| 是否复制 `.venv` | 否（V6OP 自建 .venv） |
| 是否修改 V5.10 | 否 |
| 是否修改 V6 | 否 |
| 是否真实访问外部接口 | 是（baostock API，拉取真实 K 线数据） |
| 是否读取真实密钥 | 否（baostock 不需要 API Key，免登录） |
| 是否落盘真实密钥 | 否 |
| 是否使用 fixture 冒充真实数据 | 否 |
| 是否继承 V5 Slot/漏斗池 | 否 |
| 是否写 UI | 否 |

---

## 5. 测试命令与结果

### 5.1 smoke tests

```
cd F:\v.6\v6-op
.venv\Scripts\python.exe -m pytest -q
```

**结果：**
```
20 passed in 1.46s
```

测试覆盖：
- 代码文件读取与格式验证（3项）
- ohlcv_provider 导入与缓存路径（4项）
- data_prefetch 导入与报告结构（3项）
- CZSCProducer 输出结构与 mask_id 稳定性（4项）
- V5 隔离验证（4项）

### 5.2 真实预热

```
.venv\Scripts\python.exe scripts\data_prefetch.py --codes data\ashare_codes.txt --limit 50 --days 365 --workers 8
```

**结果：**
```
总计 50 只  命中缓存 0  新拉成功 42
stale 降级 0  失败 8  耗时 3.9s
workers=8 (失败=0)
```

失败 8 只（baostock 无数据，需核查是否退市/暂停上市）：
`000025.SZ, 000034.SZ, 000049.SZ, 000062.SZ, 000035.SZ, 000063.SZ, 000089.SZ, 000068.SZ`

prefetch_report.json 路径：`output\current\prefetch_report.json`

### 5.3 CZSC Producer

```
.venv\Scripts\python.exe scripts\producers\czsc_producer.py --codes data\ashare_codes.txt --limit 50 --cache-dir var\cache\kline_daily --out output\current\czsc_mask.json
```

**结果：**
```
CZSC Producer 完成 ✓  50 → 命中 24 只
miss=26  耗时=8.5s
```

Mask JSON 验证：
- `hit_semantics: "positive"` ✓
- `data_mode: "read_cache_only"` ✓
- `czsc_version: "0.10.12"` ✓
- 24 只命中（一买/二买/三买，含信号日期和中枢证据）
- 8 只缓存未命中（即预热阶段失败的代码）
- 14 只无最近 5 根信号

---

## 6. 依赖安装情况

| 库 | 安装版本 | 状态 |
|---|---|---|
| pandas | 3.0.2 | OK |
| baostock | latest | OK |
| akshare | 1.18.60 | OK |
| czsc | 0.10.12 | OK（V5 参考用 0.9.68，但 0.10.12 向后兼容 signal 函数） |
| pytest | 9.0.3 | OK |

**czsc 版本说明：**
pip 安装了 0.10.12（非命令文件指定的 0.9.68）。
实测 `cxt_first_buy_V221126`、`cxt_second_bs_V230320`、`cxt_third_bs_V230318/V230319`、
`cxt_three_bi_V230618`、`cxt_five_bi_V230619`、`cxt_bi_base_V230228` 全部可用，信号功能正常。
建议架构师确认是否锁定到 0.9.68，还是接受 0.10.12+。

---

## 7. 阻断点

无严重阻断点。所有阶段 0 验收命令均成功执行。

**已知注意事项：**

1. **czsc 版本**：安装 0.10.12 而非 0.9.68，功能兼容但需架构师确认版本策略
2. **baostock 失败 8 只**：`000025`, `000034`, `000049`, `000062`, `000035`, `000063`, `000089`, `000068`
   可能是退市/暂停上市/数据源问题，建议排雷 Producer（阶段 1）对这类代码做自动过滤
3. **yfinance 未单独测试**：降级链三源都在代码中，但预热用 FAST_FULL_SCAN 只走 baostock；
   完整三源降级在标准模式下可用，尚未在本轮实测

---

## 8. 需要 v6-op 架构师审阅的点

1. **czsc 版本锁定策略**
   当前安装 0.10.12，requirements.txt 写的是 `czsc>=0.9.68`。
   建议：是否锁定到特定版本（如 `czsc==0.10.12`）以保证重现性？

2. **baostock 失败代码列表**
   8 只代码在 baostock 无法拉取，这些代码在 READ_CACHE_ONLY 阶段也会作为缓存未命中出现。
   建议：阶段 1 的排雷 Producer 是否应该自动过滤这类代码？

3. **V6 合约引用方式**
   v6_compat.py 通过 sys.path 动态引用 `F:\v.6\v6\scripts`。
   如果 V6 项目目录迁移，需要更新路径逻辑。
   建议：是否在 .env 中提供 `V6_SCRIPTS_PATH` 覆盖？

4. **pandas 3.0.2 兼容性**
   V5 原有代码基于 pandas 1.x/2.x API。V6OP 重写的 ohlcv_provider.py 已做适配，
   但后续阶段接更多 Producer 时需注意 pandas 3.x 的 Breaking Changes（如 DataFrame.copy 行为）。

5. **prefetch 失败率阈值**
   当前 50 只中失败 8 只（16%），接近 20% 中止阈值。
   全量 5000 只预热时，建议调整阈值或分批预热，避免单次运行因偶发失败中止。

---

## 9. 下一步建议

- **阶段 1**：实现 SMCProducer、KlineProducer、WaveProducer、LandmineProducer（负向）、WencaiSource
- 可在本轮 prefetch 的 42 只缓存代码上立即开始 Producer 开发，无需等待新一次预热
- 建议在 LandmineProducer 中首先过滤掉 baostock 无数据的代码类型

---

## 10. 文件清单

```
F:\v.6\v6-op\
├── .env.example
├── .gitignore
├── pytest.ini
├── requirements.txt
├── data\
│   └── ashare_codes.txt              (5466 只代码，从 V5 复制)
├── docs\claude_v6op\
│   ├── commands\
│   │   └── V6OP-001_phase0_data_engine_and_czsc.md
│   ├── reports\
│   │   └── V6OP-001_phase0_data_engine_and_czsc_report.md  (本文件)
│   ├── current_status.md
│   └── latest_report.md
├── output\current\
│   ├── prefetch_report.json          (真实预热报告)
│   └── czsc_mask.json                (V6 Mask JSON，24命中/26未命中)
├── scripts\
│   ├── __init__.py
│   ├── ohlcv_provider.py
│   ├── data_prefetch.py
│   ├── v6_compat.py
│   └── producers\
│       ├── __init__.py
│       └── czsc_producer.py
├── tests\
│   ├── __init__.py
│   ├── conftest.py
│   └── test_smoke.py                 (20项 smoke tests, 全部通过)
└── var\cache\kline_daily\
    └── (42只股票 pickle 缓存)
```
