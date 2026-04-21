#!/usr/bin/env python3
"""Simple uptime probe for admin backend health endpoint."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib import request

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = REPO_ROOT / "_deploy" / "logs" / "uptime_checks.log"


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe admin backend health endpoint and append status log.")
    parser.add_argument("--url", default="http://127.0.0.1:8787/api/health", help="Health endpoint URL")
    parser.add_argument("--timeout", type=float, default=10.0, help="Request timeout in seconds")
    args = parser.parse_args()

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    row = {"checked_at_utc": now, "url": args.url, "ok": False}
    try:
        with request.urlopen(args.url, timeout=args.timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            row["http_status"] = resp.status
            row["ok"] = bool(payload.get("ok")) and resp.status == 200
            row["uptime_seconds"] = payload.get("uptime_seconds")
            row["started_at_utc"] = payload.get("started_at_utc")
    except Exception as exc:
        row["error"] = str(exc)

    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(json.dumps(row, ensure_ascii=False))
    raise SystemExit(0 if row["ok"] else 1)


if __name__ == "__main__":
    main()
