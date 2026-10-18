# Mabini Street — City Walk

A browser-based Three.js prototype focused on building **A. Mabini Street in Malate, Manila one block at a time**. The current milestone is Block 01: a short playable street section with a third-person character and two real-photo visual references from Wikimedia Commons.

## Run it

The game is a standalone HTML page and does not need npm or Vite.

- Open `game/index.html` through a static web host (for example, GitHub Pages once Pages is enabled), or serve the repository locally with any simple static HTTP server.
- An internet connection is required for Three.js and the Wikimedia Commons photo references.

## Controls

- **W / A / S / D** or **arrow keys** — move
- **Shift** — run
- **Space** — jump
- **Drag the mouse** — look around
- **Esc** — release mouse capture if your browser has captured it

## Incremental build plan

1. **Block 01 (current):** short playable street segment, first two Mabini/Malate photo references, basic street furniture, and movement/camera.
2. Add more reference photos for this same stretch and replace placeholder building faces with measured, photo-matched facades.
3. Extend to the next real block and its intersections only after the first block is better matched.
4. Add more detail, signage, traffic, and pedestrians in later passes.

This is an early photo-backed blockout, **not yet a photorealistic 1:1 reconstruction**. The photographs are used as visual anchors while the 3D layout is incrementally refined; they do not magically provide full 360-degree geometry.

## Photo references

- [Hostel 1632, Mabini Street, Malate — Wikimedia Commons](https://commons.wikimedia.org/wiki/File:06127jfHotels_Building_Streets_Mabini_Malate_Manilafvf_12.jpg) — public-domain dedication indicated on the file page.
- [Mabini/Ocampo/Roxas Boulevard area, Malate — Wikimedia Commons](https://commons.wikimedia.org/wiki/File:05261jfStreets_Mabini_Ocampo_Roxas_Boulevard_Malate_Manilafvf_08.jpg) — released into the public domain by the photographer.

## Current limitations

The first block still includes simple 3D placeholder geometry. Some image URLs may fail if Wikimedia redirects or cross-origin restrictions change. Exact facades, scale, street layout, and turning views will improve as additional real-world references are integrated.
