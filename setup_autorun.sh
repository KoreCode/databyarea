#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
RUN_CMD="cd $ROOT_DIR && ./run_daily.sh >> $ROOT_DIR/_deploy/autorun.log 2>&1"
CRON_EXPR="${CRON_EXPR:-15 3 * * *}"
CRON_LINE="$CRON_EXPR $RUN_CMD"

if ! command -v crontab >/dev/null 2>&1; then
  mkdir -p "$ROOT_DIR/_deploy"
  printf '%s\n' "$CRON_LINE" > "$ROOT_DIR/_deploy/cron_entry.txt"
  echo "crontab command not found on this machine."
  echo "Saved scheduler line to: $ROOT_DIR/_deploy/cron_entry.txt"
  echo "Add this line to your scheduler manually:"
  cat "$ROOT_DIR/_deploy/cron_entry.txt"
  exit 0
fi
EXISTING="$(crontab -l 2>/dev/null || true)"
if printf '%s\n' "$EXISTING" | grep -Fq "$RUN_CMD"; then
  echo "Autorun entry already exists."
  exit 0
fi

{
  printf '%s\n' "$EXISTING"
  printf '%s\n' "$CRON_LINE"
} | crontab -

echo "Installed cron entry:"
echo "$CRON_LINE"
