# Real-world game data foundation — Jordan and Palestine

Status: inventory of the repository's real geospatial sources. This file deliberately distinguishes mapped geometry from scanned 3D reality.

## Existing, repository-stored data

| Area | Buildings / building tags | Roads | Other layers | Source |
|---|---:|---:|---|---|
| Jordan | 464,413 features in `buildings.geojson.gz`; 464,456 in `building_details.geojson.gz` | 174,522 street features | street names, boundaries, water, landcover, places, addresses | Saved Geofabrik/OpenStreetMap PBF extract; ODbL |
| Palestine coverage | 2,087,961 building features; 2,088,828 building-detail features | 625,120 street features | street names, boundaries, water, landcover, places, addresses | Saved Geofabrik Israel+Palestine extract processed into spatial layers; ODbL |

Counts are feature counts in the existing layer metadata, not counts of unique physical buildings. Geometry exports include multiple geometry types and should be filtered/validated before game use.

## Accuracy limits

- OSM building polygons are mapped footprints, not photogrammetry. An outline is not proof of a real façade, roof shape, door, window, or exact height.
- Height is only usable where source tags provide values such as `height`, `building:levels`, or roof metadata. Estimated defaults must be marked as estimates and never labelled surveyed.
- Roads are real mapped centerlines/areas, but need width, surface, connectivity, and collision checks before use as drivable/walkable game geometry.
- A DEM describes ground elevation at its own resolution; it does not supply building heights or building interiors.
- No city-wide scanned mesh or comprehensive set of photographed façades is currently established by this inventory.

## Game-world data contract

For each feature, preserve:
- original OSM element ID and tags where present;
- source URL/dataset name, retrieval date, licence, and source confidence;
- WGS84 coordinates plus a documented projected/local coordinate transform;
- explicit provenance flags: `mapped`, `surveyed_height`, `estimated_height`, `photogrammetry`, `facade_reference`;
- validation status and any processing warnings.

Do not replace or shift the source footprint to make a render look nicer. Any render offset must be a documented transform, not a mutation of source coordinates.

## Next processing stages

1. Validate saved PBF/layer metadata and discover actual height/roof/material tag coverage before assigning any building heights.
2. Create tiled, spatially bounded game exports rather than loading country-scale GeoJSON into a game client.
3. Add terrain DEM tiles with stated resolution and vertical datum for the selected playable area.
4. Add scanned/photo-reconstructed buildings only when a real source and redistribution licence are verified. Keep scanned landmarks separate from footprint-only buildings.
5. Add road/building collision meshes and walkable surfaces after geometry validation.

## Licensing

OpenStreetMap data is © OpenStreetMap contributors and distributed under the Open Database License (ODbL). Preserve attribution and comply with ODbL when redistributing derived databases. Other imagery, DEM, photogrammetry and 3D assets need their own licence review; do not assume they share the OSM licence.
