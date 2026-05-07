# 问财选A股 法典

**skill_key**: astock  
**skill_name_zh**: 问财选A股  
**版本**: v1（初始）  
**状态**: 空法典，等待实测后通过 `canon promote` 写入

## 说明

本法典记录同花顺问财中用于选A股的中文问法，包含：

- `canonical_query_text`：标准中文问法
- `allowed_variants`：允许的同义变体（`|` 分隔）
- `risky_variants`：危险变体（需人工复核）
- `forbidden_variants`：禁用变体（不得自动生成）
- `reference_mode`：strong / weak / manual / pending / forbidden
- `evidence_level`：none / auto_test / multi_run / manual_confirmed

## 引用规则

| 引用模式 | 说明 |
|---------|------|
| strong | 系统自动生成 Query、P1-P6 优先使用 |
| weak | 系统优先建议，用户可绕过 |
| manual | 只给人看，不自动生成 |
| pending | 待实测，不进入系统 |
| forbidden | 禁用，只作为反例 |

## 当前条目

*法典为空。请运行实测后执行 `canon propose` → `canon lint` → `canon promote`。*
