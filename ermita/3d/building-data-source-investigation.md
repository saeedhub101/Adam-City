# Ermita building-data source investigation

**Last checked:** 2026-10-18  
**Area of interest:** Ermita / Rizal Park, Manila (approx. 120.965–121.005 E, 14.560–14.605 N). These bounds are an initial search window, not a validated clipping polygon.

## Executive result

The repository already contains a street-imagery index and local KartaView image files. The latest repository audit reports **740 unique API photos discovered, 246 photos matched to candidate buildings, and 238 images downloaded/stored**. That is not the same as 238 visually verified facade matches. The existing CSV stores camera-heading and position fields, but an image close to a footprint may face away from it or show another building. The KartaView image layer must remain out of the live map unless explicitly re-enabled; existing data can still be reviewed offline as evidence. KartaView terms identify imagery as CC BY-SA 4.0 and require the attribution **© Grab and KartaView Contributors**.

No source checked so far proves a single government package exists that contains every Ermita building's exact facade, windows, doors, signs, roof shape, and measured height. Access differs by source and by individual layer.

## Findings by source

| Source | Relevant output | Current access finding | Action/status |
|---|---|---|---|
| Geoportal Philippines | Government GIS layers, potentially imagery, footprints, reference layers | The official viewer and 3D app are online. A viewer or map tile is not proof that the underlying layer can be bulk-downloaded or redistributed. GeoServer exposes published map services, but a suitable Ermita building/DSM layer and its terms have not yet been verified. | Search the layer catalogue; record exact layer name, owner, metadata, service/download URL, spatial coverage, resolution, update date, and licence before using it. No new dataset downloaded. |
| NAMRIA | LiDAR DSM/DTM, LiDAR orthophoto, IfSAR DSM/DTM/ORI, topographic products | NAMRIA publishes a product and ordering process for specialized elevation and orthophoto products. Current availability, fee schedule, AOI coverage, resolution, vertical datum, source date, and republication terms must be confirmed directly. | Send an AOI-specific request/quote; prioritize LiDAR DSM + DTM + orthophoto, then IfSAR if LiDAR is unavailable. No product purchased/downloaded. |
| LiPAD / Phil-LiDAR | DEM/DTM, orthophotos, classified LAZ, resource/flood maps | The official portal states it is under maintenance and requests should use its manual requester-registration and data-request forms. Requests may require a formal letter, AOI shapefile, and additional documents; approval is not automatic. | Request Manila/Ermita coverage and permission for intended project use. No account approval or data delivery confirmed. |
| OpenDronePH / PhilSA | Drone photos, orthomosaics and derivatives | Open-access repository, but users and donors must register; the original donor may impose restrictions. Uses must acknowledge the donor and OpenDronePH. Ermita coverage is unconfirmed. | Register and search for relevant Manila imagery; check donor-level terms before copying any files into GitHub. |
| PHL-Microsat | Satellite imagery and derivative products | The data portal has a Terms and Conditions of Use Agreement; access must not be treated as unrestricted redistribution. | Consider only imagery with adequate spatial resolution and suitable dates; inspect the TCUA and product-specific terms first. |
| KartaView | Street photos, image position, camera heading and sequences | Repository has an existing metadata index and 238 image files reported as downloaded. Terms state CC BY-SA 4.0 with attribution. | Keep the imagery out of the active map renderer as requested. Use existing indexed images as candidate references, and require visual human review before assigning a photo to a building. Do not re-download existing IDs. |
| Manila City Government / eFOI | Building footprints, address records, plans/elevations and public-building records | No verified citywide public bulk package found. Individual records or GIS layers may require a formal request and may have release restrictions. | Request public/releasable GIS data and facade/elevation drawings for named public or heritage buildings. |
| National Museum of the Philippines | Selected heritage photographs and architectural records | No citywide 3D package verified; rights vary by collection item. | Investigate named landmarks and record item-specific reuse permissions. |

## What counts as a useful height/roof dataset

Ask the provider for all of the following, not just the phrase “3D map”:

- DSM and DTM raster, preferably GeoTIFF; native pixel size and horizontal/vertical CRS and datum.
- Acquisition date and sensor/platform; processing method and accuracy/quality report.
- LiDAR classified point cloud (LAZ/LAS) if available, including classification definitions and point density.
- Orthophoto/orthomosaic covering the AOI, its ground sampling distance, and its license.
- Building/roof vector layers, if supplied, and whether heights are measured, derived from DSM-minus-DTM, or merely inferred.
- Terms covering local storage, derivative 3D models, public display, and redistribution through GitHub/Pages.

DSM is the surface (often including roofs and vegetation); DTM represents bare earth. Neither automatically supplies detailed facade windows, signage, or exact building identity. Copernicus DEM GLO-30 already in the project is regional context, not a substitute for a high-resolution city survey.

## Existing street-level image evidence

Repository files:
- `ermita/3d/facade-photo-review.csv` (246 candidates with blank visual-verification and reviewer-notes columns)
- `kartaview/ermita-real-facade-images.csv`
- `kartaview/ermita-real-facade-report.json`
- `kartaview/ermita-street-imagery-metadata.csv`
- `kartaview/ermita-street-imagery-metadata.geojson`
- `kartaview/images/`

Reported audit totals: 740 API photos found, 246 candidate building matches, 238 local image files. The prior audit was an index/file-presence audit, **not a pixel-level confirmation**. The next practical step is a human-review sheet containing building ID/name, photo ID, photo date, camera coordinates, heading, building bearing, distance, image URL/local path, license and reviewer decision. Only verified matches should inform facade colors/windows/signs. Do not use these photos as a live map layer or automatically project them onto walls.

KartaView source terms: https://kartaview.org/terms  
License: https://creativecommons.org/licenses/by-sa/4.0/

## Sources checked

- Geoportal Philippines: https://geoportal.gov.ph/
- Geoportal Philippines in 3D: https://geoportal.gov.ph/gpapps/pgin3d
- Geoportal GeoServer tile/service catalogue: https://geoserver.geoportal.gov.ph/geoserver/gwc/demo
- NAMRIA products/downloads: https://www.namria.gov.ph/downloads.aspx
- NAMRIA specialized product service and fee information: https://www.namria.gov.ph/kiosk/namria03.htm
- LiPAD portal and current manual request instructions: https://lipad.dream.upd.edu.ph/?id=14
- LiPAD help: https://lipad-fmc.dream.upd.edu.ph/help/
- OpenDronePH / PhilSA: https://philsa.gov.ph/open-drone-ph/
- PHL-Microsat use terms: https://data.phl-microsat.upd.edu.ph/license/
- Manila records request portal: https://www.foi.gov.ph/
- National Museum of the Philippines: https://www.nationalmuseum.gov.ph/

## Completion status and limits

- [x] Identified existing local facade-image index and files.
- [x] Checked published terms and access instructions for KartaView, LiPAD, NAMRIA, OpenDronePH, and PHL-Microsat.
- [x] Updated the source manifest with status, legal/access checks, and next actions.
- [ ] Geoportal layer-by-layer inventory with a verified building/orthophoto/elevation layer for Ermita.
- [ ] LiPAD requester registration, approval, and dataset delivery.
- [ ] NAMRIA confirmation/quote and actual product delivery.
- [ ] OpenDronePH registration and confirmation of relevant AOI coverage.
- [ ] Human visual validation of the 246 candidate facade-photo matches.
- [ ] Actual licensed high-resolution DSM/DTM/orthophoto imported into the repository.

Do not mark the remaining items complete until an actual source file, metadata record, or written provider response is present.
