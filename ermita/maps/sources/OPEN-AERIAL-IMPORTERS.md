# Open aerial source importers

These importers are intentionally provider-specific. They never merge their geometries into the active OpenFreeMap/OpenMapTiles building file.

## OpenAerialMap

Run:

```bash
python3 ermita/scripts/import_openaerialmap_ermita.py
```

- Uses the public HOTOSM OpenAerialMap STAC catalog; no account or API key is required for catalog search.
- Searches the Ermita/Rizal Park bounding box only.
- Downloads only direct raster assets explicitly marked CC-BY-4.0, with an 80 MiB per-file cap and a 300 MiB total new-download cap per run.
- Existing assets are reused and never overwritten. SHA-256, asset identity, provider, date, licence, and repository path are recorded in `ermita/maps/external/openaerialmap/ermita-openaerialmap-import-report.json`.
- This imports georeferenced imagery, not building footprints. A later processing step would be required to derive footprints, and it must preserve per-building identity and uncertainty.

## TM Open Buildings

Run:

```bash
python3 ermita/scripts/import_tm_open_buildings_ermita.py
```

The script records a coverage report under `ermita/maps/sources/tm-open-buildings/`. The published TM Open Buildings release covers selected 250 m tiles in 12 Philippine cities; Manila is not among the listed cities. The script therefore reports `no_coverage_for_aoi` and intentionally does not download unrelated city data or create synthetic footprints. Revisit this importer only if TM publishes Manila/Ermita coverage.

The source is under ODbL; any derivative database must comply with the source's share-alike requirements. Even if a future release covers Ermita, matching its polygons to existing buildings must be spatial and confidence-based because a shared building ID is not guaranteed.

## Workflow

`.github/workflows/import-open-aerial-sources.yml` runs both scripts when either importer changes, and can also be started manually from GitHub Actions. It commits source assets and reports back to `main`. The workflow does not publish imagery into the live 3D preview and does not alter `backup/` or `kartaview/`.

## Sources intentionally not automated here

- OpenDronePH: the official portal requires one-time registration and donor-specific usage terms; no anonymous bulk-download endpoint was verified. Do not automate around its access controls.
- Copernicus Data Space and USGS EarthExplorer: accounts/access terms may apply to bulk downloads and these sources are not building-footprint datasets by themselves.
- Mapbox, Maxar and other commercial imagery: not treated as open bulk-download sources; viewing imagery does not grant rights to scrape, store, or derive a repository dataset.

Official references:
- OpenAerialMap terms: https://openaerialmap.org/about/
- OpenAerialMap download guide: https://docs.openaerialmap.org/browser/user-guide/
- TM Open Buildings coverage and licence: https://github.com/thinkingmachines/ph-open-buildings
- OpenDronePH access requirements: https://philsa.gov.ph/open-drone-ph/
