# Canonical City Dashboard Architecture & URL Migration Plan

## Goal
Move from insight-specific city pages (for example `utility-costs/<state>/<city>/`) to a single canonical city dashboard route that renders insight tabs as views, while preserving current SEO value from indexed legacy URLs.

## 1) Current folder/URL structure (as it exists now)

The repo currently publishes multiple city URL families, including:

- Canonical-ish city pages at state/city root:
  - `/<state>/<city>/` (example: `/minnesota/lake-city/`)
- Insight-specific city pages:
  - `/utility-costs/<state>/<city>/`
  - `/insurance-costs/<state>/<city>/`
  - `/cost-of-living/<state>/<city>/`
  - `/property-taxes/<state>/<city>/`
- State-level and county-level insight hubs under those same service prefixes.

This creates template duplication and splits ranking signals across parallel URLs for the same city intent.

## 2) Target canonical architecture

### Canonical city route
Adopt one canonical URL for each city:

- `/<state>/<city>/`

(Alternative namespace `/city/<state>/<city>/` is valid, but keeping `/<state>/<city>/` minimizes migration churn because this path already exists in production.)

### Insight tabs as data views
Use one city page shell and switch insight sections via tab parameter or nested routes:

- Query form: `/<state>/<city>/?tab=utilities`
- Query form: `/<state>/<city>/?tab=insurance`
- Query form: `/<state>/<city>/?tab=cost-of-living`
- Query form: `/<state>/<city>/?tab=property-taxes`

Optional pretty nested aliases that render the same shell:

- `/<state>/<city>/utilities/`
- `/<state>/<city>/insurance/`
- `/<state>/<city>/cost-of-living/`
- `/<state>/<city>/property-taxes/`

## 3) Data contract mapped to generator output

For each city, generator should emit one payload keyed by stable section names:

```json
{
  "city": {"slug": "los-angeles", "name": "Los Angeles"},
  "state": {"slug": "california", "name": "California"},
  "demographics": {...},
  "utilities": {...},
  "cost_of_living": {...},
  "property_taxes": {...},
  "insurance": {...}
}
```

Each tab reads only its section. Missing sections should show “data not yet available” within the same canonical page (not produce a separate URL/template).

## 4) Direct mapping from legacy URLs to canonical city tabs

Implement deterministic redirects:

- `/utility-costs/<state>/<city>/` → `/<state>/<city>/?tab=utilities`
- `/insurance-costs/<state>/<city>/` → `/<state>/<city>/?tab=insurance`
- `/cost-of-living/<state>/<city>/` → `/<state>/<city>/?tab=cost-of-living`
- `/property-taxes/<state>/<city>/` → `/<state>/<city>/?tab=property-taxes`

For nested tab aliases, either:

- 301 to query-tab URL, or
- 200 render same template but set canonical to `/<state>/<city>/` (recommended canonical target).

## 5) SEO-safe migration plan (preserve indexed pages)

### Phase 0 — inventory and pairing
1. Export current published city URLs from `published_manifest.json` and `sitemap.xml`.
2. Build a migration map of every city-level legacy insight URL to its canonical city tab URL.
3. Keep non-city URLs (state/county hubs) out of this redirect set unless explicitly migrated later.

### Phase 1 — dual-serve + canonical
1. Ship new canonical city shell at `/<state>/<city>/` with tab UI.
2. Keep legacy insight city pages live temporarily (HTTP 200) but add:
   - `<link rel="canonical" href="https://databyarea.com/<state>/<city>/">`
   - Meta robots `index,follow` during warmup window.
3. Ensure structured data references canonical city page.

### Phase 2 — 301 redirect cutover
After search console recrawl confirms canonical consolidation:
1. Switch city-level legacy insight pages to 301 redirects to `/<state>/<city>/?tab=<tab>`.
2. Update internal links so nav and related links point only to canonical city URLs.
3. Regenerate sitemap entries to include only canonical city routes (plus any chosen nested tab aliases if they are indexable).

### Phase 3 — cleanup and guardrails
1. Remove per-insight city template generation in `scripts/build_site.py`.
2. Keep only one city template renderer + tab metadata injection.
3. Add validation check in quality gate to fail if a city appears in more than one template family.

## 6) Generator changes (concrete)

1. **Route model**
   - Introduce a canonical city route object (`state_slug`, `city_slug`, `available_tabs`).
2. **Template rendering**
   - Render one `index.html` per city path: `/<state>/<city>/index.html`.
3. **Legacy output mode**
   - Replace full HTML legacy city pages with lightweight redirect pages (or edge redirects) using migration map.
4. **Sitemap generation (`makesitemap.py`)**
   - City sitemap should emit only canonical city URLs.
5. **Relinking (`relink_existing_pages.py`)**
   - Repoint in-content links from service-prefixed city URLs to canonical city URLs.

## 7) Rollout checklist

- [ ] Canonical city template implemented.
- [ ] Tab query parser and default tab behavior implemented.
- [ ] Full migration map generated for all current city insight URLs.
- [ ] Canonical tags validated on all city pages.
- [ ] 301 redirect rules tested for each insight family.
- [ ] Sitemaps regenerated and submitted.
- [ ] Internal links repointed.
- [ ] Duplicate-city-template quality gate added.

## 8) Recommended canonical decision

Given current production-like structure already includes `/<state>/<city>/` pages, the least-risk path is:

- **Canonical city URL**: `/<state>/<city>/`
- **Tabs**: `?tab=<insight>` for crawl-safe single-template behavior
- **Legacy city insight URLs**: temporary canonicalization, then 301 to canonical tab

This preserves existing indexed equity while eliminating long-term template duplication.
