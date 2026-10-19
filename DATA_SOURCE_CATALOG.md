# Adam-City — Master Data Source Catalog
**Audit date:** 2026-10-19  
**Scope:** repository files discoverable on `main`; focus on Ermita/Malate, Manila and Rizal Park.  
**Purpose:** one reference table for source, file location, content, evidence/status, limitations, and recommended use. This is an inventory, not a claim that every source has been visually verified or that all repository files are complete.

## 1. Building geometry and 3D building sources

> **Critical file-level audit finding (2026-10-19):** the active `ermita/maps/generated/ermita-building-footprints.geojson` is Basemap/OpenMapTiles-derived (1,123 features), not the original OSM dataset. The original OSM snapshot (1,533 features) survives at `backup/ermita/maps/generated/ermita-building-footprints.geojson`. The Basemap import script/workflow writes to the active OSM filename, and the height-audit report is stale against the active file. Read [`DATA_AUDIT_REPORT.md`](DATA_AUDIT_REPORT.md) before rebuilding the page. No source data was changed by the audit.

| Source/layer | Repository location or delivery method | What is available now | Coverage / evidence | Limitations and decision | Correct role in a clean rebuild |
|---|---|---|---|---|---|
| **OpenStreetMap (OSM) building footprints** | Preserved snapshot: `backup/ermita/maps/generated/ermita-building-footprints.geojson`. The active path with a similar name currently contains Basemap geometry, not the original OSM dataset. | Preserved OSM GeoJSON parses as **1,533 features**: 1,528 Polygon + 5 Point; original OSM IDs and raw tags retained. | Snapshot bounds are 120.9711465–120.9929367 E, 14.5736304–14.5963994 N, narrower than the full planned Malate/Ermita AOI. | **Do not treat the active `ermita/maps/generated/ermita-building-footprints.geojson` as pure OSM.** The Basemap import workflow overwrote that path. See `DATA_AUDIT_REPORT.md`. | Keep OSM and Basemap in separate files/layers. Restore the intended OSM snapshot only after confirming it is the correct source version, and expand the OSM AOI separately. |
| **OSM height / levels evidence** | `ermita/maps/qa/building-height-evidence.csv`; `ermita/maps/qa/building-height-evidence-report.json`; `ermita/maps/BUILDING-HEIGHT-COMPARISON.md` | These reports describe the preserved 1,528-polygon OSM snapshot, not the current active Basemap-derived footprint file. | Preserved OSM snapshot: **118** polygons with numeric `height`; **633** with levels but no height; **777** with neither. | **Stale relative to the active building file.** The report's `source_file` path now points to Basemap-derived geometry while its counts still match the OSM snapshot. Re-run the audit after source separation and include input SHA/count. | Keep source height, levels and rendered/estimated height distinct; regenerate report against an explicit OSM file path. |
| **Basemap / OpenFreeMap / OpenMapTiles buildings** | Current file: `ermita/maps/generated/ermita-building-footprints.geojson`; generator: `scripts/import_basemap_buildings.py` | Actual file parses as **1,123 features**: 595 Polygon + 528 MultiPolygon; 1,048 features lack an OSM feature ID; 5 duplicate IDs detected. File size 17,882,142 bytes. | Actual bounds 120.959129–121.025734 E, 14.540718–14.626441 N, extending outside the stated working AOI; importer records 12 tiles at zoom 14 and does not clip geometry to the AOI. | **This is currently the active building file and it has overwritten the OSM file at the same path.** Most features are Basemap geometry, not OSM geometry. The import workflow explicitly commits the replacement to `main`. | Keep Basemap geometry in a separate path and layer. Never use it as the OSM source or as an AOI-clipped dataset without a separate clipping/QA step. See `DATA_AUDIT_REPORT.md`. |
| **Microsoft / Bing building footprints** | No active footprint dataset confirmed in the current repository. Retired scripts include `ermita/scripts/import_microsoft_building_footprints.py` and `ermita/scripts/prepare_microsoft_building_footprints.py`. | No accepted Microsoft geometry available for a fair current geometry comparison | Repository policy and source tracker explicitly say Microsoft/Bing footprints were rejected as inaccurate and removed. | **Not available as an active comparison layer.** Some old script text still references the former path `ermita/maps/external/ermita-microsoft-building-footprints.geojsonl.gz`; that reference does not prove the data file exists. Do not revive/re-import without explicit project-owner reversal. | Mark as rejected/unavailable in comparison tables. Do not imply a live Microsoft layer or quote old counts as current coverage. |
| **Named building / special façade treatments** | `index.html`; guidance in `ermita/3d/README.md` | Some source-specific and procedural façade styling exists in the web preview; Manila Residences Bocobo (OSM `way/90123959`) is documented as a photo-informed example | One documented case uses an approximate 102 m override based on a 34-storey listing; OSM’s 18 m tag conflicted with that evidence | Not a survey measurement. Most window bands, shopfronts, doors and roof trim are procedural approximations, not measured architectural components. | Keep hand-verified landmark overrides in a separate explicit registry with evidence URL, OSM ID, confidence and estimated/measured status. |
| **Downloaded 3D building models / model leads** | Example: `ermita/buildings/ramon_magsaysay_building.glb` was mentioned in prior repository documentation; leads are listed in `ermita/3d/KARTAVIEW_FACADE_AUDIT.md` | Audit lists Ramon Magsaysay Center, WWW Residences, Ermita Center Building and Midland Plaza Hotel as leads | The audit explicitly says these are leads and files still need acquisition/alignment before integration | A model lead/link is not proof that a correctly aligned local model is present. Export report says independently recentered procedural GLBs were not fused due to missing original transforms. | Inventory actual model files and transforms before using them. Match each model to a known footprint and coordinate origin. |

