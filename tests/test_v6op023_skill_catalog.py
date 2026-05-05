"""
test_v6op023_skill_catalog.py — V6OP-023/024 技能卡资产对齐验证

V6OP-024 更新：灰卡改为从 V6 JSON 真实装载（scripts/skill_catalog.py），
不再验证 app.js 中硬编码的 gray 数组，而是验证 skill_catalog 模块输出。

验证：
1. app.js SKILL_META 仍包含全部 5 个已接通核心技能
2. skill_catalog.py 从 V6 JSON 装载灰卡，数量正确（18 条）
3. 灰色技能在 UI 构建时标记 disabled，不可勾选
4. buildStrategy() 用 LIVE_SKILL_IDS 双重防守，灰色技能无法进入 payload
5. skill_registry.py 5 个核心能力保持可执行
6. V6 资产文件可读，22 条；4 条通过映射接通，18 条为灰卡
7. skill_catalog API 结构符合预期
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_ROOT    = Path(__file__).parent.parent.resolve()
_WEB     = _ROOT / "web"
_SCRIPTS = _ROOT / "scripts"
_V6_DATA = Path(r"F:\v.6\v6") / "data"


@pytest.fixture(scope="module")
def app_js() -> str:
    return (_WEB / "app.js").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def skill_catalog_mod():
    sys.path.insert(0, str(_SCRIPTS))
    import skill_catalog
    return skill_catalog


@pytest.fixture(scope="module")
def catalog(skill_catalog_mod):
    return skill_catalog_mod.get_catalog()


# ══════════════════════════════════════════════════════════════════════
# TestV6OP023SkillMeta — 已接通技能 SKILL_META 完整性
# ══════════════════════════════════════════════════════════════════════

class TestV6OP023SkillMeta:
    """已接通 6 个核心技能必须保留在 SKILL_META，保持可用状态。"""

    EXPECTED_LIVE_SKILLS = {"czsc", "smc", "kline", "wave", "landmine", "wencai"}

    def test_skill_meta_has_czsc(self, app_js):
        assert "czsc:" in app_js, "SKILL_META 缺少 czsc"

    def test_skill_meta_has_smc(self, app_js):
        assert "smc:" in app_js, "SKILL_META 缺少 smc"

    def test_skill_meta_has_kline(self, app_js):
        assert "kline:" in app_js, "SKILL_META 缺少 kline"

    def test_skill_meta_has_wave(self, app_js):
        assert "wave:" in app_js, "SKILL_META 缺少 wave"

    def test_skill_meta_has_landmine(self, app_js):
        assert "landmine:" in app_js, "SKILL_META 缺少 landmine"

    def test_live_skill_ids_defined(self, app_js):
        assert "LIVE_SKILL_IDS" in app_js, "app.js 缺少 LIVE_SKILL_IDS 集合"

    def test_live_skill_ids_uses_skill_meta_keys(self, app_js):
        assert "Object.keys(SKILL_META)" in app_js, \
            "LIVE_SKILL_IDS 应由 Object.keys(SKILL_META) 生成"


# ══════════════════════════════════════════════════════════════════════
# TestV6OP023SkillCatalogModule — skill_catalog.py 模块验证（V6OP-024）
# ══════════════════════════════════════════════════════════════════════

class TestV6OP023SkillCatalogModule:
    """skill_catalog.py 必须能从 V6 JSON 真实装载，返回正确结构。"""

    def test_module_importable(self, skill_catalog_mod):
        assert hasattr(skill_catalog_mod, "get_catalog"), \
            "skill_catalog 缺少 get_catalog()"

    def test_v6_to_v6op_map_has_5_entries(self, skill_catalog_mod):
        assert len(skill_catalog_mod.V6_TO_V6OP) == 5, \
            f"V6_TO_V6OP 映射应有 5 条（含 wencai），当前 {len(skill_catalog_mod.V6_TO_V6OP)}"

    def test_mapping_czsc(self, skill_catalog_mod):
        assert skill_catalog_mod.V6_TO_V6OP.get("chan-pattern-recognition") == "czsc"

    def test_mapping_smc(self, skill_catalog_mod):
        assert skill_catalog_mod.V6_TO_V6OP.get("smart-money-concepts") == "smc"

    def test_mapping_kline(self, skill_catalog_mod):
        assert skill_catalog_mod.V6_TO_V6OP.get("candlestick-pattern-recognition") == "kline"

    def test_mapping_wave(self, skill_catalog_mod):
        assert skill_catalog_mod.V6_TO_V6OP.get("elliott-wave-engine") == "wave"

    def test_catalog_returns_dict(self, catalog):
        assert isinstance(catalog, dict), "get_catalog() 应返回 dict"

    def test_catalog_has_required_keys(self, catalog):
        for k in ("live", "gray", "v6_total", "v6_mapped", "declared_total",
                  "missing_asset_count", "missing_assets", "gray_count", "live_count"):
            assert k in catalog, f"catalog 缺少字段: {k}"

    def test_v6_total_is_22(self, catalog):
        assert catalog["v6_total"] == 22, \
            f"V6 总数应为 22，当前 {catalog['v6_total']}"

    def test_declared_total_is_27(self, catalog):
        assert catalog["declared_total"] == 27, \
            f"declared_total 应为 27，当前 {catalog['declared_total']}"

    def test_missing_asset_count_is_5(self, catalog):
        assert catalog["missing_asset_count"] == 5, \
            f"missing_asset_count 应为 5（27-22），当前 {catalog['missing_asset_count']}"

    def test_missing_assets_is_list_of_5(self, catalog):
        assert isinstance(catalog["missing_assets"], list), "missing_assets 应为 list"
        assert len(catalog["missing_assets"]) == 5, \
            f"missing_assets 应有 5 条，当前 {len(catalog['missing_assets'])}"

    def test_v6_mapped_is_5(self, catalog):
        assert catalog["v6_mapped"] == 5, \
            f"V6 映射数应为 5（含 wencai），当前 {catalog['v6_mapped']}"

    def test_gray_count_is_17(self, catalog):
        assert catalog["gray_count"] == 17, \
            f"灰卡数应为 17（22-5），当前 {catalog['gray_count']}"

    def test_live_count_is_6(self, catalog):
        assert catalog["live_count"] == 6, \
            f"已接通技能应为 6（含 landmine + wencai），当前 {catalog['live_count']}"

    def test_gray_list_length_is_17(self, catalog):
        assert len(catalog["gray"]) == 17, \
            f"gray 列表应有 17 条，当前 {len(catalog['gray'])}"

    def test_live_list_length_is_6(self, catalog):
        assert len(catalog["live"]) == 6, \
            f"live 列表应有 6 条，当前 {len(catalog['live'])}"

    def test_landmine_in_live_as_native(self, catalog):
        ids = [s["skill_id"] for s in catalog["live"]]
        assert "landmine" in ids, "landmine 应在 live 列表中"
        landmine = next(s for s in catalog["live"] if s["skill_id"] == "landmine")
        assert landmine["v6_skill_id"] is None, "landmine.v6_skill_id 应为 None（v6-op 原生）"

    def test_live_skills_all_connected(self, catalog):
        for s in catalog["live"]:
            assert s["connected"] is True, f"{s['skill_id']} connected 应为 True"

    def test_gray_skills_all_not_connected(self, catalog):
        for s in catalog["gray"]:
            assert s["connected"] is False, f"{s['skill_id']} connected 应为 False"

    def test_gray_skills_have_skill_id(self, catalog):
        for s in catalog["gray"]:
            assert s.get("skill_id"), f"gray 条目缺少 skill_id: {s}"

    def test_gray_skills_have_label(self, catalog):
        for s in catalog["gray"]:
            assert s.get("label"), f"gray 技能 {s.get('skill_id')} 缺少 label"

    def test_wencai_in_live(self, catalog):
        live_ids = {s["skill_id"] for s in catalog["live"]}
        assert "wencai" in live_ids, "wencai 应在 live 列表中（问财选股）"

    def test_wencai_mapped_from_hithink_astock_selector(self, catalog):
        wencai = next((s for s in catalog["live"] if s["skill_id"] == "wencai"), None)
        assert wencai is not None, "wencai 未出现在 live 列表"
        assert wencai.get("v6_skill_id") == "hithink-astock-selector", \
            "wencai.v6_skill_id 应为 hithink-astock-selector"

    def test_hithink_astock_selector_not_in_gray(self, catalog):
        gray_ids = {s["skill_id"] for s in catalog["gray"]}
        assert "hithink-astock-selector" not in gray_ids, \
            "hithink-astock-selector 已映射为 wencai，不应在 gray 中"

    def test_gray_known_skills_present(self, catalog):
        gray_ids = {s["skill_id"] for s in catalog["gray"]}
        expected = {
            "hithink-finance-query", "hithink-market-query",
            "news-search", "geopolitical-risk-analysis", "social-media-intelligence",
        }
        missing = expected - gray_ids
        assert not missing, f"gray 列表缺少以下技能: {missing}"

    def test_catalog_changes_reflect_v6_json(self, skill_catalog_mod):
        # 验证装载路径确实来自 V6 JSON，而非硬编码
        conn_path = skill_catalog_mod._CONN_CARDS
        assert conn_path.exists(), f"V6 JSON 路径不存在: {conn_path}"
        cards = json.loads(conn_path.read_text(encoding="utf-8"))
        if isinstance(cards, dict):
            cards = cards.get("cards", [])
        assert len(cards) == 22, "skill_catalog 源文件应有 22 条"


# ══════════════════════════════════════════════════════════════════════
# TestV6OP023AppJsCatalogIntegration — app.js 与 catalog 集成
# ══════════════════════════════════════════════════════════════════════

class TestV6OP023AppJsCatalogIntegration:
    """app.js 应通过 /api/skill_catalog 动态装载灰卡，不再硬编码。"""

    def test_app_js_has_skill_catalog_gray_var(self, app_js):
        assert "SKILL_CATALOG_GRAY" in app_js, \
            "app.js 应保留 SKILL_CATALOG_GRAY 变量名（动态填充）"

    def test_app_js_fetches_skill_catalog_api(self, app_js):
        assert "/api/skill_catalog" in app_js, \
            "app.js 应 fetch('/api/skill_catalog') 动态装载灰卡"

    def test_app_js_no_hardcoded_hithink_ids(self, app_js):
        # 灰卡 skill_id 不应再硬编码在 app.js 中
        assert "hithink-finance-query" not in app_js, \
            "app.js 不应硬编码 hithink-finance-query（应由 API 动态提供）"

    def test_app_js_catalog_gray_starts_empty(self, app_js):
        assert "let SKILL_CATALOG_GRAY = []" in app_js, \
            "SKILL_CATALOG_GRAY 应初始化为空数组，由 fetch 填充"


# ══════════════════════════════════════════════════════════════════════
# TestV6OP023GrayDisabled — 灰色技能 disabled / 不可进入 payload
# ══════════════════════════════════════════════════════════════════════

class TestV6OP023GrayDisabled:
    """灰色技能在 DOM 构建时必须 disabled，buildStrategy 必须过滤掉非 LIVE_SKILL_IDS。"""

    def test_gray_skills_have_disabled_attribute(self, app_js):
        assert "cb.disabled = true" in app_js, \
            "灰色技能 checkbox 未设置 disabled=true"

    def test_gray_skill_dataset_gray(self, app_js):
        assert "dataset.gray" in app_js, \
            "灰色技能 checkbox 缺少 dataset.gray 标记"

    def test_build_strategy_filters_by_live_skill_ids(self, app_js):
        assert "LIVE_SKILL_IDS.has(cb.value)" in app_js, \
            "buildStrategy 应用 LIVE_SKILL_IDS.has() 过滤非接通技能"

    def test_gray_item_has_skill_item_gray_class(self, app_js):
        assert "skill-item-gray" in app_js, \
            "灰色技能 item 应有 skill-item-gray CSS class"

    def test_gray_separator_rendered(self, app_js):
        assert "暂未接通" in app_js, "app.js buildSkillList 应显示'暂未接通'分隔符或标签"


# ══════════════════════════════════════════════════════════════════════
# TestV6OP023SkillRegistry — Python 技能注册表核心能力保持可执行
# ══════════════════════════════════════════════════════════════════════

class TestV6OP023SkillRegistry:
    """skill_registry.py 的 5 个核心能力必须保持注册且 is_live=True。"""

    @pytest.fixture(scope="class")
    def registry_src(self):
        return (_ROOT / "scripts" / "skill_registry.py").read_text(encoding="utf-8")

    def test_czsc_registered_and_live(self, registry_src):
        assert "czsc" in registry_src, "skill_registry 缺少 czsc"
        assert "is_live" in registry_src, "skill_registry 缺少 is_live 字段"

    def test_smc_registered(self, registry_src):
        assert "smc" in registry_src

    def test_kline_registered(self, registry_src):
        assert "kline" in registry_src

    def test_wave_registered(self, registry_src):
        assert "wave" in registry_src

    def test_landmine_registered(self, registry_src):
        assert "landmine" in registry_src

    def test_wencai_registered(self, registry_src):
        assert "wencai" in registry_src

    def test_skill_registry_importable(self):
        sys.path.insert(0, str(_ROOT / "scripts"))
        import skill_registry
        live_ids = {s["skill_id"] for s in skill_registry.live_skills()}
        assert "kline"    in live_ids, "kline 不在 live 技能中"
        assert "landmine" in live_ids, "landmine 不在 live 技能中"
        assert "czsc"     in live_ids, "czsc 不在 live 技能中"
        assert "smc"      in live_ids, "smc 不在 live 技能中"
        assert "wave"     in live_ids, "wave 不在 live 技能中"

    def test_gray_skills_not_in_registry_live(self):
        sys.path.insert(0, str(_ROOT / "scripts"))
        import skill_registry
        live_ids = {s["skill_id"] for s in skill_registry.live_skills()}
        gray_sample = [
            "hithink-finance-query", "minute-data-analysis",
            "geopolitical-risk-analysis", "social-media-intelligence",
        ]
        for gid in gray_sample:
            assert gid not in live_ids, \
                f"灰色技能 {gid} 不应出现在 skill_registry live 列表"


# ══════════════════════════════════════════════════════════════════════
# TestV6OP023V6AssetCount — V6 资产文件条数核对（22 ≠ 27）
# ══════════════════════════════════════════════════════════════════════

class TestV6OP023V6AssetCount:
    """V6 技能卡资产文件应有 22 条，总纲写 27，差异 5 条需在报告中说明。"""

    @pytest.fixture(scope="class")
    def connection_cards(self):
        path = _V6_DATA / "skill_connection_cards.json"
        if not path.exists():
            pytest.skip(f"V6 资产文件不存在: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else data.get("cards", data)

    @pytest.fixture(scope="class")
    def raw_sample_cards(self):
        path = _V6_DATA / "raw_skill_sample_cards.json"
        if not path.exists():
            pytest.skip(f"V6 原始样本文件不存在: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "cards" in data:
            return data["cards"]
        return data

    def test_connection_cards_is_list(self, connection_cards):
        assert isinstance(connection_cards, list), \
            "skill_connection_cards.json 应为数组"

    def test_connection_cards_count_is_22(self, connection_cards):
        assert len(connection_cards) == 22, \
            f"skill_connection_cards.json 应有 22 条，当前 {len(connection_cards)} 条"

    def test_raw_sample_cards_count_is_22(self, raw_sample_cards):
        assert len(raw_sample_cards) == 22, \
            f"raw_skill_sample_cards.json 应有 22 条，当前 {len(raw_sample_cards)} 条"

    def test_connection_cards_have_skill_id(self, connection_cards):
        # skill_connection_cards.json 的实际结构只有 skill_id 有值（其他字段为 null）
        for card in connection_cards:
            assert "skill_id" in card, f"卡片缺少 skill_id 字段: {card}"
            assert card["skill_id"], f"卡片 skill_id 为空: {card}"

    def test_live_skills_mapped_in_v6(self, connection_cards):
        v6_ids = {c["skill_id"] for c in connection_cards}
        expected_mapped = {
            "candlestick-pattern-recognition",  # kline
            "chan-pattern-recognition",           # czsc
            "smart-money-concepts",               # smc
            "elliott-wave-engine",                # wave
        }
        for vid in expected_mapped:
            assert vid in v6_ids, \
                f"V6 资产缺少已接通技能的对应卡片: {vid}"

    def test_charter_v6op023_gap_documented(self, connection_cards):
        # 总纲写 27 条，V6 资产实际 22 条，差异 5 条
        gap = 27 - len(connection_cards)
        assert gap == 5, \
            f"总纲 27 - 实际 {len(connection_cards)} = {gap}，应为 5"

    def test_gray_count_is_22_minus_4(self, connection_cards):
        # 22 条 V6 JSON 中 4 条通过映射接通，剩余 18 条为灰卡
        mapped = {
            "chan-pattern-recognition",
            "smart-money-concepts",
            "candlestick-pattern-recognition",
            "elliott-wave-engine",
        }
        v6_ids = {c["skill_id"] for c in connection_cards}
        gray_ids = v6_ids - mapped
        assert len(gray_ids) == 18, \
            f"灰卡数应为 18，计算结果 {len(gray_ids)}"
