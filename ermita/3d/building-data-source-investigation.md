# Ermita building-data source investigation

Checked: 2026-10-18. Area of interest: Ermita / Rizal Park, Manila (approx. 120.965–121.005 E, 14.560–14.605 N).

## Results

| Source | What it may provide | Can we download automatically now? | Status / next action |
|---|---|---|---|
| NAMRIA / Geoportal Philippines — https://geoportal.gov.ph/ | Official GIS layers; some may include building footprints, imagery, or reference features | Not confirmed for a specific Ermita building layer. The portal's layer inventory and layer-specific terms must be checked; a viewer is not a downloadable dataset. | No file downloaded. Identify exact Manila building/imagery layers and verify access and redistribution terms. |
| LiPAD / Phil-LiDAR — https://lipad.dream.upd.edu.ph/ | DSM/DTM, selected orthophotos and classified LiDAR LAZ; potentially useful for roof forms and building heights | Not fully: the official guide says data access requires registration and administrator approval; selected layers also require owner permission/EULA. | Blocked pending an approved account/request. Submit a data request for Manila/Ermita and specify orthophotos, DSM, and classified LAZ. |
| Manila City Government / building-permit and planning records — https://www.foi.gov.ph/ | Potential building plans, floor plans, elevations, façade drawings, addresses and official building names | No public bulk download found/verified. Likely a records request per office or dataset. | No file downloaded. Request public GIS building footprints and, where releasable, architectural elevations/façade records for Rizal Park and surrounding Ermita blocks. |
| National Museum of the Philippines — https://www.nationalmuseum.gov.ph/ | Heritage-building documentation, photographs, and selected architectural records | No citywide downloadable building model verified. Collection-specific material may be available online or by request. | No bulk file downloaded. Use for named heritage buildings and document item-level rights. |
| NAMRIA downloads — https://namria.gov.ph/downloads.aspx | Published topographic maps and selected mapping products | Public map downloads exist, but these are not equivalent to a detailed building/façade database. | No suitable detailed Ermita building dataset found in the download catalogue. |
| Microsoft Open Buildings Philippines (supplemental, NOT a Philippine government source) — https://github.com/microsoft/IdMyPhBuildingFootprints | National-scale building footprint polygons extracted from imagery (2016–2020) | Public download exists, but the Philippines archive is about 1.1 GB compressed and requires a separate area-clipping pipeline. | Not downloaded into this repository yet. Useful fallback for footprint comparison, not façades/windows/logos. ODbL terms apply. |
| Thinking Machines Open Buildings — https://github.com/thinkingmachines/ph-open-buildings | Manually traced footprints and roof/building attributes in selected Philippine city tiles | Public dataset, but its documented city coverage does not include Manila/Ermita. | Not a viable direct coverage source for this project unless new tiles are added. |

## Important limits

- **No new government geospatial data files were downloaded in this investigation.** The relevant government sources do not expose a verified, openly downloadable Ermita package containing all required layers; LiPAD specifically requires an approved account for the relevant datasets.
- A DSM/orthophoto can help infer roof shape and building height, but does not itself supply detailed façade geometry, windows, signs, or logos.
- Façades, windows, logos, and building numbers will likely require licensed street-level photos, official architectural drawings, or a documented photogrammetry/modeling workflow. Do not scrape Google Maps/Street View or redistribute imagery without permission.
- Do not commit a nationwide 1.1 GB archive to this repository. If the supplemental Microsoft dataset is pursued, download it in a workflow, clip to the Ermita bounding box, validate it, and only store the small clipped derivative with attribution/licence notes.
- Coordinates are approximate and should be replaced by the project's authoritative AOI polygon before clipping datasets.

## Request checklist

1. Ask LiPAD for approved access covering the Ermita/Rizal Park AOI: orthophotos, DSM, classified LAZ, and any building/roof resource layers.
2. Search Geoportal Philippines for individual building-footprint and imagery layers; save each layer's metadata, owner, resolution, access status, and licence before download.
3. Submit a Manila City records request for public building footprints/addresses and releasable architectural elevations for major public/heritage buildings.
4. Request heritage documentation from the National Museum/NHCP for named landmark buildings.
5. Track each actual download, source date, licence, geographic coverage, and processing steps in `ermita/3d/source-manifest.csv`.
