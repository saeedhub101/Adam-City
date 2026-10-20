# Adam City building edit preservation policy

## Source and canonical data

- `ermita/maps/generated/ermita-osm-raw.json` is the cached OSM source snapshot. The importer merges source records by OSM `type/id`; partial refreshes do not clear the cache.
- `ermita/maps/generated/ermita-building-details.geojson` is the canonical building-detail dataset used by the facade generators. When `import_osm_and_build_3d.py` rebuilds it, the importer carries forward explicitly namespaced `properties.adam_city` edits by stable `osm_feature_id`.
- `ermita/maps/generated/ermita-building-footprints.geojson` is rebuilt from the same merged building collection.
- Generated GLB files are derived outputs, not the only place where a building edit should be recorded.

## How to record a lasting edit

Add an `adam_city` object to the relevant feature's `properties` in the canonical building-detail GeoJSON. Do not write custom changes directly into the OSM `tags` alone: a future source refresh will replace those tags.

Example:

```json
{
  "osm_feature_id": "way/123456",
  "adam_city": {
    "tag_overrides": {
      "building:colour": "#d8c5a2",
      "building:material": "stone"
    },
    "lock_geometry": false
  }
}
```

- `tag_overrides` is a dictionary of tag values that must survive OSM refreshes. These values are merged into the current source tags and are available to the existing generators.
- Set `lock_geometry: true` only when a verified, curated footprint is intentionally stored in that feature's `geometry`. The importer will preserve that geometry across source refreshes.
- For a manually modelled building without an OSM counterpart, mark its feature with `properties.adam_city.user_created: true` and give it a stable project ID in `properties.osm_feature_id`. Such features are retained when the OSM building collection is rebuilt.

## Safety rules

1. Never replace the canonical building dataset with a raw source export without running the preservation merge.
2. Never treat a generated model as the sole copy of a manual edit.
3. Do not lock a footprint unless its identity and geometry have been checked; a bad locked footprint would also persist.
4. New source objects are added, existing source objects are refreshed by ID, and curated edits are reapplied. Missing source objects are not deleted from the raw cache just because an incremental response omitted them.
5. A change to the importer or generator should invalidate only the affected derived outputs; it must not erase the canonical edits.
6. Before publishing, validate the GeoJSON and generated assets, then commit the canonical data and generated outputs to `main`.

## Current limitation

This preservation mechanism protects edits explicitly recorded under `properties.adam_city` in the canonical GeoJSON. Existing visual edits that exist only in a GLB, HTML, or external source are not automatically converted into this edit format. Record future building edits in the canonical feature first, then regenerate the affected output.
