# Ermita/Malate building linkage coverage audit

**Audit date:** 2026-10-22  
**Source registry:** `layers/buildings-part1.csv` + `layers/buildings-part2.csv`  
**Scope caution:** the current OpenFreeMap export boundary and the OSM source files are described as Ermita. This report must not be treated as a complete census of every building in the broader Malate district or all of Manila.

## Result: all buildings are not linked yet

The current OpenFreeMap component registry has **1,721 polygon components**. These are not confirmed unique physical buildings. The current linkage coverage is partial:

| Check | Count | Meaning |
|---|---:|---|
| OpenFreeMap polygon components in registry | 1,721 | Includes components that may represent duplicate geometry, building parts or LOD/style variants |
| Components with a populated OSM feature ID | 876 | Spatial match assigned in the current enriched registry; not an exact source-ID join |
| Components without an assigned OSM feature ID | 845 | Includes both review candidates and completely unmatched rows |
| High-confidence method group: centroid inside OSM polygon | 692 | Best spatial-match group; still needs exception review |
| Near OSM centroid under 3 m | 65 | Proximity match; confirm footprint identity |
| Near OSM centroid under 8 m | 119 | Proximity match; confirm footprint identity |
| Low-confidence nearest candidate, review required | 236 | Do not automatically copy names/attributes from this candidate |
| No OSM candidate assigned | 609 | No current spatial OSM building candidate in this registry |
| Records with a building name or name candidate | 320 | Includes candidate names, not all confirmed official building identities |
| Records with OSM building levels | 513 | Storey count is not a measured height |
| Records with an OSM height tag | 112 | Source tag; verify before treating as measured |
| Records with street | 256 | Street value exists |
| Records with house number | 111 | House-number value exists |
| Records with postcode | 88 | Postcode value exists |
| Records with city | 369 | City value exists |
| Records with facade/building colour | 16 | Sparse mapped data; not all are photo-verified |
| Records with building material | 3 | Very sparse |
| Records with roof shape/material/colour | 62 | At least one roof field populated |
| Records with building-specific photo evidence currently catalogued | 2 named buildings | NIH and Bahay Silungan; other catalog entries may be source discoveries rather than completed photo-to-footprint matches |

The 876 spatial matches are composed of 692 centroid-inside matches, 65 nearest-centroid matches under 3 m, and 119 under 8 m. A separate numeric confidence threshold of >=0.90 yields a different count because the registry's confidence values and match-method categories are not equivalent. Do not conflate the two.

## What is actually linked now?

- **National Institutes of Health:** candidate OSM feature `way/27650470`; candidate OpenFreeMap registry key `OFM-ERMITA-01494`; building-specific Commons photo and visual observations documented. Spatial correspondence to the exact OpenFreeMap footprint remains provisional.
- **Bahay Silungan / PGH Nurses' Home:** candidate OSM feature `way/16554323`; candidate OpenFreeMap registry key `OFM-ERMITA-01472`; Commons photo and PGH parent-campus relationship documented. Spatial correspondence to the exact OpenFreeMap footprint remains provisional.
- The two rows in `building-evidence-links.csv` are an evidence crosswalk for these two named buildings, **not a complete all-building linkage table**.

## Next work in the right order

1. **Confirm the geographic scope.** Current source labels and extraction are for Ermita. Before claiming full Malate coverage, verify the polygon boundary covers the intended Malate area; extend extraction only if required.
2. **Resolve geometry duplicates.** The deduplication audit finds 1,629 exact unique ring geometries among 1,721 components, 92 exact duplicates, 136 OSM IDs attached to multiple components, and two duplicate geometry groups with conflicting render heights. Keep all source components until those cases are resolved.
3. **Resolve OSM spatial candidates.** Accept centroid-inside matches after checking geometry overlap; inspect 184 proximity matches and 236 review candidates; keep 609 unmatched records explicitly unmatched rather than guessing.
4. **Enrich each matched building.** Join building tags and address points conservatively; keep multiple address candidates in review. A tenant/POI name must not be automatically used as the building's official name.
5. **Add image evidence per building.** Search official sources and building-specific photo archives; verify the image depicts the exact footprint. Record observed colours and visible details separately from verified construction materials.
6. **Publish coverage metrics again.** Report component counts, unique geometries, accepted OSM matches, review candidates, unmatched records, photo-confirmed matches, and remaining missing attributes as separate measures.

## Geometry and provenance safeguards

- Do not replace OpenFreeMap footprints or coordinates with OSM footprints.
- Do not turn OpenFreeMap `render_height_m` into a verified real-world building height.
- Do not copy attributes from low-confidence candidates automatically.
- Keep original source IDs, matching method, confidence, source URLs, and review status for every join.
- Image observations must be labelled provisional unless independently confirmed; retain image attribution/licensing terms when reusing image pixels.

## Source files

- `layers/buildings-part1.csv`
- `layers/buildings-part2.csv`
- `layers/buildings-part1-enriched.csv.gz`
- `layers/buildings-part2-enriched.csv.gz`
- `building-deduplication-audit.json`
- `building-evidence-links.csv`
- `building-visual-evidence.csv`
