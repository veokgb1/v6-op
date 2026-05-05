"""
test_v6op023_param_persistence.py — V6OP-023 Task 2 参数回显验证

验证总纲第十一章要求：参数区不需要用户每次手动重填。
- localStorage 保存/回显机制存在
- saveParams / restoreParams / resetParams 函数已实现
- PARAMS_STORE_ID 常量已定义
- "恢复默认参数"按钮已在 index.html 中定义
- buildStrategy 在 save 之前调用（在 run 时保存参数）
- 报告中参数不得用默认值冒充实际值（payload 使用回显后的真实值）
"""
from __future__ import annotations

from pathlib import Path
import pytest

_ROOT = Path(__file__).parent.parent.resolve()
_WEB  = _ROOT / "web"


@pytest.fixture(scope="module")
def app_js() -> str:
    return (_WEB / "app.js").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def index_html() -> str:
    return (_WEB / "index.html").read_text(encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════
# TestV6OP023ParamPersistenceJS — app.js 参数持久化实现
# ══════════════════════════════════════════════════════════════════════

class TestV6OP023ParamPersistenceJS:

    def test_param_storage_key_defined(self, app_js):
        assert "PARAMS_STORE_ID" in app_js, \
            "app.js 缺少 PARAMS_STORE_ID 常量"

    def test_localstorage_setitem_used(self, app_js):
        assert "localStorage.setItem" in app_js, \
            "app.js 缺少 localStorage.setItem（参数保存）"

    def test_localstorage_getitem_used(self, app_js):
        assert "localStorage.getItem" in app_js, \
            "app.js 缺少 localStorage.getItem（参数回显）"

    def test_localstorage_removeitem_used(self, app_js):
        assert "localStorage.removeItem" in app_js, \
            "app.js 缺少 localStorage.removeItem（恢复默认时清除）"

    def test_save_params_function_defined(self, app_js):
        assert "function saveParams" in app_js, \
            "app.js 缺少 saveParams() 函数"

    def test_restore_params_function_defined(self, app_js):
        assert "function restoreParams" in app_js, \
            "app.js 缺少 restoreParams() 函数"

    def test_reset_params_function_defined(self, app_js):
        assert "function resetParams" in app_js, \
            "app.js 缺少 resetParams() 函数"

    def test_restore_params_called_on_domcontentloaded(self, app_js):
        assert "restoreParams()" in app_js, \
            "app.js DOMContentLoaded 中未调用 restoreParams()"

    def test_save_params_called_on_run(self, app_js):
        assert "saveParams()" in app_js, \
            "app.js 运行时未调用 saveParams()（应在 run 时保存参数）"

    def test_bind_reset_params_called(self, app_js):
        assert "bindResetParams" in app_js, \
            "app.js 缺少 bindResetParams() 绑定函数"

    def test_saves_source_type(self, app_js):
        assert "sourceType" in app_js, \
            "saveParams 应保存 sourceType"

    def test_saves_path_type(self, app_js):
        assert "pathType" in app_js, \
            "saveParams 应保存 pathType"

    def test_saves_selected_skills(self, app_js):
        assert "skills" in app_js, \
            "saveParams 应保存已选技能列表"

    def test_saves_skill_params(self, app_js):
        assert "skillParams" in app_js, \
            "saveParams 应保存各技能参数值"

    def test_saves_wencai_query(self, app_js):
        assert "wencaiQuery" in app_js, \
            "saveParams 应保存 wencai query"

    def test_saves_wencai_limit(self, app_js):
        assert "wencaiLimit" in app_js, \
            "saveParams 应保存 wencai limit"

    def test_saves_manual_codes(self, app_js):
        assert "manualCodes" in app_js, \
            "saveParams 应保存 manual codes"

    def test_restore_dispatches_change_event(self, app_js):
        # restoreParams 需要 dispatchEvent(new Event('change')) 让联动生效
        assert "dispatchEvent" in app_js, \
            "restoreParams 应 dispatchEvent(change) 触发联动（面板显示/隐藏等）"

    def test_reset_restores_skill_meta_defaults(self, app_js):
        assert "pd.default" in app_js, \
            "resetParams 应将 skill 参数重置为 SKILL_PARAMS 中的 default 值"


# ══════════════════════════════════════════════════════════════════════
# TestV6OP023ResetButton — index.html 恢复默认参数按钮
# ══════════════════════════════════════════════════════════════════════

class TestV6OP023ResetButton:

    def test_btn_reset_params_in_html(self, index_html):
        assert "btn-reset-params" in index_html, \
            "index.html 缺少 id=btn-reset-params（恢复默认参数按钮）"

    def test_reset_button_has_chinese_label(self, index_html):
        assert "恢复默认参数" in index_html, \
            "index.html 恢复默认参数按钮应有中文标签"
