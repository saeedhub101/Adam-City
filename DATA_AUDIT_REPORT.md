# Adam-City Repository Data Audit

**Audit date:** 2026-10-19  
**Branch inspected:** `main` only  
**Purpose:** verify the committed data files themselves, not just documentation. This audit did not alter or delete any source dataset.

## Executive result

**Critical finding: the active building-footprints path is not currently the original OSM dataset.** It contains Basemap/OpenMapTiles-derived geometry. The original OSM GeoJSON still exists under `backup/`, but the active path used by the page has been overwritten.

This is not merely a documentation mismatch:

- Active file: `ermita/maps/generated/ermita-building-footprints.geojson` — **17,882,142 bytes**, 1,123 polygon/multipolygon features, metadata explicitly says Basemap-authoritative geometry.
- Preserved OSM file: `backup/ermita/maps/generated/ermita-building-footprints.geojson` — **631,703 bytes**, 1,533 features: 1,528 polygons and 5 points, with OSM IDs and raw tags.
- The active file has 1,048 of 1,123 features without an OSM feature ID; only 75 have an `osm_feature_id`. It also has 5 duplicate feature identifiers in the inspected properties/IDs.
- The active file's coordinate bounds are `[120.959129, 14.540718, 121.025734, 14.626441]`, which extend well beyond the stated working AOI `[120.965, 14.555, 121.005, 14.605]`. The importer is not clipping the result to that AOI.
- The OSM file in `backup/` has bounds `[120.9711465, 14.5736304, 120.9929367, 14.5963994]`. It is an Ermita-centred extract and does not span the full planned Malate/Ermita working rectangle.

The repository's `DATA_ASSET_POLICY.md` says OSM is the active footprint source and datasets must not be silently replaced. The current import script and workflow contradict that policy: `scripts/import_basemap_buildings.py` writes directly to the active OSM filename, and `.github/workflows/import-basemap-buildings.yml` commits the replacement to `main`.

## 1. Building data: actual file-level comparison

| Check | Active footprints file | Preserved OSM file in backup | Audit result |
|---|---|---|---|
| Path | `ermita/maps/generated/ermita-building-footprints.geojson` | `backup/ermita/maps/generated/ermita-building-footprints.geojson` | Different datasets at different paths |
| Size | 17,882,142 bytes | 631,703 bytes | Active file is about 28 times larger |
| Declared source | OpenFreeMap/OpenMapTiles vector tiles; OSM attributes only where matched | OpenStreetMap contributors | Active file is not pure OSM |
| Feature count | 1,123 | 1,533 | Not a like-for-like count |
| Geometry types | 595 Polygon + 528 MultiPolygon | 1,528 Polygon + 5 Point | Active dataset has no points |
| Features with OSM building tags | 1,123 | 1,528 polygon footprints | Tag presence in active file does not prove OSM geometry |
| Features lacking `osm_feature_id` | 1,048 | 0 | Active file loses source identity for most features |
| Explicit numeric height fields | 1,123 have generated Basemap height metadata | 118 OSM polygons have a numeric `height` tag | These counts mean different things; Basemap render height is not an OSM survey tag |
| Levels tags | 65 | 743 polygons have `building:levels` | Active file retains only a subset of the original OSM levels evidence |
| Duplicate IDs | 5 duplicate IDs detected in the active file's available ID properties | 0 detected | Active data needs ID reconciliation |
| Coordinate bounds (W,S,E,N) | 120.959129, 14.540718, 121.025734, 14.626441 | 120.9711465, 14.5736304, 120.9929367, 14.5963994 | Active extent extends outside intended project rectangle; OSM extract is narrower than full planned AOI |
| Basic polygon-ring closure check | 0 unclosed Polygon rings found | 0 unclosed Polygon rings found | Ring closure passes; this does not prove polygon validity, correct building identity or alignment |

### Height audit status

The files `ermita/maps/qa/building-height-evidence-report.json`, `ermita/maps/qa/building-height-evidence.csv`, and `ermita/maps/BUILDING-HEIGHT-COMPARISON.md` report **1,528 OSM polygons**, including 118 with a numeric height, 633 with levels but no height, and 777 with neither. These numbers match the preserved OSM file in `backup/`.

