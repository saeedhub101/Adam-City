# Ermita Streets and Buildings — Source Tracker

Scope: Ermita, Manila, Philippines. Priorities are mapped streets, building footprints, addresses, street features and verified facades.

**Status reviewed:** 2026-10-19.

## Source status

| Source | Current repository state | Licence / reuse notes | Next action |
|---|---|---|---|
| OpenStreetMap (OSM) | Active building footprints, road/path geometry and tags under `ermita/maps/generated/` | ODbL attribution and share-alike obligations apply | Keep as the sole active footprint layer; preserve IDs/tags and improve only from validated evidence |
| Microsoft/Bing building footprints | Rejected as inaccurate and removed from active repository data; importer and comparison workflows are retired | Do not use prior Microsoft outline counts as active coverage | Do not download or re-import this source |
| DPWH road / bridge services | Clipped road/bridge references under `ermita/maps/external/` | Preserve service attribution and data vintage | Cross-check road attributes only; do not replace building geometry |
| Geoportal Philippines | Candidate catalogue/layers; no new building dataset is confirmed imported | Layer-specific access and reuse terms | Record exact layer ID, coverage, date and licence before import |
| NAMRIA | Candidate topographic/elevation/orthophoto products; exact reusable coverage not confirmed | Product-specific; may require request or purchase | Verify the exact downloadable tile and terms before import |
| Manila City Government | No citywide building GIS package confirmed in this review | Depends on issuing office and dataset | Seek official GIS/planning/address records |
| NHCP National Registry | Public registry links documented; full source-linked extraction is not confirmed | Verify each record and image's reuse conditions | Compile only evidence-backed records |

## Primary links

- OSM Ermita boundary relation: https://www.openstreetmap.org/relation/103706
- OSM copyright/licence: https://www.openstreetmap.org/copyright
- OSM Overpass API: https://overpass-api.de/
- Geoportal Philippines: https://www.geoportal.gov.ph/
- NAMRIA downloads: https://namria.gov.ph/downloads.aspx
- DPWH: https://www.dpwh.gov.ph/
- Manila City Government: https://manila.gov.ph/
- NHCP Ermita registry: https://philhistoricsites.nhcp.gov.ph/province/ermita-manila/
- NHCP National Registry: https://memory.nhcp.gov.ph/historical-sites/

## Import and reconciliation rules

1. Prioritize real data exports over summaries/catalogues.
2. Save accepted raw data separately from cleaned/normalized datasets.
3. Record source URL, retrieval date, coverage, licence, attribution, fields and transformations.
4. Do not label a dataset downloaded until the actual file is committed and its report reviewed.
5. Do not rehost map tiles or imagery unless source terms permit it.
6. Use a local metric CRS for spatial checks and retain original IDs/geometries.
7. Do not deduplicate using centroid distance alone.
8. Absence in one source is not proof that a feature is absent on the ground.

## Current import status

OSM building/road data and four DPWH road/bridge references remain active. The Microsoft footprint set has been removed and must not be restored. Geoportal, NAMRIA and Manila local-government building layers remain candidate sources until a specific dataset is obtained and its access, alignment and reuse terms are verified.
