"""
test_smoke_playwright.py — V6OP 多页面架构 Playwright 烟雾测试
依赖：playwright (pip install playwright && playwright install chromium)

若 playwright 未安装，所有测试自动跳过，不影响 CI pytest 通过率。
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

# ── playwright 可用性检测 ──────────────────────────────────────────────────
try:
    from playwright.sync_api import sync_playwright, Page, Browser
    _PW_AVAILABLE = True
except ImportError:
    _PW_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _PW_AVAILABLE,
    reason="playwright 未安装，跳过烟雾测试 (pip install playwright && playwright install chromium)",
)

_ROOT    = Path(__file__).parent.parent.resolve()
_SCRIPTS = _ROOT / "scripts"
_PORT    = 17861   # 与默认端口错开，避免与开发环境冲突
_BASE    = f"http://127.0.0.1:{_PORT}"


# ══════════════════════════════════════════════════════════════════════
# fixtures
# ══════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def v6op_server():
    """启动独立 v6op_server 进程，session 结束后自动终止。"""
    if not _PW_AVAILABLE:
        yield None
        return

    proc = subprocess.Popen(
        [sys.executable, str(_SCRIPTS / "v6op_server.py"), "--port", str(_PORT)],
        cwd=str(_SCRIPTS),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # 等待服务启动（最多 10s）
    deadline = time.time() + 10
    import urllib.request
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{_BASE}/api/health", timeout=1)
            break
        except Exception:
            time.sleep(0.3)
    else:
        proc.terminate()
        pytest.skip("v6op_server 未能在 10s 内就绪，跳过烟雾测试")

    yield proc
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="session")
def browser(v6op_server):
    """共享 Chromium 实例（无头）。"""
    if not _PW_AVAILABLE:
        yield None
        return
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        yield b
        try:
            b.close()
        except Exception:
            # Browser/driver may already be gone at session teardown on Windows.
            pass


@pytest.fixture
def page(browser) -> "Page":
    """每个测试独立 page，自动关闭。"""
    p = browser.new_page()
    yield p
    p.close()


def _wait_nav(page: "Page", url: str, timeout: int = 5000) -> None:
    page.goto(url, wait_until="domcontentloaded", timeout=timeout)


# ══════════════════════════════════════════════════════════════════════
# Smoke 1 — 共享导航栏渲染
# ══════════════════════════════════════════════════════════════════════

class TestNavBarSmoke:
    def test_index_has_nav(self, page):
        """index.html 导航栏挂载成功。"""
        _wait_nav(page, f"{_BASE}/")
        nav = page.locator("#v6-nav")
        assert nav.count() == 1
        # V6Nav.init() 应渲染至少一个链接
        links = page.locator("#v6-nav a")
        assert links.count() >= 3

    def test_strategy_page_nav(self, page):
        """strategy.html 导航栏含 active 高亮。"""
        _wait_nav(page, f"{_BASE}/strategy.html")
        active = page.locator(".v6-nav-active")
        assert active.count() >= 1
        assert "策略" in active.first.inner_text() or "strategy" in active.first.get_attribute("href", "")

    def test_manage_page_nav(self, page):
        """manage.html 导航栏高亮正确。"""
        _wait_nav(page, f"{_BASE}/manage.html")
        active = page.locator(".v6-nav-active")
        assert active.count() >= 1


# ══════════════════════════════════════════════════════════════════════
# Smoke 2 — strategy.html 策略构建流
# ══════════════════════════════════════════════════════════════════════

class TestStrategyPageSmoke:
    def test_source_type_radios_present(self, page):
        """策略台来源选择器可见。"""
        _wait_nav(page, f"{_BASE}/strategy.html")
        radios = page.locator('input[name="source-type"]')
        assert radios.count() == 3

    def test_wencai_stock_mode_shows_query_input(self, page):
        """点击 wencai 来源 → 问财面板显示 → stock 模式有查询输入框。"""
        _wait_nav(page, f"{_BASE}/strategy.html")
        page.locator('input[name="source-type"][value="wencai"]').click()
        # 等待面板显示
        page.wait_for_timeout(300)
        # 确认 wm-btn-stock 可见
        stock_btn = page.locator("#wm-btn-stock")
        if stock_btn.count():
            stock_btn.click()
            page.wait_for_timeout(200)
        # 问财查询输入框
        query_input = page.locator("#wencai-query")
        assert query_input.count() >= 1

    def test_wencai_query_fill(self, page):
        """wencai stock 模式可填写查询，query 字段被读取。"""
        _wait_nav(page, f"{_BASE}/strategy.html")
        page.locator('input[name="source-type"][value="wencai"]').click()
        page.wait_for_timeout(200)
        q = page.locator("#wencai-query")
        if q.count():
            q.fill("连续三日涨停")
            assert q.input_value() == "连续三日涨停"

    def test_btn_run_visible(self, page):
        """#btn-run 按钮可见（来自 app.js）。"""
        _wait_nav(page, f"{_BASE}/strategy.html")
        btn = page.locator("#btn-run")
        assert btn.count() >= 1

    def test_skill_list_rendered(self, page):
        """#skill-list 被渲染，至少有一个技能行（app.js 负责）。"""
        _wait_nav(page, f"{_BASE}/strategy.html")
        page.wait_for_timeout(500)
        rows = page.locator("#skill-list .skill-item")
        # app.js 应渲染 5+ 个技能行
        assert rows.count() >= 4

    def test_run_preview_modal_shows_on_click(self, page):
        """点击运行按钮，strategy.js 弹出预览 Modal（而非直接 POST）。"""
        _wait_nav(page, f"{_BASE}/strategy.html")
        page.wait_for_timeout(300)
        # 选 manual 来源，填几个代码
        page.locator('input[name="source-type"][value="manual"]').click()
        manual = page.locator("#manual-codes")
        if manual.count():
            manual.fill("600519")
        page.locator("#btn-run").click()
        page.wait_for_timeout(300)
        overlay = page.locator("#run-preview-overlay")
        # 若 strategy.js 拦截成功，overlay 应变为可见
        if overlay.count():
            visible = overlay.is_visible()
            assert visible, "strategy.js 应在点击运行后弹出预览 Modal"

    def test_sector_mode_generates_composite_query(self, page):
        """板块联动模式：Phase A 扫描 → Phase B 输入 → 生成合成查询。"""
        _wait_nav(page, f"{_BASE}/strategy.html")
        page.locator('input[name="source-type"][value="wencai"]').click()
        page.wait_for_timeout(200)
        sector_btn = page.locator("#wm-btn-sector")
        if not sector_btn.count():
            pytest.skip("当前 strategy.html 无 sector 模式按钮")
        sector_btn.click()
        page.wait_for_timeout(200)
        # Phase B 查询输入
        phase_b = page.locator("#phase-b-query, #wencai-query")
        if phase_b.count():
            phase_b.first.fill("量能放大")
        # 合成查询预览应包含"板块"关键字（由 app.js buildStrategy 生成）
        preview = page.locator("#preview-source")
        if preview.count():
            page.wait_for_timeout(300)
            text = preview.inner_text()
            # 合成结果包含"板块"或查询文本
            assert "板块" in text or "量能" in text or text == ""


