"""
test_phase3_web_assets.py — V6OP-004 Phase 3 前端资产轻量测试
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent.resolve()
_WEB  = _ROOT / "web"


# ── 文件存在性 ────────────────────────────────────────────────────────

class TestWebFilesExist:
    def test_index_html_exists(self):
        assert (_WEB / "index.html").exists(), "web/index.html 不存在"

    def test_app_js_exists(self):
        assert (_WEB / "app.js").exists(), "web/app.js 不存在"

    def test_styles_css_exists(self):
        assert (_WEB / "styles.css").exists(), "web/styles.css 不存在"


# ── index.html 内容检查 ───────────────────────────────────────────────

class TestIndexHtmlContent:
    @pytest.fixture(scope="class")
    def html(self):
        return (_WEB / "index.html").read_text(encoding="utf-8")

    def test_references_app_js(self, html):
        assert "app.js" in html, "index.html 未引用 app.js"

    def test_references_styles_css(self, html):
        assert "styles.css" in html, "index.html 未引用 styles.css"

    def test_has_source_section(self, html):
        assert "来源" in html or "source" in html.lower(), "index.html 缺少来源区域"

    def test_has_skill_section(self, html):
        assert "技能" in html or "skill" in html.lower(), "index.html 缺少技能区域"

    def test_has_path_section(self, html):
        assert "路径" in html or "path" in html.lower(), "index.html 缺少路径区域"

    def test_has_run_section(self, html):
        assert "运行" in html or "btn-run" in html, "index.html 缺少运行区域"

    def test_has_result_section(self, html):
        assert "命中" in html or "hit" in html.lower(), "index.html 缺少结果区域"

    def test_has_report_section(self, html):
        assert "报告" in html or "report" in html.lower(), "index.html 缺少报告区域"

    def test_has_log_box_id(self, html):
        assert 'id="log-box"' in html, "index.html 缺少 id=log-box"

    def test_has_health_dot_id(self, html):
        assert 'id="health-dot"' in html, "index.html 缺少 id=health-dot"

    def test_has_btn_run_id(self, html):
        assert 'id="btn-run"' in html, "index.html 缺少 id=btn-run"

    def test_has_hit_list_id(self, html):
        assert 'id="hit-list"' in html, "index.html 缺少 id=hit-list"

    def test_has_failed_list_id(self, html):
        assert 'id="failed-list"' in html, "index.html 缺少 id=failed-list"

    def test_has_readiness_box_id(self, html):
        assert 'id="readiness-box"' in html, "index.html 缺少 id=readiness-box"

    def test_has_source_type_radios(self, html):
        assert 'name="source-type"' in html, "index.html 缺少 source-type 单选"

    def test_has_path_type_radios(self, html):
        assert 'name="path-type"' in html, "index.html 缺少 path-type 单选"

    def test_has_manual_codes_textarea(self, html):
        assert 'id="manual-codes"' in html, "index.html 缺少 id=manual-codes"

    def test_no_real_api_key(self, html):
        # 不允许硬编码任何长于 16 位的 token/key 字面量
        suspicious = re.findall(r'(?:key|token|secret)\s*=\s*["\'][^"\']{16,}["\']', html, re.IGNORECASE)
        assert not suspicious, f"index.html 疑似包含硬编码 key: {suspicious}"

    def test_charset_utf8(self, html):
        assert "utf-8" in html.lower() or "UTF-8" in html, "index.html 未声明 UTF-8 编码"


# ── app.js 内容检查 ───────────────────────────────────────────────────

class TestAppJsContent:
    @pytest.fixture(scope="class")
    def js(self):
        return (_WEB / "app.js").read_text(encoding="utf-8")

    def test_has_api_health(self, js):
        assert "/api/health" in js, "app.js 缺少 /api/health"

    def test_has_api_run(self, js):
        assert "/api/run" in js, "app.js 缺少 /api/run"

    def test_has_api_stream(self, js):
        assert "/api/stream" in js, "app.js 缺少 /api/stream"

    def test_has_api_result(self, js):
        assert "/api/result" in js, "app.js 缺少 /api/result"

    def test_uses_setinterval_not_sse(self, js):
        assert "setInterval" in js, "app.js 应使用 setInterval 轮询（非 true SSE）"
        assert "EventSource" not in js, "app.js 不应使用 EventSource（命令要求 JSON 轮询）"

    def test_renders_readiness(self, js):
        assert "readiness" in js, "app.js 未处理 readiness 字段"

    def test_marks_aborted(self, js):
        assert "aborted" in js, "app.js 未标注 aborted 风险"

    def test_marks_soft_filter(self, js):
        assert "soft_filter" in js, "app.js 未标注 SMC soft_filter"

    def test_marks_weak_signal(self, js):
        assert "weak_signal" in js or "isWeak" in js, "app.js 未标注 Wave 弱信号"

    def test_has_html_escape(self, js):
        assert "esc(" in js or "escape" in js.lower(), "app.js 缺少 HTML 转义函数"

    def test_uses_since_param(self, js):
        assert "since" in js, "app.js 应使用 ?since=N 轮询（避免事件截断）"

    def test_has_skill_params(self, js):
        assert "SKILL_PARAMS" in js, "app.js 缺少 SKILL_PARAMS 技能参数定义"
        for key in ["swing_length", "close_break", "pass_neutral",
                    "swing_window", "fib_tolerance"]:
            assert key in js, f"app.js 参数面板缺少 {key}"

    def test_skill_scoped_params_in_strategy(self, js):
        # buildStrategy() 组装 {params: {skills: skillParams}} — 检查对象键名出现
        assert "skillParams" in js or "skill_params" in js or "skills: skill" in js, \
            "app.js buildStrategy 应发 skill-scoped params"

    def test_bool_params_are_collected(self, js):
        assert "pd.type === 'bool'" in js
        assert "el.value === 'true'" in js

    def test_no_hardcoded_key(self, js):
        suspicious = re.findall(r'(?:key|token|secret)\s*[:=]\s*["\'][^"\']{16,}["\']', js, re.IGNORECASE)
        assert not suspicious, f"app.js 疑似包含硬编码 key: {suspicious}"

    # ── V6OP-006：证据展开 ────────────────────────────────────────────
    def test_has_toggle_evidence_function(self, js):
        assert "toggleEvidence" in js, "app.js 缺少 toggleEvidence 函数（单股证据展开）"

    def test_has_hit_evidence_class_reference(self, js):
        assert "hit-evidence" in js, "app.js 缺少 .hit-evidence 引用（证据区域）"

    def test_evidence_renders_skill_hits(self, js):
        assert "skill_hits" in js, "app.js 未渲染 skill_hits 字段"

    def test_evidence_renders_reason_cn(self, js):
        assert "reason_cn" in js, "app.js 未渲染 reason_cn 字段（中文信号描述）"

    def test_hit_header_is_clickable(self, js):
        assert "hit-header" in js, "app.js 缺少 .hit-header 可点击区域"


# ── styles.css 内容检查 ───────────────────────────────────────────────

class TestStylesCssContent:
    @pytest.fixture(scope="class")
    def css(self):
        return (_WEB / "styles.css").read_text(encoding="utf-8")

    def test_has_console_layout(self, css):
        assert "console-layout" in css, "styles.css 缺少 .console-layout"

    def test_has_badge_aborted(self, css):
        assert "badge-aborted" in css, "styles.css 缺少 .badge-aborted（需要突出标注）"

    def test_has_tag_soft(self, css):
        assert "tag-soft" in css, "styles.css 缺少 .tag-soft（SMC soft_filter 标注）"

    def test_has_tag_weak(self, css):
        assert "tag-weak" in css, "styles.css 缺少 .tag-weak（Wave 弱信号标注）"

    def test_has_alert_danger(self, css):
        assert "alert-danger" in css, "styles.css 缺少 .alert-danger"

    def test_has_responsive(self, css):
        assert "@media" in css, "styles.css 缺少响应式媒体查询"

    # ── V6OP-006：证据展开样式 ────────────────────────────────────────
    def test_has_hit_evidence_style(self, css):
        assert "hit-evidence" in css, "styles.css 缺少 .hit-evidence 样式（证据展开区域）"

    def test_has_evidence_item_style(self, css):
        assert "evidence-item" in css, "styles.css 缺少 .evidence-item 样式"

    def test_hit_evidence_hidden_by_default(self, css):
        assert "hit-evidence" in css and "display: none" in css, \
            "styles.css 的 .hit-evidence 应默认隐藏（display: none）"


# ── 服务器静态路由检查 ────────────────────────────────────────────────

class TestServerStaticRouting:
    def test_server_has_serve_static(self):
        server_path = _ROOT / "scripts" / "v6op_server.py"
        src = server_path.read_text(encoding="utf-8")
        assert "_serve_static" in src, "v6op_server.py 缺少 _serve_static 静态文件服务"

    def test_server_routes_root_to_index(self):
        server_path = _ROOT / "scripts" / "v6op_server.py"
        src = server_path.read_text(encoding="utf-8")
        assert "index.html" in src, "v6op_server.py 未将根路径路由到 index.html"

    def test_server_prevents_path_traversal(self):
        server_path = _ROOT / "scripts" / "v6op_server.py"
        src = server_path.read_text(encoding="utf-8")
        assert "relative_to" in src and "startswith(str(" not in src, \
            "v6op_server.py 静态服务未防范路径穿越"

    def test_server_rejects_sibling_prefix_traversal(self, tmp_path, monkeypatch):
        import v6op_server

        web_dir = tmp_path / "web"
        web_dir.mkdir()
        (web_dir / "index.html").write_text("ok", encoding="utf-8")

        sibling_dir = tmp_path / "web2"
        sibling_dir.mkdir()
        (sibling_dir / "secret.txt").write_text("secret", encoding="utf-8")

        monkeypatch.setattr(v6op_server, "_PROJECT_ROOT", tmp_path)

        handler = object.__new__(v6op_server.V6OPHandler)
        sent: list[tuple[int, dict]] = []
        handler._send_json = lambda code, data: sent.append((code, data))  # type: ignore[method-assign]

        handler._serve_static("/../web2/secret.txt")

        assert sent
        assert sent[0][0] == 403


# ══════════════════════════════════════════════════════════════════════
# TestV6OP007WebAssets — V6OP-007 前端资产验证
# ══════════════════════════════════════════════════════════════════════

class TestV6OP007WebAssets:
    """V6OP-007：前端资产新增验证（来源区、全 A 保护、中文优先、证据展示）。"""

    @pytest.fixture
    def html(self):
        return (_ROOT / "web" / "index.html").read_text(encoding="utf-8")

    @pytest.fixture
    def js(self):
        return (_ROOT / "web" / "app.js").read_text(encoding="utf-8")

    # ── 来源区三选项 ──────────────────────────────────────────────────

    def test_index_has_all_three_source_radios(self, html):
        assert 'value="manual"' in html, "index.html 缺少 manual 来源选项"
        assert 'value="all_a"' in html, "index.html 缺少 all_a 来源选项"
        assert 'value="wencai"' in html, "index.html 缺少 wencai 来源选项"

    # ── 问财限制输入 ──────────────────────────────────────────────────

    def test_index_wencai_panel_has_limit_input(self, html):
        assert "wencai-limit" in html, "index.html wencai 面板缺少 limit 输入框"

    def test_app_js_sends_wencai_limit(self, js):
        assert "wencai-limit" in js, "app.js buildStrategy 未读取 wencai-limit 输入"
        assert "source.limit" in js, "app.js 未向 source 对象写入 limit"

    # ── 全 A 扫描保护 UI ──────────────────────────────────────────────

    def test_index_all_a_has_warn_element(self, html):
        assert "all-a-warn" in html, "index.html all_a 面板缺少风险提示元素"

    def test_index_all_a_has_confirm_checkbox(self, html):
        assert "all-a-confirm" in html, "index.html all_a 面板缺少确认勾选框"

    def test_app_js_has_bind_all_a_limit_watch(self, js):
        assert "bindAllALimitWatch" in js, "app.js 缺少 bindAllALimitWatch 函数"

    def test_app_js_checks_confirm_before_run(self, js):
        assert "all-a-confirm" in js, "app.js run 按钮未检查 all_a 确认框"
        assert "confirm_large_scope" in js, "app.js 未向 API 发送 confirm_large_scope"

    # ── simple_hybrid 标签修正 ────────────────────────────────────────

    def test_index_simple_hybrid_no_k_of_n_label(self, html):
        assert "K-of-N" not in html, "index.html simple_hybrid 标签仍有 'K-of-N' 字样"
        assert "简单混合" in html, "index.html 缺少 '简单混合' 标签"

    # ── 中文优先 ──────────────────────────────────────────────────────

    def test_index_main_buttons_chinese(self, html):
        assert "运行" in html, "index.html 缺少中文'运行'按钮文字"
        assert "股票来源" in html, "index.html 缺少中文'股票来源'标题"
        assert "技能选择" in html, "index.html 缺少中文'技能选择'标题"
        assert "执行路径" in html, "index.html 缺少中文'执行路径'标题"

    # ── 命中证据、失败、Stale 独立显示 ───────────────────────────────

    def test_app_js_evidence_expandable(self, js):
        assert "toggleEvidence" in js, "app.js 缺少 toggleEvidence 展开函数"
        assert "hit-evidence" in js, "app.js 缺少 hit-evidence 元素引用"

    def test_app_js_failed_codes_separate_render(self, js):
        assert "renderFailed" in js, "app.js 缺少 renderFailed 独立渲染函数"
        assert "failed-list" in js, "app.js 缺少 failed-list 元素引用"

    def test_app_js_stale_codes_separate_render(self, js):
        assert "stale-list" in js, "app.js 缺少 stale-list 独立显示"
        assert "stale_codes" in js, "app.js 缺少 stale_codes 读取"


# ══════════════════════════════════════════════════════════════════════
# TestV6OP021PrefetchSummaryUI — V6OP-021 prefetch 摘要区域验证
# ══════════════════════════════════════════════════════════════════════

class TestV6OP021PrefetchSummaryUI:
    """V6OP-021: 前端 prefetch 摘要区域 DOM 元素 + JS 函数验证。"""

    @pytest.fixture(scope="class")
    def html(self):
        return (_ROOT / "web" / "index.html").read_text(encoding="utf-8")

    @pytest.fixture(scope="class")
    def js(self):
        return (_ROOT / "web" / "app.js").read_text(encoding="utf-8")

    def test_index_has_prefetch_box_id(self, html):
        assert 'id="prefetch-box"' in html, \
            "index.html 缺少 id=prefetch-box（本轮预热摘要区域，V6OP-021 新增）"

    def test_index_has_prefetch_section_title(self, html):
        assert "本轮预热摘要" in html, \
            "index.html 缺少 '本轮预热摘要' 标题（V6OP-021 新增）"

    def test_app_js_has_render_prefetch(self, js):
        assert "renderPrefetch" in js, \
            "app.js 缺少 renderPrefetch 函数（V6OP-021 新增）"

    def test_app_js_prefetch_box_reference(self, js):
        assert "prefetch-box" in js, \
            "app.js 缺少 prefetch-box 元素引用"

    def test_app_js_prefetch_reads_cache_hit(self, js):
        assert "cache_hit" in js, \
            "app.js renderPrefetch 缺少 cache_hit 字段读取"

    def test_app_js_prefetch_reads_fetched_ok(self, js):
        assert "fetched_ok" in js, \
            "app.js renderPrefetch 缺少 fetched_ok 字段读取"

    def test_app_js_prefetch_reads_recovered_count(self, js):
        assert "recovered_count" in js, \
            "app.js renderPrefetch 缺少 recovered_count 字段读取（V6OP-021 新增）"

    def test_app_js_prefetch_reads_data_time_max(self, js):
        assert "data_time_max" in js, \
            "app.js renderPrefetch 缺少 data_time_max 字段读取"

    def test_app_js_prefetch_shows_stale_days(self, js):
        assert "staleDays" in js or "stale" in js.lower(), \
            "app.js renderPrefetch 缺少数据延迟/stale 天数计算"

    def test_app_js_clear_result_resets_prefetch_box(self, js):
        assert "prefetch-box" in js and "clearResult" in js, \
            "app.js clearResult 应重置 prefetch-box 内容"

    def test_app_js_prefetch_triggered_check(self, js):
        assert "prefetch_triggered" in js, \
            "app.js renderPrefetch 应检查 prefetch_triggered 决定是否渲染"
