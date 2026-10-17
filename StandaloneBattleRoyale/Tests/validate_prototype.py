import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class PrototypeStructureTests(unittest.TestCase):
    def test_project_descriptor_is_valid(self):
        descriptor = json.loads((ROOT / "SaeedRoyale.uproject").read_text(encoding="utf-8"))
        self.assertEqual(descriptor["Modules"][0]["Name"], "SaeedRoyale")
        self.assertEqual(descriptor["Modules"][0]["Type"], "Runtime")

    def test_real_manila_map_asset_is_in_unreal_content(self):
        map_asset = ROOT / "Content/Maps/Manila-Central-District.glb"
        self.assertTrue(map_asset.is_file(), "Real Manila district GLB must be present in the Unreal project.")
        self.assertGreater(map_asset.stat().st_size, 1024 * 1024, "Map asset unexpectedly small; check that the real district model was restored.")

    def test_character_has_network_authority_and_replication(self):
        header = (ROOT / "Source/SaeedRoyale/Public/SaeedRoyaleCharacter.h").read_text(encoding="utf-8")
        source = (ROOT / "Source/SaeedRoyale/Private/SaeedRoyaleCharacter.cpp").read_text(encoding="utf-8")
        self.assertIn("UFUNCTION(Server, Reliable)", header)
        self.assertIn("ServerFire_Implementation", source)
        self.assertIn("DOREPLIFETIME(ASaeedRoyaleCharacter, Health)", source)
        self.assertIn("HasAuthority()", source)
        self.assertIn("TakeDamage(float DamageAmount", header)
        self.assertIn("Health = FMath::Clamp(Health - AppliedDamage", source)

    def test_game_mode_and_input_are_present(self):
        mode = (ROOT / "Source/SaeedRoyale/Private/SaeedRoyaleGameMode.cpp").read_text(encoding="utf-8")
        inputs = (ROOT / "Config/DefaultInput.ini").read_text(encoding="utf-8")
        engine_config = (ROOT / "Config/DefaultEngine.ini").read_text(encoding="utf-8")
        self.assertIn("DefaultPawnClass = ASaeedRoyaleCharacter::StaticClass()", mode)
        self.assertIn('ActionName="Fire"', inputs)
        self.assertIn("GlobalDefaultGameMode=/Script/SaeedRoyale.SaeedRoyaleGameMode", engine_config)

    def test_no_accidental_uefn_verse_dependency(self):
        descriptor = (ROOT / "SaeedRoyale.uproject").read_text(encoding="utf-8")
        self.assertNotIn("Verse", descriptor)
        self.assertNotIn("ForTemple", descriptor)


if __name__ == "__main__":
    unittest.main(verbosity=2)
