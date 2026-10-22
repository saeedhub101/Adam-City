# OpenFreeMap / OpenMapTiles — incremental layer catalogue

- Area: Ermita, Fifth District, Manila, Capital District, Metro Manila, 1000, Philippines
- Source maximum zoom: 14; effective requested maximum: 14
- Import mode: incremental; valid local PBF files are reused and never downloaded again.
- Existing GeoJSONL layer files are preserved; records are appended only for newly downloaded valid tiles.
- Raw tiles: vector-tiles/{z}/{x}/{y}.pbf
- Decoded records: one GeoJSON Feature per line; coordinates are WGS84 longitude/latitude.
- Every record includes _source.tile and _source.layer to trace it to the original PBF tile.
- Attribution: OpenFreeMap © OpenMapTiles Data from OpenStreetMap.

| Layer | Total features in repository | File |
|---|---:|---|
| aerodrome_label | 0 | layers/aerodrome_label.geojsonl |
| aeroway | 0 | layers/aeroway.geojsonl |
| boundary | 0 | layers/boundary.geojsonl |
| building | 0 | layers/building.geojsonl |
| housenumber | 1165 | layers/housenumber.geojsonl |
| landcover | 0 | layers/landcover.geojsonl |
| landuse | 0 | layers/landuse.geojsonl |
| mountain_peak | 0 | layers/mountain_peak.geojsonl |
| park | 0 | layers/park.geojsonl |
| place | 0 | layers/place.geojsonl |
| poi | 0 | layers/poi.geojsonl |
| transportation | 0 | layers/transportation.geojsonl |
| transportation_name | 0 | layers/transportation_name.geojsonl |
| water | 0 | layers/water.geojsonl |
| water_name | 0 | layers/water_name.geojsonl |
| waterway | 0 | layers/waterway.geojsonl |

## Incremental import report

- Existing valid tiles reused: 141
- New valid tiles downloaded: 0
- Unsupported zoom tiles skipped: 0
- Empty/failed tiles: 0
- Review import-report.json and tile-index.json for per-tile status.
- To retry previously empty tiles intentionally, set RETRY_EMPTY_TILES=1.
- Vector tiles are zoom-dependent generalized map data, not a complete raw OpenStreetMap database.


## Tile-index audit (2026-10-22)

The committed `tile-index.json` contains **141 valid tiles** across zooms 10–14. Summing the per-tile feature counts gives these *tile-feature instances* (not unique objects): `building` 1,846; `housenumber` 8,603; `poi` 78,036; `transportation` 67,593; `transportation_name` 9,727; `boundary` 537; `landuse` 6,541; `landcover` 3,112; `water` 4,175; `waterway` 5,866; `water_name` 247; `park` 217; `place` 18,622; `aeroway` 1,295; `aerodrome_label` 48; `mountain_peak` 813.

**Important discrepancy:** the decoded GeoJSONL catalogue in this folder does not contain those full counts. The existing `layers/building.geojsonl` file is empty, while `layers/housenumber.geojsonl` contains 1,165 records; `import-report.json` points to the parallel `ermita/maps/sources/openfreemap/layers/` directory rather than this `complete_data/open free tile/layers/` directory. Therefore the counts above come from raw tile metadata, include repeated features across zooms/tiles, and must not be described as unique buildings or as fully extracted local layers.

**Next data recovery step:** rebuild decoded layers from the already committed PBF tiles using `tile-index.json` and the exact OpenMapTiles schema/version, write outputs into this canonical `complete_data/open free tile/layers/` folder, deduplicate with source-aware IDs/geometry, and report counts separately for raw tile instances versus deduplicated features. This is a metadata extraction task; it does not change active building geometry or rendering.


## OpenFreeMap building extraction — 2026-10-22

- Downloaded and decoded all **141 indexed PBF tiles** from the source template in `source-metadata.json`; all 141 decoded successfully with the OpenMapTiles vector-tile schema.
- The raw tile index reports **1,846 building-layer feature instances** across zooms 10–14, representing **1,746 distinct feature IDs before spatial filtering**. These are not a unique-building count because IDs/geometry may repeat across zooms and tile edges.
- The index extent is approximately `[120.9710994, 14.5731967, 120.9930963, 14.5970416]`. Selecting zoom-14 building features whose geometry intersects this extent, then retaining only polygon components that intersect the extent, produced **350 building-feature records** for the current Ermita extent.
- Added the split metadata registry: `layers/buildings-part1.csv` (175 records plus header) and `layers/buildings-part2.csv` (175 records plus header). Each record includes feature ID, geometry type, centroid/bounds, source tile, render height/min-height, colour when present, and geometry-coordinate count.
- In these 350 records, all 350 carry OpenMapTiles `render_height`; 39 carry `colour`; none currently have building name, house number, or street in the building layer. Address and name enrichment must be joined from the `housenumber`, `poi`, `transportation_name` layers and other authoritative sources rather than guessed.
- **Important limitation:** these two CSVs are metadata indexes, not replacement geometry files. The source polygon geometry remains in the downloaded PBF tiles under `ermita/maps/sources/openfreemap/vector-tiles/{z}/{x}/{y}.pbf`; no building geometry was changed in the active map. MultiPolygon components outside the stated Ermita extent were excluded from the registry geometry-intersection count; this is a spatial filter, not a claim that the source OSM object itself ends at that boundary.
- Attribution: OpenFreeMap © OpenMapTiles; data from OpenStreetMap. Schema: https://openmaptiles.org/docs/schema/ .
