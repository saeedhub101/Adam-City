# Ermita data collection roadmap

## Priority 1 — street and map foundation
1. Fix and document the study boundary for Ermita and the Rizal Park sub-area.
2. Import permitted OpenStreetMap features for streets, named/unnamed paths, buildings, businesses, hospitals, amenities and mapped street furniture.
3. Preserve raw source exports separately from cleaned CSV/GeoJSON files.
4. Record extraction date, source URL, attribution/licence, filters and transformations for each import.

## Priority 2 — named buildings and businesses
- Reconcile individual building footprints with known names, addresses and use.
- Catalogue shops, restaurants, cafés, hotels, pharmacies and service businesses as separate records.
- Catalogue hospitals and clinics as a dedicated filtered view or export while retaining them in the full place dataset.
- Use official institution pages and government/heritage records to verify names and addresses.

## Priority 3 — street signs and visual details
- Capture sign text, sign type, nearest intersection, coordinates, date, and image reuse rights.
- Do not assume online street imagery can be downloaded or rehosted; store links/metadata unless the provider permits redistribution.
- Keep field observations distinct from records inferred from map tags.

## Priority 4 — authoritative map layers
- Inspect Geoportal Philippines layers such as Road 1:10,000 and Built-up Area 1:10,000, plus relevant DPWH and NAMRIA layers.
- Confirm each layer's actual coverage of Ermita and its restriction/redistribution terms before committing source files.
- Request high-resolution NAMRIA products and written public-repository permission where necessary.

## Data status vocabulary
- not_started: not collected
- candidate: found in a source, not checked
- imported: source file/export saved and logged
- reviewed: schema and obvious errors checked
- verified: independently checked against a reliable source or field observation
- restricted: access or licence prevents public redistribution

## Important
An empty CSV is a schema/template, not a collected dataset. Do not describe a layer as downloaded or complete until the source data has actually been saved in the repository and its import logged.
