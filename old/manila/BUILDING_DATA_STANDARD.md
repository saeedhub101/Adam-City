# Mandatory Manila Building Data Standard

This rule applies to all Manila/Ermita building CSV, GeoJSON, enrichment scripts, and rendering code.

## One schema, no variants
All published/master records MUST use the canonical names below. Source-specific aliases may be accepted only at import boundaries, where they are mapped immediately to canonical fields. Never publish multiple spellings for the same concept. Do not add or rename fields without updating this document and every reader/writer in the same change.

## Canonical fields
- Identity: `building_id`, `source_ids`
- Names/classification: `name`, `official_name`, `alt_name`, `building_type`, `building_part`, `building_use`
- Height/levels: `height_m`, `levels`, `underground_levels`, `min_height_m`, `min_level`, `roof_height_m`, `roof_levels`, `roof_angle_deg`, `roof_direction_deg`
- Address: `house_number`, `street`, `suburb`, `postcode`, `city`
- Materials/appearance: `material`, `facade_colour`, `roof_material`, `roof_colour`
- Other attributes: `operator`, `entrance`, `access`, `start_date`, `architect`, `heritage`, `historic`, `wikidata`, `wikipedia`, `website`, `building_condition`
- Geometry: original GeoJSON `geometry`, preserved during attribute-only normalization.

## Units and meanings
- `height_m`: explicit total building height, numeric metres.
- `levels`: numeric above-ground storey count, never metres.
- `min_height_m`: numeric metres; not interchangeable with `min_level`.
- `roof_height_m`: numeric metres.
- `roof_angle_deg` and `roof_direction_deg`: numeric degrees.
- Do not publish aliases such as `height`, `building_height`, `building:height`, `building_levels`, `building:levels`, or `building:storeys` as alternate canonical fields. Convert source units explicitly; flag ambiguous/unparseable values instead of guessing.

## Rendering precedence
1. Use a valid positive `height_m`.
2. Only if absent/invalid, estimate from valid positive `levels * 3.15` metres.
3. Otherwise use a 5 m display fallback and mark it as estimated/fallback when provenance fields are available.
Never take the maximum of explicit height and levels-derived height. Rendering code reads canonical fields only. Base height uses `min_height_m`, defaulting to zero.

## Integrity and validation
- Preserve IDs, source IDs, coordinates, geometry, and feature order during attribute normalization.
- Never replace explicit sourced values with estimates; leave unknown facts empty/null.
- Keep provenance, evidence, confidence, and estimated/measured status in stable documented fields.
- CSV and GeoJSON must share the same field definitions.
- Every generation/enrichment workflow must validate numeric types/units, forbidden aliases, duplicate concepts, IDs, and unchanged geometry, and report unmapped source fields and invalid values.