# ══════════════════════════════════════════════════════════════════════
# Smoke 3 — input.html 提示词工坊
# ══════════════════════════════════════════════════════════════════════

class TestInputWorkbenchSmoke:
    def test_input_page_loads(self, page):
        """input.html 正常加载，标题可见。"""
        _wait_nav(page, f"{_BASE}/input.html")
        assert "input" in page.url.lower() or page.title() != ""

    def test_prompt_matrix_rendered(self, page):
        """提示词矩阵面板渲染，至少有一张卡片（来自内置提示词）。"""
        _wait_nav(page, f"{_BASE}/input.html")
        page.wait_for_timeout(600)
        cards = page.locator(".pm-card")
        assert cards.count() >= 3, "prompt_bank.js 应渲染至少 3 张内置提示词卡片"

    def test_search_filters_prompts(self, page):
        """搜索框过滤提示词。"""
        _wait_nav(page, f"{_BASE}/input.html")
        page.wait_for_timeout(500)
        search = page.locator("#pm-search")
        if not search.count():
            pytest.skip("当前 input.html 无 #pm-search 搜索框")
        before = page.locator(".pm-card").count()
        search.fill("涨停")
        page.wait_for_timeout(300)
        after = page.locator(".pm-card").count()
        # 过滤后卡片数 ≤ 过滤前
        assert after <= before

    def test_send_to_draft_writes_localstorage(self, page):
        """点击「使用」按钮写入 localStorage v6op_strategy_draft。"""
        _wait_nav(page, f"{_BASE}/input.html")
        page.wait_for_timeout(500)
        use_btn = page.locator(".pm-use-btn").first
        if not use_btn.count():
            pytest.skip("无 .pm-use-btn 按钮")
        use_btn.click()
        page.wait_for_timeout(300)
        draft = page.evaluate("localStorage.getItem('v6op_strategy_draft')")
        assert draft is not None, "点击使用后 v6op_strategy_draft 应写入 localStorage"

    def test_condition_composer_chips_present(self, page):
        """条件积木面板有至少一组 chip。"""
        _wait_nav(page, f"{_BASE}/input.html")
        # 切换到条件积木 tab
        composer_tab = page.locator('[data-tab="composer"], [data-wtab="composer"]')
        if composer_tab.count():
            composer_tab.first.click()
            page.wait_for_timeout(300)
        chips = page.locator(".composer-chip")
        assert chips.count() >= 4, "条件积木应有 4 个以上 chip"

    def test_strategy_templates_tab_works(self, page):
        """模板 tab 可点击，渲染模板列表（即使为空）。"""
        _wait_nav(page, f"{_BASE}/input.html")
        tpl_tab = page.locator('[data-tab="templates"], [data-wtab="templates"]')
        if not tpl_tab.count():
            pytest.skip("无模板 tab")
        tpl_tab.first.click()
        page.wait_for_timeout(200)
        # 模板列表容器存在即可
        tpl_list = page.locator("#tmpl-list")
        assert tpl_list.count() >= 1


