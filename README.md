# Saeed Open World

A browser-based 3D open-world prototype built with Three.js, JavaScript, and Vite. Development is performed directly on `main`.

## Current milestone

- Load the player character from `3/saeed.glb`.
- Ignore the model's embedded animation clips; use runtime movement controls for the initial prototype.
- Provide graphics-quality presets before entering the world.
- Prototype a walkable city block, third-person camera, keyboard movement, mouse look, and jump.
- Keep the implementation modular so later milestones can add vehicles, aircraft, combat, richer Jordan-based geography, and improved environment assets.

## Run locally

Requirements: Node.js 20 or newer.

```bash
cd game
npm install
npm run dev
```

Open the local URL printed by Vite. The character GLB is loaded from the repository's raw GitHub asset URL, so an internet connection is needed for the current prototype.

## Controls

- W / A / S / D: move
- Mouse: look around (click the game to capture the pointer)
- Space: jump
- Esc: release the mouse

## Graphics

Choose Low, Medium, High, or Ultra before entering. Higher presets increase pixel ratio, shadow quality, and environment detail. Ultra may be demanding on integrated GPUs.

## Known prototype limits

This is the foundation, not a finished GTA-scale game. The first city is a procedural blockout rather than a photogrammetric copy of a real Jordanian city. Exact real-world buildings and realistic traffic/vehicles require dedicated geographic and 3D asset integration. The character's embedded clips are deliberately not played; new animation blending and facial performance remain follow-up work.
