# Streets and street names

## Real mapped geometry

- `../maps/generated/ermita-road-network.geojson` contains 1,445 actual OSM-mapped way centerlines exported from the existing cached source. It includes motor roads, service roads, pedestrian ways, footpaths and steps; use the `highway` property to filter the type you need.
- `street_segments.csv` now indexes the same 1,445 source ways, including source OSM IDs/URLs, available tags and per-way source timestamp where present.
- `../maps/generated/road-network-export-report.json` records class counts and limitations.
- The export preserves the coordinates in the cached OSM way geometry. No synthetic/straightened streets were created and no network request was made during export.
- The source cache was last imported by the project's OSM workflow; this output is not guaranteed to be a live/current complete street survey. 366 ways have a name tag and 1,079 do not. Unnamed geometry is still retained.
- These are road/path centerlines, not surveyed curb lines, lane-level geometry or road-surface polygons.

## Street names

`street_names.csv` is the normalized index of unique street names, alternate names and source-backed name references. A street name may apply to many separate geometry segments. Keep the unique name index separate from segment geometry. Preserve source spelling and alternate names rather than silently normalizing them.

## Licence and verification

OpenStreetMap contributors, ODbL 1.0: https://www.openstreetmap.org/copyright. Verify local completeness and road classification against permitted recent imagery or official data before using for engineering, navigation safety or cadastral purposes.