## 2. Streets, paths, businesses, accessibility and government road data

| Source/layer | Repository location | What is available now | Reported coverage | Limitations / role |
|---|---|---|---|---|
| **OSM raw cached extract** | `ermita/maps/generated/ermita-osm-raw.json` | Cached OSM source used by the road exporter and related exports | Road export report says 8,040 source elements | Cached snapshot, not live updates. Preserve as source data and do not repeatedly fetch if already present. |
| **OSM roads and paths** | `ermita/maps/generated/ermita-road-network.geojson`; report `ermita/maps/generated/road-network-export-report.json` | Real OSM way-node coordinates represented as line geometry | **1,445 ways**; **366 named**, **1,079 unnamed**; no degenerate ways skipped. Includes footways, paths, pedestrian ways, service roads, steps and motor-road classes. | These are centerlines, **not** road-surface polygons, lane-level geometry, sidewalks as complete surfaces, or surveyed road widths. Names only appear where OSM has names. |
| **Street index** | `ermita/streets/street_segments.csv`; `ermita/streets/street_names.csv`; `ermita/streets/README.md` | Tables indexing road segments and street names | Segment table is documented as indexing the same 1,445 OSM ways | Indexes are not an independent geometry source. Verify row counts/duplicates and link every row back to source IDs. |
| **OSM business/place points** | `ermita/maps/generated/ermita-businesses.csv` | Place records with OSM feature ID, name, geometry type, coordinates, tags, source and licence | Actual CSV is present; exact row count not asserted in this audit | OSM completeness varies. Names/brands/hours are community-mapped and may be outdated. Use as mapped POIs, not proof of current operation. |
| **OSM accessibility features** | `ermita/maps/generated/ermita-accessibility.csv` | Crossings and accessibility-related records are present | Actual CSV is present; exact row count not asserted in this audit | Mapped attributes may be incomplete or dated. Keep survey dates/source tags. |
| **DPWH national road network** | `ermita/maps/external/dpwh-national-roads-ermita.geojson` | Clipped DPWH road geometry | Import report: **286 features**; source vintage August 2026 | Official national-road layer; does not replace OSM local-street coverage. Use to cross-check classification/attributes. |
| **DPWH road surface type** | `ermita/maps/external/dpwh-road-surface-type-ermita.geojson` | Clipped surface-type geometry/attributes | Import report: **990 features**; source vintage January 2026 | Vintage and coverage may differ from local road network; not a complete road-surface mesh. |
| **DPWH number of lanes** | `ermita/maps/external/dpwh-number-of-lanes-ermita.geojson` | Clipped lane-count references | Import report: **939 features**; source vintage June 2020 | Older than other DPWH layers; attribute matching/alignment must be checked before using for exact lanes. |
| **DPWH bridge inventory** | `ermita/maps/external/` and `ermita/maps/external/dpwh-road-bridge-batch-import-report.json` | Fourth DPWH source is included in the successful 4-source import report | Report says all **4 of 4** attempted sources imported; inspect its bridge entry for exact output path/count | Bridge inventory only represents bridges included in the source inventory. Do not treat absence as proof no bridge exists. |
| **Street names / signs / starter records** | `ermita/data/README.md`; `ermita/data/streets/`, `ermita/data/signs/`, `ermita/data/initial-place-records.csv` (paths as described in README) | Category structure and starter/candidate tables are documented | Data README explicitly warns some tables are candidate records and store/sign tables may be empty schemas | Empty templates are not collected data. Distinguish candidate, imported, reviewed and verified records. |

## 3. Imagery, terrain, façade photos and park source assets

