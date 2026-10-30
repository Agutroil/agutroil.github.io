"""Run with: python3 -m unittest discover -s tools -p 'test_*.py'."""

import json
import unittest
from copy import deepcopy
from hashlib import sha256

from nythara_previews import CAPTURE_LIBRARY, CURRENT_PREVIEWS, DATABASE, FALLBACKS, VISUAL_FIELDS, apply_previews, assign_preview, local_asset, validate_previews
from site_assets import image_size


def snapshot():
    metadata = json.loads((DATABASE / "data/metadata.json").read_text())
    return {
        category["key"]: json.loads((DATABASE / "data" / f"{category['key']}.json").read_text())["entries"]
        for category in metadata["categories"]
    }


class PreviewTests(unittest.TestCase):
    def test_snapshot_has_complete_local_previews(self):
        data = snapshot()
        self.assertEqual(validate_previews(data), sum(map(len, data.values())))
        for visual in FALLBACKS.values():
            local_asset(visual["image"], DATABASE)

    def test_refresh_preserves_game_data_and_is_repeatable(self):
        original = snapshot()
        updated = deepcopy(original)
        apply_previews(updated)
        once = deepcopy(updated)
        apply_previews(updated)
        self.assertEqual(once, updated)
        for key, entries in original.items():
            for before, after in zip(entries, updated[key]):
                strip = lambda entry: {k: v for k, v in entry.items() if k not in VISUAL_FIELDS}
                self.assertEqual(strip(before), strip(after))

    def test_new_entries_receive_category_appropriate_previews(self):
        for kind in FALLBACKS:
            with self.subTest(kind=kind):
                entry = {"id": "unmapped_entry", "type": kind, "name": "New entry"}
                assign_preview(entry)
                self.assertEqual(validate_previews({kind: [entry]}), 1)
                first = deepcopy(entry)
                assign_preview(entry)
                self.assertEqual(first, entry)

    def test_stale_character_screenshots_are_replaced(self):
        for kind, stable_id in (("monster", "enemy_briarling"), ("boss", "enemy_hollow_warden"), ("npc", "npc_elara")):
            entry = {"id": stable_id, "type": kind, "name": "Character", "image": CURRENT_PREVIEWS['world_hollow_ruins']['image']}
            assign_preview(entry)
            self.assertEqual(entry, {"id": stable_id, "type": kind, "name": "Character", **CURRENT_PREVIEWS[stable_id]})
            self.assertEqual(validate_previews({kind: [entry]}), 1)

    def test_character_scene_is_rejected(self):
        entry = {"id": "bad", "type": "boss", "name": "Boss", "image": CURRENT_PREVIEWS['world_hollow_ruins']['image'], "image_alt": "Boss", "image_kind": "scene"}
        with self.assertRaises(ValueError):
            validate_previews({"bosses": [entry]})

    def test_remote_missing_and_placeholder_assets_are_rejected(self):
        for image in ("https://example.com/image.png", "assets/nonexistent.png", "assets/icons/missing.svg", "../../../index.html"):
            with self.subTest(image=image), self.assertRaises(ValueError):
                local_asset(image, DATABASE)

    def test_alt_text_and_crop_bounds_are_required(self):
        entry = {"id": "new", "type": "region", "name": "Region"}
        assign_preview(entry)
        entry["image_crop"] = [0, 0, 9999, 1, 1600, 533]
        with self.assertRaises(ValueError):
            validate_previews({"regions": [entry]})
        entry.pop("image_crop")
        entry["image_alt"] = ""
        with self.assertRaises(ValueError):
            validate_previews({"regions": [entry]})

    def test_every_approved_database_subject_uses_its_own_current_capture(self):
        data = snapshot()
        records = {entry['id']: entry for entries in data.values() for entry in entries if entry['type'] in ('monster', 'boss', 'npc', 'city', 'region', 'dungeon')}
        for stable_id, expected in CURRENT_PREVIEWS.items():
            self.assertIn(stable_id, records)
            self.assertEqual(records[stable_id]['image'], expected['image'])
            self.assertEqual(records[stable_id]['image_kind'], 'capture')
        self.assertNotEqual(records['world_hollow_ruins']['image'], records['enemy_hollow_warden']['image'])
        self.assertNotEqual(records['world_moonroot_sanctum']['image'], records['enemy_rootbound_seer']['image'])

    def test_capture_subject_cannot_be_swapped_or_cropped(self):
        records = {entry['id']: entry for entries in snapshot().values() for entry in entries if entry['type'] in ('monster', 'boss', 'npc', 'city', 'region', 'dungeon')}
        for own, foreign in [('world_hollow_ruins', 'enemy_hollow_warden'), ('world_moonroot_sanctum', 'enemy_rootbound_seer'), ('enemy_briarling', 'enemy_gloom_moth'), ('npc_elara', 'npc_mira')]:
            wrong = {**records[own], 'image': records[foreign]['image']}
            with self.subTest(own=own), self.assertRaises(ValueError):
                validate_previews({'entries': [wrong]})
        cropped = {**records['npc_elara'], 'image_crop': [0, 0, 800, 450, 1600, 900]}
        with self.assertRaises(ValueError):
            validate_previews({'entries': [cropped]})

    def test_full_capture_library_is_verified_and_game_revision_is_preserved(self):
        self.assertEqual(len(CAPTURE_LIBRARY['entries']), 35)
        self.assertEqual(len({e['stable_id'] for e in CAPTURE_LIBRARY['entries']}), 35)
        self.assertEqual(CAPTURE_LIBRARY['game_revision'], 'b2bac4d03207db30e3d8e0314056b9f96a64e0e0')
        self.assertEqual(json.loads((DATABASE / 'data/metadata.json').read_text())['source_commit'], CAPTURE_LIBRARY['game_revision'])
        for entry in CAPTURE_LIBRARY['entries']:
            asset = local_asset(entry['image'], DATABASE)
            self.assertEqual(image_size(asset), (1600, 900))
            self.assertEqual(sha256(asset.read_bytes()).hexdigest(), entry['sha256'])


if __name__ == "__main__":
    unittest.main()
