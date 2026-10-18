# Common Feature Record

Use this as a normalization guide, not as a claim that every source provides every field. Keep original source files unchanged and preserve original attributes alongside normalized fields.

| Field | Meaning |
|---|---|
| `feature_id` | Stable project ID assigned during import |
| `source_name` | Publisher/source, e.g. OpenStreetMap or NPDC |
| `source_object_id` | Original object ID, feature ID or document reference |
| `source_url` | Page or direct dataset URL |
| `source_retrieved_at` | Retrieval timestamp/date |
| `source_updated_at` | Source publication/update date, if known |
| `name` | Preferred feature name exactly as sourced |
| `name_local` | Local-language name if supplied |
| `name_alt` | Alternate/previous names, retaining source context |
| `category` | Normalized high-level category |
| `subcategory` | More specific feature class |
| `address_full` | Full public address if reliably published |
| `street_name` | Associated street name if explicitly supported |
| `geometry_type` | Point, line, polygon or multipolygon |
| `geometry` | Coordinates/geometry in a documented CRS |
| `latitude`, `longitude` | Optional representative point for point-like searches; do not replace full geometry |
| `operator` | Operator/management entity, when sourced |
| `website`, `phone`, `opening_hours` | Publicly listed details; retain provenance and date |
| `access` | Access status if the source explicitly defines it |
| `building_levels`, `height_m` | Building attributes only when sourced |
| `accessibility` | Accessibility attributes only when sourced |
| `confidence` | High/medium/low based on evidence, not intuition |
| `verification_status` | Unchecked, checked, cross-checked, conflicting or retired |
| `verification_notes` | Specific checks and unresolved issues |
| `license` | Applicable source licence/terms |
| `attribution` | Required credit |
| `original_attributes` | Original source tags/fields retained without loss |

## Normalization rules

- Never invent a building name, street name, phone number, opening hours, route, tree species or address.
- Do not assume the nearest road is the official postal street address.
- Keep duplicate candidates until compared; two similarly named features may be distinct.
- Prefer authoritative sources for official names and administrative facts, and preserve OSM for community-mapped geometry and detail.
- Store dates in ISO 8601 where possible; preserve source-provided dates separately from retrieval dates.
- For tree records, include the inventory/tree ID, common name, scientific name, tree category, geometry and map/page reference if the source supplies them.
- For conflicting sources, retain both claims with provenance and explain the conflict rather than silently choosing one.
