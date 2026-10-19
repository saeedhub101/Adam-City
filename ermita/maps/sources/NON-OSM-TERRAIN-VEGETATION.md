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

