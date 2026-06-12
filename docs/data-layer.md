# DataByArea Data Layer

The city and insight templates should be driven by versioned data records, not by one-off HTML edits.

## Current Contract

- City/location records use `schema_version: "dba.location.v1"`.
- State insight records use `schema_version: "dba.state_insight.v1"`.
- Metric definitions live in `data/metric_definitions.json`.
- The first city seed record is `data/places/minnesota/kiester.json`.
- The first state insight seed record is `data/state-insights/minnesota.json`.

## City Record Shape

Each city record has:

- `location`: city, state, county, ZIP, and geo metadata.
- `page`: canonical URL, API path, template path, title, description, and robots.
- `metrics`: canonical metric objects.
- `sections`: which metric keys belong in each dashboard section.
- `charts`: reusable chart data.
- `comparisons`: nearby city cards and comparison-table values.
- `sources`: source metadata keyed by `source_id`.
- `fallback_policy`: how templates should behave when data is missing.

Metric objects are intentionally richer than the current API response:

```json
{
  "value": 507,
  "unit": "people",
  "display": "507",
  "label": "Population",
  "source_id": "city_static_seed",
  "source_year": "2026",
  "updated_at": "2026-06-10",
  "confidence": "medium",
  "status": "fallback",
  "aliases": ["population"],
  "notes": "Static seed until live Census place match is available."
}
```

Templates should read `display` for static rendering, use `value` for calculations, and show source/caveat context near each data group.

## API Compatibility

The current backend returns flat keys under `record.data`, such as:

- `population`
- `median_household_income`
- `median_home_value`
- `median_property_tax_paid_usd`
- `electricity_price_cents_per_kwh`
- `gasoline_price_usd_per_gallon`
- `unemployment_rate`

The data layer keeps `aliases` so templates can resolve live API fields into canonical metrics without changing the backend all at once.

Resolution order:

1. Canonical metric key, e.g. `median_home_value`.
2. Metric aliases from `data/metric_definitions.json`.
3. Page-specific aliases when needed.
4. Static fallback `display`.

## Template Rules

- Do not hardcode city names, state names, ZIPs, nearby cities, API paths, or source labels in generated city pages.
- Do not show empty cards. If a metric is missing and has no fallback display value, hide that row/card.
- Every visible number should have a source, year, confidence, and status in the data record.
- Sensitive topics like insurance and property tax should keep conservative language and clear caveats.
- City pages should use `comparisons.nearby_cities` instead of hand-authored nearby cards.
- State insight pages should use `data/state-insights/{state}.json` for hero KPIs, city sets, and cross-page copy.

## Next Implementation Steps

1. Update the Kiester template to load `data/places/minnesota/kiester.json`.
2. Replace `window.DBA_CITY_TEMPLATE_CONFIG` hardcoded values with data-derived values.
3. Add a renderer/helper that maps canonical metrics to existing `data-field` elements.
4. Move shared state insight CSS into `assets/styles.css`.
5. Convert the four Minnesota insight pages to read from `data/state-insights/minnesota.json`.
6. Add validation to CI before generating or publishing pages.
