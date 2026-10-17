#!/usr/bin/env python3
"""Create a size-bounded, deterministic sample of a binary Gaussian-splat PLY.

The source is an openly hosted Helsinki photogrammetry/Gaussian-splat scene.
The output keeps complete splat records and all declared vertex properties;
it does not synthesize geometry or replace the source with primitive buildings.
"""
from __future__ import annotations

import argparse
import random
import re
import sys
from pathlib import Path

PLY_TYPES = {
    "char": "b", "int8": "b", "uchar": "B", "uint8": "B",
    "short": "h", "int16": "h", "ushort": "H", "uint16": "H",
    "int": "i", "int32": "i", "uint": "I", "uint32": "I",
    "float": "f", "float32": "f", "double": "d", "float64": "d",
}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--max-splats", type=int, default=300_000)
    args = ap.parse_args()

    with args.source.open("rb") as f:
        header_lines: list[bytes] = []
        while True:
            line = f.readline()
            if not line:
                raise RuntimeError("PLY header ended before end_header")
            header_lines.append(line)
            if line.strip() == b"end_header":
                break
        header = b"".join(header_lines)
        header_text = header.decode("ascii", errors="strict")
        if "format binary_little_endian 1.0" not in header_text:
            raise RuntimeError("Expected binary_little_endian PLY; refusing to corrupt another format")

        elements = re.findall(r"^element\s+(\S+)\s+(\d+)\s*$", header_text, re.M)
        vertex_counts = [int(count) for name, count in elements if name == "vertex"]
        if len(vertex_counts) != 1:
            raise RuntimeError("Expected exactly one vertex element")
        count = vertex_counts[0]
        properties: list[tuple[str, str]] = []
        in_vertex = False
        for line in header_text.splitlines():
            if line.startswith("element "):
                in_vertex = line.split()[1] == "vertex"
            elif in_vertex and line.startswith("property "):
                parts = line.split()
                if len(parts) != 3 or parts[1] not in PLY_TYPES:
                    raise RuntimeError(f"Unsupported vertex property declaration: {line}")
                properties.append((parts[1], parts[2]))
        if not properties or count < 1:
            raise RuntimeError("No vertex properties or no vertices")
        names = {name for _, name in properties}
        required = {"x", "y", "z", "opacity", "scale_0", "scale_1", "scale_2",
                    "rot_0", "rot_1", "rot_2", "rot_3", "f_dc_0", "f_dc_1", "f_dc_2"}
        if not required.issubset(names):
            raise RuntimeError("Source PLY is not a standard Gaussian-splat PLY; missing: " +
                               ", ".join(sorted(required - names)))
        import struct
        row_format = "<" + "".join(PLY_TYPES[t] for t, _ in properties)
        row_size = struct.calcsize(row_format)
        if row_size <= 0:
            raise RuntimeError("Invalid vertex row size")
        target = min(count, max(1, args.max_splats))
        rng = random.Random(20261017)
        selected = sorted(rng.sample(range(count), target)) if target < count else list(range(count))
        output_header = re.sub(
            rb"(?m)^(element\s+vertex\s+)\d+(\s*)$",
            lambda m: m.group(1) + str(target).encode("ascii") + m.group(2),
            header,
            count=1,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("wb") as out:
            out.write(output_header)
            next_selected = 0
            for i in range(count):
                row = f.read(row_size)
                if len(row) != row_size:
                    raise RuntimeError(f"Unexpected EOF at vertex {i}/{count}")
                if next_selected < target and i == selected[next_selected]:
                    out.write(row)
                    next_selected += 1
            if next_selected != target:
                raise RuntimeError(f"Wrote {next_selected} splats, expected {target}")

    size = args.output.stat().st_size
    if size > 95_000_000:
        raise RuntimeError(f"Output exceeds GitHub's normal file limit: {size} bytes")
    print(f"Validated Gaussian PLY: source_vertices={count}, output_vertices={target}, "
          f"record_bytes={row_size}, output_bytes={size}")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
