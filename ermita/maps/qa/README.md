# Building geometry QA

## Active geometry source

The live 3D preview uses only the committed OSM footprint file `generated/ermita-building-footprints.geojson`. Microsoft/Bing outlines were rejected as inaccurate and removed, and the associated comparison CSV/report and workflow were retired.

## Height evidence

Use `building-height-evidence.csv` and `building-height-evidence-report.json` to distinguish explicit OSM `height` tags, floor counts and unknown values. A `height` tag is source-provided but not necessarily survey-verified. Do not silently convert storeys to metres or invent a precise height where none is recorded.

Refresh the height audit with `python ../scripts/audit_building_height_evidence.py` or the `ermita-building-height-audit.yml` workflow.

## Geometry review rules

- Inspect footprints against permitted aerial imagery and street-level references.
- Preserve OSM feature IDs and tags.
- Do not deduplicate by centroid distance alone.
- Do not replace OSM geometry with a source that has not been validated for the target area.
- Record source URL, date, CRS, coverage and limitations for every accepted new layer.
