# Non-OSM terrain and vegetation imports

This pipeline deliberately does not query OpenStreetMap or an OSM-derived provider.

## Planned / generated outputs

- `sources/terrain/srtm-1arcsec-ermita.tif`: clipped elevation raster for the detailed Ermita / Rizal Park area, derived from the public AWS Terrain Tiles SRTM archive.
- `sources/landcover/esa-worldcover-2021-10m-ermita.tif`: clipped 10 m ESA WorldCover 2021 v200 raster.
- `sources/landcover/vegetation-grass-classes-ermita.geojson`: derived polygons for tree cover, shrubland, grassland, cropland, bare/sparse vegetation, wetlands, mangroves and moss/lichen.
- `qa/non-osm-terrain-landcover-report.json`: source URLs, output sizes, processing status, and warnings.

The import is incremental: valid existing outputs are reused, and files are never overwritten. If a source download fails, its failure is reported without deleting other outputs.

## Limitations

- SRTM is elevation terrain data, not building heights; in a low-relief urban area it may not represent kerbs, sidewalks or small embankments.
- ESA WorldCover is a 10 m land-cover classification from 2021. It can identify broad grass/tree/vegetation areas, not individual blades of grass, small planters or exact current landscaping.
- This workflow does not invent building footprints, facade textures, window layouts, roof geometry or logos. No verified non-OSM building/facade dataset for the Ermita area has been imported by this workflow yet.
- Attribution for WorldCover: © ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium.
- Terrain source and attribution: https://registry.opendata.aws/terrain-tiles/
- WorldCover data and license: https://esa-worldcover.org/en/data-access

## Building footprints from an independent satellite source

- **Google Research Open Buildings v3** is stored separately at `google-open-buildings/google-open-buildings-v3-ermita.geojson`.
- The verified import retained **7,443 footprint detections** for the Ermita/Rizal Park area; **3,550** have confidence scores of at least 0.80. The source archive itself is processed in temporary CI storage and is not committed.
- Source imagery/detection vintage: May 2023. The dataset contains polygon footprints and confidence/area metadata, **not** measured heights, facade photos, window positions, shop signs, or roof materials.
- Attribution and terms: Google Research Open Buildings v3, CC BY 4.0. See https://sites.research.google/gr/open-buildings/ and https://creativecommons.org/licenses/by/4.0/.

## Local display layers

- The map now has a **Google building footprints** checkbox. It draws confidence-colored outlines/fills for visual comparison; it does not merge these polygons into the existing building dataset.
- The map has a **Local SRTM relief** checkbox for a transparent hillshade PNG generated from the stored SRTM raster.
- The **Grass / vegetation** checkbox shows ESA WorldCover classes. It is a 10 m, 2021 classification, not a survey of individual plants.
- OpenAerialMap: one CC-BY-4.0 orthophoto was retained with its metadata and preview under `ermita/maps/external/openaerialmap/`. Other candidate imagery with incompatible/unclear licenses or very large file sizes was not downloaded.

## Non-OSM scope clarification

New import jobs do not query OpenStreetMap. Existing project files and the current OpenFreeMap/OSM-derived basemap have been retained rather than destructively removed; the site is therefore **not yet completely independent of OSM in its display layer**. This distinction is intentional so existing work is not lost while independent sources are collected and compared.

## Additional independent building source under import

- Microsoft/Bing satellite-derived Philippines footprints have been imported separately from Google Open Buildings v3.
- The source archive was 1,189,283,353 bytes compressed for the entire Philippines. It stayed in temporary CI storage; only **1,765 polygons** intersecting the Ermita/Rizal Park project bounds were committed under `sources/microsoft-satellite-buildings/` (about 1.04 MB).
- The original retired importer remains untouched; this is a separate, area-clipped import path. The new source is independent of OSM data, although Microsoft licenses the database under ODbL.
- Dataset information and license: https://github.com/microsoft/IdMyPhBuildingFootprints



## Cross-source building identity audit

- A spatial crosswalk was generated at `ermita/maps/qa/non-osm-building-footprint-crosswalk.csv`.
- Matching used polygon intersection-over-union of at least 0.25 and centroid separation no greater than 18 m.
- Current audit: **1,032 probable Google/Microsoft matches**, **6,411 Google-only or geometry-conflict detections**, and **733 Microsoft-only or geometry-conflict detections**.
- These are candidate identity matches, not a declaration that either geometry is always correct. Both original source files remain unchanged, and the crosswalk records disagreements rather than replacing one footprint with the other.
- Full report: `ermita/maps/qa/non-osm-building-footprint-reconciliation-report.json`.

## Canonical satellite building register

- `ermita/maps/qa/non-osm-building-canonical-register.geojson` is the unified display register containing **8,176 records** after the 1,032 probable matches are represented once.
- For matched records, the Google polygon is used only as the canonical display geometry because it carries a confidence score and has a newer documented detection vintage; the Microsoft observation and overlap metrics remain attached as metadata.
- The original Google and Microsoft GeoJSON source files are untouched. Records without a confident match remain source-specific and are flagged for review instead of being silently discarded.
- The canonical register is available in the preview through the lazy-loaded **Unified satellite building register** checkbox, so the additional 8.9 MB file is not downloaded until requested.

## Licensed facade-reference photo catalog

- `ermita/buildings/reference_photos_catalog.json` indexes **33 licensed photos** and their local file paths, Commons pages, attribution and license terms.
- Current location review labels 18 as likely Ermita/Malate-area candidates, 9 as Manila context/outside-or-unverified area, and 6 as nonlocal references. Nonlocal images were retained, not deleted, but marked as unsuitable for direct target-building assignment.
- The catalog is a research index only. It does not claim that a photo belongs to a specific footprint and does not project photos onto building façades automatically.
- Searches for Robinsons Place Manila, Manila Residences Bocobo, 7-Eleven, park grass and local hotels returned no verified filename-matched photo in the latest run; those buildings still need a better-matched licensed photo source or manual confirmation.

