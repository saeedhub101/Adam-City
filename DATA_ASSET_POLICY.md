# Data and generated-asset retention policy

**Project rule:** when we import, download, derive, or generate a reusable project asset, keep the asset in this repository whenever its size, format, and license permit. Do not leave the only copy in a temporary session or rely on an undocumented remote URL.

## Required workflow for every asset

1. Save the actual file under a descriptive project path (usually `ermita/maps/external/`, `ermita/maps/generated/`, `ermita/3d/`, or `ermita/rizal-park/`).
2. Save a machine-readable import/generation report beside it, including source URL/provider, retrieval/generation date in UTC, source vintage where known, geographic extent/CRS, resolution or scale, transformation steps, checksum where practical, license/terms, attribution, and limitations.
3. Update the relevant README or source-layer register so the file can be discovered and reused.
4. Validate geometry/schema, file size, and provenance before wiring the asset into the live preview. Keep original source files where permitted and create separate derived outputs rather than overwriting the source.
5. Commit generated code, configuration, scripts, small preview assets, and data that can legally be redistributed. Prefer compressed GeoJSON, GeoPackage, Cloud Optimized GeoTIFF, GLB, or other suitable formats where appropriate.

## Licensing and hosted imagery exception

Repository retention is a strong default, **not permission to copy any third-party content**. Before committing raster tiles, aerial imagery, basemaps, photographs, models, or datasets, check the source license and redistribution/download terms. Record the result in the report. If redistribution or bulk downloading is not clearly allowed, do not mirror the content into GitHub. Instead, commit the acquisition script/configuration and metadata, keep the source service URL, and identify the access/credential requirements. Prefer an openly licensed or public-domain source that explicitly permits downloading and redistribution when a durable local copy is required.

### Current Esri World Imagery layer

The map currently requests Esri World Imagery tiles at runtime for visual comparison. These are **streamed from Esri and are not stored in this repository**. The Esri terms state that service content is not public domain and that the terms do not automatically grant redistribution rights; the special “World Imagery (for Export)” item is designed for export/offline use and requires an ArcGIS Online subscription or developer account. Do not scrape or bulk-copy ordinary display tiles into the repository. If an authorized export workflow is used later, keep its terms/authorization evidence and export metadata with the imagery.

References checked 2026-10-18:
- Esri Web Site and Service Terms: https://www.esri.com/en-us/legal/terms/web-site-service
- World Imagery (for Export): https://www.arcgis.com/home/item.html?id=226d23f076da478bba4589e7eae95952

## Existing project examples

- OpenStreetMap extracts and derived GeoJSON are committed with source/license information; credit © OpenStreetMap contributors and comply with ODbL.
- Microsoft building footprints are retained as a compressed source extract with import and comparison reports. They are supplemental outlines, not verified current buildings or official cadastral data.
- Copernicus DEM crop and GLB terrain mesh are retained with a report describing DSM type, resolution, attribution, and limitations.
- DPWH layers are retained alongside a per-layer source and vintage report.

## Checklist before marking an import complete

- [ ] Actual reusable file is in the repository, or the licensing reason it cannot be stored is documented.
- [ ] Source URL/provider and retrieval time are recorded.
- [ ] License/attribution and source vintage are recorded.
- [ ] Extent, CRS, resolution/scale and transformations are recorded when applicable.
- [ ] Validation summary and limitations are recorded.
- [ ] Relevant README/source register is updated.
- [ ] Preview uses the committed asset when legally and technically appropriate, rather than an undocumented temporary copy.
