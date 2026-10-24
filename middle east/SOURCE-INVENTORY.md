# Jordan–Palestine map source inventory

Updated: 2026-10-24

## Locally stored and generated

- **OSM source data:** Jordan PBF at `Jordan/osm/jordan-latest.osm.pbf`; Palestine-area PBF tiles at `Palestine/osm/tiles/`.
- **Important coverage note:** the stored Palestine-area tiles were cut from Geofabrik's combined **Israel and Palestine** extract. They are not a Palestine-only source and may include surrounding areas.
- **Derived OSM layers:** `layers/` per country contains compressed GeoJSON generated from the saved PBFs. The importer records counts, compressed/uncompressed sizes, geometry types, and failures in `../layers-catalog.json`.
- **Building detail tags:** building features retain available OSM tags such as `height`, `building:levels`, `roof:shape`, `roof:material`, `roof:colour`, `building:material`, `building:colour`, `facade:material`, and `facade:colour`. These are attributes, not photographic textures or complete 3D facade models. Independently mapped windows/doors/entrances are uncommon and only exist where OSM contributors mapped them.

## OpenFreeMap and OpenMapTiles

- The map currently uses OpenFreeMap's hosted style/vector tiles as an **online** context layer. This is not the same as storing the region's vector tiles in this repository.
- OpenMapTiles is a tile schema/tooling ecosystem, not a guarantee of a free downloadable Jordan–Palestine tile archive. No standalone OpenMapTiles archive was found in the region folders at this inventory check.
- Do not bulk-scrape hosted tile endpoints. Offline copies should only be added from an explicitly downloadable source with terms permitting that use.

## Terrain and 3D assets

- The current map has an **online** Terrarium elevation layer toggle. That is not a local DEM archive.
- At this inventory check, no Jordan/Palestine-specific GLB/GLTF, GeoTIFF DEM, MBTiles, or PMTiles assets were found in the region data folders. Manila/Ermita assets elsewhere in the repository cover a different location and must not be reused as Middle East assets.
- No source can supply a real window, door, facade texture, or GLB model if the source dataset does not contain it. Those require a separate appropriately licensed dataset or purpose-built models.

## Import verification

The generated catalog is the source of truth for which derived layers actually completed. Any catalog `errors` entry means that theme needs repair/retry; a successful workflow status alone does not prove every layer was generated.
