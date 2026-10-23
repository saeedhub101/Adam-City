#!/usr/bin/env python3
"""One-time merge of source MVT layers missing from existing Manila PBF tiles."""
import concurrent.futures
import datetime
import pathlib
import sys
import time
import urllib.request

ROOT = pathlib.Path("Manila/vector-tiles")
REPORT = pathlib.Path("Manila/openfreemap-layer-import-report.md")
SOURCE = "https://tiles.openfreemap.org/planet/latest/{z}/{x}/{y}.pbf"
WORKERS = 6
RETRIES = 4


def read_varint(buf, pos):
    value = 0
    shift = 0
    while pos < len(buf):
        b = buf[pos]
        pos += 1
        value |= (b & 0x7f) << shift
        if not b & 0x80:
            return value, pos
        shift += 7
        if shift > 70:
            break
    raise ValueError("invalid protobuf varint")


def fields(buf):
    pos = 0
    while pos < len(buf):
        start = pos
        tag, pos = read_varint(buf, pos)
        number, wire = tag >> 3, tag & 7
        if number == 0:
            raise ValueError("invalid protobuf field number 0")
        payload = None
        if wire == 0:
            _, pos = read_varint(buf, pos)
        elif wire == 1:
            pos += 8
        elif wire == 2:
            size, pos = read_varint(buf, pos)
            payload = buf[pos:pos + size]
            if len(payload) != size:
                raise ValueError("truncated protobuf field")
            pos += size
        elif wire == 5:
            pos += 4
        else:
            raise ValueError(f"unsupported protobuf wire type {wire}")
        if pos > len(buf):
            raise ValueError("truncated protobuf message")
        yield number, wire, start, pos, payload


def layer_name(layer_bytes):
    for number, wire, _, _, payload in fields(layer_bytes):
        if number == 1 and wire == 2:
            return payload.decode("utf-8")
    raise ValueError("MVT layer has no name")


def tile_layers(tile_bytes):
    found = []
    for number, wire, start, end, payload in fields(tile_bytes):
        if number == 3 and wire == 2:
            found.append((layer_name(payload), tile_bytes[start:end]))
    return found


def download_tile(path):
    rel = path.relative_to(ROOT)
    z, x, y = rel.parts
    url = SOURCE.format(z=z, x=x, y=path.stem)
    last = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Adam-City-one-time-layer-audit/1.0",
                         "Accept-Encoding": "identity"}
            )
            with urllib.request.urlopen(req, timeout=45) as response:
                data = response.read()
                if response.status != 200 or not data:
                    raise RuntimeError(f"empty/non-200 response: {response.status}")
                tile_layers(data)
                return path, data
        except Exception as exc:
            last = exc
            if attempt + 1 < RETRIES:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Unable to fetch/parse {url}: {last}")


def main():
    tiles = sorted(ROOT.glob("*/*/*.pbf"))
    if not tiles:
        raise RuntimeError(f"No PBF tiles found under {ROOT}")
    print(f"Checking {len(tiles)} local tiles against OpenFreeMap latest…", flush=True)

    downloaded = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(download_tile, path): path for path in tiles}
        for future in concurrent.futures.as_completed(futures):
            path, data = future.result()
            downloaded[path] = data
            print(f"Fetched {len(downloaded)}/{len(tiles)}: {path}", flush=True)

    updates = {}
    local_union, source_union = set(), set()
    imported_counts = {}
    imported_by_tile = {}
    for path in tiles:
        original = path.read_bytes()
        local_layers = tile_layers(original)
        source_layers = tile_layers(downloaded[path])
        local_names = {name for name, _ in local_layers}
        source_names = {name for name, _ in source_layers}
        local_union.update(local_names)
        source_union.update(source_names)
        missing = [(name, raw) for name, raw in source_layers if name not in local_names]
        if missing:
            merged = original + b"".join(raw for _, raw in missing)
            tile_layers(merged)
            updates[path] = merged
            imported_by_tile[str(path)] = [name for name, _ in missing]
            for name, _ in missing:
                imported_counts[name] = imported_counts.get(name, 0) + 1

    for path, data in updates.items():
        path.write_bytes(data)

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# One-time OpenFreeMap missing-layer import",
        "",
        f"- Checked at: {timestamp}",
        f"- Local tiles checked: {len(tiles)}",
        f"- Tiles updated: {len(updates)}",
        f"- Local source-layer names before merge (union): {', '.join(sorted(local_union)) or '(none)'}",
        f"- Source-layer names observed (union): {', '.join(sorted(source_union)) or '(none)'}",
        "",
        "## Layers added",
        "",
    ]
    if imported_counts:
        lines.extend(f"- {name}: added to {count} tile(s)" for name, count in sorted(imported_counts.items()))
    else:
        lines.append("No missing source-layer names were found; no PBF tile was changed.")
    lines.extend(["", "## Per-tile additions", ""])
    if imported_by_tile:
        lines.extend(f"- {path}: {', '.join(names)}" for path, names in sorted(imported_by_tile.items()))
    else:
        lines.append("None.")
    lines.extend([
        "",
        "Only source-layer messages whose names were absent from the matching local tile were appended.",
        "Existing protobuf bytes and existing layers were preserved unchanged. This report is an audit record.",
        ""
    ])
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Done: {len(updates)} tiles updated; added layer occurrences: {sum(imported_counts.values())}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"IMPORT FAILED: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)
