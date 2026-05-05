#!/usr/bin/env python3
"""
browser_smoke.py — V6OP-023 Task 5 浏览器级 smoke 验收（HTTP API 等价）

验证：
1. /api/health 健康
2. index.html 包含技能列表、灰色技能标记、参数回显按钮
3. app.js 包含 SKILL_CATALOG_GRAY / localStorage / 灰色 disabled 标记
4. 运行 manual 小股票池后，日志实时推送，结果区可见
5. mask_cache_hits 字段出现在结果中
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

_SCRIPTS = Path(__file__).parent.resolve()
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def run_smoke(base_url: str) -> dict:
    import requests

    results: dict = {"base_url": base_url}

    # 1. Health
    r = requests.get(f"{base_url}/api/health", timeout=5)
    results["health_status"] = r.status_code
    health = r.json()
    results["health_ok"] = health.get("status") == "ok"
    results["python_version"] = health.get("python_version", "")

    # 2. index.html
    r = requests.get(f"{base_url}/", timeout=5)
    html = r.text
    results["index_ok"] = r.status_code == 200
    results["index_has_skill_list"]        = "skill-list" in html
    results["index_has_btn_run"]           = "btn-run" in html
    results["index_has_btn_reset_params"]  = "btn-reset-params" in html
    results["index_has_prefetch_box"]      = "prefetch-box" in html
    results["index_has_prefetch_section"]  = "本轮预热摘要" in html

    # 3. app.js
    r = requests.get(f"{base_url}/app.js", timeout=5)
    js = r.text
    results["app_js_ok"] = r.status_code == 200
    results["js_has_SKILL_CATALOG_GRAY"] = "SKILL_CATALOG_GRAY" in js
    results["js_has_localStorage"]       = "localStorage" in js
    results["js_gray_disabled"]          = "cb.disabled = true" in js
    results["js_has_LIVE_SKILL_IDS"]     = "LIVE_SKILL_IDS" in js
    results["js_gray_skill_count"]       = js.count("skill_id: '")
    results["js_has_restoreParams"]      = "restoreParams" in js
    results["js_has_saveParams"]         = "saveParams" in js
    results["js_has_resetParams"]        = "resetParams" in js

    # 4. Run manual small pool
    strategy = {
        "source": {"type": "manual", "codes": ["000001.SZ", "000002.SZ", "300083.SZ"]},
        "skills": ["kline", "landmine"],
        "path_type": "parallel_and",
        "params": {},
    }
    r = requests.post(f"{base_url}/api/run", json=strategy, timeout=10)
    run_data = r.json()
    results["run_http_status"] = r.status_code
    results["run_id"] = run_data.get("run_id")

    # Poll stream
    stream_data: dict = {}
    for _ in range(25):
        time.sleep(1)
        r2 = requests.get(f"{base_url}/api/stream?since=0", timeout=5)
        stream_data = r2.json()
        if stream_data.get("status") in ("completed", "error"):
            break

    results["stream_final_status"] = stream_data.get("status")
    results["stream_event_count"] = stream_data.get("event_count", 0)
    events = stream_data.get("events") or []
    results["log_events_sample"] = [e["msg"] for e in events[:5]]
    results["log_has_realtime_events"] = len(events) > 0

    # 5. Result
    r = requests.get(f"{base_url}/api/result", timeout=5)
    res = r.json()
    results["result_http_status"] = r.status_code
    results["final_hit_count"]    = res.get("final_hit_count")
    results["readiness"]          = (res.get("data_coverage") or {}).get("readiness")
    results["prefetch_triggered"] = res.get("prefetch_triggered")
    results["mask_cache_hits"]    = res.get("mask_cache_hits")
    results["mask_cache_misses"]  = res.get("mask_cache_misses")

    # Verdict
    checks = [
        results["health_ok"],
        results["index_has_skill_list"],
        results["index_has_btn_reset_params"],
        results["js_has_SKILL_CATALOG_GRAY"],
        results["js_gray_disabled"],
        results["js_has_localStorage"],
        results["stream_final_status"] == "completed",
        results["log_has_realtime_events"],
        results["mask_cache_hits"] is not None,
    ]
    results["smoke_passed"] = all(checks)
    results["checks_passed"] = sum(checks)
    results["checks_total"] = len(checks)
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="V6OP browser-level smoke test")
    parser.add_argument("--base-url", default="http://127.0.0.1:7749")
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args()

    result = run_smoke(args.base_url)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nJSON 写入: {out}", file=sys.stderr)

    sys.exit(0 if result["smoke_passed"] else 1)
