# Map extraction queries

The .overpassql files document repeatable queries for open geographic data.

## First query: Ermita core features
1. Open https://overpass-turbo.eu/
2. Copy the contents of ermita-core-features.overpassql into the editor.
3. Run the query. If the service times out, rerun in smaller thematic groups (roads, buildings, businesses, and amenities).
4. Export as GeoJSON.
5. Before committing, save the untouched export in a dated raw-data folder only if the export size and repository policy allow it. Record the Overpass timestamp, query, boundary relation, export date and ODbL attribution.
6. Produce cleaned category tables from the raw export, preserving OSM element IDs as stable source IDs.

The query is a repeatable collection recipe, not proof that data has already been downloaded. No export is included yet.

## Sources and licence
OpenStreetMap data is available under the Open Database License (ODbL). Attribution and share-alike conditions apply: https://www.openstreetmap.org/copyright. Overpass turbo converts Overpass results to GeoJSON: https://wiki.openstreetmap.org/wiki/Overpass_turbo/GeoJSON.
