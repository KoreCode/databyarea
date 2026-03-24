# Full Automation (GitHub + Cloudflare) with Single Generator

This repo is configured to use **one canonical generator only**:

- `scripts/build_site.py`

`one_button_daily.py` now fails fast if that generator is missing.

---

## Step 1 — GitHub repository settings

1. Push this repo to GitHub.
2. In **Settings → Actions → General**, allow workflow runs.
3. In **Settings → Actions → Workflow permissions**, choose:
   - **Read and write permissions** (required so workflow can commit/push updates).

---

## Step 2 — Enable daily automation workflow

Workflow file:
- `.github/workflows/daily-automation.yml`

What it does daily (03:15 UTC):
1. Checks out repo
2. Runs `./run_daily.sh` with `DBA_AUTORUN=1`
3. Regenerates `DIRECTORY_TREE.md`
4. Commits and pushes changes if any

You can also run it anytime via **Actions → Daily Site Automation → Run workflow**.

---

## Step 3 — Connect Cloudflare Pages to GitHub

1. Cloudflare Dashboard → **Workers & Pages**.
2. **Create application** → **Pages** → **Connect to Git**.
3. Select this repo.
4. Build settings:
   - Framework preset: `None`
   - Build command: *(empty)*
   - Build output directory: `/`
5. Set production branch to `main` (or your selected production branch).
6. Keep automatic deployments enabled.

Now every push from the daily GitHub workflow is auto-deployed by Cloudflare.

---

## Step 4 — Domain and SSL

In Cloudflare Pages:
- Add custom domain(s): `databyarea.com`, optionally `www.databyarea.com`.
- SSL is provisioned automatically.

---

## Step 5 — Admin backend routing (optional)

If hosting admin backend separately, proxy:
- `https://databyarea.com/admin/` → origin `127.0.0.1:8787`

Use auth env vars:
- `ADMIN_ACCESS_KEY`
- `ADMIN_KEY_PARAM` (default `admin_key`)

---

## Step 6 — Verify successful end-to-end automation

After first workflow run, confirm:
1. GitHub Actions succeeded.
2. New commit `chore: automated daily site update` exists (when content changed).
3. Cloudflare Pages deployed latest commit.
4. `assets/site-version.json` updated (autorun mode).
5. `sitemap.xml` and content pages refreshed.

---

## Notes

- Manual local runs still work via `python3 one_button_daily.py`.
- Public version stamp only updates in autorun mode (`DBA_AUTORUN=1`).
