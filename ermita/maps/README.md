# Maps and geographic layers

This folder stores source-traceable geographic data for Ermita, Manila, with a detailed focus on Rizal Park. Status below reflects repository files and import reports reviewed on 2026-10-18; a report count is not a claim of survey-grade completeness.

## Imported data currently present

- **OpenStreetMap:** `generated/import-report.json` reports 8,040 elements, 7,825 GeoJSON features, 1,533 building/building-part features, 5,661 POI/infrastructure rows, and 44 street-sign/signal features. OSM coverage depends on mapped features and its current query extent.
- **Microsoft/Bing building footprints:** `external/ermita-microsoft-building-footprints.geojsonl.gz`; report `external/microsoft-building-footprints-import-report.json` records 12,132 footprints clipped to the project's rectangular AOI. The source imagery vintage is 2016–2020. This is a supplemental dataset, not official Philippine government data.
- **DPWH road and bridge layers:** four clipped GeoJSON layers are recorded in `external/dpwh-road-bridge-batch-import-report.json`: 286 national-road features, 990 road-surface features, 939 lane-count features, and 61 bridge-inventory features. These layers have different source vintages; check each report entry before treating an attribute as current.
- **Street signs and furniture:** see `generated/ermita-street-signs-and-signals.geojson` and `generated/ermita-street_furniture.csv`.
- **Street names and segments:** see `../streets/`.

## Important distinction: imported vs. reconciled

The OSM and Microsoft building layers have both been imported, but they have **not yet been reconciled into one authoritative footprint layer**. Do not concatenate them blindly: geometries may overlap, differ in outline, reflect different dates, or include neighboring areas inside the rectangular crop. Preserve source IDs and provenance, then classify matches and conflicts before creating a merged derivative.

The project AOI is a rectangular crop, not an administrative boundary or cadastral parcel boundary. OSM absence does not prove a feature is absent on the ground.

## Next steps

1. Compare Microsoft footprints against OSM building polygons in a local metric CRS; classify high-overlap matches, Microsoft-only candidates, OSM-only features, and ambiguous/conflicting geometry.
2. Validate a sample against permitted authoritative imagery or field/street-level evidence before accepting new footprints.
3. Keep original-source files unchanged and write any deduplicated/merged output to a new, clearly named derivative with a report.
4. Review the exact coverage, vintage, attribution, and redistribution conditions of every government or third-party layer before publishing derived data.
5. For park-specific paths, amenities, boundaries, and tree locations, ingest official NPDC source material only after preserving source metadata and documenting any georeferencing uncertainty.

## Preferred formats

GeoJSON for interoperable vector exports; GeoPackage for larger GIS datasets; CSV for tabular indexes; retain raw source files separately when their terms and repository-size constraints permit it.

## Attribution and licensing

- OpenStreetMap: include attribution and comply with ODbL requirements: https://www.openstreetmap.org/copyright
- Microsoft/Bing Open Building Footprints: ODbL; retain attribution and review share-alike obligations: https://github.com/microsoft/IdMyPhBuildingFootprints
- DPWH layers: preserve the agency/source attribution recorded in the import report and verify service-specific reuse conditions before redistribution.
- Do not copy map tiles, proprietary aerial imagery, or street-view imagery unless the relevant terms permit it.
