# Technical Quality Baseline

This baseline adds practical operations controls for the current DataByArea stack.

## 1) Error Tracking + Logs

- `admin_backend.py` now writes request and runtime logs to:
  - `_deploy/logs/admin_backend.log`
- Script run responses still include the last section of stdout/stderr for quick triage.
- Uptime probe logs append JSON lines to:
  - `_deploy/logs/uptime_checks.log`

## 2) Uptime Monitoring

- Health endpoint: `GET /api/health`
- Response now includes:
  - `ok`
  - `utc`
  - `uptime_seconds`
  - `started_at_utc`
- Probe script:
  - `python3 scripts/uptime_monitor.py`

### Suggested cron (every 5 minutes)

```cron
*/5 * * * * cd /workspace/databyarea && /usr/bin/python3 scripts/uptime_monitor.py >> _deploy/logs/uptime_monitor_cron.log 2>&1
```

## 3) Backup Schedule

- Snapshot script:
  - `python3 scripts/backup_snapshot.py`
- Optional full site snapshot:
  - `python3 scripts/backup_snapshot.py --include-site`
- Retention pruning:
  - `python3 scripts/backup_snapshot.py --retention-days 21`

### Suggested cron (daily 02:30 UTC)

```cron
30 2 * * * cd /workspace/databyarea && /usr/bin/python3 scripts/backup_snapshot.py --retention-days 21 >> _deploy/logs/backup_cron.log 2>&1
```

## 4) Security Hardening Baseline

### Authentication

- Optional shared secret auth already supported and now hardened with constant-time comparison.
- Configure:
  - `ADMIN_ACCESS_KEY`
  - `ADMIN_KEY_PARAM` (default: `admin_key`)

### Rate Limits

Per-IP, in-memory rate limiting is enabled for `GET` and `POST` requests.

- `ADMIN_RATE_LIMIT_REQUESTS` (default `60`)
- `ADMIN_RATE_LIMIT_WINDOW_SECONDS` (default `60`)
- Exceeded requests return `429` with `Retry-After` header.

### Request size limits

- `ADMIN_MAX_POST_BYTES` (default `65536`)
- Oversized payloads return `413`.

### Security headers

Responses include:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- `Cache-Control: no-store`
- `Content-Security-Policy` baseline for local admin app/API calls

## 5) Operational checklist

1. Set `ADMIN_ACCESS_KEY` in production.
2. Run the backend behind TLS (Cloudflare/proxy).
3. Enable both cron jobs (uptime + backup).
4. Review `_deploy/logs/admin_backend.log` and `_deploy/logs/uptime_checks.log` daily.
5. Test backup restores monthly by extracting a snapshot into a temp folder.
