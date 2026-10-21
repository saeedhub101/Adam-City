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
