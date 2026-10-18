# Streets and street names

- street_segments.csv is intended for individual road/path segments and mapped attributes.
- street_names.csv is the normalized index of unique street names, alternate names and source-backed name references.

A street name may apply to many separate geometry segments. Keep the unique name index separate from segment geometry. Preserve source spelling and alternate names rather than silently normalizing them.

## Current status
The name index has six initial candidate names cited to existing project sources. Geometry and intersection endpoints have not yet been imported. The segment table currently contains only its schema.
