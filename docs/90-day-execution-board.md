# 90-Day Execution Board

**Window:** April 21, 2026 → July 20, 2026  
**WIP limit:** **Max 3 active tasks** at any time.

## Operating Rules
- Only move a task to **Active** if total active tasks stay at 3 or fewer.
- Every task must have one owner and a measurable completion definition.
- Prioritize shipping over starting; finish active work before pulling new tasks.
- Reserve at least one slot for reliability/error-fix work each sprint.

## Active (WIP ≤ 3)
| ID | Bucket | Task | Owner | Due | Success metric |
|---|---|---|---|---|---|
| B1 | Build | Launch unified “Cost Snapshot” template for top 4 verticals (utility, property tax, insurance, COL) | Content/Eng | 2026-05-10 | 4 templates live + QA checklist complete |
| M1 | Monetize | Add comparison-table affiliate modules on 20 highest-intent pages | Monetization | 2026-05-15 | +15% affiliate CTR vs prior 30 days |
| A1 | Automate | Stand up nightly site audit (broken links, missing metadata, orphan pages) with Slack/email report | Eng | 2026-05-12 | Daily report delivered 7/7 days with <2% false positives |

## Ready Queue

### Build
| ID | Task | Target start | Definition of done |
|---|---|---|---|
| B2 | Refresh information architecture for state → county → city internal linking | 2026-05-13 | Crawl depth reduced and all priority pages ≤3 clicks from hub |
| B3 | Add “Last updated” + source provenance blocks to all programmatic page templates | 2026-05-20 | 100% of generated pages include timestamp + sources |
| B4 | Publish 12 high-intent service pages (hvac, plumbing, roofing, etc.) with consistent schema | 2026-06-01 | 12 pages indexed + rich result eligibility validated |

### Monetize
| ID | Task | Target start | Definition of done |
|---|---|---|---|
| M2 | A/B test ad density on mobile templates | 2026-05-16 | RPM uplift without >5% CLS regression |
| M3 | Add lead-form CTA for local service pages in top 15 metro pages | 2026-05-25 | Form live + baseline conversion tracking installed |
| M4 | Build partner pipeline sheet + monthly outreach cadence | 2026-06-05 | 30 prospects contacted, 5 replies, 2 active negotiations |

### Automate
| ID | Task | Target start | Definition of done |
|---|---|---|---|
| A2 | Auto-generate monthly stale-content report (90+ days old) | 2026-05-14 | CSV + dashboard view generated automatically |
| A3 | Add pre-deploy validator (schema, canonicals, sitemap parity, broken links) | 2026-05-22 | Deploy blocked on critical errors |
| A4 | Implement anomaly alerts for traffic/revenue drops by directory | 2026-06-03 | Alert fires within 24h of threshold breach |

### Grow
| ID | Task | Target start | Definition of done |
|---|---|---|---|
| G1 | Build 8-topic editorial cluster supporting highest-RPM commercial pages | 2026-05-18 | 8 articles published + linked to money pages |
| G2 | Create topical newsletter + weekly “city cost watch” digest | 2026-05-30 | 500 subscribers + 30% open rate baseline |
| G3 | Launch backlink sprint (digital PR + HARO + partner quotes) | 2026-06-07 | 20 referring domains with DR40+ |
| G4 | Expand local landing pages in 10 priority metros using validated templates | 2026-06-15 | 10 metros shipped and indexed |

## Error-Fix Track (Fix a Few Errors)
Prioritized reliability and content-quality fixes that can be rotated into one active slot:

1. **E1 — Broken internal links cleanup** (target: <0.5% broken link rate).
2. **E2 — Canonical/duplicate title conflicts** on state + county pages (target: 0 critical SEO conflicts).
3. **E3 — Missing or stale source citations** on high-traffic pages (target: 100% citation coverage on top 200 URLs).
4. **E4 — Template data mismatch checks** (outlier values, null fields) with auto-flagging (target: 95%+ detection precision).

## 90-Day Milestones
- **Day 30 (May 21, 2026):** Core template + monetization experiment + nightly audits stable.
- **Day 60 (June 20, 2026):** Validation gates and stale-content automation live; first growth cluster complete.
- **Day 90 (July 20, 2026):** Systemized publish/monetize loop with error rate down and measurable revenue lift.

## Weekly Cadence (Lightweight)
- **Monday:** Reconfirm top 3 active tasks and blockers.
- **Wednesday:** Mid-week KPI + error budget review.
- **Friday:** Ship review, retro, and pull next tasks from Ready queue.
