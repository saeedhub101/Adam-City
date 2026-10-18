# Source Register

This register prioritizes primary/public sources and records what each can contribute. A source listing is not proof that its files have already been downloaded or imported.

| Source | URL | Expected contribution | Collection notes / cautions |
|---|---|---|---|
| OpenStreetMap (OSM), Ermita boundary relation | https://www.openstreetmap.org/relation/103706 | Boundary relation and linked mapped features; street names, road/path geometry, building footprints/names, amenities, transport and points of interest where mapped | Community-maintained and incomplete. Preserve OSM attribution and comply with ODbL. Relation ID should be checked against current tags and geometry before use. |
| OpenStreetMap copyright/licence | https://www.openstreetmap.org/copyright | Required attribution and ODbL terms | Review obligations before redistributing an extracted database or derivative database. |
| OSM Overpass API | https://overpass-api.de/ | Query selected features inside the Ermita boundary and Rizal Park coverage | Query carefully, respect service limits, save query text and retrieval date. Do not assume every OSM object is complete or current. |
| National Parks Development Committee (NPDC) downloads | https://npdc.gov.ph/downloads/ | Official Rizal Park map and brochure; tree inventory downloads; tree distribution/thematic maps; related park documents | Record the exact file, version/date, licence/permission and geographic coverage. The page lists a 2024 Rizal Park Luneta Tree Inventory download. |
| NPDC Rizal Park page | https://npdc.gov.ph/rizal-park/ | Official park context and named features | Use for official names/context; verify individual geometry from maps or geospatial sources. |
| NPDC tree inventory | https://npdc.gov.ph/inventory-of-trees/ | Tree categories, species information and park tree-map context | The site reports a total of 679 in its tree-inventory heading, while other category counts and map pages have their own scope. Do not treat summary counts as a geocoded list until the downloadable files are inspected. |
| Geoportal Philippines | https://www.geoportal.gov.ph/ | Searchable government geospatial layers, potentially including topography, land use, public facilities and hazard layers | Availability, access, data format and reuse terms vary by layer/agency; log each layer individually. |
| NAMRIA | https://namria.gov.ph/ | Official national mapping, geodetic/topographic and other reference products | Check product-specific access and licence/permission; not all products are open downloads. |
| Manila government sources | https://manila.gov.ph/ | Official city information and public-service/institution references | Use official pages/directories where available; a directory entry alone may not supply coordinates. |
| Philippine government open-data portal | https://data.gov.ph/ | Potential public datasets from government agencies | Search by agency, Manila, health, education, transport, land use and hazards; inspect metadata and licences before reuse. |

## Source acquisition record

For every downloaded dataset, record:

- Source name and publisher
- Exact page and direct file URL (when available)
- Retrieval date (ISO 8601)
- Source publication/update date, if stated
- File name, format, size and checksum when practical
- Geographic coverage and coordinate reference system
- Licence, attribution text, and redistribution restrictions
- Data transformations performed
- Known omissions, uncertainty and validation results

## Priority order

1. Obtain OSM data for the district boundary and mapped features.
2. Inspect and acquire NPDC park map, brochure and available tree inventory/distribution files.
3. Search Geoportal Philippines and NAMRIA for suitable official reference layers.
4. Add official institutional/service directories for features not adequately covered by geospatial data.
5. Cross-check and normalize records without erasing source provenance.
