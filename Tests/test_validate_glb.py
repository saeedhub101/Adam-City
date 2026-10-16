import json
import struct
import tempfile
import unittest
from pathlib import Path

from Tools.validate_glb import GlbError, inspect_glb


def make_glb(document: dict) -> bytes:
    encoded = json.dumps(document, separators=(",", ":")).encode("utf-8")
    encoded += b" " * ((4 - len(encoded) % 4) % 4)
    chunk = struct.pack("<II", len(encoded), 0x4E4F534A) + encoded
    return struct.pack("<4sII", b"glTF", 2, 12 + len(chunk)) + chunk


class ValidateGlbTests(unittest.TestCase):
    def test_valid_minimal_glb(self):
        document = {
            "asset": {"version": "2.0"},
            "nodes": [{"name": "Saeed"}],
            "meshes": [{"primitives": [{"targets": [{}, {}]}]}],
            "skins": [{"joints": [0, 1, 2]}],
            "animations": [{"name": "Idle"}, {"name": "Talking"}],
            "scenes": [{"nodes": [0]}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "minimal.glb"
            path.write_bytes(make_glb(document))
            report = inspect_glb(path)
        self.assertEqual(report["nodes"], 1)
        self.assertEqual(report["joints_total"], 3)
        self.assertEqual(report["animations_total"], 2)
        self.assertEqual(report["animation_names"], ["Idle", "Talking"])
        self.assertEqual(report["morph_targets_total"], 2)

    def test_rejects_wrong_magic(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.glb"
            path.write_bytes(b"nope" + b"\\0" * 8)
            with self.assertRaises(GlbError):
                inspect_glb(path)

    def test_rejects_declared_length_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.glb"
            path.write_bytes(make_glb({"asset": {"version": "2.0"}}) + b"x")
            with self.assertRaises(GlbError):
                inspect_glb(path)


if __name__ == "__main__":
    unittest.main()
