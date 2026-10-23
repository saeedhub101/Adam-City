# Manila OpenFreeMap building data

## Canonical dataset

- `ermita-openfreemap-building-components.csv` — one consolidated, standardized table made from the two source registries in `complete_data/open free tile/layers/buildings-part1.csv` and `buildings-part2.csv`.
- Record count: 1,721 source polygon components. These are **not confirmed unique physical buildings**.
- Source: OpenFreeMap / OpenMapTiles; underlying map data © OpenStreetMap contributors.
- Geographic scope: Ermita, Manila; source tiles zoom 10–14, extraction registry clipped to the recorded Ermita area.

## Standard field rules

- `feature_id` is a project registry key (for example `OFM-ERMITA-00001`), **not an OSM ID**.
- `source_osm_id` is retained only where an accepted OSM feature ID was recorded; `candidate_osm_id` is a candidate and must not be treated as confirmed identity.
- `height_m` uses explicit `osm_height_m` when available; otherwise it uses the OpenFreeMap render height. `height_source` states which source supplied it. Do not interpret render height as an independently verified survey height.
- `levels`, `min_height_m`, `underground_levels`, and `roof_height_m` use the single canonical field names. Empty values mean unknown/not supplied; they are not zero.
- `name` prefers the recorded official name, then the building name. Candidate-only names are not copied into `name`.
- Coordinates are WGS84 longitude/latitude. Original component order and source registry IDs are preserved; no spatial candidates were force-merged and no geometry was modified.

## Quality notes

- The source audit reports 1,721 extracted polygon components, 1,629 exact unique full-ring geometries and 92 exact duplicate components. This is geometry-level deduplication, not a physical-building census; this canonical table preserves all 1,721 components for traceability.
- Spatial matches to OSM are not exact source-ID joins in general. Match method and confidence are retained; candidates remain distinguishable from accepted IDs.
- The previous layer catalogue has incomplete decoded GeoJSONL layers. This consolidated CSV is a standardized attribute registry, not a replacement for source tile files or building geometry.

## Source references

- `complete_data/open free tile/building-extraction-report.json`
- `complete_data/open free tile/building-deduplication-audit.json`
- `complete_data/open free tile/ermita-internal-source-enrichment-report.json`
- OpenMapTiles schema: https://openmaptiles.org/docs/schema/

Attribution: OpenFreeMap © OpenMapTiles. Data from OpenStreetMap contributors.
