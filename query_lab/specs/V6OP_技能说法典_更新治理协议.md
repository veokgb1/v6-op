# V6OP 技能说法典更新治理协议

## 核心原则

技能说法典不是普通字典，也不是测试器可以随便覆盖的缓存。

它是 V6OP 后续策略台、输入工坊、P1-P6、自然语言过滤器要引用的“规则法典”。因此必须支持：

```text
测试证据
-> 候选变更
-> 冲突检查
-> 人工确认
-> 正式发布
-> 版本留痕
-> 可回滚
```

## 人工修改与自动测试必须分层

人工修改不能直接覆盖正式法典。自动测试也不能直接覆盖正式法典。

建议分层：

```text
canon/
  skills/
    astock_问财选A股/
      canon.csv
      canon.md
      versions/
      changelog.md
      evidence_index.jsonl

    sector_问财选板块/
      canon.csv
      canon.md
      versions/
      changelog.md
      evidence_index.jsonl

  review_queue/
    candidate_changes.jsonl

  manual_overrides/
    manual_overrides.csv

  conflicts/
    conflict_report.md
    conflict_items.jsonl
```

含义：

```text
canon.csv：正式法典，系统引用入口
versions/：历史版本，支持回滚
evidence_index.jsonl：每条法典对应哪些 run_id / query_id / 结果
candidate_changes.jsonl：测试器提出的候选更新，还没正式生效
manual_overrides.csv：人工指定的临时覆盖或强制规则
conflict_report.md：冲突报告
```

## 正式法典字段

每条法典项建议包含：

```text
canon_id
skill_key
skill_name_zh
op_domain
op_topic
meaning_zh
canonical_query_text
allowed_variants
risky_variants
forbidden_variants
reference_mode
evidence_level
status
risk_level
last_verified_run_id
last_verified_at
version
supersedes
deprecated
reviewer
review_reason
notes
```

## 引用方式

```text
strong / 强引用
  系统自动生成 Query、P1-P6、输入工坊推荐时必须优先使用。

weak / 弱引用
  系统优先建议，但用户可以绕过直接跑。

manual / 手动引用
  只给人看或手动选择，不自动生成。

pending / 待测
  只在待测库里，不进入正式法典。

forbidden / 禁用
  系统不得自动生成，只能作为反例。
```

## 更新流程

### 1. 测试器只生成候选变更

测试器运行后，只能写：

```text
canon/review_queue/candidate_changes.jsonl
```

不得直接改：

```text
canon/skills/*/canon.csv
```

### 2. 候选变更必须带证据

每个候选变更必须包含：

```text
change_id
change_type
canon_id
skill_key
skill_name_zh
meaning_zh
old_value
new_value
evidence_run_ids
evidence_query_ids
success_rate
none_count
error_count
empty_count
reason
created_at
status
```

`change_type` 可选：

```text
add
update
deprecate
promote_to_strong
downgrade_to_weak
mark_risky
mark_forbidden
```

### 3. 人工确认后才发布

必须支持命令或程序入口：

```text
canon propose
canon lint
canon diff
canon promote --reviewer "user" --reason "..."
canon rollback --version "..."
```

发布时：

1. 保存旧版到 `versions/`
2. 写入 `changelog.md`
3. 更新 `evidence_index.jsonl`
4. 更新正式 `canon.csv`

## 人工覆盖规则

人工覆盖不等于正式真理。人工覆盖必须单独记录：

```text
manual_overrides.csv
```

字段：

```text
override_id
canon_id
skill_key
override_type
override_value
reason
created_by
created_at
expires_at
status
notes
```

`override_type` 示例：

```text
force_strong
force_weak
force_forbidden
temporary_query
bypass_canon
```

人工覆盖可以让用户临时跑，但不能无证据地污染正式法典。

## 冲突检测

程序必须检测至少以下冲突：

1. 同一个 `meaning_zh` 出现多个 `canonical_query_text`，且都标记 strong。
2. 同一句 `canonical_query_text` 对应多个不同语义。
3. 同一句话同时出现在 allowed/risky/forbidden。
4. `astock / 问财选A股` 的说法被误放到 `sector / 问财选板块`。
5. `sector / 问财选板块` 的说法被误放到 `astock / 问财选A股`。
6. 人工覆盖与测试证据冲突。
7. 新测试结果显示某条 strong 说法失败率升高。
8. 新增条件与已有条件语义冲突，例如“小盘股”却配“大市值”。
9. 旧版本 stable，新版本 risky，需要人工复核。

冲突必须写入：

```text
canon/conflicts/conflict_items.jsonl
canon/conflicts/conflict_report.md
```

## 法典会不会自动更新

结论：法典可以自动提出更新，但不能自动发布正式更新。

允许自动：

```text
生成候选
生成证据
生成 diff
生成冲突报告
建议升级/降级/禁用
```

不允许自动：

```text
静默覆盖正式 canon.csv
静默删除旧条目
无人工确认地把 pending 升为 strong
无证据地把 risky 改为 stable
```

## 程序必须具备的功能

建议实现：

```text
scripts/canon_manager.py
scripts/canon_linter.py
scripts/canon_diff.py
scripts/canon_promote.py
scripts/canon_rollback.py
```

最少也要在总测试器中提供对应子命令。

## 最终目标

技能说法典要解决的是：

```text
这句话能不能问？
应该问 A股 还是问板块？
哪种中文说法最稳？
证据来自哪次测试？
是否允许系统自动引用？
如果以后测试结果变了，怎么更新和回滚？
```

只有这样，V6OP 后续 21 个技能扩展时，才不会越测越乱。
