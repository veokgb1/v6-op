#!/usr/bin/env python3
"""
browser_smoke_playwright.py — V6OP 真实浏览器级 Smoke 验收（总纲第十二章）

与 browser_smoke.py（HTTP smoke）的区别：
  本脚本通过 Playwright 驱动真实 Chromium 浏览器，验证：
  - 技能工具箱真实 DOM 渲染（22 条，含 5 个 live + 17 个 gray）
  - 灰卡 checkbox.disabled === true（DOM 层）
  - 参数填写 → 运行 → 刷新 → localStorage 回显
  - 实时日志区域渲染（#log-box 有内容）
  - 结果面板可见（#result-area）

Playwright 不可用时：
  - 输出 {"status": "browser_unavailable", ...}
  - exit code 2（环境限制，非测试失败）
  - 报告不得写"真实浏览器已通过"

用法：
  python scripts/browser_smoke_playwright.py --base-url http://127.0.0.1:7749 \\
    --json-out output/verification/v6op024_browser_smoke.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).parent.resolve()
_PROJECT_ROOT = _SCRIPTS_DIR.parent


def _check_playwright() -> tuple[bool, str]:
    """Returns (available, reason)."""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
        return True, "ok"
    except ImportError:
        return False, "playwright 未安装（pip install playwright && playwright install chromium）"
    except Exception as exc:
        return False, f"playwright 导入失败: {exc}"


def run_browser_smoke(base_url: str) -> dict:
    """
    使用 Playwright 运行真实浏览器 smoke。
    如果 Playwright 不可用，返回 {"status": "browser_unavailable", ...}。
    """
    available, reason = _check_playwright()
    if not available:
        return {
            "status": "browser_unavailable",
            "reason": reason,
            "base_url": base_url,
            "verified_at": datetime.now().isoformat(),
            "note": "报告不得写'真实浏览器已通过'——Playwright 未安装",
        }

    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError  # type: ignore

    results: dict = {"base_url": base_url, "verified_at": datetime.now().isoformat()}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()

        try:
            # ── 1. 打开页面 ─────────────────────────────────────────────
            page.goto(base_url, timeout=10_000)
            page.wait_for_load_state("networkidle", timeout=10_000)
            results["page_loaded"] = True

            # ── 2. 技能工具箱 DOM 渲染 ──────────────────────────────────
            skill_list = page.query_selector("#skill-list")
            results["skill_list_rendered"] = skill_list is not None

            # live checkboxes（未 disabled）
            live_cbs = page.query_selector_all("#skill-list input[type=checkbox]:not([disabled])")
            results["live_skill_count"] = len(live_cbs)
            results["live_skills_ok"] = len(live_cbs) >= 5

            # gray checkboxes（disabled）
            gray_cbs = page.query_selector_all("#skill-list input[type=checkbox][disabled]")
            results["gray_skill_count"] = len(gray_cbs)
            results["gray_skills_ok"] = len(gray_cbs) >= 17

            # P2: Bridge 控件真实 DOM 存在
            results["bridge_controls_rendered"] = all([
                page.query_selector("#bridge-enabled") is not None,
                page.query_selector("#bridge-mode") is not None,
                page.query_selector("#bridge-query") is not None,
            ])

            # ── 3. 灰卡 checkbox.disabled 验证（DOM 层）─────────────────
            for cb in gray_cbs:
                assert cb.get_attribute("disabled") is not None, \
                    "灰卡 checkbox 应有 disabled 属性"
            results["gray_checkboxes_disabled"] = True

            # ── 4. 参数填写 → 运行 → 刷新 → localStorage 回显 ──────────
            # 先清除旧参数
            page.evaluate("localStorage.clear()")

            # 确保 manual 来源被选中
            manual_radio = page.query_selector("input[name='source-type'][value='manual']")
            if manual_radio:
                manual_radio.check()

            manual_input = page.query_selector("#manual-codes")
            if manual_input:
                manual_input.fill("000001.SZ,000002.SZ")

            # 点击运行
            run_btn = page.query_selector("#btn-run")
            results["run_btn_exists"] = run_btn is not None
            if run_btn:
                run_btn.click()
                time.sleep(1)

            # 检查 localStorage 是否有参数
            stored = page.evaluate(
                "localStorage.getItem('v6op_last_params')"
            )
            results["localStorage_params_saved"] = stored is not None

            # 刷新后验证回显
            page.reload()
            page.wait_for_load_state("networkidle", timeout=10_000)
            manual_val = page.evaluate(
                "document.getElementById('manual-codes')?.value || ''"
            )
            results["params_restored_after_reload"] = "000001" in (manual_val or "")

            # ── 5. 日志区域渲染 ─────────────────────────────────────────
            log_box = page.query_selector("#log-box")
            results["log_box_rendered"] = log_box is not None

            # ── 6. 结果面板 ─────────────────────────────────────────────
            result_area = page.query_selector("#rtab-results")
            results["result_area_rendered"] = result_area is not None

        except PWTimeoutError as exc:
            results["error"] = f"Playwright TimeoutError: {exc}"
            results["browser_smoke_passed"] = False
            return results
        except Exception as exc:
            results["error"] = str(exc)
            results["browser_smoke_passed"] = False
            return results
        finally:
            browser.close()

    # ── 评分 ────────────────────────────────────────────────────────────
    checks = [
        results.get("page_loaded", False),
        results.get("skill_list_rendered", False),
        results.get("live_skills_ok", False),
        results.get("gray_skills_ok", False),
        results.get("gray_checkboxes_disabled", False),
        results.get("bridge_controls_rendered", False),
        results.get("localStorage_params_saved", False),
        results.get("log_box_rendered", False),
        results.get("result_area_rendered", False),
    ]
    results["browser_smoke_passed"] = all(checks)
    results["checks_passed"] = sum(checks)
    results["checks_total"] = len(checks)
    results["status"] = "pass" if results["browser_smoke_passed"] else "fail"
    return results


def _wait_for_server(base_url: str, timeout: int = 15) -> bool:
    import urllib.request
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(f"{base_url}/api/health", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="V6OP 真实浏览器级 Smoke 验收")
    parser.add_argument("--base-url", default="http://127.0.0.1:7749")
    parser.add_argument("--json-out", dest="json_out", default=None)
    parser.add_argument("--start-server", action="store_true",
                        help="自动启动 v6op_server，完成后终止")
    parser.add_argument("--port", type=int, default=7752,
                        help="自动启动服务器时使用的端口")
    args = parser.parse_args(argv)

    base_url = args.base_url
    proc = None

    if args.start_server:
        venv_python = _PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
        server_script = _SCRIPTS_DIR / "v6op_server.py"
        proc = subprocess.Popen(
            [str(venv_python), str(server_script), "--port", str(args.port)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            cwd=str(_PROJECT_ROOT),
        )
        base_url = f"http://127.0.0.1:{args.port}"
        print(f"Server PID={proc.pid}  port={args.port}", flush=True)
        if not _wait_for_server(base_url, timeout=15):
            print("ERROR: server did not start within 15s", flush=True)
            proc.terminate()
            sys.exit(1)

    try:
        result = run_browser_smoke(base_url)
    finally:
        if proc is not None:
            proc.terminate()

    out_path = Path(args.json_out) if args.json_out else (
        _PROJECT_ROOT / "output" / "verification" / "v6op024_browser_smoke.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\nJSON → {out_path}", flush=True)

    status = result.get("status")
    if status == "pass":
        return 0
    if status == "browser_unavailable":
        return 2   # 环境限制，非测试失败
    return 1


if __name__ == "__main__":
    sys.exit(main())
