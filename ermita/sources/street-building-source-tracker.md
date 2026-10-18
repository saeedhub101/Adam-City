# Ermita Streets and Buildings — Source Tracker

Scope: Ermita, Manila, Philippines. Priority: street names and geometry, building footprints, addresses, street features, and verified heritage buildings.

**Status reviewed:** 2026-10-18. An imported layer is not necessarily complete, current, or reconciled with other sources.

## Source status

| Source | Current repository state | Licence / reuse notes | Next action |
|---|---|---|---|
| OpenStreetMap (OSM) | Imported clipped feature set at `ermita/maps/generated/`; current report records 8,040 elements, 7,825 GeoJSON features and 1,533 building/building-part features | ODbL; attribution and share-alike obligations apply | Preserve IDs/tags; verify coverage; compare footprints against Microsoft data without replacing OSM records |
| Microsoft/Bing Open Building Footprints | Imported `ermita/maps/external/ermita-microsoft-building-footprints.geojsonl.gz`; 12,132 features in rectangular AOI | ODbL; source imagery vintage 2016–2020; supplemental non-government dataset | Spatially match against OSM, quantify overlap and conflicts, and validate unmatched candidates before any merge |
| DPWH road / bridge services | Four clipped GeoJSON files: 286 national-road features, 990 road-surface features, 939 lane-count features and 61 bridge features | Preserve DPWH/GIAS-SD attribution from report; verify each service's redistribution terms | Cross-check geometry and road attributes against OSM; note different data vintages, particularly the 2020 lane-count layer |
| Geoportal Philippines | Candidate catalogue/layers only; no new Geoportal layer is confirmed imported by these records | Layer-by-layer; a visible layer does not guarantee download or redistribution rights | Record exact service/layer ID, AOI coverage, date and licence before import |
| NAMRIA | Candidate topographic/elevation/orthophoto products; exact reusable Ermita coverage not verified | Product-specific; may require request or purchase | Ask for exact AOI tiles, resolution, cost, vertical datum and redistribution terms |
| Manila City Government | No citywide local streets/building/use GIS package confirmed in this repository review | Depends on the dataset and issuing office | Search/request official GIS, planning, address and public-asset records |
| NHCP National Registry | Public registry links documented; a complete source-linked Ermita extraction is not confirmed here | Check each record and image's conditions; preserve source URLs | Compile only verified entries with transcription date and evidence-backed coordinates |

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
- Microsoft/Bing footprints: https://github.com/microsoft/IdMyPhBuildingFootprints

## Import and reconciliation rules

1. Prioritize real data exports over summaries/catalogs.
2. Save raw source data separately from cleaned/normalized datasets.
3. For each import, record source URL, retrieval date, geographic coverage, licence/terms, attribution, fields, and transformations.
4. Do not label a dataset as downloaded until the actual file is committed and its report reviewed.
5. Do not rehost map tiles or imagery unless the source terms explicitly permit it.
6. Use a local metric CRS for spatial comparison; retain original source geometry and IDs.
7. Do not deduplicate using centroid distance alone. Use polygon overlap/IoU, area ratio, centroid distance and source attributes together, with a manual review class for ambiguous cases.
8. Never interpret absence in one source as proof that a feature is absent on the ground.

## Current import status

OSM, Microsoft building footprints and four DPWH road/bridge layers are present. The Microsoft and OSM footprint sets have **not yet been reconciled**. Geoportal, NAMRIA and Manila local-government layers remain candidate sources until an exact dataset is obtained and its access and reuse terms verified.
