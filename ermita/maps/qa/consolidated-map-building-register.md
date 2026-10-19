# Consolidated map and building source register — Ermita

Scope: map geometry and building records only. Inventory checked against files committed on `main` on 2026-10-19.

## Consolidated building records

The merged row-by-row register is [`consolidated-building-register.csv`](consolidated-building-register.csv).

It merges by OSM feature ID, retains different values rather than choosing one, lists the files in which each record appears, and marks records that appear only in one detail source. It combines:
- `../generated/ermita-building-details.csv`
- `../generated/ermita-building_details.csv` (legacy broader inventory; building-related records only)
- `building-height-evidence.csv`

Current join summary:
- 1,533 IDs appear in both detail files.
- 37 additional polygon/building-related IDs appear in the legacy detail file only.
- Height evidence contains 1,528 polygon records; it distinguishes explicit tagged heights, floor counts, and unknown heights.
- 24 consolidated records have more than one distinct value in at least one merged field. The CSV retains those values.
- A record missing from a particular file means only that it is absent from that file, not that the building is absent in reality.

## Map geometry and imagery inventory

| Data | Repository location | What it represents | Merge / comparison rule |
|---|---|---|---|
| Active building footprints | `../generated/ermita-building-footprints.geojson` | OSM polygons/multipolygons plus source IDs/tags | Active footprint source. Preserve OSM IDs and all tags. |
| Building attributes | `../generated/ermita-building-details.csv` | Names, building types/parts, heights, levels, roof/material/colour/address tags | Joined by OSM ID into the consolidated register. |
| Legacy feature attributes | `../generated/ermita-building_details.csv` | Broader OSM records, including coordinates and tag JSON | Building-related records are cross-checked by OSM ID; the 37 legacy-only records remain explicitly identified. |
| Height evidence | `building-height-evidence.csv` | 1,528 polygon records with height evidence class | Explicit height, floor count, and unknown remain distinct; floor counts are not measurements of height. |
| Active OSM road/path centerlines | `../generated/ermita-road-network.geojson` | 1,445 OSM ways, 366 named | Match corresponding street segments by OSM way ID where available; retain unnamed paths/ways. |
| Street attributes/index | `../../streets/street_segments.csv` | Street name/aliases, road class, surface, lanes, one-way, sidewalk, lighting, source way ID | Join by `geometry_id` / OSM way ID; do not discard values that differ across records. |
| DPWH national roads | `external/dpwh-national-roads-ermita.geojson` | Official road-reference geometry/attributes | Keep as a separate attributed source; only merge a road with OSM when spatial alignment/identity is verified. |
| DPWH lane counts | `external/dpwh-number-of-lanes-ermita.geojson` | Road lane-count records | Retain DPWH and OSM lane values separately if they disagree. |
| DPWH road surface | `external/dpwh-road-surface-type-ermita.geojson` | Road surface-type records | Retain source-specific surface values; do not overwrite OSM. |
| DPWH bridges | `external/dpwh-bridge-inventory-ermita.geojson` | Bridge inventory records | Keep bridge records distinct unless an identity/location match is verified. |
| Microsoft road detections | `external/ermita-microsoft-road-detections.geojson` | Road detections, not building footprints | Separate reference layer; do not treat it as a building source. |
| Esri imagery | streamed in preview | Aerial/satellite basemap | Not stored as local image tiles in the repository; cannot be merged as per-building records. |
| Microsoft/Bing building footprints | removed/retired | Rejected footprint source | Not an active comparison source; do not restore or re-import unless explicitly authorized. |

## Important source limitation

The committed building records above are multiple files derived from OpenStreetMap, not independent building-footprint providers. This register therefore consolidates and cross-checks the existing OSM-derived files; it does not claim that OSM has been independently matched against Microsoft, Esri, or government building polygons. The DPWH files currently present are road/bridge layers, not building footprints.

## Rules for future imports

1. Check this register and the existing files before importing.
2. Match records by stable source ID first; use location/name only as a candidate match, not proof.
3. If the same feature has different values, keep both values and record their sources.
4. If a feature exists in one source only, state that source explicitly.
5. Do not interpret missing data as evidence that a real-world feature does not exist.
