# Terrain and aerial-imagery expansion plan

## Terrain: imported and verified in repository

The current `terrain-import-report.json` records a successful Copernicus DEM GLO-30 import retrieved on 2026-10-18. The repository contains:

- `ermita-copernicus-dem-cropped.tif` — cropped elevation raster.
- `ermita-terrain-surface.glb` — triangulated surface for 3D viewing.
- `terrain-import-report.json` — source, extent, nominal resolution, valid cells, elevation range, attribution and limitations.

The report records a 30 m nominal grid, 20,412 valid elevation cells, and a crop of 162 rows by 126 columns. The values are a regional surface model, not a survey. Copernicus DEM is a **digital surface model (DSM)** and may include buildings and vegetation; it is not a bare-earth DTM and is not suitable for engineering, drainage design, or flood-safety decisions. Keep it separate from building geometry.

The script `ermita/scripts/import_copernicus_terrain.py` has a GLO-90 fallback if GLO-30 cannot be read in a future run. A later workflow may update the outputs/report; always inspect the latest report rather than assuming the fallback or current resolution.

## High-resolution LiDAR / DTM: not yet verified for this AOI

LiPAD / Phil-LiDAR describes DEMs, DTMs, orthophotos and classified LAZ as available product types, but the presence of those product categories does not prove that a suitable tile covers Ermita or that the tile can be redistributed publicly. Start with the portal's data-request path: https://lipad.dream.upd.edu.ph/

For each candidate tile, verify:

- footprint intersects the project AOI and covers the intended park/building area;
- acquisition date, horizontal resolution, vertical datum, CRS, units, nodata and processing lineage;
- whether the product is DSM, DTM, point cloud, orthophoto or a derivative;
- account/eligibility requirements, licence/EULA, public display and redistribution rights;
- whether derived meshes can be committed, or only referenced by a manifest.

Do not replace the current Copernicus files until a better product is actually obtained, validated, and permitted for the intended use.

## Aerial imagery: permitted-source path

### Philippine Space Agency OpenDronePH

Official portal: https://philsa.gov.ph/open-drone-ph/

OpenDronePH supports contributed drone imagery and derived products, including orthomosaics. Registration is required; donors may specify restrictions. Search/request a dataset for Ermita/Rizal Park and record the donor, spatial footprint, capture date, resolution, CRS, terms, attribution and redistribution permission before importing. Source access does not automatically imply unrestricted reuse.

### NAMRIA

Official product information: https://namria.gov.ph/kiosk/namria03.htm

NAMRIA lists specialized IfSAR/LiDAR terrain products and orthophoto/orthoimage products. Coverage, resolution, cost and redistribution permissions must be confirmed per product. Preserve written permission or licence terms and do not publish restricted imagery.

### Other imagery

Do not bulk-copy Google Maps, Google Street View, or other proprietary map imagery. KartaView street images have CC BY-SA 4.0 terms according to its terms page; retain the required credit, `© Grab and KartaView Contributors`, and comply with share-alike conditions: https://kartaview.org/terms

## Acceptance checks before a dataset becomes a project input

1. Confirm the actual spatial footprint covers the intended AOI.
2. Verify date, pixel size/point density, CRS, vertical datum (for elevation), nodata and processing history.
3. Confirm use, modification, public-display and redistribution rights.
4. Preserve source attribution and licence metadata in derived outputs.
5. Compare imagery/terrain against stable mapped landmarks; report alignment errors instead of silently shifting data.
6. Store large or restricted originals outside Git if necessary, while committing a traceable manifest and QA report.

## Current status as of 2026-10-18

- Copernicus DSM and its 3D mesh: **imported; regional accuracy only**.
- High-resolution LiDAR/DTM for Ermita: **not yet confirmed**.
- High-resolution aerial orthophoto for Ermita: **not yet imported or confirmed under reusable terms**.
- OpenDronePH and NAMRIA: **candidate/request path; coverage and terms need product-level verification**.
