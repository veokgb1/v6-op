# V6OP QueryLab — 中文问财 Query 实验体系

## 定位

这是 V6OP 的长期 OP 基础设施，不是一次性测试脚本。

目标：把模糊的中文金融想法沉淀为可验证、可复测、可对表的问财 Query 知识库。

```
用户自然语言
→ 中文 Query 候选
→ 问财实测
→ 结果分类（stable / risky / failed / forbidden / invalid_query）
→ 技能说法典
→ P1-P6 / 输入工坊 / 策略台可引用规则
```

## 项目边界

只允许修改 `F:\v.6\v6-op`，不得修改 `F:\v.6\v6` 或 `F:\v.6\v5.10`。

实验结果只写入 `query_lab/results/` 和 `query_lab/reports/`，不写主策略台 `output/current/`。

## 目录结构

```
query_lab/
  README.md                   本文件
  registry/
    skills_registry.csv       技能总注册表（21个技能的入口）
    fields_registry.csv       字段注册表
    query_templates.csv       Query 模板
    status_rules.json         状态分类规则
  cases/
    astock_问财选A股/          A股测试用例
      A1_basic.csv            基础单字段测试
      A2_synonym.csv          同义表达测试
      A3_combo.csv            组合阶梯测试
      A4_risky.csv            高风险/危险词测试
      A5_forbidden.csv        禁止案例（英文查询等）
    sector_问财选板块/          板块测试用例
      S1_basic.csv            板块基础测试
      S2_synonym.csv          板块同义表达测试
      S3_combo.csv            板块组合阶梯测试
      S4_risky.csv            板块危险词测试
    daily_kline_日线/          日线（占位）
    quote_行情/                行情（占位）
    extensions/
      pending_queries.csv     待测语义队列（KDJ/MACD/JMA等）
  scripts/
    run_query_lab.py          主入口
    query_runner.py           查询执行器
    result_analyzer.py        结果分类器
    report_writer.py          报告生成器
    canon_manager.py          法典管理器
    canon_linter.py           法典 Linter
    canon_diff.py             法典 Diff
    canon_promote.py          法典发布
    canon_rollback.py         法典回滚
    validators/
      chinese_query_validator.py  中文 Query 预检器
      schema_validator.py         Schema 校验器
    adapters/
      wencai_astock_adapter.py    问财选A股适配器
      wencai_sector_adapter.py    问财选板块适配器（含 zhishu fallback）
      daily_kline_adapter.py      日线占位
      quote_adapter.py            行情占位
  results/
    runs/                     每次运行独立目录
    latest/                   最近一次运行结果
  reports/
    stable_dictionary.md      稳定表达字典
    risk_dictionary.md        风险表达字典
    p1_p6_recommendation.md   P1-P6 候选建议
    query_normalizer_rules.md 改写规则候选
  canon/
    skills/
      astock_问财选A股/         A股法典
      sector_问财选板块/        板块法典
    review_queue/             候选变更队列（不直接修改正式法典）
    manual_overrides/         人工覆盖记录
    conflicts/                冲突报告
  specs/                      规格文件（只读）
  tests/
    test_query_lab.py         离线 pytest 测试
```

## 快速开始

### 1. 运行离线测试（无需 API Key）

```powershell
Set-Location F:\v.6\v6-op
.\.venv\Scripts\python.exe -m pytest query_lab\tests\test_query_lab.py -v
```

### 2. 列出将要跑的 Query（干跑，不调用问财）

```powershell
Set-Location F:\v.6\v6-op
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py --dry-run --route all --limit 20
```

### 3. 实测 A股基础测试（需要 IWENCAI_API_KEY）

```powershell
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py --route astock --group A1_basic --limit 20 --repeat 1 --sleep-ms 1500
```

### 4. 实测板块基础测试

```powershell
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py --route sector --group S1_basic --limit 10 --repeat 1 --sleep-ms 1500
```

### 5. 法典治理

```powershell
# 查看候选变更
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py canon propose

# 检查法典一致性
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py canon lint

# 查看差异
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py canon diff

# 发布到法典（需要人工确认）
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py canon promote --skill astock --reviewer "user" --reason "初次发布"

# 回滚
.\.venv\Scripts\python.exe .\query_lab\scripts\run_query_lab.py canon rollback --skill astock
```

## 中文 Query 硬约束

1. 所有发给问财的 `query_text` 必须是中文金融自然语言
2. 禁止英文整句（如 `A-shares with market cap...`）
3. 允许的英文缩写：A股、ST、MACD、KDJ、KD、PE、PB、ROE、ETF、BOLL、JMA
4. 英文整句查询会被 `invalid_query` 拦截，不会发送给问财

## 状态说明

| 状态 | 中文 | 说明 |
|------|------|------|
| stable | 稳定 | 实测可靠，可进入 P1-P6 候选 |
| unstable | 不稳定 | 结果忽有忽无 |
| risky | 高风险 | 含模糊/危险词，只能手动引用 |
| failed | 失败 | 返回 None / empty / error |
| forbidden | 禁用 | 明确禁止，只作为反例 |
| invalid_query | 非法查询 | 不含中文或含英文整句，不发给问财 |
| pending | 待测 | 尚未实测 |

## 法典更新规则

测试器 → `canon/review_queue/candidate_changes.jsonl` （候选）  
人工确认 → `canon promote` → `canon/skills/*/canon.csv` （正式）

**不允许**：测试器直接覆盖正式法典 `canon.csv`。

## 追加新技能或新中文问法

1. 在对应 `cases/` 目录下新增或追加 CSV 行
2. 如是全新技能，先在 `registry/skills_registry.csv` 登记
3. 未验证的语义先进入 `cases/extensions/pending_queries.csv`
4. 运行测试后通过 `canon propose → lint → promote` 发布到法典

## 数据流

```
cases/*.csv
  → QueryRunner（中文预检 + 路由）
  → Adapter（问财 API）
  → query_results.jsonl（runs/run_YYYYMMDD_HHMMSS/）
  → ResultAnalyzer（分类）
  → candidate_changes.jsonl（review_queue/）
  → ReportWriter（reports/）
  → [人工审核]
  → canon promote
  → canon.csv（正式法典）
```
