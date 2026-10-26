# Tabarbour real-world GLB build

Target: Tabarbour, Amman (35.90–35.99 E, 31.96–32.04 N). Outputs stay in this folder under `middle east/BuildGLB/tabarbour-real/`.

## Execution and persistence
- The workflow can be started manually from GitHub Actions or automatically when its own workflow/scripts change on `main`.
- Existing Jordan OSM layers and the saved Jordan PBF are reused; the workflow does not re-download OSM or overwrite existing Amman GLBs.
- The source layers are streamed and cropped to Tabarbour in temporary runner storage before Blender loads them, to avoid loading all Jordan features into memory.
- The photo-intake script searches Wikimedia Commons without an API key, downloads only files whose Commons metadata identifies a free license, verifies image payloads and checksums, and checkpoints photo batches plus the manifest to `main`.
- Each completed regional GLB and its manifest are committed/pushed during generation. A rerun skips valid existing GLBs and continues with missing tiles.
- The final stage validates GLB headers, sizes, manifest coverage and feature counts. A final validation failure does not remove already committed outputs.

## Inputs included
Locally stored OSM building footprints/details, roads and street names, addresses, landcover, water, places, and a clipped extract of OSM infrastructure including mapped trees, rail/transit features, traffic signals, power, barriers, bridges/tunnels and related mapped objects.

## Images and model fidelity
Wikimedia Commons photo files are saved as **unverified evidence candidates** with source page, author/credit, license, dimensions and SHA-256. Nearby geotagged imagery is not proof that the image shows a particular building. Candidate photos are not automatically projected onto façades; a verified building-to-photo match and appropriate facade UV/projection are required to avoid painting the wrong building. This workflow uses no Mapillary token, no Cesium ion token, no paid service and no online runtime assets.

The GLBs preserve OSM IDs/tags and use mapped heights/colors/material tags where available. Missing measured heights or façade details remain explicitly inferred/procedural; the output is not labelled photogrammetry. Publicly available OSM data cannot by itself supply true façade photographs, exact windows, or surveyed heights for every building.

## Output
- `glb/`: regional GLB files plus `manifest.json` and `failures.jsonl`.
- `photos/`: licensed Wikimedia Commons image candidates and `wikimedia-photo-manifest.json`.
