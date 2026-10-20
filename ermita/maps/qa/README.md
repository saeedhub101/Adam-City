# Building geometry QA

## Active geometry source

The live preview entry point is `../../../ermita-malate-3d.html` and its base display is OpenFreeMap with local tile-derived fallbacks. The generated file `../generated/ermita-building-footprints.geojson` is Basemap/OpenMapTiles-derived according to the repository data audit; it must not be described as pure OSM. Independent Google and Microsoft satellite-derived footprint datasets exist under `../sources/` and are not automatically active layers.

## Height evidence

Use `building-height-evidence.csv` and `building-height-evidence-report.json` to distinguish explicit OSM `height` tags, floor counts and unknown values. A `height` tag is source-provided but not necessarily survey-verified. Do not silently convert storeys to metres or invent a precise height where none is recorded.

Refresh the height audit with `python ../scripts/audit_building_height_evidence.py` or the `ermita-building-height-audit.yml` workflow.

## Geometry review rules

- Inspect footprints against permitted aerial imagery and street-level references.
- Preserve OSM feature IDs and tags.
- Do not deduplicate by centroid distance alone.
- Do not replace OSM geometry with a source that has not been validated for the target area.
- Record source URL, date, CRS, coverage and limitations for every accepted new layer.
