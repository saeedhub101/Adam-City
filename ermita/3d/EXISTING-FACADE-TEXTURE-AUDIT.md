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

## Texture application decision
1. Visually inspect each existing local photo and compare the building's facade, sign, floor pattern and neighboring structures against the target feature.
2. Reject images where the camera sees a different building, trees/vehicles obscure most of the facade, or the perspective is too oblique.
3. For an approved image, rectify/crop the visible facade, document the target OSM feature and facade side, then map it to the corresponding wall surface. A single photo should not be wrapped around every side of a building.
4. Keep original image, derived texture, source URL, license/attribution, target feature ID and transformation notes in the repository index.
5. Do not label procedural window panels or generic materials as real photographed facade texture.

## License note
KartaView entries in the existing index specify CC BY-SA 4.0 and attribution `© Grab and KartaView Contributors`. Preserve attribution and license information for any derived texture, and verify the applicable terms before publishing the derivative.

## Files consulted
- `kartaview/ermita-real-facade-images.csv`
- `kartaview/ermita-real-facade-report.json`
- `kartaview/ermita-facade-image-audit.md`
- `ermita/buildings/reference_photos_catalog.json`
- `ermita/3d/generated/facade-details-report.json`
- `ermita/3d/real-building-models.json`