| Source/layer | Repository location / delivery | What is available now | Status and limitations | Correct role |
|---|---|---|---|---|
| **Esri satellite imagery** | Streamed online in the preview when enabled | Aerial imagery can be displayed from an online service | Imagery is **not embedded as local repository assets**. Terms differ from OSM; streamed imagery must not be assumed redistributable or usable as a local texture pack. | Visual context/reference only unless the provider terms authorize a specific use. |
| **KartaView street-level photos and metadata** | `kartaview/images/`; `kartaview/ermita-real-facade-images.csv`; `kartaview/ermita-real-facade-report.json`; `kartaview/ermita-street-imagery-metadata-report.json`; audits at `kartaview/ermita-facade-image-audit.md` and `ermita/3d/KARTAVIEW_FACADE_AUDIT.md` | Audit reports **246** unique photo IDs in CSV, **238** rows marked downloaded and paths present, **239** image files (one unreferenced image); 238 photo references linked to 132 OSM IDs in the separate facade audit | **0 visually verified building-to-facade matches** in the current audit. Nearby position/heading alone does not prove which wall is shown. Keep imagery out of automatic facade projection until reviewed. Attribution and CC BY-SA 4.0 terms are documented. | Candidate evidence for manually verified facades; do not automatically stretch a street photo around a whole building. Do not redownload existing IDs. |
| **Copernicus DEM GLO-30** | `ermita/3d/terrain/ermita-copernicus-dem-cropped.tif`; `ermita/3d/terrain/terrain-import-report.json` | Cropped GeoTIFF with 20,412 valid elevation cells | Nominal **30 m** resolution; bbox approx. 120.965–121.005 E, 14.560–14.605 N; elevations recorded about -9.13 to 32.70 m. It is a **DSM**, not a bare-earth DTM; may include buildings/vegetation. | Regional terrain context only, not curb/sidewalk microtopography or engineering-grade elevations. |
| **Copernicus-derived terrain mesh** | `ermita/3d/terrain/ermita-terrain-surface.glb` | Triangulated terrain output documented in import report | Report: 20,412 valid cells; separate export report notes 20,412 vertices and 40,250 triangles. Approximate surface based on DEM. | Use as terrain mesh only after coordinate origin and vertical offset are aligned with buildings/roads. |
| **NPDC / Rizal Park reference assets** | `ermita/rizal-park/source-data/npdc-assets/`; import report `ermita/rizal-park/source-data/npdc-assets/import-report.json` | Download report records NPDC technical map (2024), brochure (2021), GIS distribution/thematic report (2025), and other park documents | Assets are reference documents, not automatically georeferenced/vectorized geometry. NPDC download page says public domain unless otherwise stated; check each file for exceptions. | Use to verify park layout and features; digitize only with a documented georeferencing/QA process. |
| **Mapillary references embedded in OSM tags** | Examples exist in `ermita/maps/generated/ermita-accessibility.csv` | Some OSM features carry Mapillary IDs/position metadata | These are references/tags, not proof that original imagery is downloaded or licensed for reuse in this repository. | Keep as source links unless separate access and reuse terms are confirmed. |

## 4. Other government / institutional sources and their actual status

| Source | Current status in source tracker / manifest | What is not yet established |
|---|---|---|
| **Geoportal Philippines** | Candidate catalogue/services documented in `ermita/3d/source-manifest.csv` and `ermita/sources/street-building-source-tracker.md` | No verified, imported Ermita-wide building-footprint dataset confirmed by the current tracker. A visible map layer is not proof of downloadable data or permission to redistribute. |
| **NAMRIA** | Candidate topographic, elevation and orthophoto products documented | Exact AOI coverage, resolution, acquisition date, download availability, fees and reuse terms not confirmed. |
| **LiPAD / Phil-LiDAR** | Request/access path documented in source manifest | Ermita coverage, registration/approval and delivered datasets are not confirmed. |
| **Manila City Government** | Official records identified as a potential source | No citywide public building GIS package confirmed in the source tracker. |
| **NHCP historical registry** | Registry URLs documented | A complete extracted dataset with verified geometry/photo reuse rights is not confirmed. |
| **OSM2CDR Manila 3D** | Candidate source listed in `ermita/3d/source-manifest.csv` | Not marked downloaded; exact Ermita coverage and terms need checking. Extruded volumes are not measured facades. |
| **Google maps / imagery** | No accepted local imagery dataset documented in this inventory | Do not claim a Google imagery/building dataset is imported. Access/API and redistribution terms must be confirmed before use. |

## 5. Existing 3D export and application/build files

