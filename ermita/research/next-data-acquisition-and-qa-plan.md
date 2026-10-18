# Next Data Acquisition and QA Plan — Ermita + Rizal Park

**Reviewed:** 2026-10-18  
**Working branch:** `main` only  
**Rule:** do not create a branch, re-download/re-import a dataset that is already present, or overwrite source files in place. Each new import must be idempotent and produce a report.

This is an execution plan based on the files and reports currently in the repository. "Source found" is not the same as "file imported", "coverage verified", or "permission to redistribute confirmed".

## Current baseline — do not repeat these imports

| Dataset | Repository evidence | Current reported scope | Action |
|---|---|---|---|
| OSM features | `ermita/maps/generated/import-report.json` | 8,040 elements; 7,825 GeoJSON features; 1,533 building/building-part features | Keep existing records; use current extract as one side of comparison |
| Microsoft/Bing footprints | `ermita/maps/external/ermita-microsoft-building-footprints.geojsonl.gz` and import report | 12,132 clipped footprints; imagery vintage 2016–2020 | Do not fetch the 1.19 GB source archive again for this task; compare local clipped data with OSM |
| DPWH roads and bridges | `ermita/maps/external/dpwh-road-bridge-batch-import-report.json` | Four imported layers: 286, 990, 939 and 61 features | Validate attribute consistency and vintage; no duplicate batch import |
| Copernicus terrain | `ermita/3d/terrain/terrain-import-report.json` plus GeoTIFF/GLB | GLO-30 DSM; 20,412 valid cells | Retain as regional baseline until a better source is obtained and permitted |
| KartaView metadata | `kartaview/ermita-street-imagery-metadata.csv`, GeoJSON, sequence CSV and report | 4,996 metadata records; 155 sequences | Audit locally; do not rerun discovery merely to repeat existing IDs |
| KartaView facade match index | `kartaview/ermita-real-facade-images.csv` and `kartaview/ermita-real-facade-report.json` | 246 building-matched photos; 238 downloaded | Audit existing files and match quality before any new image download |
| Procedural facade model | `ermita/3d/generated/facade-details-report.json` | 1,468 polygon parts; generated window/door/signboard placeholders | Do not mistake placeholders for measured architecture |

## Work package A — NPDC official park maps and reference assets

### Sources already catalogued

See `ermita/sources/downloadable-source-catalog.md` and the official NPDC downloads index: https://npdc.gov.ph/downloads/

Prioritize:
1. Rizal Park Technical Map (JPG): https://npdc.gov.ph/wp-content/uploads/2024/05/Rizal-Park-Technical-Map-scaled.jpg
2. Rizal Park brochure (PDF): https://npdc.gov.ph/wp-content/uploads/2021/06/Rizal-Park-Brochures.pdf
3. Distribution and Thematic Mapping report (PDF): https://npdc.gov.ph/wp-content/uploads/2025/02/GIS-Group_Distribution-and-Thematic-Mapping-Report.pdf
4. 2024 tree distribution map (PDF): https://npdc.gov.ph/wp-content/uploads/2025/02/Inventory-Of-Trees.pdf
5. Western Section Development Plan (PDF): https://npdc.gov.ph/wp-content/uploads/2026/08/NPDC-Western-Section-Development-Project-PUBLIC.pdf
6. Four tree inventory PDFs and map folders listed in the downloadable-source catalog.

### Steps and acceptance checks

- Enumerate exact file links and filenames in each linked Drive folder before downloading; record inaccessible/ambiguous links without guessing.
- Check whether the binary already exists in the repository before any download. The catalog currently says several binaries are source-verified but not mirrored.
- Preserve the source binary when permitted, alongside URL, retrieval date, checksum, format, page count/image dimensions, licence/reuse statement, and attribution.
- Extract map labels into a source-linked feature index. Do not treat labels as accurate GIS geometry.
- Georeference a raster/PDF only if spatial features are needed. Record control points, CRS, residual error/RMSE and estimated positional uncertainty; do not present hand-digitized boundaries as surveyed.
- Compare park-area names and alignments with existing `ermita/rizal-park/park-area-inventory.csv` and any existing map feature index before appending. Keep source-specific names and aliases instead of silently replacing values.
- Output: preserved source assets where permitted, an index/manifest, and a QA report. No derived spatial layer should be called authoritative until positional quality has been checked.

## Work package B — Microsoft vs. OSM building-footprint comparison

### Existing inputs

- OSM: `ermita/maps/generated/ermita-building-details.geojson` and the other files named by `ermita/maps/generated/import-report.json`.
- Microsoft: `ermita/maps/external/ermita-microsoft-building-footprints.geojsonl.gz`.
- Reports: `ermita/maps/external/microsoft-building-footprints-import-report.json` and `ermita/maps/generated/import-report.json`.

First confirm the exact OSM building file path from the current tree/report; do not assume the detail GeoJSON is a complete raw OSM export.

### Comparison method

