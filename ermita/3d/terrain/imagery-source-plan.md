# Terrain and aerial-imagery expansion plan

## Terrain import configured

The automated workflow now runs `ermita/scripts/import_copernicus_terrain.py` after the OSM import. It tries the public Copernicus DEM GLO-30 cloud-optimized GeoTIFF tile for Manila first, then GLO-90 as a fallback. If neither tile can be read, it records a failure report and preserves the successful OSM import rather than breaking the whole workflow.

Expected outputs, only when a source tile is reachable:
- `ermita-copernicus-dem-cropped.tif`: cropped/resampled elevation raster for the Ermita/Rizal Park vicinity
- `ermita-terrain-surface.glb`: simple triangulated terrain surface for 3D viewing
- `terrain-import-report.json`: chosen source, resolution, valid-cell count, elevation range, attribution and limitations

The Copernicus DEM is a **digital surface model (DSM)** and may include buildings and vegetation. Its 30 m / 90 m grid is regional context, not street-level topography and not suitable for engineering, drainage design or flood-safety decisions. Keep the elevation surface separate from the OSM-extruded building model.

## Aerial imagery: permitted-source path

### Philippine Space Agency OpenDronePH
Official portal: https://philsa.gov.ph/open-drone-ph/

OpenDronePH is a repository for contributed drone imagery and derived products such as orthomosaics. Access/use requires registration; each dataset may carry donor-specific restrictions. Before importing a dataset, record the contributor, geographic footprint, capture date, resolution, coordinate reference system, licence/permission, attribution and any redistribution limits. Only ingest an Ermita/Rizal Park product after its actual metadata and permissions have been checked.

### NAMRIA
Official product and service information: https://namria.gov.ph/kiosk/namria03.htm

NAMRIA lists IfSAR/ LiDAR terrain products and orthophoto/orthoimage products among its specialized offerings. These may require purchase or a formal request; do not assume they are openly downloadable. If acquired, retain the receipt/permission and usage terms in the source manifest and do not publish restricted source imagery.

## Acceptance checks before a dataset becomes a project input

1. Confirm that its spatial footprint covers Ermita or Rizal Park.
2. Verify date, pixel size, CRS, vertical datum (for elevation), nodata and any processing history.
3. Confirm reuse, modification, public-display and redistribution rights.
4. Preserve source attribution and licence metadata in derived outputs.
5. Compare imagery/terrain against mapped streets and landmarks; flag alignment errors instead of silently shifting data.
6. Do not scrape or bulk-republish Google Maps or Street View imagery.

## Current status

The workflow and terrain script are committed. The terrain files themselves are **not confirmed yet**; inspect `terrain-import-report.json` after the next successful workflow run. No high-resolution aerial imagery has been downloaded by this project yet.
