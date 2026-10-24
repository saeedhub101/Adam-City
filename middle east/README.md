# Middle East data inventory

This is the regional data root for the combined Jordan–Palestine map. Each country has its own folders; shared map display does not merge source datasets.

## Source rules
- OpenStreetMap (OSM): free under ODbL; preserve attribution and source timestamps. Keep object type + id.
- OpenFreeMap: hosted vector style is used by the live map without a private API key. Hosted access does not guarantee bulk/offline extraction.
- OpenFreeTile / terrain: only import publicly downloadable, key-free sources with a documented license and stable URL. Never label a live remote tile layer as a locally archived dataset.
- No paid API or API-key-required source is part of this plan.

## Folder convention
For each region, keep osm/, openfreetile/, openfreemap/, terrain/, metadata/, and reports/. Use descriptive filenames with region, source, content, date and format. Large exports should be partitioned by region and thematic layer first; split further only when needed. Keep each GitHub file comfortably below 100 MB (target 40–70 MB).

## Completeness and deduplication
- Keep OSM object type, id, version, timestamp, tags and geometry when available.
- Manifest each source URL, query/coverage, retrieval time, feature/byte counts, checksum, license, status and errors.
- Never claim all data when a source is rate-limited or incomplete, or hosted service does not permit bulk download.
- Save each successful artifact immediately, verify it, then mark that task complete. On rerun, verify checksums and skip completed artifacts; retry incomplete tasks. A failed region must not block others.
- Country extracts are not the same as city-specific exports. Regional folders are destinations until region-level files and coverage reports exist.

## Region index
Jordan: Amman, Irbid, Zarqa, Ma'an, Karak, Petra, Aqaba, Dead Sea/Jordan Valley, Mafraq, Jerash, Ajloun, Madaba, Salt/Balqa, Tafileh.
Palestine: Jerusalem, Ramallah/Al-Bireh, Nablus, Jenin, Tulkarm, Qalqilya, Salfit, Jericho, Bethlehem, Hebron, Gaza Strip subregions, plus Tiberias/Sea of Galilee and Eilat–Aqaba Gulf boundary context.
