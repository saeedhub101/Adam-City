# Ermita Streets and Buildings — Source Tracker

Scope: Ermita, Manila, Philippines. Priority: street names and geometry, building footprints, addresses, street features, and verified heritage buildings.

## Source status

| Source | Target data | Access / reuse status | Next action |
|---|---|---|---|
| OpenStreetMap (OSM) | Named streets, road geometry, building footprints, addresses, mapped street features | Downloadable; ODbL applies. Include attribution and comply with share-alike obligations for adapted databases. | Export the Ermita boundary and features to GeoJSON/CSV; record extract date and query. |
| Geoportal Philippines | Government road layers and other available geospatial layers | Layer-by-layer; a visible map layer does not guarantee public download or unrestricted redistribution. | Search the catalog for NCR/Manila road and building layers; record each layer's terms. |
| NAMRIA | Topographic maps and digital road-map products sourced from DPWH | Free map downloads are available; digital road data may require a request/order. Verify product terms before rehosting. | Contact NAMRIA (oss@namria.gov.ph) and ask for road GIS data covering Ermita, format, cost, and redistribution terms. |
| DPWH | Official road network and road classifications | Publicly downloadable complete GIS data not yet confirmed. | Request Metro Manila road vector data, including road names/classification and available attributes; ask for licence/redistribution permission. |
| Manila City Government | Local streets, building/use/planning layers, addresses, permits or local asset data | Open downloadable GIS dataset not yet confirmed. | Search city planning/open-data pages and request GIS layers from the appropriate city office. |
| NHCP National Registry | Verified heritage buildings/sites, descriptions, marker details, locations | Public registry pages are available; NHCP states its site content is public domain unless otherwise stated. Individual images/third-party items may have separate terms. | Compile Ermita heritage entries into a source-linked CSV; preserve the registry URLs and transcription date. |

## Primary links

- OSM Ermita boundary relation: https://www.openstreetmap.org/relation/103706
- OSM copyright/licence: https://www.openstreetmap.org/copyright
- OSM Overpass API: https://overpass-api.de/
- Geoportal Philippines: https://www.geoportal.gov.ph/
- NAMRIA downloads and road-map FAQ: https://namria.gov.ph/downloads.aspx
- DPWH: https://www.dpwh.gov.ph/
- Manila City Government: https://manila.gov.ph/
- NHCP Ermita registry: https://philhistoricsites.nhcp.gov.ph/province/ermita-manila/
- NHCP National Registry: https://memory.nhcp.gov.ph/historical-sites/

## Import rules

1. Prioritize real data exports over summaries/catalogs.
2. Save raw source data separately from cleaned/normalized datasets.
3. For each import, record source URL, access date, geographic coverage, licence/terms, attribution, fields, and any transformations.
4. Do not label a dataset as downloaded until the actual file is committed.
5. Do not rehost map tiles, Google Maps content, or Street View imagery unless the specific terms permit it.
6. Preferred formats: GeoJSON for geometry; CSV for tabular records; original ZIP/SHP/GPKG when redistribution is allowed.

## Current import status

No new street/building GIS files have been imported by this tracker commit. This file records the acquisition path; datasets will be marked imported only after the actual source files are obtained and checked.
