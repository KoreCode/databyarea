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
        "safe_args": ["--cities", "--services", "--no-cities", "--relink", "--clean", "--force"],
        "value_args": ["--cities", "--services"],
        "examples": [
            ["--cities", "10"],
            ["--services", "1", "--cities", "10"],
            ["--no-cities", "--relink", "--clean"],
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
    "agent_quality_review": {
        "path": "scripts/site_quality_agents.py",
        "description": "Run multi-agent quality checks and optional site generation.",
        "safe_args": ["--generate"],
        "examples": [[], ["--generate"]],
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
        examples = " • ".join(" ".join(e) if e else "(no args)" for e in spec["examples"])
        safe_args = " ".join(spec["safe_args"]) or "(none)"
        cards.append(
            f"""
            <button class="command-card" onclick="runScript('{key}')">
              <div class="command-head">
                <span class="status-dot"></span>
                <span class="command-name">{key}</span>
                <span class="chip">Run</span>
              </div>
              <p class="command-desc">{spec['description']}</p>
              <div class="command-meta"><strong>Script:</strong> <code>{spec['path']}</code></div>
              <div class="command-meta"><strong>Allowed args:</strong> <code>{safe_args}</code></div>
              <div class="command-meta"><strong>Examples:</strong> <code>{examples}</code></div>
            </button>
            """
        )

    return f"""<!doctype html>
<html>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width,initial-scale=1'>
  <title>DataByArea Admin Backend</title>
  <style>
    :root {{
      --bg:#050505;
      --panel:#0a0a0a;
      --border:#1e293b80;
      --text:#e2e8f0;
      --muted:#64748b;
      --accent:#f59e0b;
      --success:#34d399;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      padding: 24px;
    }}
    .shell {{ max-width: 1280px; margin: 0 auto; }}
    .topbar {{
      display:flex; justify-content: space-between; align-items:flex-end; gap:14px;
      border-bottom:1px solid var(--border); padding-bottom:16px; margin-bottom:20px;
      flex-wrap:wrap;
    }}
    h1 {{ margin:0; text-transform:uppercase; letter-spacing:-0.02em; font-size:30px; color:#fff; }}
    .version {{ color:var(--accent); font-size:11px; font-style:italic; margin-left:6px; }}
    .subtitle {{ margin-top:6px; font-size:10px; text-transform:uppercase; letter-spacing:0.2em; color:var(--muted); font-weight:700; }}
    .uptime {{
      border:1px solid var(--border); background:#0f172a70; border-radius:10px;
      padding:10px 14px; text-align:right;
    }}
    .uptime-label {{ font-size:9px; text-transform:uppercase; color:var(--muted); font-weight:700; }}
    .uptime-val {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size:24px; color:var(--success); line-height:1.1; }}
    .stats {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(220px,1fr)); gap:12px; margin-bottom:20px; }}
    .stat {{
      background:var(--panel); border:1px solid var(--border); border-radius:12px; padding:14px;
    }}
    .stat-label {{ font-size:10px; text-transform:uppercase; color:var(--muted); font-weight:700; }}
    .stat-value {{ color:#fff; font-size:26px; font-weight:900; margin-top:4px; }}
    .stat-sub {{ font-size:10px; color:#475569; margin-top:2px; }}
    .grid {{ display:grid; grid-template-columns:2fr 1fr; gap:18px; }}
    .panel {{ background:var(--panel); border:1px solid var(--border); border-radius:12px; overflow:hidden; }}
    .panel-head {{
      padding:14px 16px; border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center; gap:8px;
      font-size:12px; text-transform:uppercase; letter-spacing:.08em; font-weight:700;
    }}
    .small {{ font-size:10px; color:var(--muted); }}
    table {{ width:100%; border-collapse:collapse; }}
    th, td {{ padding:12px; border-bottom:1px solid #1e293b50; text-align:left; }}
    th {{ font-size:10px; text-transform:uppercase; color:var(--muted); }}
    td {{ font-size:13px; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
    .status {{ text-align:right; }}
    .badge {{
      display:inline-block; font-size:9px; border:1px solid #34d39950; color:var(--success);
      background:#34d39915; padding:3px 6px; border-radius:999px; text-transform:uppercase; font-weight:700;
    }}
    .commands {{ padding:10px; display:grid; gap:10px; }}
    .command-card {{
      width:100%; border:1px solid var(--border); background:#0f172a40; color:inherit; text-align:left;
      border-radius:10px; padding:12px; cursor:pointer;
    }}
    .command-card:hover {{ border-color:#334155; }}
    .command-head {{ display:flex; align-items:center; gap:8px; margin-bottom:8px; }}
    .status-dot {{ width:8px; height:8px; border-radius:99px; background:var(--success); }}
    .command-name {{ font-size:12px; text-transform:uppercase; font-weight:800; letter-spacing:.08em; }}
    .chip {{
      margin-left:auto; font-size:9px; text-transform:uppercase; padding:2px 8px; border-radius:999px;
      border:1px solid #f59e0b40; color:var(--accent); background:#f59e0b12; font-weight:700;
    }}
    .command-desc {{ margin:0 0 6px 0; color:#94a3b8; font-size:12px; }}
    .command-meta {{ color:#94a3b8; font-size:11px; margin-top:2px; }}
    code {{ background:#1e293b80; color:#cbd5e1; padding:2px 6px; border-radius:4px; }}
    .controls {{ padding:12px; border-top:1px solid var(--border); display:grid; gap:8px; }}
    .input {{
      width:100%; border:1px solid #334155; background:#020617; color:#e2e8f0;
      border-radius:8px; padding:8px 10px;
    }}
    .actions {{ display:flex; gap:8px; flex-wrap:wrap; }}
    .btn {{
      cursor:pointer; padding:8px 12px; border-radius:8px; border:1px solid #334155;
      background:#0f172a; color:#e2e8f0; font-size:12px; font-weight:700;
    }}
    .btn:hover {{ border-color:#475569; }}
    textarea {{
      width:100%; min-height:240px; border-radius:10px; border:1px solid var(--border); background:#020617;
      color:#cbd5e1; margin-top:14px; padding:12px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size:12px;
    }}
    @media (max-width: 1000px) {{
      .grid {{ grid-template-columns:1fr; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <header class="topbar">
      <div>
        <h1>DataByArea <span class="version">Mogul Command v1.0</span></h1>
        <p class="subtitle">National Data Infrastructure // Internal System Reboot Active</p>
      </div>
      <div class="uptime">
        <div class="uptime-label">Sovereign Uptime</div>
        <div id="uptime" class="uptime-val">DAY 01</div>
      </div>
    </header>

    <section class="stats">
      <article class="stat"><div class="stat-label">System Saturation</div><div class="stat-value">0.00 ng/mL</div><div class="stat-sub">Reset from legacy load</div></article>
      <article class="stat"><div class="stat-label">Survival Probability</div><div class="stat-value">0.1%</div><div class="stat-sub">Outlier status confirmed</div></article>
      <article class="stat"><div class="stat-label">Domain Fleet</div><div id="domain-count" class="stat-value">0 Active</div><div class="stat-sub">Connected admin endpoints</div></article>
      <article class="stat"><div class="stat-label">Whitelisted Scripts</div><div id="script-count" class="stat-value">0</div><div class="stat-sub">Run-safe catalog entries</div></article>
    </section>

    <div class="grid">
      <section class="panel">
        <div class="panel-head">
          <span>Automation Pipeline Controls</span>
          <span class="small">Live Local Feed</span>
        </div>
        <div class="commands">
          {''.join(cards)}
        </div>
        <div class="controls">
          <label for="args" class="small">Optional args for selected script (space-separated):</label>
          <input id="args" class="input" placeholder="--services 1 --cities 10 --relink --clean" />
          <div class="actions">
            <button class="btn" onclick="loadOverview()">Refresh Overview</button>
            <button class="btn" onclick="runScript('one_button_daily')">Run Daily Pipeline</button>
          </div>
        </div>
      </section>

      <aside class="panel">
        <div class="panel-head">
          <span>Mission Status</span>
          <span class="small">Latest Signals</span>
        </div>
        <table>
          <thead>
            <tr><th>Module</th><th>State</th><th class="status">Status</th></tr>
          </thead>
          <tbody class="mono">
            <tr><td>Config API</td><td>/api/config</td><td class="status"><span class="badge">Synced</span></td></tr>
            <tr><td>History API</td><td>/api/history</td><td class="status"><span class="badge">Synced</span></td></tr>
            <tr><td>Summary API</td><td>/api/last-summary</td><td class="status"><span class="badge">Synced</span></td></tr>
          </tbody>
        </table>
      </aside>
    </div>

    <textarea id='out' readonly></textarea>
  </div>

<script>
const qp = new URLSearchParams(window.location.search);
const keyParam = '{ADMIN_KEY_PARAM}';
const keyValue = qp.get(keyParam);
const suffix = keyValue ? `?${{keyParam}}=${{encodeURIComponent(keyValue)}}` : '';

async function loadOverview() {{
  const [cfg, hist, summary] = await Promise.all([
    fetch('/api/config' + suffix).then(r=>r.json()),
    fetch('/api/history' + suffix).then(r=>r.json()),
    fetch('/api/last-summary' + suffix).then(r=>r.json()),
  ]);
  const scriptCount = Object.keys(cfg.scripts || {{}}).length;
  document.getElementById('script-count').textContent = String(scriptCount);
  document.getElementById('domain-count').textContent = scriptCount + ' Active';

  const now = new Date();
  const day = String(now.getUTCDate()).padStart(2, '0');
  document.getElementById('uptime').textContent = `DAY ${{day}}`;

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
