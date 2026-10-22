# Part 001 — First 30 Building Completeness Audit

**Source:** `part-001.geojson` in this directory, filtered to the first 30 features whose geometry is Polygon/MultiPolygon and whose OSM `tags.building` field is present. Non-building points and auxiliary queue records are excluded. The source GeoJSON is unchanged.

Detailed row-level results: [part-001-first30-building-audit.csv](./part-001-first30-building-audit.csv)

## Result

**0 of 30 are complete for realistic, building-specific reconstruction under the audit criteria.** Every record has an OSM feature ID and polygon geometry in the source, but most do not contain enough identity, address, height, facade, and roof information.

| Field group | Records with data |
|---|---:|
| Name / official identity | 17 / 30 |
| Street or place plus house number | 1 / 30 |
| Explicit height or storey count | 24 / 30 |
| Facade material or colour | 1 / 30 |
| Roof shape, material or colour | 10 / 30 |
| Complete across all required groups | 0 / 30 |

## Interpretation

- A generic `building=yes` or a building-type tag does not identify the real-world building.
- `building:levels` gives a floor count, not an exact measured height. A missing height must not be inferred from the OpenFreeMap render-height field.
- City/province tags alone do not constitute a street address.
- Facade colour/material, window layout, balcony details, roof appearance and photo-to-footprint confirmation are largely missing from these 30 OSM records. They require separately verified imagery or reliable records; do not fabricate them.
- Some records are identifiable by name (for example, PGH Nurses Home, PGH Out-Patient Department, Centennial Building, and National Institutes of Health), but their OSM building tags still do not provide complete address and visual reconstruction details.

This is a metadata completeness audit, not a claim that every building lacks external photographs. Any image must be matched to the specific footprint before its visual details are applied.
