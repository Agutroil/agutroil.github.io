"""Run with: python3 -m unittest discover -s tools -p 'test_*.py'."""

import json
import unittest
from copy import deepcopy

from nythara_previews import DATABASE, FALLBACKS, VISUAL_FIELDS, apply_previews, assign_preview, local_asset, validate_previews


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
        for kind in ("monster", "boss", "npc"):
            entry = {"id": "unmapped_entry", "type": kind, "name": "New character", "image": "../assets/hollow-warden.jpg"}
            assign_preview(entry)
            self.assertIn(entry["image_kind"], ("sprite", "portrait"))
            self.assertNotIn(".jpg", entry["image"])

    def test_character_scene_is_rejected(self):
        entry = {"id": "bad", "type": "boss", "name": "Boss", "image": "../assets/hollow-warden.jpg", "image_alt": "Boss", "image_kind": "scene"}
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


if __name__ == "__main__":
    unittest.main()
