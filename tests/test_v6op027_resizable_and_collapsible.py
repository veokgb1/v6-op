"""
test_v6op027_resizable_and_collapsible.py — V6OP-027 前端静态验证

覆盖：
  - 存在两个 resizer div
  - localStorage 宽度保存键名 v6op_layout_columns
  - V6 assets collapse toggle 存在
  - localStorage 折叠状态键名 v6op_v6_assets_collapsed
  - 灰卡 disabled 逻辑仍存在
  - SKILL_CATALOG_GRAY 仍来自 /api/skill_catalog
  - CSS resizer / v6-gray 样式存在
  - 布局改为 flex
"""
from __future__ import annotations
from pathlib import Path

_ROOT = Path(__file__).parent.parent.resolve()
_WEB  = _ROOT / "web"


class TestV6OP027IndexHtml:
    @staticmethod
    def _html() -> str:
        return (_WEB / "index.html").read_text(encoding="utf-8")

    def test_has_resizer_left(self):
        assert 'id="resizer-left"' in self._html(), \
            "index.html 缺少 id=resizer-left"

    def test_has_resizer_right(self):
        assert 'id="resizer-right"' in self._html(), \
            "index.html 缺少 id=resizer-right"

    def test_resizer_left_before_middle_panel(self):
        html = self._html()
        pos_resizer = html.find('id="resizer-left"')
        pos_mid     = html.find('aria-label="运行进度"')
        assert pos_resizer < pos_mid, \
            "resizer-left 应出现在中间面板之前"

    def test_resizer_right_before_result_panel(self):
        html = self._html()
        pos_resizer = html.find('id="resizer-right"')
        pos_right   = html.find('aria-label="命中结果"')
        assert pos_resizer < pos_right, \
            "resizer-right 应出现在右侧面板之前"


class TestV6OP027AppJs:
    @staticmethod
    def _js() -> str:
        return (_WEB / "app.js").read_text(encoding="utf-8")

    def test_has_init_resizers_function(self):
        assert "initResizers" in self._js(), \
            "app.js 缺少 initResizers 函数（V6OP-027）"

    def test_layout_store_key_present(self):
        assert "v6op_layout_columns" in self._js(), \
            "app.js 缺少 localStorage 键名 v6op_layout_columns"

    def test_layout_store_uses_local_storage(self):
        js = self._js()
        assert "localStorage.setItem" in js, \
            "app.js 缺少 localStorage.setItem（宽度持久化）"
        assert "localStorage.getItem" in js, \
            "app.js 缺少 localStorage.getItem（宽度恢复）"

    def test_gray_store_key_present(self):
        assert "v6op_v6_assets_collapsed" in self._js(), \
            "app.js 缺少 localStorage 键名 v6op_v6_assets_collapsed"

    def test_gray_toggle_element_id(self):
        assert "v6-gray-toggle" in self._js(), \
            "app.js 缺少 v6-gray-toggle 元素创建"

    def test_gray_body_element_id(self):
        assert "v6-gray-body" in self._js(), \
            "app.js 缺少 v6-gray-body 元素创建"

    def test_gray_collapsed_class(self):
        assert "collapsed" in self._js(), \
            "app.js 缺少 collapsed 类操作（折叠逻辑）"

    def test_gray_count_displayed(self):
        assert "v6-gray-count" in self._js(), \
            "app.js 折叠时应显示数量（v6-gray-count）"

    def test_gray_cards_disabled(self):
        js = self._js()
        assert "cb.disabled = true" in js or "disabled = true" in js, \
            "app.js 灰卡 disabled 逻辑不存在"

    def test_gray_cards_have_data_gray(self):
        assert 'data-gray' in self._js() or "dataset.gray" in self._js(), \
            "app.js 灰卡缺少 data-gray 标记"

    def test_skill_catalog_gray_from_api(self):
        js = self._js()
        assert "/api/skill_catalog" in js, \
            "app.js SKILL_CATALOG_GRAY 应来自 /api/skill_catalog"
        assert "SKILL_CATALOG_GRAY" in js, \
            "app.js 缺少 SKILL_CATALOG_GRAY 变量"

    def test_drag_uses_mousedown(self):
        assert "mousedown" in self._js(), \
            "app.js 拖拽应监听 mousedown 事件"

    def test_drag_uses_mousemove_mouseup(self):
        js = self._js()
        assert "mousemove" in js, "app.js 拖拽缺少 mousemove 监听"
        assert "mouseup"   in js, "app.js 拖拽缺少 mouseup 监听"

    def test_min_width_enforced(self):
        js = self._js()
        assert "MIN_LEFT" in js or "MIN_MID" in js or "MIN_RIGHT" in js, \
            "app.js 拖拽缺少最小宽度保护"

    def test_init_resizers_called_in_domcontentloaded(self):
        js = self._js()
        dom_pos  = js.find("DOMContentLoaded")
        call_pos = js.find("initResizers()", dom_pos)
        assert call_pos != -1, \
            "app.js initResizers() 未在 DOMContentLoaded 中调用"


class TestV6OP027StylesCss:
    @staticmethod
    def _css() -> str:
        return (_WEB / "styles.css").read_text(encoding="utf-8")

    def test_console_layout_is_flex(self):
        css = self._css()
        assert "display: flex" in css, \
            "styles.css .console-layout 应改为 display: flex"

    def test_resizer_class_exists(self):
        assert ".resizer" in self._css(), \
            "styles.css 缺少 .resizer 样式"

    def test_resizer_col_resize_cursor(self):
        assert "col-resize" in self._css(), \
            "styles.css .resizer 缺少 cursor: col-resize"

    def test_resizer_hover_highlight(self):
        css = self._css()
        assert ".resizer:hover" in css or ".resizer.dragging" in css, \
            "styles.css .resizer 缺少 hover/dragging 高亮样式"

    def test_v6_gray_toggle_class_exists(self):
        assert ".v6-gray-toggle" in self._css(), \
            "styles.css 缺少 .v6-gray-toggle 样式"

    def test_v6_gray_body_collapsed_hidden(self):
        assert ".v6-gray-body.collapsed" in self._css(), \
            "styles.css 缺少 .v6-gray-body.collapsed { display: none }"

    def test_v6_gray_count_class_exists(self):
        assert ".v6-gray-count" in self._css(), \
            "styles.css 缺少 .v6-gray-count 样式"
