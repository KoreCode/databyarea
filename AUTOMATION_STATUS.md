# Automation Status

- Daily runner command: `./run_daily.sh`
- Daily target: **1 service + 10 cities**
- Scheduler expression: `15 3 * * *` (UTC)
- Publish behavior: **fail-fast quality gate enabled** (`python3 scripts/site_quality_agents.py` must pass before any commit/push/deploy continuation).

## Current environment status

- `setup_autorun.sh` was executed.
- `crontab` is not available in this environment, so the cron line was written to `_deploy/cron_entry.txt` for manual installation on the host scheduler.

## Gate outputs written each run

- `_deploy/agent_quality_report.json`
- `_deploy/last_daily_run_summary.json` (includes `quality_gate` status block)
- `_deploy/last_daily_run_summary.md` (includes publish gate pass/fail section)

## Manual enable command

Add this exact line to your host scheduler:

```cron
15 3 * * * cd /workspace/databyarea && ./run_daily.sh >> /workspace/databyarea/_deploy/autorun.log 2>&1
```
