# Building Match Audit — Ermita / Malate

Generated from the current OSM building polygons and the repository's licensed photo catalog. This is a work queue, **not a claim that buildings are matched**. Candidate photos are only suggested by name-text overlap; each must be visually checked against the real target before use. Never apply a candidate based only on this CSV.

- Polygon building features inventoried: 1306
- Licensed catalog images: 33
- Buildings with at least one name-based candidate: 2
- Buildings marked individually verified: 0 in this inventory; verification must be recorded only after visual review.

CSV columns include OSM ID, name, type, levels/height, possible reference-photo candidates, and separate facade/roof/model verification states.

Source geometry: `ermita/maps/generated/ermita-building-details.geojson` (OpenStreetMap contributors, ODbL 1.0). Reference catalog: `ermita/buildings/reference_photos_catalog.json`.

## Visual evidence rules
1. Confirm the photo depicts the same building, not a neighboring structure or a similar building elsewhere.
2. Record the exact facade side and camera direction; a facade photo does not establish roof details.
3. Reject images that are too oblique, occluded, low-resolution, or mostly signage/vegetation.
4. Track facade, roof, footprint/height, materials and signage separately. Keep unmatched buildings explicitly unmatched rather than inventing detail.

## Detailed queue
See `building-match-audit.csv` in this directory.


## New high-value reference sources found (2026-10-21)

### National Museum of Fine Arts — architectural elevations and dimensions
The National Museum of the Philippines' official bidding documents describe the National Museum of Fine Arts building and include facade photographs, elevation drawings, and stated dimensions for the facade along Padre Burgos Avenue: 118.85 m long by 24.3 m high. Other document editions describe the Finance Road and Taft Avenue sides. These are substantially better references for matching the long neoclassical facade than generic street photos.

- Official National Museum of the Philippines complex documents (2024): https://weblinks.nationalmuseum.gov.ph/wp-content/uploads/2024/08/14130015/Bidding-Documents.pdf
- Official National Museum of the Philippines complex documents (2025): https://weblinks.nationalmuseum.gov.ph/wp-content/uploads/2025/05/22085545/Bidding-Documents-monumental.pdf
- Additional public photo with camera location metadata (CC0): https://commons.wikimedia.org/wiki/File:National_Museum_of_Fine_Arts_of_the_Philippines_Building.jpg
- Additional facade photograph (CC BY 4.0): https://commons.wikimedia.org/wiki/File:National_Museum_of_Fine_Arts_fa%C3%A7ade_golden_hour_(Manila,_2024).jpg

**Important status:** These sources are now identified for targeted review, but they are not marked as imported, visually approved for texture projection, or integrated into a GLB by this note. The official elevations are suitable for dimensional/facade comparison; roof matching still requires overhead or elevated views.
