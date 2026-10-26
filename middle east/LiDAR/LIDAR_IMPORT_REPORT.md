# Jordan — building-useful LiDAR import audit

Last checked: 2026-10-26 06:04 UTC

## Decision

Satellite laser observations (GEDI and ICESat-2 ATL03/ATL06/ATL08) are not being imported by this workflow. Their sparse orbital footprints are not dense airborne/terrestrial point clouds and do not provide reliable building facades or complete roof surfaces. They are not a suitable substitute for the requested building-focused LiDAR.

This workflow is now audit-only until a source is verified to contain actual airborne or terrestrial LiDAR point clouds covering Jordan. It will not crawl global catalogs, download satellite observations, or count catalog JSON as imported data.

## Existing point-cloud files checked

- LAS/LAZ/COPC files found: 0
- Files with valid LASF signature and plausible size: 0

## What would be useful for building reconstruction

- Airborne/vehicle-mounted LiDAR point clouds (LAS/LAZ/COPC) with roof and building returns, preferably classified building points.
- Point density, coordinate reference system, acquisition date, vertical datum, and license must be recorded per dataset.
- A bare-earth DEM alone helps terrain placement but cannot reconstruct facades. GEDI/ICESat-2 samples may help broad vegetation/terrain research, but not the requested city building detail.

## Current result

No new LiDAR payloads were downloaded by this audit. Existing files were not deleted. A future import must first prove geographic overlap with Jordan and that the source is an airborne/terrestrial point cloud before downloading payloads.
