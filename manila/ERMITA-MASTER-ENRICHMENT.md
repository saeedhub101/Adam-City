# Ermita master-data enrichment — working log

## Objective
Enrich the master CSV and its chunked GeoJSON with evidence already present in this repository before external research. Preserve every row/feature and its existing data. This is metadata-only.

## Exact-ID pass
Run from the repository root:
```bash
python3 manila/enrich_ermita_master_data.py
```

Inputs:
- `complete_data/OSM/data/buildings/Ermita/osm-building-details.csv`
- `complete_data/OSM/quality/building-height-evidence.csv`
- `ermita/3d/building-match-audit.csv`

The script adds `enriched_*`, `enrichment_sources`, and `enrichment_status` fields to the master CSV and both GeoJSON parts. It copies values only when an explicit OSM ID matches. If sources disagree, the disputed field remains blank and the conflict is reported in `ermita-master-enrichment-report.json`. No proximity/name-only joins, unreviewed image candidates, or invented architectural measurements are used.

## Safety invariants
- Do not change geometry, coordinates, source IDs, feature IDs, existing attributes, or rendering heights.
- Do not merge/delete rows or features because they may describe the same physical building.
- Do not treat image candidates as verified facade photos or texture assignments.
- Exact-ID enrichment is the first pass; unmatched records need a separate conservative review.

## Next steps
1. Review field coverage and conflicts in the generated report.
2. Build a crosswalk for other source IDs and geometry fingerprints; ambiguous cases remain in review.
3. Inspect candidate images visually and verify the depicted building before extracting facade details.
4. Search authoritative external sources only for remaining important gaps, recording URLs, access dates, and confidence per field.
