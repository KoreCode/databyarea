# Cloudflare + GitHub Auto-Deploy and Domain Admin Access

This guide sets up two things:

1. **Automatic retrieval/deploy of GitHub changes** (Cloudflare Pages)
2. **Admin backend access on your domain** with URL variable auth key

---

## 1) Cloudflare Pages: auto-retrieve GitHub updates

1. In Cloudflare Dashboard, go to **Workers & Pages**.
2. Click **Create application** → **Pages** → **Connect to Git**.
3. Connect your GitHub account and select repo: `KoreCode/databyarea`.
4. Build settings:
   - Framework preset: `None`
   - Build command: *(leave empty)*
   - Build output directory: `/`
5. Save and deploy.
6. In project settings:
   - Enable **Production branch** = `main` (or your chosen branch).
   - Keep **Automatic deployments** enabled.

Result: every push to the production branch triggers Cloudflare to pull and publish the latest site automatically.

Recommended: enable this repo's GitHub workflow (`.github/workflows/daily-automation.yml`) so a scheduled run can commit/push fresh site updates daily, which Cloudflare then auto-deploys.

---

## 2) Route domain traffic

In **Custom domains**, attach:
- `databyarea.com`
- `www.databyarea.com` (optional)

Cloudflare will provision SSL certificates automatically.

---

## 3) Admin backend on domain with URL-variable auth

`admin_backend.py` supports:
- Query key auth: `?admin_key=YOUR_SECRET`
- Header auth: `X-Admin-Key: YOUR_SECRET`

Environment variables:
- `ADMIN_ACCESS_KEY` = your secret
- `ADMIN_KEY_PARAM` = query variable name (default: `admin_key`)

Example startup:

```bash
ADMIN_ACCESS_KEY='replace-with-strong-secret' \
ADMIN_KEY_PARAM='admin_key' \
python3 admin_backend.py --host 127.0.0.1 --port 8787
```

Example secure URL:

```text
https://databyarea.com/admin/?admin_key=replace-with-strong-secret
```

---

## 4) Put `/admin` behind reverse proxy (Cloudflare Tunnel / origin proxy)

Recommended mapping:
- `https://databyarea.com/` → static site (Pages)
- `https://databyarea.com/admin/` → admin backend origin (`127.0.0.1:8787`)

If using NGINX on origin:

```nginx
location /admin/ {
  proxy_pass http://127.0.0.1:8787/;
  proxy_set_header Host $host;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

Also add Cloudflare WAF/IP allow rules for `/admin/*` if possible.

---

## 5) Optional hardening

- Use a long random `ADMIN_ACCESS_KEY`.
- Rotate key periodically.
- Restrict `/admin/*` by Cloudflare Access or IP allowlist.
- Keep `/api/health` open only if needed for monitoring.

---

## 6) Daily content automation on host

Daily command already prepared:

```bash
./run_daily.sh
```

Scheduler line (UTC 03:15):

```cron
15 3 * * * cd /workspace/databyarea && ./run_daily.sh >> /workspace/databyarea/_deploy/autorun.log 2>&1
```

If `crontab` is unavailable in your environment, run `./setup_autorun.sh` to print and save this line.
