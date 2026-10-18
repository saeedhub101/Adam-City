# Ermita named-place and street starter inventory

**Status:** Sourced starter records, not a complete directory. Names and district membership must be checked against boundaries and current records before assigning coordinates.

## Street and road names to map

These names appear in published maps and/or descriptions of the Ermita–Rizal Park area. Map the actual road geometry and segment names from an openly licensed geographic source rather than tracing a copyrighted commercial map.

| Name | Record type | Notes for mapping | Source |
|---|---|---|---|
| Roxas Boulevard | Road | Major boulevard along Manila Bay; map segments and crossings separately | https://www.openstreetmap.org/relation/103706 |
| Taft Avenue | Road | Important north–south corridor; nearby institutions should be geocoded individually | https://talapamana.ncca.gov.ph/index.php/component/content/article/works-of-national-artists-architecture?Itemid=101&catid=15 |
| Padre Faura Street | Road | Named in published descriptions of the Ermita civic/institutional area | https://www.visitphilippines.org/discover-it/manila/southern-districts/ermita/ |
| T.M. Kalaw Street | Road | Road adjacent to the Rizal Park / National Library area | https://www.visitphilippines.org/discover-it/manila/southern-districts/ermita/ |
| United Nations Avenue | Road | Important Ermita corridor; map intersection and transit features from current open data | https://www.openstreetmap.org/relation/103706 |
| Padre Burgos Avenue / P. Burgos Street | Road | Name forms vary by segment/source; preserve source spelling and verify current map naming | https://npdc.gov.ph/contact-us/ |
| Ayala Boulevard | Road | Near the civic complex; verify exact segments within the project boundary | https://www.openstreetmap.org/relation/103706 |
| Pedro Gil Street | Road | Border/nearby corridor toward Malate; include only segments falling inside chosen coverage | https://www.openstreetmap.org/relation/103706 |

## Named institutions, landmarks, and heritage records to geocode

| Name | Category | What is supported by source | Source |
|---|---|---|---|
| Rizal Park (Luneta / Bagumbayan) | Historic site / public park | NHCP registry lists Rizal Park (Bagumbayan) Historical Site in Ermita, Manila | https://philhistoricsites.nhcp.gov.ph/labels/manila/page/7/ |
| National Museum complex | Museums / civic buildings | National Museum project document locates the complex in Rizal Park, Ermita | https://www.nationalmuseum.gov.ph/wp-content/uploads/2021/09/BidDocs-NMC-P1-Final.pdf |
| Philippine General Hospital (PGH) | Hospital / heritage building | NCCA heritage entry describes PGH on Taft Avenue, Ermita, Manila, and records its founding and opening history | https://talapamana.ncca.gov.ph/index.php/component/content/article/works-of-national-artists-architecture?Itemid=101&catid=15 |
| Philippine Normal University | University / historic institution | Listed in the NHCP registry under Ermita/Manila search results; verify current entrance and campus footprint | https://philhistoricsites.nhcp.gov.ph/province/ermita-manila/ |
| United Nations Plaza | Public space / historic site | Listed in the NHCP registry with location Ermita, Manila | https://philhistoricsites.nhcp.gov.ph/province/ermita-manila/ |
| Luneta Hotel | Heritage building | Listed in the NHCP registry's Ermita label results; exact address and current use need a dedicated record | https://philhistoricsites.nhcp.gov.ph/labels/ermita/ |
| Elks Club Building Historical Landmark | Heritage building | Listed by NHCP with location Ermita, Manila | https://philhistoricsites.nhcp.gov.ph/province/ermita-manila/ |
| Army and Navy Club Building | Heritage building | Listed in NHCP's Ermita label results | https://philhistoricsites.nhcp.gov.ph/labels/ermita/ |
| Church of San Vicente de Paul | Religious building / heritage | Listed in NHCP's Ermita label results; verify exact location and official current name | https://philhistoricsites.nhcp.gov.ph/labels/ermita/ |
| Old Planetarium / NPDC offices | Park administration | NPDC gives its office address as the Old Planetarium, Rizal Park, Luneta, P. Burgos Street, Manila | https://npdc.gov.ph/contact-us/ |
| Quirino Grandstand | Monumental/event structure | NPDC includes it in its western-section Rizal Park landmark list used in this project | https://npdc.gov.ph/rizal-park/ |
| Musical Dancing Fountain | Park feature | NPDC includes it in the park landmark information; map location and operating schedule separately | https://npdc.gov.ph/rizal-park/ |
| Rizal Monument | Monument | NPDC includes it in park landmark information; record monument geometry separately from nearby paths/plaza | https://npdc.gov.ph/rizal-park/ |
| National Library of the Philippines | Library / public institution | Identified in published descriptions of the Rizal Park/Ermita area; verify current address and building footprint | https://www.visitphilippines.org/discover-it/manila/southern-districts/ermita/ |

## How to expand this list safely

1. Use the NHCP National Registry to search the district and capture each individual registry record, its official title, category, location, declaration date/marker text when available, and source URL.
2. Use NPDC park maps and its tree inventory downloads for park-specific geometry and individual-tree records.
3. Use OpenStreetMap/Overpass for streets, buildings, paths, amenities, entrances, and public transport tags; retain OSM element IDs, tags, coordinates/geometry, retrieval date, and attribution.
4. Add a separate record for each building or feature. Do not treat a campus or complex as one building when the source provides multiple structures.
5. Add a location-confidence field with values such as confirmed-in-boundary, near-boundary, or needs-review until a point or footprint is checked against the selected Ermita boundary.
6. For hospitals, emergency services, transit, opening hours, phone numbers, and accessibility, verify against the organization's own current website or authoritative government data.

## Boundary caution

“Ermita” can mean a barangay/district area, a general neighborhood, or a tourism area described loosely. Some institutions and road segments near Rizal Park sit close to boundaries or are described as “Manila” rather than specifically “Ermita.” Keep a boundary reference and do not silently include nearby Intramuros or Malate features as if their district membership were confirmed.