1. Read both local files; do not download either source again.
2. Validate geometry, coordinate order, invalid polygons and empty geometries. Record repair attempts separately.
3. Transform both layers into the same local metric CRS suitable for Manila (choose and document the EPSG based on AOI; retain source CRS in metadata).
4. Build spatial candidates with an R-tree/STRtree or equivalent.
5. For candidate pairs calculate polygon intersection-over-union (IoU), area ratio, centroid distance, and—where useful—Hausdorff/boundary distance.
6. Classify into:
   - likely match (high overlap and plausible area ratio);
   - partial/changed outline;
   - Microsoft-only candidate;
   - OSM-only feature;
   - ambiguous/overlapping complexes or building parts requiring review.
7. Use thresholds as triage only, not ground truth. Inspect samples across the AOI and compare permitted imagery/source records.
8. Keep source IDs and attributes from both providers. Do not merge building parts into whole buildings or treat adjacent footprints as duplicates without evidence.
9. Write a new comparison CSV/GeoJSON and a JSON report containing counts, thresholds, CRS, invalid geometry counts, match categories, and sample-review notes. Do not overwrite either input.
10. Only after QA, decide whether to create a separate reconciled derivative; preserve the source datasets unchanged.

### Licence checkpoint

The Microsoft Philippines release identifies ODbL. OSM is also ODbL. Keep attribution and review share-alike obligations for the resulting database. Record source lineage; do not assume the licence removes the need to verify each source's current terms.

## Work package C — LiDAR, DTM and aerial imagery availability

### Sources

- LiPAD / Phil-LiDAR: https://lipad.dream.upd.edu.ph/
- NAMRIA downloads: https://www.namria.gov.ph/downloads.aspx
- NAMRIA product information: https://namria.gov.ph/kiosk/namria03.htm
- OpenDronePH (PhilSA): https://philsa.gov.ph/open-drone-ph/

LiPAD describes DEM, DTM, orthophoto and classified LAZ products, but exact coverage and public redistribution permissions for Ermita are not established by the catalogue alone. OpenDronePH requires registration and a donor may impose restrictions. NAMRIA terms are product-specific.

### Steps and acceptance checks

- Query each source for tiles whose actual footprint intersects the project AOI; record exact tile IDs and coverage maps.
- Request/inspect metadata before requesting bulk files: acquisition date, horizontal resolution or point density, vertical datum, CRS, units, classification, processing lineage, no-data handling, and whether the elevation is DSM or bare-earth DTM.
- Record eligibility/account requirements, EULA/licence, permitted modification, public display and redistribution, attribution, and whether derived GLB/GeoTIFF can be committed.
- If a LiDAR tile is inaccessible or outside coverage, mark it as such rather than calling it imported.
- Do not replace Copernicus baseline until a higher-quality file is actually obtained, aligned, QA-checked and permitted.
- Prefer committing compact derived products and a complete manifest when the original point cloud/archive is too large or restricted; never omit provenance.

## Work package D — Audit existing KartaView imagery

### Inputs and rights

- Metadata: `kartaview/ermita-street-imagery-metadata.csv`, `.geojson`, `ermita-street-imagery-sequences.csv`.
- Building matches: `kartaview/ermita-real-facade-images.csv`.
- Report: `kartaview/ermita-real-facade-report.json`.
- Terms: https://kartaview.org/terms — imagery is described as CC BY-SA 4.0, with credit `© Grab and KartaView Contributors`.

### Audit steps

1. Reconcile photo IDs across metadata, facade CSV and downloaded files under `kartaview/images/`; count missing files, repeated IDs, duplicate URLs, broken paths and metadata-only records.
2. Confirm that every local image's filename maps to a unique photo ID and that the CSV status agrees with file existence.
3. Validate latitude/longitude ranges, capture dates, sequence IDs, image URLs and source attribution.
4. Segment the matches by distance-to-wall and heading-difference; flag missing heading, uncertain direction, large distance, stale capture dates and unclear building identity.
5. Treat `direction_checked` as a recorded status, not independent proof that the image is a true facade photograph. Sample visual inspection is still required.
6. Do not automatically map photos onto 3D walls. First make a review index (photo ID, building OSM ID/name, distance, heading difference, capture date, local file, decision).
7. Keep current image binaries unchanged during audit. Download new photos only for a clearly identified coverage gap and only after checking that the photo ID is not already indexed or present.
8. Keep required attribution and CC BY-SA terms with displayed or adapted imagery.

## Work package E — Documentation and consistency

- Current status has been reconciled in `ermita/maps/README.md`, `ermita/3d/README.md`, `ermita/3d/terrain/imagery-source-plan.md`, and `ermita/sources/street-building-source-tracker.md`.
- Continue to treat `ermita/sources/downloadable-source-catalog.md` as a link/acquisition register, not proof that all listed binaries are in Git.
- When any workflow changes files, update the relevant report and status docs in the same commit where feasible.
- Distinguish: source located; link tested; file downloaded; file committed; import validated; layer reconciled; licence verified.
- Do not copy outdated files from `backup/` over the current project. Backup snapshots are historical, not the source of truth.

## Recommended execution order

1. Audit local KartaView files and produce a no-download integrity report.
2. Run local Microsoft-vs-OSM footprint comparison and inspect representative matches/conflicts.
3. Enumerate and ingest NPDC map binaries not already present; extract labels and assess georeferencing quality.
4. Check LiPAD/NAMRIA/OpenDronePH coverage, request steps and terms; import only a confirmed, permitted dataset.
5. Review comparison reports and only then decide which derived layers should be integrated into the viewer.
