# databyarea
DataByArea

## Automation

### Generator mode
- Single canonical generator only: `scripts/build_site.py`
- `one_button_daily.py` fails fast if this generator is missing.

### Daily auto-generation runner
- Run: `python3 one_button_daily.py`
- Optional flags: `--services`, `--cities`, `--no-cities`, `--relink`, `--clean`, `--force`
- After each run, a summary is written to:
  - `_deploy/last_daily_run_summary.json`
  - `_deploy/last_daily_run_summary.md`
- State coverage check runs first via `scripts/ensure_states.py` to keep state-level hubs in place.
- SEO baseline is refreshed each run by rebuilding `sitemap.xml`, `robots.txt`, and generating internal-link-ready state/city pages.
- City publishing is forced inside the one-button pipeline so both daily and manual runs attempt to add up to `--cities` new city pages each run.

### Daily autorun (1 service + 10 cities)
- Command used by runner script: `./run_daily.sh`
  - Runs: `DBA_AUTORUN=1 python3 one_button_daily.py --services 1 --cities 10 --relink --clean`
  - Runs: `python3 one_button_daily.py --services 1 --cities 10 --relink --clean`
- Install cron job: `./setup_autorun.sh`
  - Default schedule is daily at `03:15 UTC`
  - Override schedule: `CRON_EXPR=\"0 2 * * *\" ./setup_autorun.sh`
  - If `crontab` is unavailable, the cron line is written to `_deploy/cron_entry.txt` for manual host setup.

### EIA API integration
- EIA API helper lives at `scripts/eia_client.py`.
- Default key is configured for this repo and can be overridden with env var `EIA_API_KEY`.
- Example usage:
  - `python3 -c "from scripts.eia_client import fetch_series; print(fetch_series('electricity/retail-sales/data'))"`

### Fast API pull/store/display pipeline
- Script: `scripts/eia_pipeline.py`
- Purpose: quickly pull EIA data, cache responses, store normalized points in sqlite, and render an HTML dashboard.
- Safety / API-rule controls:
  - Request pacing via `EIA_MIN_REQUEST_INTERVAL_SECONDS` (default `0.35`)
  - Retry with backoff via `EIA_MAX_RETRIES` (default `3`)
  - Cache TTL via `EIA_CACHE_TTL_SECONDS` (default `21600` seconds)
- Local artifacts:
  - sqlite: `data/api_metrics.db`
  - snapshots: `data/api_snapshots/*.json`
  - dashboard: `site/api-dashboard/index.html`
- Quick start:
  - `python3 scripts/eia_pipeline.py`
  - `python3 scripts/eia_pipeline.py --series electricity/retail-sales/data --length 12`
  - `python3 scripts/eia_pipeline.py --skip-pull` (render from stored data only)

### Multi-agent quality review
- Run all quality agents: `python3 scripts/site_quality_agents.py`
- Run quality agents + regenerate site: `python3 scripts/site_quality_agents.py --generate`
- Report output: `_deploy/agent_quality_report.json`
- Admin backend script key: `agent_quality_review`

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

### Static admin panel (no routing)
- File: `admin/index.html`
- This is a plain static page (no framework/router) that calls the backend APIs directly.
- Open it directly from your site and point `API base URL` to your admin backend origin when needed.
- Optional query params for convenience:
  - `?base=https://admin.example.com`
  - `&key=YOUR_KEY`
  - `&kp=admin_key`

### Monetization feature flags and rollout
- File: `monetization_flags.json` (repo root).
- `scripts/build_site.py` reads this file when rendering pages and controls:
  - Affiliate recommendation module placement (below the primary informational section)
  - Optional lead form placement (near the bottom of the page)
  - Per-page-type and per-geography enablement
  - Sensitive template suppression until quality threshold passes

#### Config shape
- `global`: default switches and shared safety controls
  - `affiliate_enabled`
  - `lead_form_enabled`
  - `quality_threshold_passed`
  - `max_above_fold_units` (set to `1` to keep strict top-of-page cap)
- `page_type`: overrides keyed by inferred template class (`home_services`, `utilities`, `insurance`, `property_taxes`)
- `geography`: overrides keyed by inferred geography (`us`, `by_state`)
- `sensitive_templates`: keyword guardrail and master enable switch

#### Rollout procedure (enable/disable)
1. Start safe:
   - Keep `global.lead_form_enabled=false`
   - Keep `global.quality_threshold_passed=false`
   - Keep `sensitive_templates.enabled=false`
2. Enable affiliate on low-risk templates first:
   - Set `page_type.home_services.affiliate_enabled=true`
   - Keep `insurance` and `property_taxes` disabled
3. Generate a small batch:
   - `python3 scripts/build_site.py --daily-max 5`
4. Measure module performance using HTML markers:
   - Affiliate module marker: `.dba-affiliate-module`
   - Lead module marker: `.dba-lead-form-module`
5. Expand geography gradually:
   - Toggle `geography.by_state` and then `geography.us` as metrics hold
6. Enable lead form only after quality and SEO checks:
   - Turn on `lead_form_enabled` in targeted `page_type`/`geography` scopes
7. Sensitive/YMYL-like templates:
   - Keep disabled until review completes
   - To permit, set both:
     - `global.quality_threshold_passed=true`
     - `sensitive_templates.enabled=true`
8. Fast rollback:
   - Set `global.affiliate_enabled=false` and/or `global.lead_form_enabled=false`
   - Re-run generator to publish templates without those modules

## Ops Files
- `DIRECTORY_TREE.md` — clean repository tree map.
- `AUTOMATION_STATUS.md` — current automation enablement status and scheduler line.
- `CLOUDFLARE_GITHUB_AUTODEPLOY.md` — Cloudflare + GitHub auto-deploy + domain admin routing steps.
- `FULL_AUTOMATION_SINGLE_GENERATOR.md` — full end-to-end setup (GitHub Actions + Cloudflare) with single generator mode.

## Site Version Footer
- A small version badge is injected at the bottom-right of pages via `/assets/version-footer.js`.
- Version metadata lives in `/assets/site-version.json`.
- The version file is updated **only when autorun succeeds** (`DBA_AUTORUN=1`), so manual runs do not advance the public version stamp.
- Footer JavaScript is rewritten on each run to keep deployed pages aligned with the latest footer code.
