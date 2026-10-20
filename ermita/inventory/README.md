# Layer Inventory and Collection Status

> **Status note (2026-10-20):** this matrix originated as an initial collection plan and is not a current repository inventory. Several layers listed below have since been imported. For actual file presence, counts, and provenance, use [`docs/data-source-catalog.md`](../../docs/data-source-catalog.md) and [`docs/data-audit-report.md`](../../docs/data-audit-report.md). Do not read the historical status cells as current state.

Status meanings:

- **Planned** — identified as a target, not yet collected.
- **Source identified** — a plausible source is listed, but the data file has not yet been inspected.
- **Collected** — a source file has been saved with provenance.
- **Reviewed** — schema, coverage and basic quality checks completed.
- **Cross-checked** — compared with at least one independent source or official reference where possible.
- **Limited/unavailable** — source does not publish the needed data, access is restricted, or coverage is inadequate.

At initial setup, no layer below should be assumed to be collected unless an actual file and provenance record are added.

| Layer | Target contents | Priority source(s) | Status |
|---|---|---|---|
| District boundary | Ermita boundary polygon and relation metadata | OSM relation 103706; official boundary data if available | Source identified |
| Street/road network | Names, alternate names, geometry, class, one-way, surface, access | OSM; official road layers if available | Source identified |
| Pedestrian network | Footways, sidewalks where mapped, crossings, steps, park paths | OSM; NPDC park map | Source identified |
| Building footprints | Polygons, building type/height/levels where mapped | OSM; authoritative layers if published | Source identified |
| Building/place names | Names, addresses, use/category, source ID | OSM; official directories and institution websites | Planned |
| Health | Hospitals, clinics, pharmacies and related services | OSM; official health facility directories | Planned |
| Education | Schools, colleges, universities, libraries | OSM; official institution directories | Planned |
| Emergency/public service | Police, fire, government offices, public toilets | OSM; city/national agency directories | Planned |
| Businesses/hospitality | Hotels, restaurants, shops, markets, parking | OSM; official business/institution sources where usable | Planned |
| Culture/heritage | Museums, monuments, heritage structures, religious sites | OSM; official cultural/heritage sources | Planned |
| Transport | Rail/transit stations, stops, routes where published, terminals, taxi/parking | OSM; relevant transport agencies | Planned |
| Rizal Park internal features | Named areas, entrances, gardens, paths, monuments, fountains, facilities | NPDC maps/brochure; OSM | Source identified |
| Rizal Park trees | Individual tree points/records, species and identifiers where supplied | NPDC tree inventory and distribution maps | Source identified |
| Land use/topography | Land-use categories, elevation and topographic reference | Geoportal Philippines; NAMRIA | Source identified |
| Hazards | Available flood, earthquake/fault or other hazard layers | Geoportal Philippines and responsible agencies | Source identified |
| Imagery/reference maps | Official park map and other permitted reference imagery | NPDC; authorized map providers | Source identified |
| Addresses/contact details | Publicly listed addresses, phones, websites and hours | Official organization websites/directories | Planned |

## Acceptance checks for each imported layer

1. File opens and format is known.
2. Coverage is checked against Ermita and park boundaries.
3. Coordinate reference system and geometry type are recorded.
4. Required attributes and missing-value rates are summarized.
5. Duplicates and obvious geometry problems are checked.
6. Names/addresses are not silently inferred; uncertain fields stay blank or flagged.
7. Licence and attribution are recorded.
8. Source IDs are retained so records can be traced back.
9. A date is recorded for collection and for the source's stated update.
10. Limitations and known gaps are documented.
