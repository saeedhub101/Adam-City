from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class GodotProjectTests(unittest.TestCase):
    def test_project_and_main_scene_exist(self):
        self.assertTrue((ROOT / "project.godot").is_file())
        self.assertTrue((ROOT / "main.tscn").is_file())
        self.assertTrue((ROOT / "export_presets.cfg").is_file())
        self.assertIn('run/main_scene="res://main.tscn"', (ROOT / "project.godot").read_text())
        preset = (ROOT / "export_presets.cfg").read_text()
        self.assertIn('name="Windows Desktop"', preset)
        self.assertIn("binary_format/64_bits=true", preset)
        self.assertIn("binary_format/embed_pck=true", preset)
        self.assertIn("application/modify_resources=false", preset)

    def test_gameplay_systems_are_present(self):
        source = (ROOT / "scripts/main.gd").read_text()
        for token in ("func _ready", "func _process", "func _unhandled_input",
                      "func _shoot", "func _spawn_bots", "storm_radius",
                      "func _finish_game", "func _spawn_pickup"):
            self.assertIn(token, source)

if __name__ == "__main__":
    unittest.main(verbosity=2)
