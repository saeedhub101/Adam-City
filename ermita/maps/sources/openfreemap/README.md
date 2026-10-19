# OpenFreeMap / OpenMapTiles — layer catalogue

- Area: Ermita, Fifth District, Manila, Capital District, Metro Manila, 1000, Philippines
- Raw tiles: vector-tiles/{z}/{x}/{y}.pbf
- Decoded layer records: one GeoJSON Feature per line; geometry coordinates are WGS84 longitude/latitude.
- Every record includes _source.tile and _source.layer so it can be traced to the original PBF tile.
- Tile coordinates and exact source URL are recorded in source-metadata.json and tile-index.json.
- Attribution: OpenFreeMap © OpenMapTiles Data from OpenStreetMap.

| Layer | Features extracted | File |
|---|---:|---|
| aerodrome_label | 7 | layers/aerodrome_label.geojsonl |
| aeroway | 281 | layers/aeroway.geojsonl |
| boundary | 51 | layers/boundary.geojsonl |
| building | 570 | layers/building.geojsonl |
| housenumber | 1165 | layers/housenumber.geojsonl |
| landcover | 585 | layers/landcover.geojsonl |
| landuse | 916 | layers/landuse.geojsonl |
| mountain_peak | 22 | layers/mountain_peak.geojsonl |
| park | 24 | layers/park.geojsonl |
| place | 1067 | layers/place.geojsonl |
| poi | 14976 | layers/poi.geojsonl |
| transportation | 11098 | layers/transportation.geojsonl |
| transportation_name | 1727 | layers/transportation_name.geojsonl |
| water | 236 | layers/water.geojsonl |
| water_name | 41 | layers/water_name.geojsonl |
| waterway | 541 | layers/waterway.geojsonl |

## Notes

- Raw PBF tiles are retained unchanged for exact reprocessing.
- Tile coverage is the rectangular bounding box returned for Ermita; boundary geometry is saved separately.
- Vector tiles are zoom-dependent generalized map data, not a complete raw OpenStreetMap database.
- If a layer has zero features, its file is still present and the zero count is recorded.
- Review import-report.json for errors and tile-index.json for each tile status.
