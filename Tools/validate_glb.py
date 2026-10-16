#!/usr/bin/env python3
"""Read-only structural validator for glTF 2.0 binary (.glb) files.

Uses only Python's standard library. It checks container/chunk integrity and
reports structural facts; it does NOT certify that UEFN supports every feature.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
from typing import Any

MAGIC = b"glTF"
VERSION = 2
JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942


class GlbError(ValueError):
    pass


def inspect_glb(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) < 12:
        raise GlbError("File is too small to contain a GLB header.")
    magic, version, declared_length = struct.unpack_from("<4sII", raw, 0)
    if magic != MAGIC:
        raise GlbError("Invalid GLB magic; expected 'glTF'.")
    if version != VERSION:
        raise GlbError(f"Unsupported GLB container version {version}; expected 2.")
    if declared_length != len(raw):
        raise GlbError(
            f"Header length is {declared_length} bytes, actual file is {len(raw)} bytes."
        )

    offset = 12
    json_doc = None
    chunks: list[dict[str, int]] = []
    while offset < len(raw):
        if offset + 8 > len(raw):
            raise GlbError("Truncated chunk header.")
        chunk_length, chunk_type = struct.unpack_from("<II", raw, offset)
        offset += 8
        end = offset + chunk_length
        if end > len(raw):
            raise GlbError("Chunk extends beyond end of file.")
        chunks.append({"type": chunk_type, "length": chunk_length})
        if chunk_type == JSON_CHUNK:
            if json_doc is not None:
                raise GlbError("Multiple JSON chunks found.")
            try:
                json_doc = json.loads(raw[offset:end].decode("utf-8").rstrip(" \\t\\r\\n\\0"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise GlbError(f"Invalid JSON chunk: {exc}") from exc
        offset = end

    if offset != len(raw):
        raise GlbError("Chunk boundaries do not match file length.")
    if not chunks or chunks[0]["type"] != JSON_CHUNK:
        raise GlbError("The first GLB chunk must be JSON.")
    if json_doc is None:
        raise GlbError("Missing JSON chunk.")
    if not isinstance(json_doc, dict) or "asset" not in json_doc:
        raise GlbError("JSON chunk is missing the required 'asset' object.")

    meshes = json_doc.get("meshes", [])
    nodes = json_doc.get("nodes", [])
    skins = json_doc.get("skins", [])
    animations = json_doc.get("animations", [])
    scenes = json_doc.get("scenes", [])
    morph_targets = sum(
        len(primitive.get("targets", []))
        for mesh in meshes
        for primitive in mesh.get("primitives", [])
    )
    joints = sum(len(skin.get("joints", [])) for skin in skins)
    animation_names = [
        anim.get("name", f"(unnamed animation {i})")
        for i, anim in enumerate(animations)
    ]

    return {
        "file": path.name,
        "size_bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "glb_version": version,
        "gltf_asset_version": json_doc.get("asset", {}).get("version"),
        "nodes": len(nodes),
        "meshes": len(meshes),
        "skins": len(skins),
        "joints_total": joints,
        "animations_total": len(animations),
        "animation_names": animation_names,
        "morph_targets_total": morph_targets,
        "scenes": len(scenes),
        "chunks": chunks,
        "extensions_used": json_doc.get("extensionsUsed", []),
        "structural_checks": "passed",
        "uefn_compatibility": "not determined; import and test in UEFN",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("glb", type=Path, help="Path to a .glb file")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()
    try:
        report = inspect_glb(args.glb)
    except (OSError, GlbError) as exc:
        print(f"GLB validation failed: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"GLB structural validation: PASS — {report['file']}")
        for key in (
            "size_bytes", "sha256", "nodes", "meshes", "skins", "joints_total",
            "animations_total", "morph_targets_total",
        ):
            print(f"{key}: {report[key]}")
        print("Animations:")
        for name in report["animation_names"]:
            print(f"  - {name}")
        print("Note: structural validity does not prove UEFN import compatibility.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
