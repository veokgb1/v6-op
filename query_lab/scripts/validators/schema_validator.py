"""
schema_validator.py — 测试用例行字段校验器

校验每行测试用例 CSV 中必须字段是否存在，skill_type 是否合法等。
"""
from __future__ import annotations

from dataclasses import dataclass, field

REQUIRED_FIELDS = [
    "query_id", "skill_type", "skill_name_zh", "op_domain",
    "test_group", "category", "query_text", "normalized_intent",
    "status",
]

VALID_SKILL_TYPES = {"astock", "sector", "daily_kline", "quote",
                     "technical_indicator", "capital_flow"}

VALID_STATUSES = {
    "pending", "testing", "stable", "unstable", "risky",
    "failed", "forbidden", "invalid_query",
}


@dataclass
class SchemaValidationResult:
    valid: bool
    query_id: str = ""
    errors: list[str] = field(default_factory=list)


class SchemaValidator:
    """测试用例行 schema 校验"""

    def validate_row(self, row: dict) -> SchemaValidationResult:
        errors: list[str] = []
        qid = row.get("query_id", "?")

        for f in REQUIRED_FIELDS:
            if f not in row or row[f] is None or str(row[f]).strip() == "":
                errors.append(f"缺少必须字段: {f}")

        skill_type = row.get("skill_type", "")
        if skill_type and skill_type not in VALID_SKILL_TYPES:
            errors.append(f"无效 skill_type: {skill_type!r}")

        status = row.get("status", "")
        if status and status not in VALID_STATUSES:
            errors.append(f"无效 status: {status!r}")

        return SchemaValidationResult(
            valid=len(errors) == 0,
            query_id=qid,
            errors=errors,
        )

    def validate_rows(self, rows: list[dict]) -> list[SchemaValidationResult]:
        return [self.validate_row(r) for r in rows]
