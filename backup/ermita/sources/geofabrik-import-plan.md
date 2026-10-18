# Geofabrik data plan for Ermita and Rizal Park

## Why use Geofabrik?

Geofabrik distributes extracts of OpenStreetMap (OSM) data. It does not provide an official city survey, and coverage depends on what OSM contributors have mapped. Its Philippines download page offers:

- Raw OSM PBF extract (latest at research time: approximately 582 MB; country-wide).
- GIS-ready Shapefile archive (approximately 1.3 GB).
- GIS-ready GeoPackage archive (approximately 1.4 GB).
- Historical dated extracts, daily change files, and tag statistics.

Source: https://download.geofabrik.de/asia/philippines.html
General format and licensing notes: https://www.geofabrik.de/en/data/download.html

## Recommended workflow

**Do not commit the entire Philippines extract to this GitHub repository.** It is large and contains data far outside the project area. Download it locally or in a GIS environment, extract the Ermita area using the chosen boundary, then commit only the relevant small-area export and its metadata.

### Candidate feature layers

| Layer | OSM tags / data to retain | Project use |
|---|---|---|
| Roads | `highway=*`, `name`, `ref`, `surface`, `lanes`, `oneway`, `bridge`, `tunnel`, `lit`, `sidewalk` when present | Named streets, paths, intersections, road types |
| Buildings | `building=*`, `name`, `addr:*`, `height`, `building:levels`, `heritage`, `wikidata` when present | Building footprints, names, addresses, recorded heights |
| Places / amenities | `amenity=*`, `shop=*`, `tourism=*`, `office=*`, `craft=*`, `leisure=*`, `historic=*` | Hospitals, clinics, schools, police/fire, shops, hotels, attractions |
| Public transport | `public_transport=*`, `highway=bus_stop`, `railway=station`, `railway=tram_stop`, `route=*` relations where available | Stops, stations, terminals and mapped routes |
| Pedestrian access | `highway=footway/path/pedestrian/steps/crossing`, `kerb`, `ramp`, `wheelchair` when present | Walking network and accessibility review |
| Park and greenery | `leisure=park/garden`, `landuse=grass/forest`, `natural=tree/wood`, tree species tags where mapped, benches, toilets, drinking water, shelters | Park limits, green areas, facilities, mapped trees |
| Water and terrain | `natural=water`, waterways, water features | Lakes, ponds, fountains/water features if mapped |
| Boundaries | Administrative boundary relation and local area polygons | Clip data to a defined project boundary |

Not every listed tag will be present in the Geofabrik thematic files. The raw PBF generally preserves more OSM tags and geometry than the simplified thematic export. Check the export schema before assuming a field exists.

## Preferred file formats

- **GeoPackage (.gpkg):** best practical choice for multiple GIS layers in one file; suitable for QGIS.
- **GeoJSON:** useful for small clipped datasets and Git diffs, but avoid one enormous file.
- **CSV:** use for tabular points of interest and non-spatial inventories; include coordinates and OSM IDs.
- **PBF (.osm.pbf):** keep as an external source/download, not in the Git repository; process with Osmium or similar tools.
- **Shapefile:** supported widely, but field names and data types can be limited; prefer GeoPackage when possible.

## Data fields to preserve

For each imported feature, retain as applicable:
- OSM element type and ID (for example, way/123456 or node/789012)
- Geometry and coordinate reference system
- Original OSM tags (or a documented selected subset)
- Feature type / project category
- Source dataset and exact download URL
- Download date and dataset timestamp
- OSM attribution and ODbL license notice
- Project boundary version and clipping method
- Verification status and notes
- Separate official source or field-verification reference when available

Do not invent a name when OSM has no name tag. Preserve raw source spelling and distinguish mapped values from editorially normalized names.

## Geographic extraction

The free Geofabrik extract is for the **whole Philippines**, not a dedicated Ermita clip. A suitable next operation is to use the official project boundary or a carefully reviewed boundary polygon to clip the national dataset. Keep a buffer around the district when extracting roads and transit connections, then classify which features are within the boundary and which are nearby. This prevents roads or entrances crossing the boundary from being cut off.

Potential tools:
- QGIS: https://qgis.org/
- Osmium: https://osmcode.org/osmium-tool/
- Geofabrik downloads: https://download.geofabrik.de/asia/philippines.html

## Licensing and attribution

Geofabrik states that its downloadable OSM-derived data is available under the Open Database License (ODbL 1.0), with OpenStreetMap attribution required; derived databases must retain the applicable license. Include attribution such as:

> © OpenStreetMap contributors; data extract distributed by Geofabrik; licensed under ODbL 1.0. Source: https://www.openstreetmap.org/copyright

Review ODbL obligations before publishing a derived database or combining it with other datasets. Do not mix proprietary Google Maps data into the OSM-derived database.

## Coverage limitations and complements

Geofabrik/OSM will not reliably provide all building owners, exact floor counts, opening hours, current phone numbers, indoor layouts, every tree species, all park facilities, or complete historical facts. Fill gaps with:
- NPDC official maps, park inventories, and tree spreadsheets: https://npdc.gov.ph/downloads/
- NHCP heritage registry: https://philhistoricsites.nhcp.gov.ph/database/
- Official institutional websites and government records
- Field notes and photographs made by the project team, where legally and ethically appropriate

## Import checklist

- [ ] Download current Philippines extract and record its timestamp.
- [ ] Select/verify the Ermita boundary; keep a buffer for connected roads.
- [ ] Extract road, building, POI, transit, pedestrian, green-space, water and boundary layers.
- [ ] Save a GeoPackage for GIS use and smaller CSV/GeoJSON exports for Git review.
- [ ] Count features by layer and report records without names or addresses.
- [ ] Validate geometry and remove duplicates without deleting source IDs.
- [ ] Add OSM/Geofabrik attribution and ODbL licensing notes.
- [ ] Compare park features with NPDC official sources.
- [ ] Record missing coverage and avoid claiming exhaustive completeness.
