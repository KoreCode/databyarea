# DUPLICATION REMEDIATION PROMPTS

## Context
The KoreCode/databyarea repository has multiple daily automation tasks that duplicate work, wasting ~50% of daily CI/CD time. Fix #1 (remove duplicate pipeline) has already been applied. This document provides prompts for Fixes #2-4.

---

## FIX #2: Consolidate Sitemap Rebuild (MEDIUM PRIORITY)

**Problem:** 
- Sitemap is rebuilt twice per daily automation:
  1. In `scripts/build_site.py` (lines 799-872 in `update_sitemap()`)
  2. In `one_button_daily.py` (lines 265-338 in `rebuild_sitemap_from_filesystem()`)
- Both functions scan all index.html files and create identical sitemaps
- The second rebuild in `one_button_daily.py` is now REDUNDANT since `build_site.py` already rebuilt it

**Solution:** Remove the redundant sitemap rebuild from `one_button_daily.py`

### PROMPT FOR COPILOT/CLAUDE:

```
You are helping optimize the KoreCode/databyarea repository. 

TASK: Remove duplicate sitemap rebuild from one_button_daily.py

BACKGROUND:
- scripts/build_site.py already calls update_sitemap() which rebuilds sitemap.xml from filesystem
- one_button_daily.py then calls rebuild_sitemap_from_filesystem() which does the SAME THING
- This causes sitemaps/* XML files and sitemap.xml to be written twice per daily run

GOAL: 
- Remove the redundant sitemap rebuild from one_button_daily.py (lines 265-338)
- Remove the calls to rebuild_sitemap_from_filesystem() (lines 449 and in variable assignment)
- Remove the update_robots() call from one_button_daily.py (lines 340-346, 450)
- Keep these operations in scripts/build_site.py as the source of truth
- Update comments in one_button_daily.py to reflect this change
- Update the final output summary to still report sitemap counts (can be queried from manifest instead)

FILE TO MODIFY: one_button_daily.py

SPECIFIC CHANGES:
1. Delete function: rebuild_sitemap_from_filesystem() (lines 265-338)
2. Delete function: update_robots() (lines 340-346)
3. Delete line 449: sitemap_counts = rebuild_sitemap_from_filesystem()
4. Delete line 450: update_robots()
5. In main() function, remove the variables that depend on sitemap_counts
6. Update header comment (lines 1-27) to remove references to "Rebuilds sitemap.xml" and "Updates robots.txt"
7. Update write_run_summary() to handle missing sitemap_counts gracefully
8. Add comment: "# Sitemap and robots.txt are now built by scripts/build_site.py"

VALIDATION:
- Ensure one_button_daily.py still runs without errors
- Ensure it still produces the deploy zip correctly
- Ensure it still tracks/reports changes to the site
- Test that daily automation still works end-to-end

EXPECTED SAVINGS: ~1-2 minutes per daily run
```

---

## FIX #3: Consolidate robots.txt Updates (LOW PRIORITY)

**Problem:**
- `robots.txt` is written 2-4 times per daily run:
  1. In `scripts/build_site.py` (line 874-880 in `update_robots()`)
  2. In `one_button_daily.py` (line 340-346 in `update_robots()`)
- Both functions write identical content

**Solution:** Same as Fix #2 - keep in `build_site.py` only

This is addressed by Fix #2 prompt above.

---

## FIX #4: Clarify ensure_states.py Ownership & Frequency (LOW PRIORITY)

**Problem:**
- `scripts/ensure_states.py` runs daily (optional in `one_button_daily.py` line 399-404)
- It generates/updates 4 section category pages + 200 state pages (4 sections × 50 states)
- This is expensive and likely doesn't need to run daily since state pages are unlikely to change
- `scripts/build_site.py` only ensures system pages (privacy-policy, terms), not state pages

**Solution:** Make `ensure_states.py` a separate weekly scheduled task instead of daily

### PROMPT FOR COPILOT/CLAUDE:

```
You are helping optimize the KoreCode/databyarea repository.

TASK: Refactor ensure_states.py to run weekly instead of daily

BACKGROUND:
- one_button_daily.py calls scripts/ensure_states.py every day (lines 399-404)
- ensure_states.py generates 4 category pages + 200 state pages
- These pages rarely change day-to-day (only when new content is added)
- Running this daily wastes ~1-2 minutes each run
- Total waste: ~7-14 minutes per week

GOAL:
1. Remove the ensure_states.py call from one_button_daily.py (lines 399-404)
2. Create a new GitHub Actions workflow: .github/workflows/weekly-ensure-states.yml
3. This workflow should run weekly (suggest: Sundays at 10:00 UTC)
4. The workflow should only call: python3 scripts/ensure_states.py (no other daily tasks)

FILE CHANGES NEEDED:
1. Modify: one_button_daily.py
   - Delete lines 399-404 (the ensure_states.py block)
   - Delete the state_ensurer variable from initial setup (line 52)
   - Delete state_rc tracking from main() function (line 396)
   - Delete state_rc from summary dict (line 489)
   - Delete state_rc from history log (line 506)
   - Update header comment to remove reference to state page check

2. Create: .github/workflows/weekly-ensure-states.yml
   - Schedule: cron '0 10 * * 0' (Sunday 10:00 UTC)
   - Steps:
     a) Checkout repo (v4)
     b) Setup Python 3.11
     c) Run: python3 scripts/ensure_states.py
     d) Commit & push changes if any (like other workflows)
   - Permissions: contents: write

VALIDATION:
- Ensure one_button_daily.py still works without ensure_states.py
- Ensure new workflow syntax is valid
- Verify weekly workflow would be triggered as expected

EXPECTED SAVINGS: ~1-2 minutes per daily run (7-14 minutes per week)
```

---

## SUMMARY OF ALL FIXES

| Fix # | Issue | Files | Savings | Priority |
|-------|-------|-------|---------|----------|
| #1 ✅ | Duplicate pipeline execution | `run_daily.sh` | 4-6 min/day | HIGH |
| #2 | Duplicate sitemap rebuild | `one_button_daily.py` | 1-2 min/day | MEDIUM |
| #3 | Duplicate robots.txt write | (same as #2) | <1 min/day | LOW |
| #4 | Daily state page regeneration | `one_button_daily.py` + new workflow | 1-2 min/day | LOW |

**Total Expected Savings After All Fixes:** 
- **Daily:** 6-11 minutes (from 10-14 min → 4-8 min)
- **Weekly:** 42-77 minutes saved

---

## TESTING RECOMMENDATIONS

After implementing each fix:

1. Run locally: `./run_daily.sh` and verify output
2. Verify all artifacts are created:
   - `_deploy/last_daily_run_summary.json`
   - `_deploy/last_daily_run_summary.md`
   - `_deploy/databyarea-deploy-YYYY-MM-DD.zip`
   - `sitemap.xml` and `sitemaps/*.xml`
   - `robots.txt`
   - `published_manifest.json`
3. Verify workflow runs successfully in GitHub Actions
4. Check that all summary counts are accurate
5. Confirm no pages or data are missing in deploy artifacts

