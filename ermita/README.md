# Ermita, Manila — Geographic Data Collection

**Scope:** Ermita, Manila, Philippines, with extra-detailed coverage of Rizal Park (Luneta).

**Goal:** Build a broad, source-traceable collection of map features and place information. This is a data project, not an application or website. No game or map viewer is being built at this stage.

## Coverage targets

- Administrative boundary and subareas
- Named streets, road geometry, alleys, paths, crossings and intersections
- Building footprints, known building names, addresses and building-use tags
- Hospitals, clinics, pharmacies, schools, universities, police/fire stations and government offices
- Hotels, restaurants, shops, museums, heritage sites, religious buildings and other public destinations
- Public transport stops/stations, parking and other transport infrastructure where mapped
- Parks, plazas, gardens, monuments, fountains, playgrounds, public facilities and other mapped public-space features
- Rizal Park tree inventories and tree distribution maps published by the National Parks Development Committee (NPDC)
- Supporting geography such as land use, elevation/topography and hazard layers when authoritative data is available and reuse terms permit it

## Repository layout

- `sources/README.md` — source register and access links
- `inventory/README.md` — data layers to collect and their status
- `schemas/feature-record.md` — proposed common fields for cataloguing features
- `quality/verification-log.md` — checks, discrepancies and unresolved issues
- `rizal-park/README.md` — park-specific collection plan

Raw data should be kept separate from cleaned/normalized exports. Prefer original files and preserve each source's licence, attribution, download date, version and original metadata.

## Important limitations

“Everything” cannot be guaranteed: sources omit features, may be outdated, use different boundaries, restrict redistribution, or lack precise addresses and coordinates. A feature should not be marked verified merely because it appears in one source. The inventory must distinguish **not yet collected**, **collected**, **checked**, **conflicting**, and **unavailable/restricted**.

## Current status

This folder establishes the collection structure and source/quality plan. It does **not** yet claim that the raw map datasets or all individual buildings and places have been downloaded, imported, deduplicated, or field-verified. Do not treat the starter inventory as a completed map database.

## Attribution

OpenStreetMap-derived data must be credited to OpenStreetMap contributors and comply with the ODbL: https://www.openstreetmap.org/copyright. Other sources retain their own terms; check the terms before copying, redistributing, or combining their data.


## Repository layout

- `assets/textures/` — shared reusable surface materials, including road, sidewalk, courtyard, and façade texture maps.
- `buildings/` — building-specific model files, building inventory, and reference photography.
- `3d/` — city model outputs, terrain products, and 3D source/catalog metadata.
- `maps/` — geographic source data, derived layers, external datasets, and QA registers.
- `scripts/` — importers, reconciliation tools, and geometry/model generation utilities.
