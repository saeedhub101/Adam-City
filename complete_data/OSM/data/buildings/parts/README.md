# Button 4 — four spatial GLB parts

Generated from both GeoJSON sources drawn by button 4 in test.html. Each partN/partN.glb has an origin sidecar and complete feature inventory. Inventories preserve original properties/tags, resolved color, height, base height, polygon component count, area, centroid, and PBR material fields.

The GLB parts are preserved as committed assets; this metadata enrichment workflow does not regenerate or modify them. See `parts-report.json` for source hashes and export counts.


## Metadata enrichment index

- `building-enrichment-index.json` joins each exported part feature to available OSM names, addresses, building tags, and material/roof tags when an exact OSM feature ID is available.
- `building-enrichment-report.json` records coverage counts and limitations.
- Rebuild both metadata files from the repository root with:

  `python3 complete_data/OSM/scripts/generate_building_enrichment_index.py`

The enrichment is metadata-only: it does not change GLBs, footprints, geometry, coordinates, IDs, heights, or existing colors. Matching intentionally uses exact OSM IDs only; it does not guess a name or address based on proximity. Facade photographs and verified photographic material estimates are not yet included. Source attributes are incomplete for many buildings, so missing values remain missing until supported by additional evidence.
