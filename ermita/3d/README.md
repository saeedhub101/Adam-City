# Ermita 3D Map Collection

Goal: build a source-traceable 3D model of Ermita, Manila, with a more detailed model of Rizal Park. The model should be based on actual geographic geometry, not an AI-generated guess.

## Planned deliverables
- `building-footprints.geojson`: individual building outlines, with source IDs and tags.
- `buildings-3d.geojson`: building footprints plus measured or explicitly estimated height/levels and height provenance.
- `streets-3d.geojson`: road/path centerlines and optional width/bridge/tunnel attributes.
- `terrain/`: permitted elevation/DEM files or a manifest linking to restricted source products.
- `exports/`: generated glTF/GLB/3D Tiles or other derived 3D exports when file size and licensing permit.
- `source-manifest.csv`: provenance, coverage, download date, licence and import status for every layer.

## Candidate sources
1. OpenStreetMap / Geofabrik: road network, building footprints, building levels/heights and tagged points of interest. Data is ODbL; attribute OpenStreetMap contributors and comply with the licence. Start at https://download.geofabrik.de/asia/philippines.html and https://www.openstreetmap.org/copyright.
2. OSM2World / OSM2CDR: possible derived 3D building export for Manila. The listed Manila COLLADA export describes extruded building volumes from OSM outlines, but we must verify its exact extent, current availability, data attribution and licence before treating it as the Ermita model. Source: https://osm2cdr.ru/map/philippines/manila/collada/
3. Geoportal Philippines in 3D: useful for exploring available layers and imagery, but a 3D viewer is not proof that its underlying data can be downloaded or redistributed. Viewer: https://geoportal.gov.ph/gpapps/pgin3d
4. NAMRIA: potential topographic maps, aerial imagery and elevation products. Coverage, resolution, cost and redistribution permission must be confirmed per product. https://www.namria.gov.ph/downloads.aspx

## Modelling rules
- Keep source geometry in its original coordinate reference system and record the CRS.
- Use real tagged heights when present. Otherwise derive height from `building:levels` only as an explicitly estimated value and preserve the method; never label an estimate as measured.
- Do not infer a building's shape, height, roof or interior from a 2D footprint alone.
- Keep DEM/terrain distinct from building geometry.
- Do not copy proprietary map tiles or aerial imagery into the repository unless the terms explicitly allow it.
- Do not mix government data with ODbL data unless the government source's permission is compatible with the intended distribution.
- Keep raw downloads separate from clipped/cleaned derivatives. Record source version/date and processing steps.
- Check repository file-size limits; use Git LFS or release assets for large permitted files.

## Status
This is the initial 3D collection plan. **No 3D geographic source file has yet been imported by this folder.** The first target is to obtain a permitted building/road geometry export for Ermita and validate it before generating a 3D model.
