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
