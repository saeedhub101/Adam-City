# Ermita + Rizal Park data acquisition register

**Purpose:** track real, source-backed datasets needed for a comprehensive geographic inventory. This is a working collection log, not a claim that every feature has already been imported.

**Last reviewed:** 2026-10-18

## Highest-priority source collections

| Collection | Primary source | What it can contribute | Current state | Next import / validation |
|---|---|---|---|---|
| Rizal Park 2024 tree inventory | https://npdc.gov.ph/downloads/ | Individual tree records; reported fields include tree number, common/scientific name, height, DBH, coordinates, and risk/classification | Source located; individual-tree rows not yet imported | Retrieve original spreadsheet/PDF, preserve IDs and units, convert to CSV, validate coordinates and duplicates |
| Other park tree inventories | https://npdc.gov.ph/downloads/ | Bachelor's Garden, Kanlungan ng Sining, Noli Me Tangere Garden, Western Section | Download links located; source files not yet imported | Import each inventory separately, retain source/date, check spatial overlap |
| Tree distribution and risk maps | https://npdc.gov.ph/downloads/ | Native, exotic, fruit-bearing, thematic and inventory maps | Report notes and links exist; spatial features not extracted | Check for GIS files/spreadsheets; georeference PDFs only if needed and record method/error |
| Roads, paths, buildings and amenities | https://www.openstreetmap.org/relation/103706 | Reusable OSM features and geometry where mapped | Starter records only; full clipped OSM export not imported | Export all available OSM features for Ermita and park buffer; preserve OSM IDs, tags, geometry, timestamp and attribution |
| Official historical/heritage properties | https://philhistoricsites.nhcp.gov.ph/province/ermita-manila/ | Declared sites, markers, dates and official descriptions | Several known records listed | Traverse registry entries; normalize names and designations; geocode entries only with evidence |
| National Museum complex facilities/site plans | https://www.nationalmuseum.gov.ph/ and https://weblinks.nationalmuseum.gov.ph/wp-content/uploads/2024/11/16091703/Bidding-Documents-99-1.pdf | Building/facility names and labeled roads, parking, loading and landscape areas | One official plan example located; not digitized | Extract labeled names; digitize geometry only when placement is reliable |
| Healthcare and emergency services | https://manila.gov.ph/ and https://www.openstreetmap.org/ | Hospitals, clinics, pharmacies, police/fire, contact details | Starter records only | Create facility-by-facility data; cross-check official directories and label time-sensitive details |
| Schools and government offices | https://www.deped.gov.ph/ ; https://ched.gov.ph/ ; https://manila.gov.ph/ | Institution names, addresses, points and campus extents where published | Some named institutions recorded | Import mapped records and cross-check institutional directories |
| Public transport | https://www.openstreetmap.org/ plus official operator sources | LRT stations, entrances, stops, terminals, crossings and pedestrian access | Known nearby station references only | Import route/station/stop features and verify current service status |
| Shops, restaurants and street-level services | https://www.openstreetmap.org/ | Named POIs, categories and addresses where tagged | Starter examples only | Import all tagged POIs within boundary; de-duplicate and flag missing fields |
| Park furniture and amenities | https://npdc.gov.ph/ and https://www.openstreetmap.org/ | Toilets, benches, bins, signs, fountains, play/chess facilities and mapped paths | Named areas and landmarks recorded; object-level inventory incomplete | Extract mapped features; use official park maps and field survey records for unmapped objects |
| Historical photos and street-level references | Official archives and https://www.google.com/maps/search/?api=1&query=Rizal+Park%2C+Manila%2C+Philippines | Contextual visual verification and links to imagery | Reference links only | Store links, attribution, capture date and viewpoint; do not bulk-copy Google imagery or treat visual estimates as survey measurements |

## Tree dataset: known scope and interpretation

NPDC's tree inventory page (https://npdc.gov.ph/inventory-of-trees/) and public species list (https://npdc.gov.ph/inventory-of-trees-2/) are primary sources. The 2024 distribution map (https://npdc.gov.ph/wp-content/uploads/2025/02/Inventory-Of-Trees.pdf) reports 1,084 native trees and palms in mapped western and central sections, with reported counts of Narra (413), Manila Palm (159), and Molave (151). Do not conflate these map totals with web-page category counters: scope and counting method may differ and require reconciliation against the original downloadable inventory.

The file npdc-published-tree-name-index.csv transcribes names shown on NPDC's public species list by category. It is a name/category index, **not a count of individual trees**. Scientific names and families are blank unless independently verified; local names and ambiguous labels require taxonomic review. Category overlap may occur, so category totals must not be added to estimate unique species.

A third-party article describes the downloadable NPDC tree dataset as including individual tree IDs, common/scientific names, height, DBH, coordinates and risk ratings: https://onedayisangbagay.substack.com/p/data-surprisingly-hidden-plain-sight-inventory-trees-luneta-rizal-paco-park. Treat this as a discovery lead; the original NPDC download must be the source of record.

## Geographic and completeness rules

1. Define Ermita's administrative boundary separately from Rizal Park's operational boundary.
2. Keep each source's original ID, URL, retrieval date, licence, date/version and geometry.
3. Preserve unknown values as blank/null; distinguish not mapped, not published, not checked and not applicable.
4. Absence from a map does not prove that a real-world feature is absent.
5. For every layer, report imported record count, duplicates, geometry failures, source coverage and unresolved gaps.
6. For individual trees, do not invent IDs or coordinates or estimate DBH, height, health, defects or risk from imagery without labeling the method and observation date.
7. OSM data is under the Open Database License; include attribution and review share-alike obligations before redistribution. Reference Google Maps/Street View by links rather than bulk-copying.

## Current status

- [x] Source-linked starter place CSV
- [x] Starter roads/buildings/institutions research
- [x] Park area inventory
- [x] NPDC tree-mapping report notes
- [x] NPDC-published tree name/category index
- [ ] Import all rows from the original NPDC 2024 tree inventory
- [ ] Import other NPDC area-specific tree inventories
- [ ] Import full OSM road/path/building/amenity/POI geometries for Ermita
- [ ] Reconcile park and Ermita boundaries
- [ ] Import and geocode NHCP registry records relevant to Ermita
- [ ] Build verified healthcare, emergency, education, government and transit inventories
- [ ] Digitize park features and amenities from official maps where source quality permits
- [ ] Publish coverage/QA summaries per dataset

This status records progress without claiming an import that has not been performed.
