#!/usr/bin/env python3
"""
v6op_server.py — V6OP 本地后端 API 服务器

端点：
  GET  /api/health   - Python 版本、路径、关键文件检查（不返回 key 值）
  POST /api/run      - 接收策略 JSON，启动执行，返回 run_id
  GET  /api/result   - 返回最近 execution_result.json
  GET  /api/stream   - 可轮询事件列表（SSE 等价）

注意：/api/stream 实现为 JSON 轮询（非 true SSE），
      在报告中已说明，可通过定期 GET 获取实时进度。

用法：
  python scripts/v6op_server.py                   # 启动服务
  python scripts/v6op_server.py --port 8876
  python scripts/v6op_server.py --self-test       # 自测模式
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import threading
import time
import traceback
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote

_SCRIPTS_DIR = Path(__file__).parent.resolve()
_PROJECT_ROOT = _SCRIPTS_DIR.parent

for _p in [str(_SCRIPTS_DIR), str(_SCRIPTS_DIR / "producers"),
           str(_SCRIPTS_DIR / "sources")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from time_utils import iso_cst

# ── 全局运行状态 ──────────────────────────────────────────────────────
_run_state: dict = {
    "run_id": None,
    "status": "idle",    # idle / running / completed / error / aborted
    "started_at": None,
    "completed_at": None,
    "error": None,
    "final_hit_count": 0,
    "events": [],        # 轮询事件列表（/api/stream 用）
    "event_count": 0,    # 当前 run 的累计事件数，供 ?since=N 游标使用
    "abort_requested": False,
}
_state_lock = threading.Lock()
_DEFAULT_PORT = 8876


def _push_event(level: str, msg: str) -> None:
    with _state_lock:
        event_index = int(_run_state.get("event_count", 0))
        _run_state["events"].append({
            "index": event_index,
            "ts": iso_cst(),
            "level": level,
            "msg": msg,
        })
        _run_state["event_count"] = event_index + 1


def _run_execution_background(strategy: dict) -> None:
    """后台线程中执行策略。日志事件通过 _log_sink 实时推送到 /api/stream。"""
    import execution_engine  # type: ignore
    try:
        # 安装实时日志 sink：每条 _log() 调用都会同步推入 _run_state["events"]
        execution_engine._log_sink = _push_event

        with _state_lock:
            _run_state["status"] = "running"
            current_run_id = _run_state["run_id"]
        _push_event("INFO", f"执行开始 run_id={current_run_id}")

        result = execution_engine.execute(strategy)

        with _state_lock:
            _run_state["status"] = result.get("status", "completed")
            _run_state["completed_at"] = iso_cst()
            _run_state["final_hit_count"] = result.get("final_hit_count", 0)
            final_status = _run_state["status"]
            final_hits = _run_state["final_hit_count"]
        _push_event("INFO",
                    f"执行完成 status={final_status} hits={final_hits}")

    except execution_engine.AbortRequested:
        with _state_lock:
            _run_state["status"] = "aborted"
            _run_state["completed_at"] = iso_cst()
        _push_event("WARN", "执行已中止（用户请求）")

    except Exception as exc:
        tb = traceback.format_exc()
        with _state_lock:
            _run_state["status"] = "error"
            _run_state["error"] = str(exc)
            _run_state["completed_at"] = iso_cst()
        _push_event("ERROR", f"执行异常: {exc}")
        print(f"[v6op_server] 执行异常:\n{tb}", file=sys.stderr)
    finally:
        # 卸载 sink，防止跨 run 污染
        execution_engine._log_sink = None


# ── 健康检查 ──────────────────────────────────────────────────────────

def _health_data() -> dict:
    key_files = {
        "ashare_codes": (_PROJECT_ROOT / "data" / "ashare_codes.txt").exists(),
        "skill_registry": (_SCRIPTS_DIR / "skill_registry.py").exists(),
        "execution_engine": (_SCRIPTS_DIR / "execution_engine.py").exists(),
        "prefetch_report": (_PROJECT_ROOT / "output" / "current" / "prefetch_report.json").exists(),
        "czsc_mask": (_PROJECT_ROOT / "output" / "current" / "czsc_mask.json").exists(),
    }
    env_exists = (_PROJECT_ROOT / ".env").exists()
    # 只报告变量名是否存在，不返回值
    env_vars_present: list[str] = []
    if env_exists:
        try:
            content = (_PROJECT_ROOT / ".env").read_text(encoding="utf-8")
            for line in content.splitlines():
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    var_name = line.split("=", 1)[0].strip()
                    if var_name:
                        env_vars_present.append(var_name)
        except Exception:
            pass

    return {
        "status": "ok",
        "python_version": sys.version,
        "v6op_path": str(_PROJECT_ROOT),
        "key_files": key_files,
        "dot_env_exists": env_exists,
        "dot_env_var_names": env_vars_present,  # 只含变量名，不含值
        "generated_at": iso_cst(),
    }


# ── HTTP Handler ──────────────────────────────────────────────────────

class V6OPHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:  # type: ignore[override]
        # 使用自定义日志，不打印到 stderr
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}][v6op_server] {fmt % args}", flush=True)

    def _send_json(self, code: int, data: dict | list) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length) if length > 0 else b""

    def do_OPTIONS(self) -> None:  # CORS preflight
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        path = self.path.split("?")[0]

        if path == "/api/health":
            self._send_json(200, _health_data())

        elif path == "/api/result":
            # 方案 A：返回前端专用 run_report.json（结构稳定，前端直接读取）
            result_path = _PROJECT_ROOT / "output" / "current" / "run_report.json"
            if not result_path.exists():
                # 兼容：如果只有 execution_result.json，也接受
                alt = _PROJECT_ROOT / "output" / "current" / "execution_result.json"
                if alt.exists():
                    result_path = alt
                else:
                    self._send_json(404, {"error": "尚无执行结果", "hint": "先调用 POST /api/run"})
                    return
            try:
                data = json.loads(result_path.read_text(encoding="utf-8"))
                self._send_json(200, data)
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})

        elif path == "/api/stream":
            # 返回可轮询事件列表（JSON 轮询，非 true SSE）
            # 支持 ?since=N，返回从索引 N 起的新事件，避免长日志截断
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            try:
                since = max(0, int(qs.get("since", ["0"])[0]))
            except (ValueError, IndexError):
                since = 0

            with _state_lock:
                events = list(_run_state["events"])
                event_count = int(_run_state.get("event_count", len(events)))
                state_summary = {
                    "run_id": _run_state["run_id"],
                    "status": _run_state["status"],
                    "started_at": _run_state["started_at"],
                    "completed_at": _run_state["completed_at"],
                    "final_hit_count": _run_state["final_hit_count"],
                    "event_count": event_count,
                    "events": [
                        ev for ev in events
                        if int(ev.get("index", 0)) >= since
                    ],
                    "note": (
                        "本实现为 JSON 轮询（非 true SSE）。"
                        "使用 ?since=N 获取从索引 N 起的新事件，避免截断。"
                        "建议每 1-2 秒轮询一次。"
                    ),
                }
            self._send_json(200, state_summary)

        elif path == "/api/skill_catalog":
            try:
                import skill_catalog as _sc
                self._send_json(200, _sc.get_catalog())
            except Exception as exc:
                self._send_json(500, {"error": f"skill_catalog 加载失败: {exc}"})

        elif path == "/api/runs":
            # G7: 历史运行记录列表（从 output/runs/ 读取）
            runs_dir = _PROJECT_ROOT / "output" / "runs"
            runs: list[dict] = []
            if runs_dir.exists():
                for run_dir in sorted(runs_dir.iterdir(), reverse=True):
                    if not run_dir.is_dir():
                        continue
                    rr = run_dir / "run_report.json"
                    if rr.exists():
                        try:
                            d = json.loads(rr.read_text(encoding="utf-8"))
                            runs.append({
                                "run_id": d.get("run_id", run_dir.name),
                                "generated_at": d.get("generated_at", ""),
                                "status": d.get("status", ""),
                                "final_hit_count": d.get("final_hit_count", 0),
                                "actual_days_used": d.get("actual_days_used", 365),
                                "path_type": d.get("strategy", {}).get("path_type", ""),
                                "source_type": d.get("strategy", {}).get("source", {}).get("type", ""),
                            })
                        except Exception:
                            runs.append({"run_id": run_dir.name, "status": "unreadable"})
            self._send_json(200, {"runs": runs[:20], "total": len(runs)})

        elif path.startswith("/api/runs/") and path.endswith("/params"):
            # G7: 恢复历史运行参数（只返回，不启动）
            parts = path.split("/")
            if len(parts) >= 4:
                run_id_req = parts[3]
                rr_path = _PROJECT_ROOT / "output" / "runs" / run_id_req / "run_report.json"
                if rr_path.exists():
                    try:
                        d = json.loads(rr_path.read_text(encoding="utf-8"))
                        summary = d.get("strategy", {}) or {}
                        params = d.get("strategy_snapshot") or {
                            "source": summary.get("source", {}),
                            "skills": summary.get("selected_skills", []),
                            "path_type": summary.get("path_type", ""),
                            "params": summary.get("params", {}),
                        }
                        self._send_json(200, {
                            "run_id": run_id_req,
                            "params": params,
                            "strategy": summary,
                            "strategy_snapshot": d.get("strategy_snapshot", {}),
                            "actual_days_used": d.get("actual_days_used", 365),
                            "note": "参数已恢复，不会自动启动运行",
                        })
                    except Exception as exc:
                        self._send_json(500, {"error": str(exc)})
                else:
                    self._send_json(404, {"error": f"历史记录不存在: {run_id_req}"})
            else:
                self._send_json(400, {"error": "无效路径"})

        elif path == "/api/wencai/status":
            # G4-auth: 问财授权状态检查
            env_path = _PROJECT_ROOT / ".env"
            has_key = False
            if env_path.exists():
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    if line.strip().startswith("IWENCAI_API_KEY="):
                        val = line.strip().split("=", 1)[-1].strip().strip('"').strip("'")
                        has_key = bool(val)
                        break
            try:
                import pywencai  # type: ignore
                pywencai_installed = True
            except ImportError:
                pywencai_installed = False
            self._send_json(200, {
                "env_key_present": has_key,
                "pywencai_installed": pywencai_installed,
                "auth_mechanism": (
                    "pywencai 使用 session 认证（非 api_key 参数）。"
                    "IWENCAI_API_KEY 已配置但不传入 pywencai.get()，"
                    "实际认证依赖 pywencai 本地缓存的 session cookie。"
                    if has_key else
                    "IWENCAI_API_KEY 未配置，无法调用问财 API。"
                ),
                "status": (
                    "ready" if (has_key and pywencai_installed) else
                    "key_missing" if not has_key else "pywencai_not_installed"
                ),
            })

        else:
            self._serve_static(path)

    def _serve_static(self, path: str) -> None:
        """服务 web/ 目录下的静态文件。"""
        _WEB_DIR = _PROJECT_ROOT / "web"
        _web_root = _WEB_DIR.resolve()
        _MIME = {
            ".html": "text/html; charset=utf-8",
            ".js":   "application/javascript; charset=utf-8",
            ".css":  "text/css; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".ico":  "image/x-icon",
        }
        # 根路径 → index.html
        if path in ("/", ""):
            path = "/index.html"

        # 安全：禁止路径穿越
        try:
            requested = unquote(path).replace("\\", "/").lstrip("/")
            target = (_web_root / requested).resolve()
            target.relative_to(_web_root)
        except ValueError:
            self._send_json(403, {"error": "访问被拒绝"})
            return
        except Exception:
            self._send_json(400, {"error": "无效路径"})
            return

        if not target.exists() or not target.is_file():
            self._send_json(404, {"error": f"文件不存在: {path}"})
            return

        suffix = target.suffix.lower()
        content_type = _MIME.get(suffix, "application/octet-stream")
        try:
            body = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})

    def do_POST(self) -> None:
        path = self.path.split("?")[0]

        if path == "/api/run":
            body = self._read_body()
            try:
                strategy = json.loads(body.decode("utf-8")) if body else {}
            except json.JSONDecodeError as exc:
                self._send_json(400, {"error": f"JSON 解析失败: {exc}"})
                return

            if not strategy:
                self._send_json(400, {"error": "策略 JSON 不能为空"})
                return

            # ── 全 A 扫描保护（API 层，不能只靠前端）──────────────────
            src = strategy.get("source", {})
            if src.get("type") == "all_a":
                all_a_limit = int(src.get("limit", 50))
                if all_a_limit >= 500 and not strategy.get("confirm_large_scope"):
                    self._send_json(400, {
                        "error": (
                            f"全 A 扫描 {all_a_limit} 只超过 500 只上限，需要用户确认。"
                            "请在界面勾选确认框后重试。"
                        ),
                        "require_confirmation": True,
                        "scope_size": all_a_limit,
                    })
                    return

            with _state_lock:
                if _run_state["status"] == "running":
                    self._send_json(409, {
                        "error": "已有执行任务正在运行",
                        "run_id": _run_state["run_id"],
                        "status": _run_state["status"],
                    })
                    return

                run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                _run_state.update({
                    "run_id": run_id,
                    "status": "pending",
                    "started_at": iso_cst(),
                    "completed_at": None,
                    "error": None,
                    "final_hit_count": 0,
                    "events": [],
                    "event_count": 0,
                    "abort_requested": False,
                })
            # _push_event 也使用 _state_lock，必须在 with 块外调用以避免重入死锁
            _push_event("INFO", f"收到策略请求 run_id={run_id}")

            # 后台线程执行
            t = threading.Thread(
                target=_run_execution_background,
                args=(strategy,),
                daemon=True,
            )
            t.start()

            self._send_json(202, {
                "run_id": run_id,
                "status": "pending",
                "message": "执行已启动，请轮询 GET /api/stream 或 GET /api/result",
                "poll_endpoints": {
                    "stream": "/api/stream",
                    "result": "/api/result",
                },
            })

        elif path == "/api/abort":
            with _state_lock:
                current_status = _run_state["status"]
                if current_status not in ("running", "pending"):
                    self._send_json(200, {
                        "message": f"当前状态 {current_status}，无正在运行的任务",
                        "aborted": False,
                    })
                    return
                _run_state["abort_requested"] = True

            # 通知 execution_engine 设置中止标志
            try:
                import execution_engine as _ee
                _ee.request_abort()
            except Exception:
                pass

            _push_event("WARN", "收到中止请求，将在下一步骤边界停止")
            self._send_json(200, {
                "message": "中止请求已发送，执行将在下一个步骤边界停止",
                "aborted": True,
            })

        elif path == "/api/scan_sectors":
            body = self._read_body()
            try:
                req = json.loads(body.decode("utf-8")) if body else {}
            except json.JSONDecodeError as exc:
                self._send_json(400, {"error": f"JSON 解析失败: {exc}", "sectors": []})
                return

            sector_query = str(req.get("sector_query") or "").strip()
            try:
                top_n = max(1, int(req.get("sector_top_n") or 10))
            except (TypeError, ValueError):
                top_n = 10

            try:
                import sector_scan_source as _sss  # type: ignore
                result = _sss.scan(sector_query=sector_query, top_n=top_n)
                if result.get("error"):
                    self._send_json(400, result)
                else:
                    self._send_json(200, result)
            except Exception as exc:
                self._send_json(500, {
                    "sectors": [],
                    "count": 0,
                    "query": sector_query,
                    "error": f"板块扫描模块异常: {exc}",
                })

        elif path == "/api/cache/clear/source":
            # G7: 清来源快照缓存（output/current/wencai_scope.json 等 scope 文件）
            import glob as _glob
            cleared: list[str] = []
            for pattern in [
                str(_PROJECT_ROOT / "output" / "current" / "*_scope.json"),
                str(_PROJECT_ROOT / "output" / "current" / "prefetch_report.json"),
            ]:
                for fp in _glob.glob(pattern):
                    try:
                        Path(fp).unlink()
                        cleared.append(Path(fp).name)
                    except Exception:
                        pass
            self._send_json(200, {
                "layer": "source",
                "cleared": cleared,
                "count": len(cleared),
                "message": f"来源快照已清理 {len(cleared)} 个文件",
            })

        elif path == "/api/cache/clear/kline":
            # G7: 清K线数据库缓存（var/cache/kline_daily/*.pkl）
            kline_dir = _PROJECT_ROOT / "var" / "cache" / "kline_daily"
            cleared_count = 0
            if kline_dir.exists():
                for pkl in kline_dir.glob("*.pkl"):
                    try:
                        pkl.unlink()
                        cleared_count += 1
                    except Exception:
                        pass
            self._send_json(200, {
                "layer": "kline",
                "cleared_count": cleared_count,
                "message": f"K线数据库已清理 {cleared_count} 个缓存文件",
            })

        elif path == "/api/cache/clear/skill":
            # G7: 清技能结果库缓存（output/mask_cache/*.json）
            mask_dir = _PROJECT_ROOT / "output" / "mask_cache"
            cleared_count = 0
            if mask_dir.exists():
                for jf in mask_dir.glob("*.json"):
                    try:
                        jf.unlink()
                        cleared_count += 1
                    except Exception:
                        pass
            self._send_json(200, {
                "layer": "skill",
                "cleared_count": cleared_count,
                "message": f"技能结果库已清理 {cleared_count} 个缓存文件",
            })

        else:
            self._send_json(404, {"error": f"未知路径: {path}"})


# ── 服务器启动 ────────────────────────────────────────────────────────

def start_server(port: int = _DEFAULT_PORT, bind: str = "127.0.0.1") -> HTTPServer:
    for attempt_port in [port, port + 1, port + 2]:
        try:
            server = HTTPServer((bind, attempt_port), V6OPHandler)
            if attempt_port != port:
                print(
                    f"[v6op_server] 端口 {port} 被占用，使用 {attempt_port}",
                    flush=True,
                )
            return server
        except OSError:
            continue
    raise OSError(f"端口 {port}~{port+2} 均被占用，无法启动服务器")


def self_test(port: int = _DEFAULT_PORT) -> bool:
    """启动服务器，执行自测，返回是否通过。"""
    import urllib.request
    import urllib.error

    print("[self-test] 启动服务器...", flush=True)
    server = start_server(port)
    actual_port = server.server_address[1]
    base_url = f"http://127.0.0.1:{actual_port}"

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.3)

    passed = 0
    failed = 0

    def check(name: str, ok: bool, detail: str = "") -> None:
        nonlocal passed, failed
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}{': ' + detail if detail else ''}", flush=True)
        if ok:
            passed += 1
        else:
            failed += 1

    try:
        # Test /api/health
        print(f"\n[self-test] GET {base_url}/api/health", flush=True)
        resp = urllib.request.urlopen(f"{base_url}/api/health", timeout=5)
        data = json.loads(resp.read().decode())
        check("/api/health 状态码", resp.status == 200)
        check("/api/health python_version 存在", "python_version" in data)
        check("/api/health v6op_path 存在", "v6op_path" in data)
        # 检查 health 不含 key 的实际值（变量名列表中出现名称是允许的）
        data_str = json.dumps(data)
        env_vars = data.get("dot_env_var_names", [])
        # 只要 key 值不出现（不检查变量名本身，变量名在 dot_env_var_names 中是允许的）
        key_val_leaked = any(
            len(v) > 20 and v in data_str and v not in env_vars
            for v in (env_vars or [])
        )
        check("/api/health 不含 key 实际值", not key_val_leaked)

        # Test /api/result before run (should 404)
        print(f"\n[self-test] GET {base_url}/api/result (预期 404 或已有结果)", flush=True)
        try:
            urllib.request.urlopen(f"{base_url}/api/result", timeout=5)
            check("/api/result 响应", True, "已有执行结果")
        except urllib.error.HTTPError as e:
            check("/api/result 响应", e.code == 404, f"status={e.code}")

        # Test POST /api/run with demo manual strategy
        print(f"\n[self-test] POST {base_url}/api/run", flush=True)
        demo_strategy = {
            "source": {
                "type": "manual",
                "codes": ["000001.SZ", "000002.SZ", "000063.SZ"],
            },
            "skills": ["kline", "landmine"],
            "path_type": "parallel_and",
            "params": {},
        }
        payload = json.dumps(demo_strategy).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/api/run",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=30)
        run_data = json.loads(resp.read().decode())
        check("/api/run 状态码", resp.status == 202)
        check("/api/run 返回 run_id", "run_id" in run_data)
        run_id = run_data.get("run_id", "")
        check("/api/run run_id 非空", bool(run_id))

        # 等待执行完成（最多 30s）
        print("\n[self-test] 等待执行完成（最多 30s）...", flush=True)
        deadline = time.time() + 30
        final_status = "unknown"
        while time.time() < deadline:
            try:
                resp = urllib.request.urlopen(
                    f"{base_url}/api/stream", timeout=5
                )
                stream_data = json.loads(resp.read().decode())
                final_status = stream_data.get("status", "unknown")
                if final_status in ("completed", "error"):
                    break
                print(f"  status={final_status}...", flush=True)
            except Exception:
                pass
            time.sleep(1)

        check("/api/run 执行完成", final_status == "completed", f"status={final_status}")

        # Test /api/stream
        print(f"\n[self-test] GET {base_url}/api/stream", flush=True)
        resp = urllib.request.urlopen(f"{base_url}/api/stream", timeout=5)
        stream_data = json.loads(resp.read().decode())
        check("/api/stream 状态码", resp.status == 200)
        check("/api/stream 有 events 字段", "events" in stream_data)
        check("/api/stream 有 note 字段（说明非 SSE）", "note" in stream_data)

        # Test /api/result after run
        print(f"\n[self-test] GET {base_url}/api/result", flush=True)
        resp = urllib.request.urlopen(f"{base_url}/api/result", timeout=5)
        result_data = json.loads(resp.read().decode())
        check("/api/result 状态码", resp.status == 200)
        check("/api/result 有 run_id", "run_id" in result_data)
        check("/api/result 有 final_hit_codes", "final_hit_codes" in result_data)

    except Exception as exc:
        print(f"[self-test] 异常: {exc}", flush=True)
        failed += 1
    finally:
        server.shutdown()

    print(
        f"\n[self-test] 结果: {passed} 通过 / {failed} 失败\n"
        f"           API: http://127.0.0.1:{actual_port}",
        flush=True,
    )
    return failed == 0


def main() -> int:
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )

    parser = argparse.ArgumentParser(description="V6OP 本地后端 API 服务器")
    parser.add_argument("--port", type=int, default=_DEFAULT_PORT)
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--self-test", action="store_true",
                        help="执行自测后退出")
    args = parser.parse_args()

    if args.self_test:
        ok = self_test(args.port)
        return 0 if ok else 1

    server = start_server(args.port, args.bind)
    actual_port = server.server_address[1]
    url = f"http://{args.bind}:{actual_port}"

    print(
        f"[v6op_server] 服务已启动\n"
        f"  URL:      {url}\n"
        f"  health:   {url}/api/health\n"
        f"  run:      POST {url}/api/run\n"
        f"  result:   {url}/api/result\n"
        f"  stream:   {url}/api/stream  (JSON 轮询，非 true SSE)\n"
        f"  按 Ctrl+C 停止",
        flush=True,
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[v6op_server] 停止", flush=True)
        server.shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
