# Ermita building-height comparison audit

Generated from `ermita/maps/generated/ermita-building-footprints.geojson` on 2026-10-19.
OSM data source: OpenStreetMap contributors (ODbL). This is a local-tag audit and fallback-rule comparison; it is **not** a claim that every footprint has been matched one-to-one against live basemap vector tiles.

## Dataset inventory

- Total OSM features: 1,533 (includes point features)
- Polygon/MultiPolygon features considered building footprints: 1,528
- Polygon footprints with a numeric `height`: 118
- Polygon footprints with numeric `building:levels` but no `height`: 633
- Polygon footprints with neither usable `height` nor `building:levels`: 777
- Polygon footprints with numeric `min_height`: 2
- Polygon footprints with numeric `min_level`: 3
- Invalid/non-numeric height or level values found by the audit: 0

## Shared height policy

The local OSM extrusion in `ermita/maps/preview.html` now follows the same fallback sequence used by OpenMapTiles building rendering:

1. Use the tagged `height` when available.
2. Otherwise use `building:levels × 3.66 m`.
3. Otherwise use a consistent default of `5 m`.
4. For base height, use `min_height`, else `min_level × 3.66 m`, else `0 m`.

Local extrusion height is rounded up to whole meters and clamped to at least 2 m; base height is rounded down and clamped to at least 0 m. This preserves a minimum visible extrusion, so it is close to, but not byte-for-byte identical to, the basemap's raw rendering expression.

## Important comparison result

The shared formula reduces discrepancies caused by different fallback calculations. It cannot eliminate differences caused by the underlying records themselves: the basemap and local GeoJSON may have different update dates, missing footprints, different building tags, or geometry differences. In particular, **777 of 1,528 polygon footprints (50.8%) have neither a usable height nor a levels tag**, so those buildings use the 5 m fallback and are the highest-priority set for later source enrichment or direct tile-by-tile matching.

Examples of existing tagged heights include Pearl of the Orient (52 m, 13 levels), Times Plaza (24.5 m, 7 levels), Eton Baypark Manila (28 m, 8 levels), and Manila Executive Regency (28 m, 8 levels). Tagged `height` takes precedence over levels when both exist.

## Follow-up validation

- Keep both UI layers independent: `BASEMAP 3D BUILDINGS` and `OSM 3D buildings`.
- Do not shift OSM coordinates to compensate for a height mismatch.
- If a specific building still differs, compare its footprint/OSM ID and source tags first; do not globally alter the height formula again.
- A true per-building basemap comparison requires fetching the actual vector-tile features for the same map viewport and matching their geometries/IDs. This audit does not pretend that this tile-level match has already been performed.

## References

- OpenMapTiles schema: https://openmaptiles.org/docs/schema/
- OpenMapTiles building SQL: https://github.com/openmaptiles/openmaptiles/blob/master/layers/building/building.sql
- OSM copyright: https://www.openstreetmap.org/copyright
