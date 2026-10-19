# Ermita 3D Map Collection

Goal: build a source-traceable 3D model of Ermita, Manila, with extra detail for Rizal Park.

## Active building geometry

- **Building footprints:** only the committed OpenStreetMap layer at `../maps/generated/ermita-building-footprints.geojson` is used by the live preview. Microsoft/Bing footprint data was rejected as inaccurate and removed from the repository.
- **Street geometry:** `../maps/generated/ermita-road-network.geojson` contains the cached OSM road/path centerlines.
- **Height evidence:** use `../maps/qa/building-height-evidence.csv` and its report. Explicit source heights remain distinct from floor counts; unknown heights must not be described as surveyed.
- **Facade details:** `index.html` builds a batched 3D facade-detail pass for OSM footprints, including window/shopfront openings, floor bands, entrance panels and roof-edge trim. Most details are procedural visual estimates, not measured architectural records.
- **Photo-reviewed building:** Manila Residences Bocobo (OSM `way/90123959`) has a source-specific 34-floor facade treatment based on the inspected reference photo at [Philippine Realty Group](https://philippinerealtygroup.com/manila-residences-bocobo). The photo shows a cream podium, dark horizontal window/balcony bands and orange vertical accents. The listing reports 34 storeys; the local OSM 18 m height tag conflicted with that evidence, so the preview uses a documented approximate 102 m override. This is an estimate, not a survey measurement.
- **Photo provenance:** the online photo is a visual modeling reference, not copied into the repository or stretched across a wall. Recheck source terms before any redistribution of the original photo.
- **Terrain:** `terrain/ermita-copernicus-dem-cropped.tif` and `terrain/ermita-terrain-surface.glb`; source is Copernicus DEM GLO-30, nominally 30 m, and represents a DSM rather than bare-earth DTM.
- **Street-level imagery:** KartaView records remain a separate source archive. They are not automatically assigned to building facades; a nearby camera point alone cannot verify a building face.

## Modeling and QA rules

1. Keep OSM as the sole active footprint source until a replacement source is explicitly validated.
2. Do not use third-party basemap building extrusions as a hidden second footprint layer.
3. Never apply a street photo to a facade unless building identity, camera direction, and the exact street-facing wall are verified.
4. Keep real measured data and procedural visual details clearly distinguished.
5. Preserve all accepted data in repository files and make imports incremental; never re-download assets already present.
