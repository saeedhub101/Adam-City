# Ermita internal building-source audit

**Date:** 2026-10-22  
**Purpose:** Inspect existing repository data before seeking new external information.

## Key finding

The master files are **multi-source collections, not one row/feature per real building**:

- Master CSV: **24,102 rows, 193 columns, 18 source files** represented in the merged rows.
- Master GeoJSON: **22,977 features** across two chunks (12,507 + 10,470), originally collected from seven GeoJSON sources.
- The master-generation script removes byte-identical source files, but intentionally retains features from different sources even when they may describe the same physical building.
- In the master CSV, 7,786 rows carry `osm_feature_id`, but those rows refer to only 1,909 unique OSM IDs. Thus the raw row count cannot be used as the unique building count.

## Existing internal sources with useful information

| Repository source | Existing content | Safe use now |
|---|---|---|
| `complete_data/OSM/data/buildings/Ermita/osm-building-details.csv` | 1,909 unique OSM IDs; 650 named rows | Exact OSM-ID tag join only |
| `complete_data/OSM/quality/building-height-evidence.csv` | 1,528 unique IDs; 118 height tags, 743 level tags, 97 roof-shape tags | Preserve source tags and distinguish tagged heights from estimates |
| `ermita/3d/building-match-audit.csv` | 1,306 OSM-ID rows | Supplemental type/height/level evidence by exact ID |
| `ermita/3d/facade-photo-review.csv` | 246 unique photo records | Candidate photo IDs, not automatic facade textures |
| `complete_data/OSM/data/buildings/Ermita/building-visual-research-queue.csv` | 1,132 footprint records with coordinates and search links | Internal review queue; do not attach nearby names automatically |
| `complete_data/OSM/data/buildings/Ermita/building-image-candidates.csv` | 1,049 image candidates but only 330 unique source feature IDs | Multiple candidate images per target; review identity before use |
| `ermita/maps/qa/consolidated-building-register.csv` | 1,570 OSM IDs with source-presence/conflict notes | Find missing sources and conflicts by exact ID |
| `ermita/maps/qa/non-osm-building-footprint-crosswalk.csv` | 8,176 Google/Microsoft rows; 1,032 probable cross-source matches | Potential geometry cross-check; not yet joined to OFM geometry |
| `building-data/buildings.csv` | 30-row pilot register with building-use, website, heritage, architect, address and barangay fields | Exact-ID enrichment only; preserve provisional barangay status |
| `ermita/buildings/reference_photos_catalog.json` and `building-image-links.json` | Licensed/candidate photo metadata and named-building leads | Use as evidence candidates, not automatic texture assignments |

## Work already applied to the OpenFreeMap sort

The file `complete_data/open free tile/ermita-building-geographic-completeness-sort.csv` now includes source provenance and additional fields from exact accepted OSM-ID matches:

- 692 rows joined against the OSM details source and 692 against the height-evidence source.
- 605 rows cross-referenced against the building-match audit.
- 28 exact-ID matches to the 30-row pilot register; **296 previously blank pilot fields** were copied with provenance. Barangay values retain their provisional assignment status.
- 28 exact-ID joins to field-level evidence records.
- 184 existing facade-photo-review entries were linked to 95 OFM component rows. Those rows are flagged **unverified photo candidate**; no image was declared verified or assigned as a texture.
- One named-building image-link record joined by exact OSM ID.

No GeoJSON geometry, coordinates, source IDs, or render heights were changed.

## Current first-pass OFM component triage

| Class | Count |
|---|---:|
| Partially enriched | 368 |
| Needs match review | 355 |
| Insufficient data | 998 |
| Strictly verified complete | 0 |

These are 1,721 OpenFreeMap polygon components, not a confirmed count of unique physical buildings. The current triage is not the final result for the 22,977-feature/24,102-row master files.

## Next internal step

Build a record-level crosswalk between the 22,977 master GeoJSON features and 24,102 source CSV rows. Match exact source IDs first, then use geometry fingerprints and conservative spatial checks. Preserve all source records; ambiguous/duplicate candidates must go into review rather than being silently merged or deleted.

The Google/Microsoft footprint crosswalk already labels 1,032 pairs as probable same-building matches, but that crosswalk is between those two footprint sources only and still needs to be reconciled against the OFM master geometry.


## Read-only crosswalk builder added

A reusable script is now available at `complete_data/OSM/scripts/reconcile_ermita_master_geojson_csv.py`. It streams both large GeoJSON parts, computes geographic order, matches explicit identifiers against the 24,102-row master CSV, and writes a feature-level CSV crosswalk plus JSON report. It preserves all source records and sends multiple/unmatched identifiers to review instead of silently merging them. **The script has been committed but has not been executed; no workflow was run.**
