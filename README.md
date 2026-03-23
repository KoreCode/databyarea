# databyarea
DataByArea

## Automation

### Daily auto-generation runner
- Run: `python3 one_button_daily.py`
- Optional flags: `--services`, `--cities`, `--no-cities`, `--relink`, `--clean`, `--force`
- After each run, a summary is written to:
  - `_deploy/last_daily_run_summary.json`
  - `_deploy/last_daily_run_summary.md`
- State coverage check runs first via `scripts/ensure_states.py` to keep state-level hubs in place.
- SEO baseline is refreshed each run by rebuilding `sitemap.xml`, `robots.txt`, and generating internal-link-ready state/city pages.

### Daily autorun (1 service + 10 cities)
- Command used by runner script: `./run_daily.sh`
  - Runs: `python3 one_button_daily.py --services 1 --cities 10 --relink --clean`
- Install cron job: `./setup_autorun.sh`
  - Default schedule is daily at `03:15 UTC`
  - Override schedule: `CRON_EXPR=\"0 2 * * *\" ./setup_autorun.sh`
  - If `crontab` is unavailable, the cron line is written to `_deploy/cron_entry.txt` for manual host setup.

### Admin backend
- Run: `python3 admin_backend.py --host 127.0.0.1 --port 8787`
- Open: `http://127.0.0.1:8787`
- Includes:
  - Script catalog with descriptions and allowed options
  - Current settings and log file paths
  - Run history and latest daily summary
  - API to execute allowed scripts (`POST /api/run`)
  - Health endpoint: `GET /api/health`
- Safety behavior:
  - Only whitelisted options are accepted per script
  - Only one script can run at a time via the admin backend
  - Script execution has a timeout guard

## Ops Files
- `DIRECTORY_TREE.md` — clean repository tree map.
- `AUTOMATION_STATUS.md` — current automation enablement status and scheduler line.
