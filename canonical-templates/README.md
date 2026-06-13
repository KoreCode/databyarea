# Canonical Templates

Reusable template snapshots copied from current production-style pages.

These files are source examples for future canonical template work. They are not
wired into the site generator yet.

The actively wired high-intent project template lives at
`templates/high-intent-service-guide.html`. Refine that file when perfecting the
detailed service guide pattern; `scripts/generate_service_guides.py` renders
project pages from it.

## Production Readiness Standard

Each template should follow the same design philosophy as the refined insight
pages:

- Use the shared DataByArea shell, top navigation, topic rail, footer, and
  `/assets/styles.css`.
- Keep pages dense, scannable, and planning-focused with compact hero panels,
  metric cards, source notes, and clear next-step links.
- Include title, meta description, robots policy, viewport, canonical URL, and
  version footer script.
- Use only links that exist in the current static site.
- Keep internal/admin templates `noindex,nofollow`.
- Avoid mojibake, decorative clutter, and one-off visual systems.
- For state, city, county, and hub templates, use the contextual service guide
  module with `/assets/service-guide-data.js` and
  `/assets/service-guide-context.js`.
- Include reusable monetization slots through `/assets/monetization.js` where
  the page type supports offers, with partner targeting controlled by
  `data/monetization_config.json`.
- Keep affiliate disclosures available through the shared footer when
  monetization is activated.
- Prefer service-guide CTAs first, especially detailed project guides, and keep
  AdSense-compatible display slots disabled until configured.
- Preserve click/event tracking hooks before sending traffic to partners.

| Template copy | Source page |
| --- | --- |
| `city-dashboard/index.html` | `/minnesota/kiester-template/` |
| `cost-of-living-state/index.html` | `/cost-of-living/minnesota/` |
| `utility-costs-state/index.html` | `/utility-costs/minnesota/` |
| `insurance-costs-state/index.html` | `/insurance-costs/minnesota/` |
| `property-taxes-state/index.html` | `/property-taxes/minnesota/` |
| `state-hub/index.html` | `/minnesota/` |
| `service-guide-hub/index.html` | `/service-guides/` |
| `service-guide-national/index.html` | `/service-guides/electrician/` |
| `service-guide-state/index.html` | `/service-guides/electrician/minnesota/` |
| `service-guide-city/index.html` | `/service-guides/electrician/minnesota/lake-city/` |
| `detailed-high-intent-service-guide/index.html` | `/service-guides/electrician/minnesota/lake-city/new-outlets/` |
| `national-category-hub/index.html` | `/cost-of-living/` |
| `high-intent-service-guide/index.html` | `/plumber-rates-by-state/` |
| `city-insight/index.html` | `/utility-costs/minnesota/lake-city/` |
| `county-insight/index.html` | `/cost-of-living/arizona/maricopa-county/` |
| `search-page/index.html` | `/search/` |
| `admin-panel/index.html` | `/admin/` |
| `legal-trust-page/index.html` | `/privacy-policy/` |
