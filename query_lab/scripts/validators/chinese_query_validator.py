"""
chinese_query_validator.py — 中文 Query 预检器

规则：
1. query_text 必须包含中文字符
2. 不得出现英文整句（超过3个连续英文单词视为整句）
3. 除白名单缩写外，英文单词标记为 invalid_query
4. 空串直接 invalid_query
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# 白名单缩写（可在问财中文金融语境中使用）
CHINESE_ABBREV_WHITELIST: set[str] = {
    "A股", "ST", "MACD", "KDJ", "KD", "PE", "PB", "ROE", "ETF", "BOLL", "JMA",
}

# 白名单英文（纯字母部分）
_WHITELIST_UPPER: set[str] = {
    "ST", "MACD", "KDJ", "KD", "PE", "PB", "ROE", "ETF", "BOLL", "JMA", "A",
}

# 中文字符正则
_HAS_CHINESE = re.compile(r"[一-鿿]")

# 英文单词正则（不含数字和标点）
_EN_WORD = re.compile(r"\b[a-zA-Z]{2,}\b")

# 英文整句判断：连续3+英文单词（允许中间有空格/连字符）
_EN_SENTENCE = re.compile(r"\b[a-zA-Z]{2,}(?:[\s\-]+[a-zA-Z]{2,}){2,}\b")


@dataclass
class ValidationResult:
    valid: bool
    status: str  # "ok" | "invalid_query"
    reason: str = ""
    details: list[str] = field(default_factory=list)


class ChineseQueryValidator:
    """中文问财 Query 预检器"""

    def __init__(self, whitelist: set[str] | None = None) -> None:
        self.whitelist_upper = _WHITELIST_UPPER.copy()
        if whitelist:
            self.whitelist_upper.update(w.upper() for w in whitelist)

    def validate(self, query_text: str) -> ValidationResult:
        """
        返回 ValidationResult。
        valid=True 表示可以发送给问财。
        """
        if not query_text or not query_text.strip():
            return ValidationResult(
                valid=False,
                status="invalid_query",
                reason="查询语句为空",
                details=["query_text 是空字符串"],
            )

        q = query_text.strip()

        # 规则1：必须包含中文字符
        if not _HAS_CHINESE.search(q):
            return ValidationResult(
                valid=False,
                status="invalid_query",
                reason="不含中文字符",
                details=[f"query_text 中未找到中文字符: {q[:80]}"],
            )

        # 规则2：不得出现英文整句
        en_sentence_match = _EN_SENTENCE.search(q)
        if en_sentence_match:
            matched = en_sentence_match.group(0)
            return ValidationResult(
                valid=False,
                status="invalid_query",
                reason="包含英文整句",
                details=[f"检测到英文整句: {matched!r}"],
            )

        # 规则3：除白名单外不得有英文单词
        en_words = _EN_WORD.findall(q)
        forbidden_en = [
            w for w in en_words
            if w.upper() not in self.whitelist_upper
        ]
        if forbidden_en:
            return ValidationResult(
                valid=False,
                status="invalid_query",
                reason="包含非白名单英文单词",
                details=[f"非法英文单词: {forbidden_en}"],
            )

        return ValidationResult(valid=True, status="ok")

    def bulk_validate(self, queries: list[str]) -> list[ValidationResult]:
        return [self.validate(q) for q in queries]
