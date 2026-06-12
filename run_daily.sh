#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

mkdir -p _deploy
DBA_AUTORUN=1 python one_button_daily.py --services 1 --cities 10 --relink --clean

# Required fail-fast publish gates. If any returns non-zero, stop before commit/push/deploy action.
python scripts/build_search_index.py
python scripts/validate_data_layer.py
python scripts/check_conflict_markers.py
python scripts/site_quality_agents.py
python scripts/production_check.py
