#!/usr/bin/env python3
"""Lightweight admin backend for DataByArea automation.

Provides:
- Script catalog with descriptions and run options
- Runner settings/status
- Recent run history and latest daily summary
- API endpoint to trigger approved scripts

Run:
  python3 admin_backend.py
  python3 admin_backend.py --host 127.0.0.1 --port 8787
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
import os

REPO_ROOT = Path(__file__).resolve().parent
DAILY_LOG = REPO_ROOT / ".daily_runs.json"
CITY_LOG = REPO_ROOT / ".daily_city_runs.json"
SUMMARY_JSON = REPO_ROOT / "_deploy" / "last_daily_run_summary.json"
RUN_TIMEOUT_SECONDS = 1800
RUN_LOCK = threading.Lock()
ADMIN_ACCESS_KEY = os.getenv("ADMIN_ACCESS_KEY", "").strip()
ADMIN_KEY_PARAM = os.getenv("ADMIN_KEY_PARAM", "admin_key").strip() or "admin_key"

SCRIPT_CATALOG: dict[str, dict[str, Any]] = {
    "one_button_daily": {
        "path": "one_button_daily.py",
        "description": "Main daily pipeline: city publish + build + sitemap + zip + summary.",
        "safe_args": ["--cities", "--no-cities", "--relink", "--clean", "--force"],
        "value_args": ["--cities"],
        "examples": [
            ["--cities", "10"],
            ["--cities", "20", "--relink", "--clean"],
            ["--no-cities", "--force"],
        ],
    },
    "publish_popular_cities": {
        "path": "publish_popular_cities_daily.py",
        "description": "Generate city pages from data/popular_cities.csv.",
        "safe_args": ["--max", "--inject", "--force", "--overwrite"],
        "value_args": ["--max"],
        "examples": [["--max", "10"], ["--max", "25", "--inject"]],
    },
    "build_site": {
        "path": "scripts/build_site.py",
        "description": "Generate service/state pages and update manifest.",
        "safe_args": [],
        "examples": [[]],
    },
    "relink": {
        "path": "relink_existing_pages.py",
        "description": "Rebuild internal links across existing pages.",
        "safe_args": [],
        "examples": [[]],
    },
    "clean_site": {
        "path": "auto_clean_site.py",
        "description": "Cleanup helper for generated site files.",
        "safe_args": [],
        "examples": [[]],
    },
    "ensure_indexes": {
        "path": "index_everywhere.py",
        "description": "Ensures every directory has an index.html file.",
        "safe_args": [],
        "examples": [[]],
    },
    "make_sitemap": {
        "path": "makesitemap.py",
        "description": "Regenerates sitemap.xml.",
        "safe_args": [],
        "examples": [[]],
    },
}

SETTINGS = {
    "repo_root": str(REPO_ROOT),
    "logs": {
        "daily_runs": str(DAILY_LOG),
        "daily_city_runs": str(CITY_LOG),
        "latest_summary": str(SUMMARY_JSON),
    },
    "python_executable": sys.executable,
    "timezone": "UTC",
    "run_timeout_seconds": RUN_TIMEOUT_SECONDS,
    "admin_key_param": ADMIN_KEY_PARAM,
    "admin_access_key_configured": bool(ADMIN_ACCESS_KEY),
}


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def validate_args(script_key: str, args: list[str]) -> tuple[bool, list[str], str]:
    spec = SCRIPT_CATALOG[script_key]
    allowed = set(spec.get("safe_args", []))
    value_args = set(spec.get("value_args", []))

    out: list[str] = []
    i = 0
    while i < len(args):
        token = args[i]
        if token not in allowed:
            return False, [], f"Argument not allowed for {script_key}: {token}"
        out.append(token)
        if token in value_args:
            if i + 1 >= len(args):
                return False, [], f"Missing value for argument: {token}"
            value = args[i + 1]
            if value.startswith("--"):
                return False, [], f"Expected value after {token}, got option: {value}"
            out.append(value)
            i += 2
            continue
        i += 1

    return True, out, ""


def run_script(script_key: str, args: list[str]) -> dict[str, Any]:
    if script_key not in SCRIPT_CATALOG:
        return {"ok": False, "error": f"Unknown script key: {script_key}"}

    spec = SCRIPT_CATALOG[script_key]
    script_path = REPO_ROOT / spec["path"]
    if not script_path.exists():
        return {"ok": False, "error": f"Script not found: {script_path}"}
    ok, checked_args, err = validate_args(script_key, args)
    if not ok:
        return {"ok": False, "error": err}

    if not RUN_LOCK.acquire(blocking=False):
        return {"ok": False, "error": "Another script is currently running. Try again shortly."}

    started = time.perf_counter()
    try:
        cmd = [sys.executable, str(script_path)] + checked_args
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
            timeout=RUN_TIMEOUT_SECONDS,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "cmd": cmd,
            "stdout": proc.stdout[-12000:],
            "stderr": proc.stderr[-12000:],
            "ran_at_utc": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": round(time.perf_counter() - started, 3),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "error": f"Script timed out after {RUN_TIMEOUT_SECONDS} seconds",
            "cmd": [sys.executable, str(script_path)] + checked_args,
            "stdout": (exc.stdout or "")[-12000:],
            "stderr": (exc.stderr or "")[-12000:],
            "ran_at_utc": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": round(time.perf_counter() - started, 3),
        }
    finally:
        RUN_LOCK.release()


def dashboard_html() -> str:
    cards = []
    for key, spec in SCRIPT_CATALOG.items():
        examples = "<br>".join(" ".join(e) if e else "(no args)" for e in spec["examples"])
        cards.append(
            f"""
            <div class='card'>
              <h3>{key}</h3>
              <p>{spec['description']}</p>
              <p><b>Script:</b> <code>{spec['path']}</code></p>
              <p><b>Allowed args:</b> <code>{' '.join(spec['safe_args']) or '(none)'}</code></p>
              <p><b>Examples:</b><br><code>{examples}</code></p>
              <button onclick="runScript('{key}')">Run</button>
            </div>
            """
        )

    return f"""<!doctype html>
