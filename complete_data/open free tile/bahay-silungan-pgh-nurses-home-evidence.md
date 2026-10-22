# Building evidence update: Bahay Silungan (PGH Nurses' Home)

**Matched OSM feature:** `way/16554323`  
**Source GeoJSON:** `complete_data/OSM/data/buildings/Ermita/ermita-building-details.geojson`  
**Official/current name supplied:** **Bahay Silungan** (formerly PGH Nurses' Home)

## Location

PGH Nurses Home, inside the Philippine General Hospital (PGH) compound along Taft Avenue, Ermita, Manila, 1000 Metro Manila, Philippines.

This adds useful address context to the building record, but no house number has been verified. Do not fabricate one.

## Building facts from the user-supplied description

- 18 bedrooms total.
- Ground floor: 6 bedrooms.
- Second floor: 12 bedrooms.
- Terraces and verandas on both floors.
- The supplied Inquirer article describes the heritage building's restoration: https://lifestyle.inquirer.net/390451/heritage-nurses-home-in-pgh-compound-restored/amp/

The article URL returned HTTP 403 when accessed in this session, so these article-specific facts are recorded as supplied evidence, not as independently fetched page text.

## Exterior evidence

A Wikimedia Commons exterior photograph is available at https://commons.wikimedia.org/wiki/File:PGH_Nurses_Home.jpg. The photograph shows a light-coloured facade, red pitched/tile roof, dark multi-pane windows and arched ground-floor openings. These are **visual observations**, not verified specifications for exact paint, masonry, roof or window materials. The description of terraces and verandas is recorded separately from the photo observation.

## Important floor-count discrepancy

The current OSM tags on `way/16554323` say `building:levels=3`, while the supplied description allocates bedrooms across the ground and second floors (two floors). These statements may refer to different counting conventions, a partial/roof level, or stale OSM tagging. **Keep the original OSM tag unchanged until the geometry and source are checked.** Do not derive a precise height from either claim alone.

## Recommended data treatment

Keep the OpenFreeMap building footprint and coordinates unchanged. Attach the verified name/location context and source facts as attributes; use the photo only for provisional facade/roof/window appearance after confirming the image matches this exact footprint. Mark height, exact materials, and the third-level question as unresolved.