**They do not describe the active 1,123-feature Basemap-derived file.** The report's `source_file` points to the active path, but its recorded counts correspond to the older OSM dataset. Therefore the report is stale relative to the active file and should not be used as if it validates the current active geometry.

## 2. Why the active file was replaced

The inspected script `scripts/import_basemap_buildings.py` declares its output as:

```text
ermita/maps/generated/ermita-building-footprints.geojson
```

Its docstring says it will replace local OSM footprints with Basemap footprints. The workflow `.github/workflows/import-basemap-buildings.yml` runs on a manual dispatch and on pushes affecting the importer/workflow, then stages and commits that same file to `main`.

**Required correction before rebuilding the page:** store Basemap output at a separate path such as `ermita/maps/external/ermita-basemap-building-footprints.geojson`; keep OSM at its own active path; update the page and audit scripts to load each source independently. Do not merge the two into one source file or label Basemap geometry as OSM.

The retired Microsoft-building workflows/scripts are intentionally disabled. This audit did find a separate Microsoft road-detections file, `ermita/maps/external/ermita-microsoft-road-detections.geojson`, containing 2,626 line features. That is road-detection data, not Microsoft building footprints, and must not be presented as building coverage.

## 3. Roads and DPWH files: actual parsed counts

| Dataset | Path | Actual feature count | Geometry types | Coordinate bounds (W,S,E,N) | What it represents |
|---|---|---:|---|---|---|
| OSM roads and paths | `ermita/maps/generated/ermita-road-network.geojson` | 1,445 | 1,445 LineString | 120.9713186, 14.5687053, 120.992146, 14.5975376 | OSM way centre-lines, not asphalt or sidewalk surface polygons |
| DPWH national roads | `ermita/maps/external/dpwh-national-roads-ermita.geojson` | 286 | 277 LineString, 9 MultiLineString | 120.9602967, 14.555, 121.005, 14.61 | Official national-road references |
| DPWH road surface type | `ermita/maps/external/dpwh-road-surface-type-ermita.geojson` | 990 | 984 LineString, 6 MultiLineString | 120.9602967, 14.555, 121.005, 14.61 | Road-segment surface attributes, not rendered road-surface polygons |
| DPWH number of lanes | `ermita/maps/external/dpwh-number-of-lanes-ermita.geojson` | 939 | 932 LineString, 7 MultiLineString | 120.9602967, 14.555, 121.005, 14.61 | Lane-count references; source vintage is June 2020 |
| DPWH bridge inventory | `ermita/maps/external/dpwh-bridge-inventory-ermita.geojson` | 61 | 61 Point | 120.9614318, 14.5621871, 121.0047560, 14.6094245 | Bridge inventory points, not bridge meshes |

The four DPWH files parse as GeoJSON and their observed feature counts agree with the import report. OSM roads also parse as GeoJSON. These checks do not establish that the road lines perfectly align with building edges or that DPWH segment attributes can be joined to every OSM segment.

## 4. KartaView imagery and facade evidence

| Dataset | Path | Verified file-level status | Interpretation |
|---|---|---|---|
| Street-image metadata | `kartaview/ermita-street-imagery-metadata.csv` | 20,767,791 bytes; report records 4,996 metadata records | Metadata catalogue, not 4,996 downloaded image binaries |
| Street-image point GeoJSON | `kartaview/ermita-street-imagery-metadata.geojson` | 25,802,138 bytes; report records 4,996 Point features | Capture locations/sequences, not verified building facades |
| Facade-candidate CSV | `kartaview/ermita-real-facade-images.csv` | Audit records 246 unique photo IDs, 238 marked downloaded and 238 referenced local image paths present | Candidate association only; exact wall/building identity has not been visually verified |
| Local images | `kartaview/images/` | Earlier tree audit found 239 image files, including one image not referenced by the facade CSV | Do not delete the unreferenced image without checking all manifests |
| Facade crops | `kartaview/facade-crops/manifest.csv`, `manifest.json` | Crop manifests are present | Presence of a crop does not prove correct UV alignment or exact facade match |

