#!/usr/bin/env python3
"""Run the shared production gate sequence for local and CI automation."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_STEPS = [
    ("Generate capped service guides", ["scripts/generate_service_guides.py"]),
    ("Build search index", ["scripts/build_search_index.py"]),
    ("Validate data layer", ["scripts/validate_data_layer.py"]),
    ("Check conflict markers", ["scripts/check_conflict_markers.py"]),
    ("Run production readiness checks", ["scripts/production_check.py"]),
]


def run_step(name: str, args: list[str]) -> int:
    cmd = [sys.executable, *args]
    print(f"\n==> {name}", flush=True)
    print("$ " + " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=ROOT, check=False)
    if proc.returncode:
        print(f"Step failed: {name} exited with {proc.returncode}", file=sys.stderr)
    return int(proc.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run shared DataByArea production gates.")
    parser.add_argument("--skip-service-guides", action="store_true", help="Skip static service-guide generation.")
    parser.add_argument("--quality-agents", action="store_true", help="Run scripts/site_quality_agents.py after production checks.")
    args = parser.parse_args()

    steps = DEFAULT_STEPS[:]
    if args.skip_service_guides:
        steps = [step for step in steps if step[0] != "Generate capped service guides"]
    if args.quality_agents:
        steps.append(("Run site quality agents", ["scripts/site_quality_agents.py"]))

    for name, step_args in steps:
        rc = run_step(name, step_args)
        if rc:
            return rc
    print("\nAll production gates passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