| Asset | Path | Recorded contents / status | Caveat |
|---|---|---|---|
| **Combined GLB export** | `ermita/3d/exports/adam-city-complete.glb` | Report `ermita/3d/exports/adam-city-complete-report.json` records 1,487 buildings, 1,437 road segments, 20,412 terrain vertices and 40,250 terrain triangles | The report describes a geometry export of source layers, not a screen capture. Esri tiles are not embedded. Heights may use a 9.6 m fallback; road widths are estimates. Check the actual GLB file exists before claiming it is downloadable/current. |
| **Single-page map preview** | Root `index.html`; deployment workflow `.github/workflows/deploy-ermita-preview.yml` | GitHub Pages workflow copies `index.html` to `_site/index.html` and deploys it | Workflow's configured path filters include the page and two principal GeoJSON files. A committed code change is not proof the published page has deployed or passed visual QA. |
| **GLB export workflow** | `.github/workflows/adam-city-export-glb.yml` | Workflow configuration for exporting the GLB is present | Artifact existence/size and latest run outcome must be checked separately. Never treat workflow artifact alone as durable repository storage. |
| **Backups/checkpoints** | Search results show `backup/` and `checkpoints/road-texture-before/` | Older copies of scripts/docs/data and a prior HTML checkpoint are still discoverable | These can be stale and inconsistent with `main`. They are not the authoritative live data. Per project preference, do not use them as an import source or recreate backups automatically. |

## 6. Cross-source building comparison summary

| Comparison dimension | OSM | Basemap / OpenMapTiles | Microsoft/Bing |
|---|---|---|---|
| Building geometry is a committed local dataset | **Yes** — GeoJSON | **No** — streamed vector tiles from style | **No accepted dataset** |
| Reported feature/footprint count | 1,533 total features; 1,528 polygon/multipolygon footprints in current audit | No complete local count; current loaded tiles are viewport-dependent | Not comparable; source rejected and removed |
| Stable source identifiers/tags | OSM IDs and tags retained | Tile properties/IDs depend on provider schema and tile encoding | No current dataset to inspect |
| Building height evidence | 118 explicit numeric heights; 633 levels-only; 777 neither | May expose rendered height/min-height in tile properties; values/style can change | Not available |
| Exact facade texture, windows, signage | Not generally supplied by footprint tags; some candidate tags/place-specific evidence | Basemap extrusion is not a real facade photograph/model | Not available |
| Appropriate status in a rebuilt page | **Primary footprint layer** | **Separate comparison/display layer only** | **Rejected / disabled** |
| Key caution | Incomplete tags and unknown heights | Never replace the whole OSM dataset with currently loaded tiles | Do not imply active coverage or restore without explicit approval |

## 7. Data quality and rebuild rules

1. **Do not delete or overwrite source datasets during the inventory/rebuild.** Keep source files, cleaned outputs, derived geometry and presentation layers separate.
2. Use `main` only. Inspect existing repository files first; do not re-import data that is already present.
3. Never make a partial viewport query stand in for a full-area dataset.
4. Every feature should retain source ID, source name, original tags/properties, source URL, retrieval date, licence/attribution and transformation history where available.
5. Separate measured/source-provided facts from estimates: explicit height, storey count, inferred display height, procedural windows, guessed roof shape and manually verified façade must not share one unlabeled field.
6. Keep OSM and Basemap as independent layers/toggles. Do not reactivate Microsoft footprints based on stale script references.
7. Keep roads, sidewalks, curbs, crossings and road-surface polygons as distinct geometry concepts. OSM centerlines are not asphalt/sidewalk surfaces.
8. KartaView images remain candidate references until a human verifies the exact building and wall. Esri tiles remain streamed imagery unless licensed local assets are explicitly acquired.
9. Treat old backups/checkpoints as historical references only, not live sources.
10. Before building a new page, run a file-existence/schema/count/extent audit for each layer, then validate alignment and visibility per layer. Record failures and exact counts in a QA report rather than claiming success from code inspection alone.

## 8. Existing supporting documentation

- `DATA_ASSET_POLICY.md`
- `ermita/maps/README.md`
- `ermita/maps/BUILDING-HEIGHT-COMPARISON.md`
- `ermita/3d/README.md`
- `ermita/3d/source-manifest.csv`
- `ermita/3d/building-data-source-investigation.md`
- `ermita/sources/street-building-source-tracker.md`
- `ermita/data/README.md`
- `kartaview/ermita-facade-image-audit.md`
- `ermita/3d/KARTAVIEW_FACADE_AUDIT.md`

**Audit boundary:** this catalog is based on repository documentation, reports, source-code references and files successfully read during the audit. It is deliberately explicit where a file/count, live deployment, source access, license or visual alignment has not been verified.
