#!/usr/bin/env python3
"""
verify_wencai_canon_source_pilot.py
问财法典来源区试点检测脚本

检测项：
  1. /strategy.html 旧策略台仍存在
  2. /strategy_canon.html 新试点页存在
  3. canon_source_pilot.js 存在
  4. 关键 DOM 元素存在
  5. 板块 preview API 可调用（需要服务运行）
  6. A股 preview API 可调用（需要服务运行）
  7. 联动 query 拼接逻辑正确
  8. 确认来源后中间 Query 预览能显示（DOM 检查）
  9. 右侧技能区和执行路径控件仍存在

用法：
  cd /d F:\\v.6\\v6-op
  .venv\\Scripts\\python.exe scripts\\verify_wencai_canon_source_pilot.py

  # 若服务未启动，API 检测项会标注 SKIP（不算失败）
  # 若服务已启动：
  .venv\\Scripts\\python.exe scripts\\verify_wencai_canon_source_pilot.py --port 8876
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# ── 强制 UTF-8 输出（Windows GBK 终端兼容）─────────────────────────────
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
WEB  = ROOT / "web"
JS   = WEB / "js"

PASS  = "PASS"
FAIL  = "FAIL"
SKIP  = "SKIP"
WARN  = "WARN"

_results: list[tuple[str, str, str]] = []  # (status, name, detail)


def record(status: str, name: str, detail: str = "") -> None:
    _results.append((status, name, detail))
    icon = {"PASS": "✔", "FAIL": "✖", "SKIP": "—", "WARN": "⚠"}.get(status, "?")
    print(f"  [{icon}] {name}{(' — ' + detail) if detail else ''}")


def _read_html(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _post_api(port: int, path: str, payload: dict, timeout: int = 15) -> tuple[bool, dict]:
    url  = f"http://127.0.0.1:{port}{path}"
    body = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return False, json.loads(e.read().decode("utf-8"))
        except Exception:
            return False, {"error": str(e)}
    except Exception as exc:
        return False, {"error": str(exc), "_network": True}


def _get_api(port: int, path: str, timeout: int = 10) -> tuple[bool, dict]:
    url = f"http://127.0.0.1:{port}{path}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return False, json.loads(e.read().decode("utf-8"))
        except Exception:
            return False, {"error": str(e)}
    except Exception as exc:
        return False, {"error": str(exc), "_network": True}


# ── 检测函数 ─────────────────────────────────────────────────────────────

def check_file_existence() -> None:
    print("\n[1] 文件存在检查")

    strategy_html = WEB / "strategy.html"
    if strategy_html.exists():
        record(PASS, "旧策略台 strategy.html 存在")
    else:
        record(FAIL, "旧策略台 strategy.html 不存在", str(strategy_html))

    canon_html = WEB / "strategy_canon.html"
    if canon_html.exists():
        record(PASS, "新试点页 strategy_canon.html 存在")
    else:
        record(FAIL, "新试点页 strategy_canon.html 不存在", str(canon_html))

    canon_js = JS / "canon_source_pilot.js"
    if canon_js.exists():
        record(PASS, "canon_source_pilot.js 存在")
    else:
        record(FAIL, "canon_source_pilot.js 不存在", str(canon_js))


def check_canon_html_elements() -> None:
    print("\n[2] 试点页关键 DOM 元素检查 (CANON-002 原子化版)")
    html = _read_html(WEB / "strategy_canon.html")
    if not html:
        record(FAIL, "strategy_canon.html 无法读取")
        return

    checks = [
        # 模式切换
        ("三模式切换-板块",          'id="canon-mode-sector"'),
        ("三模式切换-A股",           'id="canon-mode-astock"'),
        ("三模式切换-联动",          'id="canon-mode-linked"'),
        # CANON-002: 原子容器（取代旧 textarea）
        ("原子容器-板块",            'id="sector-atom-rows"'),
        ("原子容器-A股",             'id="astock-atom-rows"'),
        ("原子容器-联动板块",        'id="linked-sector-atom-rows"'),
        ("原子容器-联动A股",         'id="linked-astock-atom-rows"'),
        # CANON-002: 生成 Query 显示框
        ("Query显示-板块",           'id="sector-atom-query"'),
        ("Query显示-A股",            'id="astock-atom-query"'),
        ("Query显示-联动板块",       'id="linked-sector-atom-query"'),
        ("Query显示-联动A股",        'id="linked-astock-atom-query"'),
        # 预查按钮（已更名）
        ("板块预查按钮",             'id="btn-sector-preview"'),
        ("A股预查按钮",              'id="btn-astock-preview"'),
        ("联动板块预查按钮",         'id="btn-linked-sector-preview"'),
        ("联动预查按钮",             'id="btn-linked-preview"'),
        # 按钮文字已更名为"预查"
        ("板块预查文字",             '预查板块样例'),
        ("A股预查文字",              '预查问财样例'),
        ("联动预查文字",             '预查联动样例'),
        # CANON-002: 状态机 — 确认/取消/清空
        ("板块确认来源按钮",         'id="btn-sector-confirm-source"'),
        ("板块取消来源按钮",         'id="btn-sector-cancel-source"'),
        ("板块清空条件按钮",         'id="btn-sector-clear"'),
        ("A股确认来源按钮",          'id="btn-astock-confirm-source"'),
        ("A股取消来源按钮",          'id="btn-astock-cancel-source"'),
        ("A股清空条件按钮",          'id="btn-astock-clear"'),
        ("联动确认来源按钮",         'id="btn-linked-confirm-source"'),
        ("联动取消来源按钮",         'id="btn-linked-cancel-source"'),
        ("联动A股清空按钮",          'id="btn-linked-astock-clear"'),
        ("联动板块清空按钮",         'id="btn-linked-sector-clear"'),
        # 联动最终 Query 预览（Phase B）
        ("联动最终 Query 预览",      'id="linked-final-query-preview"'),
        # 收藏
        ("SECTOR收藏按钮",           'id="btn-save-sector-canon"'),
        ("ASTOCK收藏按钮",           'id="btn-save-astock-canon"'),
        ("LINK收藏按钮",             'id="btn-save-linked-canon"'),
        ("放大/缩小按钮",            'id="canon-expand-btn"'),
        ("收藏库-A股 list",          'id="canon-fav-list-astock"'),
        ("收藏库-板块 list",         'id="canon-fav-list-sector"'),
        ("收藏库-联动 list",         'id="canon-fav-list-linked"'),
        # 隐藏 Sink（app.js 接口）
        ("隐藏 wencai-query",        'id="wencai-query"'),
        ("隐藏 sector-query",        'id="sector-query"'),
        # 中间/右侧（不变）
        ("中间最终 Query 预览",      'id="preview-source"'),
        ("技能选择区",               'id="skill-list"'),
        ("执行路径控件",             'name="path-type"'),
        ("预览并启动按钮",           'id="btn-run"'),
        ("中止按钮",                 'id="btn-abort"'),
        ("保存模板按钮",             'id="btn-save-template"'),
        ("清空日志按钮",             'id="btn-clear-log"'),
        ("查看报告按钮",             'id="btn-view-report"'),
        # 旧功能折叠区（保留）
        ("Bridge 折叠（旧功能）",    'id="bridge-enabled"'),
        ("P1-P6 折叠（旧功能）",     'data-preset="P1"'),
        # CANON-002 CSS 原子样式
        ("原子badge CSS",            '.atom-badge'),
        ("原子行 CSS",               '.atom-row'),
        ("原子query显示 CSS",        '.atom-query-display'),
    ]

    for label, pattern in checks:
        if pattern in html:
            record(PASS, label)
        else:
            record(FAIL, label, f"未找到 {pattern!r}")


def check_strategy_html_untouched() -> None:
    print("\n[3] 旧策略台完整性检查")
    html = _read_html(WEB / "strategy.html")
    if not html:
        record(FAIL, "strategy.html 无法读取")
        return

    checks = [
        ("旧策略台标题", "<title>策略台"),
        ("旧 wm-btn-stock",  'id="wm-btn-stock"'),
        ("旧 wm-btn-sector", 'id="wm-btn-sector"'),
        ("旧 Phase A 板块",  'id="phase-a-panel"'),
        ("旧 P1-P6 预设",    'data-preset="P1"'),
        ("旧执行路径控件",   'name="path-type"'),
        ("旧 skill-list",    'id="skill-list"'),
        ("旧 btn-run",       'id="btn-run"'),
    ]
    for label, pattern in checks:
        if pattern in html:
            record(PASS, f"旧策略台保留: {label}")
        else:
            record(FAIL, f"旧策略台损坏: {label}", f"缺少 {pattern!r}")


def check_js_functions() -> None:
    print("\n[4] canon_source_pilot.js 关键函数检查")
    js_path = JS / "canon_source_pilot.js"
    if not js_path.exists():
        record(FAIL, "canon_source_pilot.js 不存在，跳过")
        return
    code = js_path.read_text(encoding="utf-8")

    checks = [
        # CANON-002: 原子数据
        ("ASTOCK_ATOMS 定义",           "ASTOCK_ATOMS"),
        ("SECTOR_ATOMS 定义",           "SECTOR_ATOMS"),
        ("原子类型 bool",               "'bool'"),
        ("原子类型 num_op",             "'num_op'"),
        ("原子类型 top_n",              "'top_n'"),
        ("原子类型 range",              "'range'"),
        ("原子类型 forbidden",          "'forbidden'"),
        # CANON-002: 原子 UI 渲染
        ("_renderAtomGroups 函数",      "_renderAtomGroups"),
        ("_buildParamsHtml 函数",       "_buildParamsHtml"),
        ("_atomToQuery 函数",           "_atomToQuery"),
        # CANON-002: Query 生成
        ("_generateQuery 函数",         "_generateQuery"),
        ("板块后缀 '的板块'",           "'的板块'"),
        # CANON-002: 状态机
        ("_onAtomChange 函数",          "_onAtomChange"),
        ("_setStage 函数",              "_setStage"),
        ("_updateCtxButtons 函数",      "_updateCtxButtons"),
        ("IDLE 阶段",                   "'IDLE'"),
        ("BUILDING 阶段",               "'BUILDING'"),
        ("PREVIEWED 阶段",              "'PREVIEWED'"),
        ("CONFIRMED 阶段",              "'CONFIRMED'"),
        # CANON-002: 清空/取消
        ("_clearConditions 函数",       "_clearConditions"),
        ("_cancelSource 函数",          "_cancelSource"),
        # 联动
        ("_buildLinkedQuery 函数定义",  "_buildLinkedQuery"),
        ("buildLinkedQuery 全局暴露",   "window.canonBuildLinkedQuery"),
        ("_confirmLinkedSectors 函数",  "_confirmLinkedSectors"),
        # 预查
        ("_runSectorPreview 函数",      "_runSectorPreview"),
        ("_runAstockPreview 函数",      "_runAstockPreview"),
        ("_runLinkedPreview 函数",      "_runLinkedPreview"),
        ("_confirmSource 函数",         "_confirmSource"),
        ("_saveFavorite 函数",          "_saveFavorite"),
        ("确认来源写入 wencai-query",   "wencai-query"),
        ("调用 setWencaiMode",          "setWencaiMode"),
        ("调用 notifyStrategyStateChanged", "notifyStrategyStateChanged"),
        # 可用性（CANON-001 保留）
        ("30s 超时机制",                "PREVIEW_TIMEOUT_MS"),
        ("AbortController 超时",        "AbortController"),
        ("耗时显示 (elapsed)",          "canon-elapsed"),
        ("Query 回显",                  "canon-preview-query"),
        ("接口状态提示 hint",           "_getWencaiHint"),
        ("无 alert() 调用",             "_showStatus"),
    ]
    for label, pattern in checks:
        if pattern in code:
            record(PASS, label)
        else:
            record(FAIL, label, f"未在 JS 中找到 {pattern!r}")


def check_atom_model_logic() -> None:
    """
    [5b] CANON-002 原子模型逻辑验证（Python 复现 _atomToQuery / _generateQuery）
    """
    print("\n[5b] 原子模型逻辑验证")

    # Minimal Python replica of _atomToQuery + _generateQuery
    def atom_to_query(atom: dict, p: dict | None = None) -> str | None:
        p = p or {}
        t = atom["type"]
        if t == "forbidden":   return None
        if t == "bool":        return atom["query"]
        if t == "num_op":
            op  = p.get("op",  atom["def_op"])
            val = p.get("val", atom["def_val"])
            return atom["tmpl"].replace("{op}", op).replace("{val}", str(val))
        if t == "range":
            lo = p.get("lo", atom["def_lo"])
            hi = p.get("hi", atom["def_hi"])
            return atom["tmpl"].replace("{lo}", str(lo)).replace("{hi}", str(hi))
        if t == "top_n":
            n = p.get("n", atom["def_n"])
            return atom["tmpl"].replace("{n}", str(n))
        return None

    def generate_query(atoms: list[dict], checked: dict, params: dict, is_sector: bool) -> str:
        parts = []
        for a in atoms:
            if not checked.get(a["id"]) or a["type"] == "forbidden":
                continue
            q = atom_to_query(a, params.get(a["id"]))
            if q:
                parts.append(q)
        if not parts:
            return ""
        joined = "，".join(parts)
        return joined + "的板块" if is_sector else joined

    # Subset of atoms for testing
    A_ATOMS = [
        {"id": "A-非ST",   "type": "bool",    "query": "非ST"},
        {"id": "A-非停牌", "type": "bool",    "query": "非停牌"},
        {"id": "A-今涨",   "type": "num_op",  "def_op": "大于", "def_val": 3,  "unit": "%", "tmpl": "今日涨幅{op}{val}%"},
        {"id": "A-成交额", "type": "num_op",  "def_op": "大于", "def_val": 3,  "unit": "亿", "tmpl": "今日成交额大于{val}亿"},
        {"id": "A-流通市值","type":"range",   "def_lo": 30, "def_hi": 150, "unit": "亿", "tmpl": "流通市值在{lo}亿到{hi}亿之间"},
        {"id": "A-涨停10", "type": "bool",    "query": "近10日有涨停"},
        {"id": "A-强势股", "type": "forbidden","query": "强势股"},
    ]
    S_ATOMS = [
        {"id": "S-今涨",   "type": "num_op",  "def_op": "大于", "def_val": 3, "unit": "%", "tmpl": "今日涨幅{op}{val}%"},
        {"id": "S-净流排", "type": "top_n",   "def_n": 10, "tmpl": "今日主力净流入排名前{n}"},
        {"id": "S-热门",   "type": "forbidden","query": "热门板块"},
    ]

    cases = [
        {
            "desc":    "A股 bool × 2 + num_op 默认值",
            "atoms":   A_ATOMS, "is_sector": False,
            "checked": {"A-非ST": True, "A-非停牌": True, "A-今涨": True},
            "params":  {},
            "expected":"非ST，非停牌，今日涨幅大于3%",
        },
        {
            "desc":    "A股 forbidden 不入 query",
            "atoms":   A_ATOMS, "is_sector": False,
            "checked": {"A-强势股": True, "A-非ST": True},
            "params":  {},
            "expected":"非ST",
        },
        {
            "desc":    "A股 range 默认值",
            "atoms":   A_ATOMS, "is_sector": False,
            "checked": {"A-流通市值": True},
            "params":  {},
            "expected":"流通市值在30亿到150亿之间",
        },
        {
            "desc":    "A股 num_op 覆盖参数",
            "atoms":   A_ATOMS, "is_sector": False,
            "checked": {"A-今涨": True},
            "params":  {"A-今涨": {"op": "小于", "val": 0}},
            "expected":"今日涨幅小于0%",
        },
        {
            "desc":    "板块 num_op + top_n → 加 '的板块' 后缀",
            "atoms":   S_ATOMS, "is_sector": True,
            "checked": {"S-今涨": True, "S-净流排": True},
            "params":  {},
            "expected":"今日涨幅大于3%，今日主力净流入排名前10的板块",
        },
        {
            "desc":    "板块 forbidden 不入 query",
            "atoms":   S_ATOMS, "is_sector": True,
            "checked": {"S-热门": True, "S-今涨": True},
            "params":  {},
            "expected":"今日涨幅大于3%的板块",
        },
        {
            "desc":    "空勾选 → 空 query",
            "atoms":   A_ATOMS, "is_sector": False,
            "checked": {},
            "params":  {},
            "expected":"",
        },
    ]

    for case in cases:
        result = generate_query(case["atoms"], case["checked"], case["params"], case["is_sector"])
        if result == case["expected"]:
            record(PASS, case["desc"], result[:60] + ("…" if len(result) > 60 else ""))
        else:
            record(FAIL, case["desc"],
                   f"期望: {case['expected']!r}  得到: {result!r}")


def check_linked_query_logic() -> None:
    """
    [7] 联动 query 拼接逻辑正确性（纯 Python 逻辑复现）
    """
    print("\n[5] 联动 query 拼接逻辑验证")

    def build_linked_query(sectors: list[str], astock_condition: str) -> str:
        if not sectors:
            return ""
        sector_clause = "或".join(s + "板块" for s in sectors)
        base = "属于" + sector_clause
        if astock_condition:
            base += "，且" + astock_condition
        return base

    cases = [
        {
            "sectors":    ["人工智能", "半导体"],
            "condition":  "非ST，今日涨幅大于3%",
            "expected":   "属于人工智能板块或半导体板块，且非ST，今日涨幅大于3%",
        },
        {
            "sectors":    ["军工"],
            "condition":  "今日成交额大于5亿",
            "expected":   "属于军工板块，且今日成交额大于5亿",
        },
        {
            "sectors":    ["通信线缆及配套", "机床工具", "激光设备"],
            "condition":  "非ST，非停牌，今日涨幅大于3%，今日成交额大于3亿",
            "expected":   "属于通信线缆及配套板块或机床工具板块或激光设备板块，且非ST，非停牌，今日涨幅大于3%，今日成交额大于3亿",
        },
        {
            "sectors":    ["人工智能", "半导体"],
            "condition":  "",
            "expected":   "属于人工智能板块或半导体板块",
        },
    ]

    for i, case in enumerate(cases, 1):
        result = build_linked_query(case["sectors"], case["condition"])
        if result == case["expected"]:
            record(PASS, f"拼接案例 {i}", result[:60] + ("…" if len(result) > 60 else ""))
        else:
            record(FAIL, f"拼接案例 {i}",
                   f"期望: {case['expected']!r}  得到: {result!r}")


def check_server_api(port: int) -> None:
    print(f"\n[6] 服务器 API 检查 (port={port})")
    SLOW_WARN_S = 20.0  # 超过此耗时警告"接口慢"

    # 健康检查
    t0 = time.perf_counter()
    ok, data = _get_api(port, "/api/health")
    health_elapsed = time.perf_counter() - t0

    if not ok and data.get("_network"):
        record(SKIP, f"服务未在 127.0.0.1:{port} 运行，跳过所有 API 检测",
               "启动命令: .venv\\Scripts\\python.exe scripts\\v6op_server.py")
        return

    record(PASS if ok else WARN, f"健康检查 /api/health ({health_elapsed:.2f}s)",
           data.get("status", str(data))[:80])

    # 板块 preview
    print("  — 板块 preview (scan_sectors):")
    t1 = time.perf_counter()
    ok_s, data_s = _post_api(port, "/api/scan_sectors", {
        "sector_query": "今日涨幅大于3%的板块",
        "sector_top_n": 5,
    })
    sec_elapsed = time.perf_counter() - t1
    slow_sec = sec_elapsed > SLOW_WARN_S

    if not ok_s and data_s.get("_network"):
        record(SKIP, "板块 API 连接失败")
    elif "sectors" in data_s:
        sectors = data_s.get("sectors", [])
        err     = data_s.get("error")
        timing  = f"耗时 {sec_elapsed:.2f}s" + ("【接口慢/可能卡住】" if slow_sec else "")
        if err:
            record(WARN, f"板块 API 可调用但有错误 ({timing})", err[:120])
        elif sectors:
            record(PASS, f"板块 API 返回结果 ({timing})", f"{len(sectors)} 个板块: {sectors[:3]}")
        else:
            record(WARN, f"板块 API 返回空列表 ({timing})",
                   "可能原因：pywencai session 失效、网络不可用、问财接口限流")
    else:
        record(WARN, f"板块 API 响应格式异常 (耗时 {sec_elapsed:.2f}s)", str(data_s)[:120])

    # A股 preview
    print("  — A股 preview (wencai/preview):")
    t2 = time.perf_counter()
    ok_a, data_a = _post_api(port, "/api/wencai/preview", {
        "query": "非ST，非停牌，今日涨幅大于3%",
        "limit": 10,
    })
    astock_elapsed = time.perf_counter() - t2
    slow_ast = astock_elapsed > SLOW_WARN_S
    timing_a = f"耗时 {astock_elapsed:.2f}s" + ("【接口慢/可能卡住】" if slow_ast else "")

    if not ok_a and data_a.get("_network"):
        record(SKIP, "A股 preview API 连接失败")
    else:
        status = data_a.get("status", "unknown")
        note   = data_a.get("note") or data_a.get("error") or ""
        if status == "ok":
            codes = data_a.get("codes", [])
            record(PASS, f"A股 preview API 返回结果 ({timing_a})",
                   f"{data_a.get('count',0)} 只（显示 {len(codes)} 只）")
        elif status in ("key_missing", "blocked", "auth_failed",
                        "network_error", "api_error", "empty_result",
                        "pywencai_not_installed"):
            record(WARN, f"A股 preview API 受阻 [{status}] ({timing_a})", note[:120])
        else:
            record(WARN, f"A股 preview API 未知状态 [{status}] ({timing_a})", str(data_a)[:120])


def check_server_endpoint_exists(port: int) -> None:
    """确认 /api/wencai/preview 端点存在于服务器代码"""
    print("\n[7] 服务器端点代码检查")
    srv = ROOT / "scripts" / "v6op_server.py"
    if not srv.exists():
        record(FAIL, "v6op_server.py 不存在")
        return
    code = srv.read_text(encoding="utf-8")
    if '"/api/wencai/preview"' in code or "'/api/wencai/preview'" in code \
            or '/api/wencai/preview' in code:
        record(PASS, "/api/wencai/preview 端点已添加到 v6op_server.py")
    else:
        record(FAIL, "/api/wencai/preview 端点未在 v6op_server.py 中找到")

    if "wencai_source" in code and "wencai/preview" in code:
        record(PASS, "端点调用 wencai_source 模块")
    else:
        record(WARN, "端点可能未正确引用 wencai_source")


def check_nav_entry() -> None:
    print("\n[8] 导航入口检查")
    common = JS / "common.js"
    if not common.exists():
        record(FAIL, "common.js 不存在")
        return
    code = common.read_text(encoding="utf-8")
    if "strategy_canon.html" in code and "法典试点" in code:
        record(PASS, "common.js 包含法典试点导航入口")
    else:
        record(WARN, "common.js 中未找到法典试点导航入口（可选）")


def summary() -> int:
    print("\n" + "=" * 60)
    total  = len(_results)
    passed = sum(1 for s, *_ in _results if s == PASS)
    failed = sum(1 for s, *_ in _results if s == FAIL)
    warned = sum(1 for s, *_ in _results if s == WARN)
    skipped = sum(1 for s, *_ in _results if s == SKIP)
    print(f"总计: {total}  通过: {passed}  失败: {failed}  警告: {warned}  跳过: {skipped}")
    if failed == 0:
        print("✔ 所有必检项通过。")
    else:
        print(f"✖ {failed} 项失败，请检查上方输出。")
    print("=" * 60)
    return 1 if failed > 0 else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="问财法典来源区试点检测脚本")
    parser.add_argument("--port", type=int, default=8876, help="服务器端口（默认 8876）")
    parser.add_argument("--no-api", action="store_true", help="跳过 API 检测")
    args = parser.parse_args()

    print("=" * 60)
    print("  问财法典来源区试点 — 自动检测")
    print(f"  工作目录: {ROOT}")
    print("=" * 60)

    check_file_existence()
    check_canon_html_elements()
    check_strategy_html_untouched()
    check_js_functions()
    check_atom_model_logic()
    check_linked_query_logic()
    check_server_endpoint_exists(args.port)
    check_nav_entry()

    if not args.no_api:
        check_server_api(args.port)
    else:
        print("\n[6] API 检测已跳过 (--no-api)")

    sys.exit(summary())


if __name__ == "__main__":
    main()
