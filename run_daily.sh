#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

mkdir -p _deploy
DBA_AUTORUN=1 python3 one_button_daily.py --services 1 --cities 10 --relink --clean
python3 one_button_daily.py --services 1 --cities 10 --relink --clean
