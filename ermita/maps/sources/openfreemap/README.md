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
