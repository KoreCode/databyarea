# DataByArea Site Audit Backlog (2026-04-21)

Audit date: **2026-04-21 (UTC)**

## Scope and method
- Ran the repository quality gate (`python3 scripts/site_quality_agents.py`) and reviewed generated output in `_deploy/agent_quality_report.json`.
- Performed repository-wide HTML checks (metadata, canonical tags, JSON-LD presence, thin content count, and internal link integrity) across non-`_deploy` pages.
- Spot-reviewed representative templates (`index.html`, category hubs, city pages, and standalone service pages).

## Snapshot metrics
- HTML pages scanned (excluding `_deploy` and `site/` copies): **776**.
- Pages missing canonical tags: **13**.
- Pages missing JSON-LD schema: **402**.
- Thin-content pages under ~250 words: **397**.
- Broken internal-link references found: **993** total references across **440** unique missing targets.
- Most frequent missing destination: **`/services/` appears 455 times**.

---

## 1) Must-fix bugs (P0/P1)

### P0-1: Systemic broken internal links to `/services/`
- **Impact:** Hard 404 risk on hundreds of pages; damages UX and crawl quality.
- **Evidence:** 455 references to `/services/` from generated pages; example in Seattle utility page links “Home Service Cost Guides” to `/services/`.
- **Backlog action:**
  1. Either generate and publish `/services/index.html`, or
  2. Remove/replace `/services/` links in generator templates with valid targets.
  3. Add publish-gate check that fails build if missing-target links exceed threshold.

### P0-2: Hundreds of other broken internal links to non-generated city pages
- **Impact:** Navigation dead ends and poor indexability for geographic drill-down flow.
- **Evidence:** 993 broken references total across 440 unique missing targets (examples include many city links under utility and cost-of-living trees).
- **Backlog action:**
  1. Add template-level guard: only emit city/county links when page exists.
  2. Add link resolver to generator with existence check.
  3. Run a full-link audit in CI and fail on regressions.

### P1-1: Missing canonical tags on 13 money pages
- **Impact:** Canonical ambiguity and duplicate-content risk.
- **Evidence:** Missing canonical on key pages including:
  - `plumber-rates-by-state/index.html`
  - `roof-replacement-cost-by-state/index.html`
  - `water-heater-installation-cost-by-state/index.html`
  - `garage-door-repair-cost-by-state/index.html`
  - `concrete-driveway-cost-by-state/index.html`
  - `window-replacement-cost-by-state/index.html`
  - `foundation-repair-cost-by-state/index.html`
  - `hvac-installation-cost-by-state/index.html`
  - `electrician-rates-by-state/index.html`
  - `deck-building-cost-by-state/index.html`
  - plus legal/admin pages.
- **Backlog action:** Ensure all production templates emit absolute canonical URLs.

---

## 2) UX issues

### P1-UX-1: Homepage category cards are semantically mismatched
- **Impact:** Confusing IA and lower trust (e.g., “Demographics” links to `/about/`, “Crime” links to insurance pages).
- **Backlog action:** Map each homepage card to a true destination and real supporting data module.

### P1-UX-2: Footer links and policy naming inconsistency across templates
- **Impact:** Inconsistent mental model and perceived quality.
- **Evidence:** Some pages use `/privacy/`, others `/privacy-policy/`.
- **Backlog action:** Standardize legal URL structure and nav labels across all templates.

### P2-UX-3: Redundant long state lists on hubs increase scroll fatigue
- **Impact:** Excessive vertical scanning on mobile; low discoverability of county/city drill-down.
- **Backlog action:** Add grouped accordion/filter + top “popular paths” with intent-based shortcuts.

---

## 3) Missing content

### P1-CONTENT-1: Thin content footprint is very high
- **Impact:** Low differentiation and weaker long-tail rankings.
- **Evidence:** 397 pages below ~250 words (many county pages around 70–190 words).
- **Backlog action:**
  1. Set minimum content floor by template type.
  2. Expand county/city pages with local utility/provider notes, methodology snippets, and unique FAQs.

### P1-CONTENT-2: Partial schema coverage
- **Impact:** Lost rich-result opportunity and weaker machine readability.
- **Evidence:** 402 pages missing JSON-LD.
- **Backlog action:** Add baseline `WebPage`/`BreadcrumbList` schema globally, then layer template-specific schema.

### P2-CONTENT-3: Service-guide pages are structurally sparse
- **Impact:** These pages look under-templated relative to core hubs.
- **Evidence:** Example `plumber-rates-by-state/index.html` lacks canonical and richer module structure.
- **Backlog action:** Migrate service pages onto shared site template with nav, trust signals, and cross-links.

---

## 4) Performance issues

### P1-PERF-1: Heavy third-party map scripts loaded on category hubs without progressive enhancement
- **Impact:** Render delay on slower devices/connections; unnecessary JS cost for users not interacting with map.
- **Backlog action:** Lazy-load map library after interaction/viewport entry and provide non-JS fallback list first.

### P2-PERF-2: Large amount of dead-link crawl budget waste
- **Impact:** Crawlers spend budget on missing pages, reducing effective crawl on high-value URLs.
- **Backlog action:** Fix internal linking graph first, then recrawl and monitor via Search Console coverage.

### P2-PERF-3: No explicit image lazy-loading on homepage logo
- **Impact:** Small but avoidable; easy optimization.
- **Backlog action:** Add `loading="lazy"` where non-critical and ensure responsive dimensions.

---

## 5) Monetization blockers

### P0-MON-1: Monetization globally disabled in config
- **Impact:** No revenue modules can render regardless of traffic.
- **Evidence:** `global.affiliate_enabled=false` and `global.lead_form_enabled=false`.
- **Backlog action:** Enable phased rollout by page type after quality gate passes.

### P0-MON-2: Quality threshold gate disabled for sensitive templates
- **Impact:** Monetization rollout is structurally blocked for key YMYL-adjacent verticals.
- **Evidence:** `global.quality_threshold_passed=false`, `sensitive_templates.enabled=false`.
- **Backlog action:** Define checklist for threshold pass and staged activation criteria.

### P1-MON-3: No monetization module markers detected in published HTML
- **Impact:** Even with flags, current output appears not to include placement scaffolding.
- **Backlog action:** Ensure template render path outputs affiliate/lead containers (`.dba-affiliate-module`, `.dba-lead-form-module`) and instrumentation events.

---

## Recommended execution order (first 2 sprints)

### Sprint 1 (stability + trust)
1. Fix `/services/` and top broken-link patterns.
2. Add canonical tags on all service/legal templates.
3. Enforce build-time broken-link and canonical checks.
4. Normalize legal nav URLs.

### Sprint 2 (content + monetization readiness)
1. Raise content floor for thin city/county pages.
2. Roll out baseline JSON-LD on missing templates.
3. Add monetization container scaffolding + analytics events.
4. Run low-risk monetization pilot on home-services/state pages only.

## Definition of “audit complete” for this pass
- Backlog has been split into:
  - must-fix bugs
  - UX issues
  - missing content
  - performance issues
  - monetization blockers
- Each item includes impact + action and is prioritized.
