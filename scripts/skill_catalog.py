#!/usr/bin/env python3
"""
skill_catalog.py — 从 V6 JSON 真实装载技能目录（总纲第四章）

数据源（只读）：
  F:/v.6/v6/data/skill_connection_cards.json   ← 22 条 V6 技能 ID 权威列表
  F:/v.6/v6/data/raw_skill_sample_cards.json    ← 中文名称补充（ID 部分重叠）

映射规则（5 条，V6 → v6-op）：
  V6 ID                          → v6-op skill_id
  chan-pattern-recognition       → czsc
  smart-money-concepts           → smc
  candlestick-pattern-recognition → kline
  elliott-wave-engine            → wave
  hithink-astock-selector        → wencai   （来源技能，API 实时选股）

  landmine 是 v6-op 原生能力，不来自 V6 JSON。

返回 get_catalog() 的 dict（V6OP-024 新增字段）：
  {
    "live":              [...],       # 6 条（含 landmine + wencai）
    "gray":              [...],       # 17 条（22 - 5 已映射）
    "v6_total":          22,
    "v6_mapped":         5,
    "declared_total":    27,          # 总纲声明应有 27 张
    "missing_asset_count": 5,         # 27 - 22 = 5 张 V6 JSON 尚未提供
    "missing_assets":    [...],       # 5 条占位 ID，用于检测
    "gray_count":        17,
    "live_count":        6,
    "generated_at":      "...",
  }
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

_V6_DATA_DIR = Path(__file__).parent.parent.parent / "v6" / "data"
_CONN_CARDS   = _V6_DATA_DIR / "skill_connection_cards.json"
_RAW_CARDS    = _V6_DATA_DIR / "raw_skill_sample_cards.json"

# V6 技能 ID → v6-op skill_id 映射（5 条，含 wencai）
V6_TO_V6OP: dict[str, str] = {
    "chan-pattern-recognition":        "czsc",
    "smart-money-concepts":            "smc",
    "candlestick-pattern-recognition": "kline",
    "elliott-wave-engine":             "wave",
    "hithink-astock-selector":         "wencai",  # 问财：来源技能，API 实时选股
}

# 总纲声明的技能总数；V6 JSON 实际提供 22 条；差 5 条为缺失资产
_DECLARED_TOTAL = 27
# 5 张尚未以 JSON 形式提供的 V6 技能（按总纲）；用于机器检测，不进入主 UI
_MISSING_ASSET_IDS = [
    "v6-missing-asset-01",
    "v6-missing-asset-02",
    "v6-missing-asset-03",
    "v6-missing-asset-04",
    "v6-missing-asset-05",
]

# v6-op live 技能元数据（与 SKILL_META 对齐）
_V6OP_LIVE_META: dict[str, dict] = {
    "czsc":     {"label": "缠论选股",    "label_en": "CZSC Pattern"},
    "smc":      {"label": "聪明钱",      "label_en": "Smart Money Concepts"},
    "kline":    {"label": "K 线形态",    "label_en": "Candlestick Pattern"},
    "wave":     {"label": "艾略特波浪",  "label_en": "Elliott Wave"},
    "landmine": {"label": "雷区扫描",    "label_en": "Landmine Scanner"},
    "wencai":   {"label": "问财选股",    "label_en": "Wencai Stock Selector"},
}


def _load_v6_cards(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"V6 JSON 不存在: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return data.get("cards", [])


def _derive_label(skill_id: str) -> str:
    """从 skill_id 派生可读标签（例如 'chan-pattern-recognition' → 'Chan Pattern Recognition'）。"""
    return " ".join(w.capitalize() for w in skill_id.replace("-", " ").split())


def get_catalog() -> dict:
    """
    从 V6 JSON 真实装载技能目录，返回 live/gray 分组。
    可被多次调用；每次都从磁盘读取（保证 V6 JSON 更新后即时生效）。
    """
    conn_cards = _load_v6_cards(_CONN_CARDS)   # 权威 22 条

    # 建立 raw_cards 的 cn_name 查找表（仅用于补充标签）
    raw_by_id: dict[str, str] = {}
    try:
        for c in _load_v6_cards(_RAW_CARDS):
            sid = c.get("skill_id", "")
            cn  = c.get("cn_name", "")
            if sid and cn:
                raw_by_id[sid] = cn
    except Exception:
        pass   # raw_cards 不影响核心逻辑

    live: list[dict] = []
    gray: list[dict] = []

    for card in conn_cards:
        v6_id = card.get("skill_id", "")
        if not v6_id:
            continue

        label_cn = raw_by_id.get(v6_id) or _derive_label(v6_id)

        if v6_id in V6_TO_V6OP:
            v6op_id = V6_TO_V6OP[v6_id]
            live_meta = _V6OP_LIVE_META.get(v6op_id, {})
            live.append({
                "skill_id":    v6op_id,
                "v6_skill_id": v6_id,
                "label":       live_meta.get("label", label_cn),
                "label_en":    live_meta.get("label_en", _derive_label(v6_id)),
                "status":      "connected",
                "statusCn":    "已接通（V6 映射）",
                "connected":   True,
            })
        else:
            gray.append({
                "skill_id":    v6_id,
                "v6_skill_id": v6_id,
                "label":       label_cn,
                "label_en":    _derive_label(v6_id),
                "status":      "not_connected",
                "statusCn":    "暂未接通",
                "connected":   False,
            })

    # 插入 landmine（v6-op 原生，不来自 V6 JSON）
    landmine_meta = _V6OP_LIVE_META["landmine"]
    live.insert(0, {
        "skill_id":    "landmine",
        "v6_skill_id": None,
        "label":       landmine_meta["label"],
        "label_en":    landmine_meta["label_en"],
        "status":      "connected",
        "statusCn":    "已接通（v6-op 原生）",
        "connected":   True,
    })

    v6_mapped = len(V6_TO_V6OP)
    missing_count = _DECLARED_TOTAL - len(conn_cards)
    return {
        "live":                live,
        "gray":                gray,
        "v6_total":            len(conn_cards),
        "v6_mapped":           v6_mapped,
        "declared_total":      _DECLARED_TOTAL,
        "missing_asset_count": max(0, missing_count),
        "missing_assets":      _MISSING_ASSET_IDS,
        "gray_count":          len(gray),
        "live_count":          len(live),
        "generated_at":        datetime.now().isoformat(),
    }


if __name__ == "__main__":
    import sys
    cat = get_catalog()
    print(f"v6_total={cat['v6_total']}  declared_total={cat['declared_total']}  "
          f"missing_asset_count={cat['missing_asset_count']}  "
          f"mapped={cat['v6_mapped']}  gray={cat['gray_count']}  live={cat['live_count']}")
    print("LIVE:")
    for s in cat["live"]:
        print(f"  [LIVE] {s['skill_id']:<12}  v6={s['v6_skill_id']}  {s['statusCn']}")
    print("GRAY:")
    for s in cat["gray"]:
        print(f"  [GRAY] {s['skill_id']}")
    print("MISSING ASSETS:")
    for aid in cat["missing_assets"]:
        print(f"  [MISSING] {aid}")
    json.dump(cat, sys.stdout, ensure_ascii=False, indent=2)
