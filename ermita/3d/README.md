# Ermita 3D Map Collection

Goal: build a source-traceable 3D model of Ermita, Manila, with more detail for Rizal Park. Geometry should come from documented geographic sources, not an AI-generated guess.

## Priority: real geographic geometry before decorative 3D detail

The current reliable base is the actual mapped geometry in OpenStreetMap plus the supplementary Microsoft building-footprint snapshot. The dedicated OSM road/path centerline layer is `../maps/generated/ermita-road-network.geojson` (1,445 mapped ways from the current cached OSM source); its segment index is `../streets/street_segments.csv`. For buildings, use the OSM footprint layer and the 12,132 Microsoft outline candidates as separate source layers, then adjudicate overlaps. Do not present procedural windows, doors, signboards, or generic extrusions as surveyed/photorealistic real buildings. Until verified façade/height data is available, prioritize correct road layout and building footprints, and label extruded heights as estimated or unknown.

## Real-geometry inspection and height evidence

- Open `../maps/preview.html` for an interactive 2D inspection of the actual OSM road centerlines and mapped building polygons before evaluating 3D output.
- Use `../maps/qa/building-height-evidence.csv` and its report to distinguish explicit source height tags from level counts and unknown heights. Never silently convert levels to meters or fill missing heights with guessed values.
- Microsoft footprints remain a separate outline candidate layer and are not automatically fused with OSM. The first-pass comparison under `../maps/qa/` must be reviewed before creating a merged building layer.

## Data already imported or generated

- **OSM map/building features:** `../maps/generated/import-report.json`; 1,533 building/building-part features are reported in the current OSM export.
- **Microsoft/Bing building footprints:** `../maps/external/ermita-microsoft-building-footprints.geojsonl.gz`; 12,132 AOI-clipped features, with limitations documented in `../maps/external/microsoft-building-footprints-import-report.json`.
- **DPWH road/bridge references:** four clipped layers under `../maps/external/`; see `dpwh-road-bridge-batch-import-report.json`.
- **Procedural building facade details:** `generated/ermita-buildings-facade-details.glb` and `generated/facade-details-report.json`. The report describes 1,468 polygon parts, 234,990 window panels, 6,390 door placeholders and 1,802 named signboard placeholders. These are procedural placeholders, not surveyed architecture.
- **Extruded buildings:** `generated/ermita-buildings-extruded.glb`.
- **Terrain:** `terrain/ermita-copernicus-dem-cropped.tif` and `terrain/ermita-terrain-surface.glb`, documented by `terrain/terrain-import-report.json`. The source is Copernicus DEM GLO-30, nominally 30 m, and is a DSM rather than bare-earth DTM.
- **Street-level image index:** `../../kartaview/ermita-street-imagery-metadata.csv` and related GeoJSON/sequence files; facade matches are indexed in `../../kartaview/ermita-real-facade-images.csv`.

## Planned outputs and provenance

- Source building footprints with source IDs and tags.
- A reconciled building-footprint layer that keeps source provenance and does not silently replace conflicting outlines.
- Building heights from actual source attributes where available; any inferred heights must retain an explicit estimation method.
- Streets and paths with source and attribute provenance.
- Permitted elevation and imagery products, or a manifest that records why restricted products cannot be mirrored.
- glTF/GLB or other 3D exports when file size and licensing allow.

## Known limitations and gaps

- Microsoft footprints date from imagery acquired in 2016–2020 and do not include facades, signs, or guaranteed names.
- OSM coverage and building tags are uneven. The OSM and Microsoft building layers have not yet been systematically matched, deduplicated, or adjudicated.
- Procedural windows, doors and signboards are placeholders. Their presence is not evidence of measured facade geometry, exact lettering, or true logos.
- KartaView images are not automatically calibrated or projected onto building walls.
- Copernicus terrain is regional context, not street-level survey data and not suitable for engineering, drainage design, or flood-safety decisions.
- High-resolution LiDAR/DTM and aerial imagery for this exact AOI have not yet been verified as accessible under terms that permit project redistribution.

## Candidate and request-based sources

1. OpenStreetMap / Geofabrik: https://download.geofabrik.de/asia/philippines.html and https://www.openstreetmap.org/copyright
2. Geoportal Philippines: https://geoportal.gov.ph/ — inspect individual layer metadata; a viewer is not proof of download rights.
3. NAMRIA elevation, topographic and orthophoto products: https://www.namria.gov.ph/downloads.aspx — confirm coverage, resolution, cost and reuse terms per product.
4. LiPAD / Phil-LiDAR: https://lipad.dream.upd.edu.ph/ — request/check tiles for the AOI and confirm account eligibility and terms.
5. OpenDronePH: https://philsa.gov.ph/open-drone-ph/ — registration is required and donor restrictions may apply.
6. Microsoft/Bing Open Building Footprints: https://github.com/microsoft/IdMyPhBuildingFootprints — already imported for this AOI; do not download it again merely to repeat the same import.

## Modelling and licensing rules

- Keep source geometry, source IDs, source date, CRS and transformations traceable.
- Do not label estimated heights as measured.
- Do not infer roof, facade, or interior geometry from a 2D footprint alone.
- Keep DEM/terrain separate from building geometry.
- Do not mix datasets with incompatible reuse conditions; preserve source-specific attribution and review ODbL share-alike obligations for derived databases.
- Keep original source files unchanged. Record every cleaned/merged derivative and its QA counts.
- Check repository size limits; use appropriate external artifact storage for large permitted source archives.