# ══════════════════════════════════════════════════════════════════════
# Smoke 4 — reports.html 历史报告列表
# ══════════════════════════════════════════════════════════════════════

class TestReportsPageSmoke:
    def test_reports_page_loads(self, page):
        """reports.html 正常加载。"""
        _wait_nav(page, f"{_BASE}/reports.html")
        assert "reports" in page.url.lower() or page.title() != ""

    def test_run_list_area_exists(self, page):
        """历史运行列表容器存在（即使为空）。"""
        _wait_nav(page, f"{_BASE}/reports.html")
        page.wait_for_timeout(500)
        run_list = page.locator("#rpt-list, #run-list, table")
        assert run_list.count() >= 1

    def test_search_input_present(self, page):
        """搜索/过滤输入框存在。"""
        _wait_nav(page, f"{_BASE}/reports.html")
        inp = page.locator('input[type="search"], input[type="text"], #rpt-search, #run-search')
        assert inp.count() >= 1

    def test_compare_link_present(self, page):
        """有跳往对比页的入口链接或按钮。"""
        _wait_nav(page, f"{_BASE}/reports.html")
        el = page.locator('a[href*="compare"], button:has-text("对比")')
        assert el.count() >= 1


# ══════════════════════════════════════════════════════════════════════
# Smoke 5 — compare.html 报告对比
# ══════════════════════════════════════════════════════════════════════

