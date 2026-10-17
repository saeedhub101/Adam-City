# Adam Royal — Amman city source and model notes

- Geography: Central Amman, Jordan (Downtown/Al-Balad and nearby hillside streets).
- Source geometry: OpenStreetMap building footprints and road centerlines in SaeedRoyaleGodot/assets/amman_core.geojson.
- Original regional source: https://download.geofabrik.de/asia/jordan-latest.osm.pbf
- Attribution: © OpenStreetMap contributors.
- License: Open Database License (ODbL) 1.0. Review https://www.openstreetmap.org/copyright and https://osmfoundation.org/wiki/Licence_and_Legal_FAQ.
- Generated output: Amman-Central-District.glb and Amman-Central-District-3D.png in the GitHub Actions artifact named Adam-Royal-Amman-City-Source-Review.

## Reality and limits

Road alignments and building footprints come from mapped real-world features. The generator adds window panels, frames, roof surfaces, and approximate heights to make the district visually readable. Those facade details are procedural, not photographed or surveyed, and do not guarantee that each real building looks identical. Missing height data is estimated from conservative floor counts.

This is a reviewable 3D city blockout with improved geometry, not a photogrammetric scan or a fully textured photorealistic environment. The OSM source does not include facade photographs.

## Unreal import and quality gate

Import the generated GLB into Unreal with a compatible glTF importer, or convert it to FBX in Blender if required by the installed engine version. Inspect scale, materials, collision, and frame rate in Unreal before using it as a gameplay map.

The workflow requires at least 100 buildings, 50 road ways and 500 window panels, plus a structurally valid GLB and a 1440×900 preview PNG.
