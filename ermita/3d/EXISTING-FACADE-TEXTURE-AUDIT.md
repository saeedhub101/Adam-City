# Existing Facade Texture Candidates — First Pass

**Date:** 2026-10-19  
**Branch:** main  
**Scope:** Existing repository files only. No new images or data were downloaded.

## What was checked
- `kartaview/ermita-real-facade-images.csv`: 246 indexed candidate photos.
- Existing downloaded paths and per-photo metadata: photo ID, associated OSM feature ID, wall distance, camera heading difference, date and local path.
- `ermita/buildings/reference_photos_catalog.json`: 30 already-catalogued reference photos.
- `ermita/3d/generated/facade-details-report.json`: existing procedural facade GLB, which explicitly contains placeholder windows, doors and signs rather than photographed facades.
- `ermita/3d/real-building-models.json`: local Ramon Magsaysay Center model and other model leads.

## First-pass result
Five downloaded KartaView photos pass this metadata filter:
- status is `direction_checked`
- distance to mapped building wall <= 6 m
- heading difference <= 15 degrees

The list is saved in `kartaview/facade-texture-review-candidates.csv`.

These five are **priority candidates for visual review, not approved textures**. Distance and camera heading are useful screening signals but cannot prove that the image shows the correct building facade or that perspective distortion is acceptable. Do not apply them automatically to a building.

## Priority candidates
| Photo ID | OSM feature | Name in index | Wall distance | Heading difference | Local image |
|---|---|---|---:|---:|---|
| 2488521673 | way/91233257 | YWCA Manila | 3.92 m | 3.6° | `kartaview/images/2488521673.jpg` |
| 2488519305 | way/89774335 | Commodore Building | 4.38 m | 10.9° | `kartaview/images/2488519305.jpg` |
| 2506564233 | way/822413216 | Unnamed OSM feature | 0.46 m | 1.8° | `kartaview/images/2506564233.jpg` |
| 1718194953 | way/642781531 | Unnamed OSM feature | 3.84 m | 1.4° | `kartaview/images/1718194953.jpg` |
| 2488518665 | way/308695382 | Unnamed OSM feature | 4.52 m | 6.5° | `kartaview/images/2488518665.jpg` |

## Current implementation
The 3D preview now loads its existing facade-texture mesh layer alongside the OSM building layer. It uses the repository's existing generic wall material for unverified/unnamed buildings, plus the already-catalogued National Museum, UP Manila and PGH Cancer Institute reference images where OSM building names match those candidates.

The five KartaView photos above are wired to their corresponding OSM way IDs. For each of those footprints, the code selects the footprint edge whose midpoint is nearest the photo's recorded camera coordinate and maps that photo to that single wall; the other walls keep the generic material. This avoids wrapping one street photo around all four sides. The target assignments are still metadata-based candidates and have **not** been visually verified, so image-to-facade identity and wall orientation may need correction after inspecting the live scene.

The building checkbox controls both the OSM extrusion layer and the facade-texture mesh layer. All images are loaded from files already stored in the repository; no new imagery was downloaded.

## Remaining work
1. Visually inspect each existing local photo against the target building's facade, sign, floor pattern and neighboring structures.
2. Reject or correct images where the camera sees a different building, vegetation/vehicles obscure most of the facade, or perspective is too oblique.
3. Rectify/crop usable facades when needed, and document target OSM feature, facade side, source URL, license/attribution and transformation notes.
4. Extend named photo mappings only where the repository metadata supports a credible building identity. Several catalog entries are generic/false search candidates (for example, some City Hall query results describe buildings in Bayambang or Cebu), so they must not be applied to unrelated Ermita buildings.
5. Generic material and procedural window panels are improvements to surface appearance, not real photographs of each building.

## License note
KartaView entries in the existing index specify CC BY-SA 4.0 and attribution `© Grab and KartaView Contributors`. Preserve attribution and license information for any derived texture, and verify the applicable terms before publishing the derivative.

## Files consulted
- `kartaview/ermita-real-facade-images.csv`
- `kartaview/ermita-real-facade-report.json`
- `kartaview/ermita-facade-image-audit.md`
- `ermita/buildings/reference_photos_catalog.json`
- `ermita/3d/generated/facade-details-report.json`
- `ermita/3d/real-building-models.json`