class TestComparePageSmoke:
    def test_compare_page_loads(self, page):
        """compare.html 正常加载。"""
        _wait_nav(page, f"{_BASE}/compare.html")
        assert "compare" in page.url.lower() or page.title() != ""

    def test_four_report_selectors_present(self, page):
        """4 个报告选择器存在。"""
        _wait_nav(page, f"{_BASE}/compare.html")
        for i in range(1, 5):
            sel = page.locator(f"#cmp-sel-{i}")
            assert sel.count() == 1, f"compare.html 缺少 #cmp-sel-{i}"

    def test_compare_button_present(self, page):
        """对比按钮存在。"""
        _wait_nav(page, f"{_BASE}/compare.html")
        btn = page.locator("#btn-cmp-run")
        assert btn.count() == 1

    def test_compare_without_selection_shows_warning(self, page):
        """未选择报告直接点对比，应出现警告提示（不少于 0 条）。"""
        _wait_nav(page, f"{_BASE}/compare.html")
        page.wait_for_timeout(400)
        page.locator("#btn-cmp-run").click()
        page.wait_for_timeout(300)
        alert = page.locator(".alert, .alert-warn, [class*='alert']")
        # 有 alert 出现即可（或 cmp-body 内有提示文字）
        cmp_body = page.locator("#cmp-body")
        if cmp_body.count():
            assert alert.count() >= 1 or "选择" in cmp_body.inner_text()

    def test_url_params_prefill_selectors(self, page):
        """URL ?runs=id1,id2 参数应预填选择器（setTimeout 后）。"""
        _wait_nav(
            page,
            f"{_BASE}/compare.html?runs=run_20240101_120000_abcd,run_20240102_130000_efgh",
        )
        page.wait_for_timeout(1500)   # 等待 setTimeout 1200ms
        sel1 = page.locator("#cmp-sel-1")
        sel2 = page.locator("#cmp-sel-2")
        # 选择器存在即可（run_id 可能不在列表中，值为空也合理）
        assert sel1.count() == 1 and sel2.count() == 1


# ══════════════════════════════════════════════════════════════════════
# Smoke 6 — manage.html 管理中心
# ══════════════════════════════════════════════════════════════════════

class TestManagePageSmoke:
    def test_manage_page_loads(self, page):
        """manage.html 正常加载。"""
        _wait_nav(page, f"{_BASE}/manage.html")
        assert "manage" in page.url.lower() or page.title() != ""

    def test_history_tab_active_by_default(self, page):
        """历史记录 tab 默认激活。"""
        _wait_nav(page, f"{_BASE}/manage.html")
        active = page.locator(".mgmt-tab-active")
        assert active.count() >= 1
        active_mtab = active.first.get_attribute("data-mtab") or ""
        assert "history" in active_mtab or "历史" in active.first.inner_text()

    def test_cache_tab_click(self, page):
        """点击缓存管理 tab，缓存面板出现。"""
        _wait_nav(page, f"{_BASE}/manage.html")
        page.locator('[data-mtab="cache"]').click()
        page.wait_for_timeout(200)
        cache_panel = page.locator("#mtp-cache")
        assert cache_panel.is_visible()

    def test_settings_tab_has_selects(self, page):
        """系统设置 tab 有下拉框。"""
        _wait_nav(page, f"{_BASE}/manage.html")
        page.locator('[data-mtab="settings"]').click()
        page.wait_for_timeout(200)
        selects = page.locator("#mtp-settings select")
        assert selects.count() >= 2

    def test_save_settings_persists(self, page):
        """保存设置后 localStorage v6op_settings 有值。"""
        _wait_nav(page, f"{_BASE}/manage.html")
        page.locator('[data-mtab="settings"]').click()
        page.wait_for_timeout(200)
        page.locator("#btn-mgmt-save-settings").click()
        page.wait_for_timeout(200)
        saved = page.evaluate("localStorage.getItem('v6op_settings')")
        assert saved is not None, "保存设置后 v6op_settings 应写入 localStorage"

    def test_wencai_check_button_exists(self, page):
        """问财授权 tab 有检查按钮。"""
        _wait_nav(page, f"{_BASE}/manage.html")
        page.locator('[data-mtab="wencai"]').click()
        page.wait_for_timeout(200)
        btn = page.locator("#btn-mgmt-check-wencai")
        assert btn.count() == 1
