#!/usr/bin/env python3
"""Split oversized part-001 GeoJSON without changing the source file."""
import hashlib
import json
from pathlib import Path

ROOT = Path("complete_data/OSM/data/buildings/Ermita/ermita-buildings-master.parts")
SOURCE = ROOT / "part-001.geojson"
OUT = ROOT / "part-001-readable-parts"
TARGET_BYTES = 2 * 1024 * 1024

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def extract_features(raw):
    marker = b'"features":['
    marker_at = raw.find(marker)
    if marker_at < 0:
        raise ValueError('Could not find top-level "features" array')
    i = marker_at + len(marker)
    n = len(raw)
    while i < n and raw[i] in b" \t\r\n":
        i += 1
    while i < n and raw[i] != ord("]"):
        if raw[i] in b", \t\r\n":
            i += 1
            continue
        if raw[i] != ord("{"):
            raise ValueError(f"Unexpected byte at offset {i} in features array")
        start = i
        depth = 0
        in_string = False
        escaped = False
        while i < n:
            c = raw[i]
            if in_string:
                if escaped:
                    escaped = False
                elif c == ord("\\\\"):
                    escaped = True
                elif c == ord('"'):
                    in_string = False
            else:
                if c == ord('"'):
                    in_string = True
                elif c in (ord("{"), ord("[")):
                    depth += 1
                elif c in (ord("}"), ord("]")):
                    depth -= 1
                    if depth == 0:
                        i += 1
                        feature = raw[start:i]
                        json.loads(feature)
                        yield feature
                        break
            i += 1
        else:
            raise ValueError("Unterminated GeoJSON feature")

def main():
    raw = SOURCE.read_bytes()
    OUT.mkdir(parents=True, exist_ok=True)
    features = list(extract_features(raw))
    chunks, current, current_bytes = [], [], 0
    for feature in features:
        if current and current_bytes + len(feature) + 1 > TARGET_BYTES:
            chunks.append(current)
            current, current_bytes = [], 0
        current.append(feature)
        current_bytes += len(feature) + 1
    if current:
        chunks.append(current)

    for stale in OUT.glob("part-*.geojson"):
        stale.unlink()

    entries = []
    for index, group in enumerate(chunks, 1):
        data = b'{"type":"FeatureCollection","features":[' + b",".join(group) + b"]}"
        path = OUT / f"part-{index:03d}.geojson"
        path.write_bytes(data)
        parsed = json.loads(data)
        if len(parsed["features"]) != len(group):
            raise ValueError(f"Validation failed for {path}")
        entries.append({
            "path": str(path).replace("\\\\", "/"),
            "features": len(group),
            "bytes": len(data),
            "sha256": sha256(data),
        })

    if sum(item["features"] for item in entries) != len(features):
        raise ValueError("Feature count mismatch after splitting")
    manifest = {
        "source": str(SOURCE).replace("\\\\", "/"),
        "source_bytes": len(raw),
        "source_sha256": sha256(raw),
        "source_features": len(features),
        "split_target_bytes": TARGET_BYTES,
        "ordering": "Source feature order preserved; each feature kept intact.",
        "original_preserved": True,
        "parts": entries,
    }
    manifest_path = ROOT / "part-001-readable-parts-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\\n", encoding="utf-8")
    print(f"Validated {len(features)} features into {len(entries)} readable files.")
    print(f"Original unchanged: {SOURCE}; manifest: {manifest_path}")

if __name__ == "__main__":
    main()
