# Ermita 3D Map Collection

Goal: build a source-traceable 3D model of Ermita, Manila, with extra detail for Rizal Park.

## Active building geometry

- **Live preview:** the deployed entry point is `../../ermita-malate-3d.html`. It starts with the OpenFreeMap style and uses committed local OpenFreeMap/OpenMapTiles-derived fallbacks under `../maps/sources/openfreemap/`; this is not the same as loading the generated OSM GeoJSON file.
- **Generated footprint file:** `../maps/generated/ermita-building-footprints.geojson` is documented by the data audit as Basemap/OpenMapTiles-derived and must not be labelled pure OSM. Keep its provenance explicit and do not overwrite source-specific datasets in place.
- **Independent satellite-derived footprints:** Google Open Buildings and Microsoft satellite-derived footprints are stored separately under `../maps/sources/`. Their existence does not mean they are active in the live preview; keep them as separate comparison sources until individually validated and enabled.
- **Street geometry:** `../maps/generated/ermita-road-network.geojson` contains the cached OSM road/path centerlines.
- **Height evidence:** use `../maps/qa/building-height-evidence.csv` and its report. Explicit source heights remain distinct from floor counts; unknown heights must not be described as surveyed.
- **Facade details:** generated facade-detail assets and indexes are catalogued in this folder. Do not assume the active `ermita-malate-3d.html` preview loads every generated model or index; verify its explicit asset requests before claiming a detail is displayed. Most procedural facade details are estimates, not measured architectural records.
- **Photo-reviewed building:** Manila Residences Bocobo (OSM `way/90123959`) has a source-specific 34-floor facade treatment based on the inspected reference photo at [Philippine Realty Group](https://philippinerealtygroup.com/manila-residences-bocobo). The photo shows a cream podium, dark horizontal window/balcony bands and orange vertical accents. The listing reports 34 storeys; the local OSM 18 m height tag conflicted with that evidence, so the preview uses a documented approximate 102 m override. This is an estimate, not a survey measurement.
- **Photo provenance:** the online photo is a visual modeling reference, not copied into the repository or stretched across a wall. Recheck source terms before any redistribution of the original photo.
- **Terrain:** `terrain/ermita-copernicus-dem-cropped.tif` and `terrain/ermita-terrain-surface.glb`; source is Copernicus DEM GLO-30, nominally 30 m, and represents a DSM rather than bare-earth DTM.
- **Street-level imagery:** KartaView records remain a separate source archive. They are not automatically assigned to building facades; a nearby camera point alone cannot verify a building face.

## Modeling and QA rules

1. Keep OSM, OpenFreeMap/OpenMapTiles, Google Open Buildings and Microsoft satellite-derived footprints in separate source paths. The current preview is OpenFreeMap-based; the generated footprints file is not a pure OSM source.
2. Do not overwrite one source with another or describe rendered basemap heights as surveyed building heights.
3. Never apply a street photo to a facade unless building identity, camera direction, and the exact street-facing wall are verified.
4. Keep real measured data and procedural visual details clearly distinguished.
5. Preserve all accepted data in repository files and make imports incremental; never re-download assets already present.
