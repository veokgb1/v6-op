#!/usr/bin/env python3
"""Starts v6op_server, runs browser_smoke, then kills the server."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).parent.parent.resolve()
PORT = 7751


def wait_for_server(base_url: str, timeout: int = 15) -> bool:
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


def main():
    venv_python = _ROOT / ".venv" / "Scripts" / "python.exe"
    server_script = _ROOT / "scripts" / "v6op_server.py"

    proc = subprocess.Popen(
        [str(venv_python), str(server_script), "--port", str(PORT)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        cwd=str(_ROOT),
    )
    print(f"Server PID={proc.pid}  port={PORT}", flush=True)

    base_url = f"http://127.0.0.1:{PORT}"
    if not wait_for_server(base_url, timeout=15):
        print("ERROR: server did not start within 15s", flush=True)
        proc.terminate()
        sys.exit(1)

    print("Server ready. Running smoke...", flush=True)
    sys.path.insert(0, str(_ROOT / "scripts"))
    from browser_smoke import run_smoke

    result = run_smoke(base_url)
    proc.terminate()

    out_path = _ROOT / "output" / "verification" / "v6op023_browser_smoke.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\nJSON → {out_path}", flush=True)
    sys.exit(0 if result.get("smoke_passed") else 1)


if __name__ == "__main__":
    main()
