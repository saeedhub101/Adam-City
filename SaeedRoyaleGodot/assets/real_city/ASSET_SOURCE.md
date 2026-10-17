# Real city scan asset

- **Place:** Helsinki, Finland — photogrammetry/Gaussian-splat capture.
- **Source file:** `2024_750_gcps_ultra_splatting_ply.ply`.
- **Publisher/source host:** City of Helsinki open 3D-data host.
- **Original URL:** https://3d.hel.ninja/HelsinkiOpen/testi_gs_ply/2024_750_gcps_ultra_splatting_ply.ply
- **Related official 3D-data page:** https://www.hel.fi/en/decision-making/information-on-helsinki/maps-and-geospatial-data/helsinki-3d
- **Attribution:** City of Helsinki.
- **License reference:** Helsinki 3D open-data page identifies its 3D mesh data as CC BY 4.0. The experimental Gaussian-splat file is hosted separately; its specific metadata/license should be rechecked before redistribution beyond this personal project.
- **Processing:** deterministic spatially distributed record sampling to at most 350,000 complete Gaussian records so the source asset fits GitHub's normal 100 MB file limit. No synthetic buildings or road geometry are added by this processing step.
- **Runtime format:** binary little-endian Gaussian-splat PLY, intended for the GDGS Godot renderer.
- **Original source checksum:** stored in the acquisition workflow run log.
- **Processed asset checksum:** stored in the acquisition workflow run log.