The repository audit document explicitly states that the facade matching audit did not inspect every image pixel, EXIF record, camera calibration, or exact wall identity. Do not automatically project candidate street photos onto building models.

## 5. Terrain, GLB and freshness mismatches

| Asset | Path | Verified status | Audit concern |
|---|---|---|---|
| DEM | `ermita/3d/terrain/ermita-copernicus-dem-cropped.tif` | File exists, 61,631 bytes | Reported nominal 30 m surface model; not curb-level terrain |
| Terrain mesh | `ermita/3d/terrain/ermita-terrain-surface.glb` | File exists, 728,704 bytes | Requires common coordinate origin/vertical alignment with road and building meshes |
| Complete GLB | `ermita/3d/exports/adam-city-complete.glb` | File exists, 2,525,432 bytes | Its report says 1,487 buildings and 1,437 road segments, while current active building source has 1,123 features and current road file has 1,445 ways. Export is not demonstrably regenerated from the currently active inputs; treat as potentially stale until rebuilt and compared |
| Facade-details GLB | `ermita/3d/generated/ermita-buildings-facade-details.glb` | File exists, 66,146,492 bytes | Large generated asset; report and coordinate transforms need to be checked before use |
| Ramon Magsaysay building GLB | `ermita/buildings/ramon_magsaysay_building.glb` | File exists, 2,702,072 bytes | Presence alone does not prove alignment with its map footprint |

The complete GLB report itself says streamed Esri imagery is not embedded and that procedural facade placeholders were not fused because their transforms could not be safely aligned.

## 6. Repository structure and workflow risks

- The inspected recursive Git tree contains **1,829 tracked files** in total, including the historical `backup/` subtree and many image files.
- The `backup/` tree contains useful older source data and large generated assets, but it is not the active source of truth for the website.
- The root `index.html` is 67,996 bytes. The deployment workflow publishes this page and the page loads the committed building and road GeoJSON paths.
- The Basemap import workflow can overwrite the active building-footprints path. This is the most important workflow/data-integrity risk found.
- The Microsoft building-footprint importer and comparison workflow are retired as documented. Microsoft road-detections remain a separate dataset.
- A commit or a file existing in the tree does not prove the published Pages deployment has completed or that the browser displays all geometry correctly. Visual QA has not been performed as part of this repository-file audit.

## 7. Recommended order of repair

1. **Protect and restore source separation:** preserve the original OSM extract as OSM; put Basemap geometry in a separate file/path. The old OSM file is still available at `backup/ermita/maps/generated/ermita-building-footprints.geojson`, but should be copied back only after the owner confirms that the preserved snapshot is the intended source version.
2. Generate an AOI-clipped Basemap dataset separately, recording its zoom, tile list, feature count, extent and matching method.
3. Regenerate height QA against the exact file named in each report; embed the input file SHA and feature count in every report so stale reports are detectable.
4. Expand/refresh the OSM extract to cover the agreed Malate/Ermita AOI; do not infer completeness from the existing central-Ermita bbox.
5. Compare source layers independently using per-feature source IDs, spatial intersection/IoU and nearest-centroid diagnostics. Keep unmatched features instead of silently dropping them.
6. Rebuild the GLB from the explicitly selected source versions, then verify feature counts, extents and shared coordinates against its inputs.
7. Only after the data audit passes, rebuild the page from a clean layer architecture: OSM footprints, Basemap footprints, roads, DPWH references, terrain and imagery each remain separate toggles.
8. Run browser visual QA at the same extent and zoom for each layer, record screenshots/results, and verify the actual GitHub Pages deployment before claiming the page is fixed.

## Scope and limitations

This audit parsed the full active building GeoJSON, preserved OSM GeoJSON, OSM roads GeoJSON and the four DPWH GeoJSON files via their committed Git blobs. It also checked tracked file paths/sizes and inspected relevant source scripts, reports and workflows. It performed basic JSON, geometry-type, bounding-box, ID and polygon-ring-closure checks, **not** a full GIS topology validation, independent image-by-image review, browser screenshot test, or live deployment check.
