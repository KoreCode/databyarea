#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

mkdir -p _deploy
DBA_AUTORUN=1 python one_button_daily.py --services 1 --cities 10 --relink --clean

python scripts/generate_tree_map.py

# Required fail-fast publish gates. If any returns non-zero, stop before commit/push/deploy action.
python scripts/run_production_gates.py --quality-agents
