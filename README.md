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
  - Runs: `DBA_AUTORUN=1 python3 one_button_daily.py --services 1 --cities 10 --relink --clean`
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
  - Optional URL/header auth key via env vars:
    - `ADMIN_ACCESS_KEY` (secret value)
    - `ADMIN_KEY_PARAM` (query variable name, default `admin_key`)

### Admin access on your domain
- Example local URL with key: `http://127.0.0.1:8787/?admin_key=YOUR_KEY`
- Example production URL pattern behind proxy/domain:
  - `https://databyarea.com/admin/?admin_key=YOUR_KEY`
- Full guide: `CLOUDFLARE_GITHUB_AUTODEPLOY.md`

## Ops Files
- `DIRECTORY_TREE.md` — clean repository tree map.
- `AUTOMATION_STATUS.md` — current automation enablement status and scheduler line.
- `CLOUDFLARE_GITHUB_AUTODEPLOY.md` — Cloudflare + GitHub auto-deploy + domain admin routing steps.

## Site Version Footer
- A small version badge is injected at the bottom-right of pages via `/assets/version-footer.js`.
- Version metadata lives in `/assets/site-version.json`.
- The version file is updated **only when autorun succeeds** (`DBA_AUTORUN=1`), so manual runs do not advance the public version stamp.
