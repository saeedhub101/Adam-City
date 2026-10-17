#!/usr/bin/env python3
"""Fetch a small real elevation grid for the cached Manila district from OpenTopoData SRTM90m."""
import json
import time
from pathlib import Path
import requests

S, W, N, E = 14.575, 120.965, 14.600, 120.990
GRID = 15
LAT0, LON0 = (S + N) / 2, (W + E) / 2
points = []
for row in range(GRID):
    lat = N - (N - S) * row / (GRID - 1)
    for col in range(GRID):
        lon = W + (E - W) * col / (GRID - 1)
        points.append((lat, lon))

values = []
session = requests.Session()
session.headers.update({"User-Agent": "AdamRoyal-Game/1.0 (terrain data; SRTM90m)"})
for start in range(0, len(points), 100):
    batch = points[start:start + 100]
    locations = "|".join(f"{lat:.7f},{lon:.7f}" for lat, lon in batch)
    last = None
    for attempt in range(3):
        try:
            response = session.get(
                "https://api.opentopodata.org/v1/srtm90m",
                params={"locations": locations},
                timeout=45,
            )
            response.raise_for_status()
            result = response.json()
            if len(result.get("results", [])) != len(batch):
                raise RuntimeError("Elevation API returned an incomplete grid batch")
            values.extend(item.get("elevation") for item in result["results"])
            last = None
            break
        except Exception as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
    if last:
        raise RuntimeError(f"Could not obtain SRTM elevation samples: {last}")

if len(values) != GRID * GRID or any(value is None for value in values):
    raise RuntimeError("SRTM elevation grid contains missing samples")

# Keep the map's existing local metric coordinate system and modest vertical scale.
minimum = min(values)
grid = []
for row in range(GRID):
    row_values = []
    for col in range(GRID):
        elevation = float(values[row * GRID + col])
        row_values.append(round((elevation - minimum) * 0.06, 3))
    grid.append(row_values)

out = Path("GodotAdamRoyal/assets/manila_terrain.json")
out.parent.mkdir(parents=True, exist_ok=True)
payload = {
    "source": "OpenTopoData SRTM90m",
    "attribution": "Elevation data from SRTM via OpenTopoData",
    "bounds": {"south": S, "west": W, "north": N, "east": E},
    "grid_size": GRID,
    "minimum_elevation_m": minimum,
    "maximum_elevation_m": max(values),
    "heights_scaled_m": grid,
}
out.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
print(f"TERRAIN_ELEVATION_PASS source=SRTM90m grid={GRID}x{GRID} min={minimum} max={max(values)} output={out}")
