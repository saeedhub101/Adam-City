# Building evidence update: Bahay Silungan (PGH Nurses' Home)

**Matched OSM feature:** `way/16554323`  
**Existing OSM name:** `PGH Nurses Home`  
**Current/common name:** **Bahay Silungan** (formerly PGH Nurses' Home)  
**Parent institution/campus:** Philippine General Hospital (PGH), operated by the University of the Philippines Manila  
**Source GeoJSON:** `complete_data/OSM/data/buildings/Ermita/ermita-building-details.geojson`  
**Candidate OpenFreeMap visual registry key:** `OFM-ERMITA-01472` — retain as a candidate until the footprint match is confirmed.

## Location and institutional relationship

The building is inside the Philippine General Hospital compound in Ermita, Manila, along the Taft Avenue area. The PGH Wikipedia article explicitly describes Bahay Silungan as the restored Nurses' Home within the hospital compound. PGH is a public teaching hospital administered by the University of the Philippines Manila.

Sources:
- https://en.wikipedia.org/wiki/Philippine_General_Hospital
- https://lifestyle.inquirer.net/390451/heritage-nurses-home-in-pgh-compound-restored/
- https://www.philstar.com/other-sections/newsmakers/2021/09/10/2126193/pghs-bahay-silungan-healer-home/amp/

No verified house number is available; do not fabricate one.

## Building facts

- The restored building is known as Bahay Silungan and was formerly the Nurses' Home.
- It was restored during 2020 and inaugurated/reopened as a place for nurses, resident doctors and transient patients.
- Published descriptions state 18 bedrooms, terraces and verandas.
- The supplied floor allocation is 6 bedrooms on the ground floor and 12 on the second floor.

The Wikipedia PGH article and the supplied restoration reporting support the identity, PGH compound relationship and 18-bedroom/terrace context.

## Photo evidence and visible attributes

Building-specific photograph: https://commons.wikimedia.org/wiki/File:PGH_Nurses_Home.jpg  
Photo date: 16 December 2022. Author: Joven Jacolbia. License: CC BY-SA 4.0.

Visible in the photo:
- light cream/off-white facade;
- red pitched roof;
- dark multi-pane window frames;
- arched ground-floor openings;
- verandas/terraces and a central entrance.

These are visual observations from the photograph, not verified material specifications. Do not claim the walls are a particular stone, plaster, or concrete solely from their appearance. If the actual image pixels are reused in a product, preserve the author attribution and CC BY-SA 4.0 obligations.

## Floor-count discrepancy — keep both sources visible

OSM `way/16554323` currently has `building:levels=3`, while the supplied bedroom allocation describes the ground and second floors. However, a Philippine government environmental report for PGH lists a Nurses Home Building with ground, mezzanine, second and third-floor spaces. This suggests that “18 bedrooms on ground and second floors” may describe only the bedroom allocation, not the building's complete physical floor count.

Sources:
- PGH article: https://en.wikipedia.org/wiki/Philippine_General_Hospital
- PGH environmental report: https://ncr.emb.gov.ph/wp-content/uploads/2023/05/NCR2023-FT1N15629-File_3.pdf

Do not overwrite `building:levels=3` based only on the bedroom distribution. The evidence presently supports retaining three mapped levels while recording the mezzanine/room-allocation nuance. A precise measured height remains unverified.

## Record linkage and geometry rules

1. Link the institutional identity and the Commons image to OSM `way/16554323`.
2. Link the OSM candidate to OpenFreeMap registry key `OFM-ERMITA-01472` only after confirming that the polygon outlines the same Nurses' Home in the PGH compound.
3. Keep the Nurses' Home as its own building feature within the PGH campus. Do not merge it with the PGH campus boundary, hospital-wide geometry, or administration building.
4. Preserve the OpenFreeMap footprint, coordinates, orientation and geometry unchanged. Add identity, parent institution, photo URL, image observations and source citations as attributes.
5. Keep exact facade material, roof material, RGB colour and real-world height as unknown until supported by better evidence.