<html>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width,initial-scale=1'>
  <title>DataByArea Admin Backend</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #f8fafc; }}
    h1 {{ margin-bottom: 6px; }}
    .muted {{ color: #475569; }}
    .grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px; margin-top: 18px; }}
    .card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px; }}
    code {{ background: #eef2ff; padding: 2px 5px; border-radius: 4px; }}
    textarea {{ width:100%; min-height: 220px; margin-top: 12px; }}
    button {{ cursor: pointer; padding: 8px 12px; }}
    .top {{ display:grid; gap:8px; max-width: 800px; }}
    input {{ padding:7px; }}
  </style>
</head>
<body>
  <h1>DataByArea Admin Backend</h1>
  <p class='muted'>Review scripts, settings, and run tasks from one place.</p>

  <div class='top'>
    <label>Optional args for selected script (space-separated):</label>
    <input id='args' placeholder='--cities 15 --relink'>
    <button onclick='loadOverview()'>Refresh Overview</button>
  </div>

  <div class='grid'>
    {''.join(cards)}
  </div>

  <h2>Latest Output</h2>
  <textarea id='out' readonly></textarea>

<script>
const qp = new URLSearchParams(window.location.search);
const keyParam = '{ADMIN_KEY_PARAM}';
const keyValue = qp.get(keyParam);
const suffix = keyValue ? `?${keyParam}=${encodeURIComponent(keyValue)}` : '';

async function loadOverview() {{
  const [cfg, hist, summary] = await Promise.all([
    fetch('/api/config' + suffix).then(r=>r.json()),
    fetch('/api/history' + suffix).then(r=>r.json()),
    fetch('/api/last-summary' + suffix).then(r=>r.json()),
  ]);
  document.getElementById('out').value = JSON.stringify({{config: cfg, history: hist, last_summary: summary}}, null, 2);
}}

async function runScript(scriptKey) {{
  const argLine = document.getElementById('args').value.trim();
  const args = argLine ? argLine.split(/\s+/) : [];
  const res = await fetch('/api/run' + suffix, {{
    method: 'POST',
    headers: {{'Content-Type':'application/json'}},
    body: JSON.stringify({{script: scriptKey, args}})
  }});
  const data = await res.json();
  document.getElementById('out').value = JSON.stringify(data, null, 2);
}}

loadOverview();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _path_parts(self):
        parsed = urlparse(self.path)
        return parsed.path, parse_qs(parsed.query)

    def _extract_admin_key(self) -> str:
        _, query = self._path_parts()
        qv = (query.get(ADMIN_KEY_PARAM) or [""])[0]
        hv = self.headers.get("X-Admin-Key", "")
        return (hv or qv or "").strip()

    def _authorized(self) -> bool:
        # If no ADMIN_ACCESS_KEY is configured, keep current behavior open.
        if not ADMIN_ACCESS_KEY:
            return True
        return self._extract_admin_key() == ADMIN_ACCESS_KEY

    def _send_json(self, payload: Any, status: int = 200) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_html(self, html: str) -> None:
        raw = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path, _ = self._path_parts()
        if path != "/api/health" and not self._authorized():
            self._send_json({"ok": False, "error": f"Unauthorized. Supply {ADMIN_KEY_PARAM}=... in URL or X-Admin-Key header."}, status=401)
            return

        if path == "/":
            self._send_html(dashboard_html())
            return
        if path == "/api/config":
            payload = {
                "scripts": SCRIPT_CATALOG,
                "settings": SETTINGS,
            }
            self._send_json(payload)
            return
        if path == "/api/health":
            self._send_json({"ok": True, "utc": datetime.now(timezone.utc).isoformat()})
            return
        if path == "/api/history":
            self._send_json(
                {
                    "daily_runs": load_json(DAILY_LOG, {}),
                    "daily_city_runs": load_json(CITY_LOG, {}),
                }
            )
            return
        if path == "/api/last-summary":
            self._send_json(load_json(SUMMARY_JSON, {"note": "No summary generated yet."}))
            return
        self._send_json({"error": "Not found"}, status=404)

    def do_POST(self):
        path, _ = self._path_parts()
        if not self._authorized():
            self._send_json({"ok": False, "error": f"Unauthorized. Supply {ADMIN_KEY_PARAM}=... in URL or X-Admin-Key header."}, status=401)
            return

        if path != "/api/run":
            self._send_json({"error": "Not found"}, status=404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            self._send_json({"ok": False, "error": "Invalid JSON body"}, status=400)
            return

        script_key = str(payload.get("script", "")).strip()
        args = payload.get("args", [])
        if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            self._send_json({"ok": False, "error": "args must be a list of strings"}, status=400)
            return

        result = run_script(script_key, args)
        self._send_json(result, status=200 if result.get("ok") else 400)


def main() -> None:
    parser = argparse.ArgumentParser(description="DataByArea admin backend for script operations.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Admin backend running at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
