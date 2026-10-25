# Photogrammetry intake — Jordan and Palestine

Updated: 2026-10-25  
Repository: `saeedhub101/Adam-City`  
Branch: `main`  
Policy: **no API keys, no paid APIs, no API-dependent sources**. Prefer downloadable source files that can be archived and processed locally.

## Scope and reality check

This work is for the Middle East game world, starting with **Jordan and Palestine** — not the Manila project.

Photogrammetry creates textured 3D meshes from real photographs. The verified open sources found so far primarily document **specific archaeological landmarks**, not entire modern cities. They are useful as high-detail landmark assets, but they do not provide complete photorealistic coverage of Amman, all Jordan, or all Palestine. Keep the existing OSM building/road data as geographic coverage; do not relabel footprint extrusions as photogrammetry.

## Intake candidates

| Priority | Site / area | Dataset and contents | Access without API | License / status | Repository status |
|---|---|---|---|---|---|
| JOR-001 | Madaba, Jordan — Burnt Palace | Terrestrial photogrammetry, 49.02 GB; aerial photogrammetry, 3.36 GB | Open Heritage 3D download request; links are emailed, no API key described | CC BY-NC-SA; non-commercial only, attribution and share-alike required | `discovered`; download request still required; large raw imagery not yet stored |
| JOR-002 | Madaba, Jordan — Church of the Virgin Mary & Hippolytus Hall | Terrestrial photogrammetry, 75.98 GB; aerial, 13.25 GB | Open Heritage 3D download request; links emailed | CC BY-NC-SA; non-commercial only; very large | `discovered`; defer until storage/processing is ready |
| JOR-003 | Jordan — ACOR / Global Digital Heritage collection | Published 3D documentation and models including Petra, Amman Citadel and museum collections | Public model catalogue; individual model access and download must be checked | No blanket licence assumed; check each item | `catalogue`; inspect individual model links and licences |
| PSE-001 | West Bank — Deir Mar Saba monastery, Kidron Valley | Aerial photogrammetry dataset, 17 GB | Open Heritage 3D download request; links emailed | Source catalogue labels country as “Israel”; site description places the monastery about 20 km east of Jerusalem in the West Bank. Verify dataset terms and geographic scope before use | `discovered`; download request still required |
| PSE-002 | Jericho, Palestine — Tel Sultan Tower | Published individual 3D landmark model | Sketchfab model page; verify whether original file download is enabled without account/API | Candidate page indicates CC BY; verify current download availability and exact attribution on the model page | `candidate`; mesh not yet downloaded or georeferenced |
| JOR-004 | Abila (Qweilbeh), northern Jordan — Rock-cut Tomb | Published photogrammetry model; creator reports 523 photographs | Public Sketchfab model page; verify download control and terms | Model page describes photogrammetry; verify exact reuse licence and download rights before integration | `candidate`; mesh not yet downloaded or georeferenced |

## Source links

- Madaba — Burnt Palace: https://openheritage3d.org/project.php?id=7bzx-v340
- Madaba — Church of the Virgin Mary & Hippolytus Hall: https://openheritage3d.org/project.php?id=mv5j-ef62
- ACOR / Global Digital Heritage: https://acorjordan.org/acor-gdh/
- Deir Mar Saba: https://openheritage3d.org/project.php?id=ytkp-dm38
- Tel Sultan Tower, Jericho: https://sketchfab.com/3d-models/tel-sultan-tower-a6147999cab34e3e8d767a9eda81eabe
- Rock-cut Tomb, Abila: https://sketchfab.com/3d-models/rock-cut-tomb-abila-fc6c8d5364fb4a3c9be22e016e85103f

## Next actions

1. Obtain a small, downloadable model first (prioritize Tel Sultan Tower or an ACOR/GDH model) to validate the full local workflow without an API.
2. For Open Heritage 3D, submit the normal dataset download request and retrieve the emailed links; this is not an API workflow. Do not claim a download is complete until the files are received and checked.
3. For every downloaded asset, record original URL, exact filename, byte size, SHA-256, licence/attribution, geographic anchor/CRS, units, up-axis, bounding box and processing steps.
4. Inspect raw mesh/textures before any optimization. Do not invent coordinates or visually guess placement. Integrate only after a reliable georeference is established.
5. Store metadata and small optimized deliverables in the country folders. Raw datasets can be tens of gigabytes; do not attempt to commit giant raw image sets to Git. Use the repository's documented large-asset storage policy and keep each normal Git file below 100 MB.
6. Continue searching for openly downloadable aerial/urban photogrammetry covering whole cities. Do not substitute paid API services or hosted tiles that require an API key.

## Current completion state

- [x] Project scope corrected to Middle East: Jordan and Palestine.
- [x] No-API source discovery started.
- [x] Candidate sources and their known size/licence constraints recorded.
- [ ] Download and checksum first model.
- [ ] Verify geographic registration.
- [ ] Create an optimized, locally hosted GLB test overlay.
- [ ] Find broader city-scale photogrammetry coverage.
