# City Data Framework

This folder stores structured JSON for each city page.

## Path pattern

`data/city-data/<section>/<state-slug>/<city-slug>.json`

Example:

`data/city-data/utility-costs/texas/austin.json`

## Lifecycle

1. A city page is created under `/<section>/<state>/<city>/index.html`.
2. The generators call `ensure_city_data_seed(...)`.
3. A starter JSON payload is created if missing.
4. Future enrichment jobs can safely update `data` values while keeping source metadata.

## Suggested data ingestion pipeline

1. **Raw collection**: gather city datasets from public APIs/CSVs and store snapshots in `data/raw/<provider>/...`.
2. **Normalization**: map provider columns to canonical keys in city JSON.
3. **Validation**: enforce required keys and ranges before publish.
4. **Publication**: write back normalized values into `data/city-data/...`.
5. **Rendering**: city pages and APIs read from this canonical JSON layer.
