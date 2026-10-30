#!/usr/bin/env python3
"""Curate and validate static database previews without accessing game sources."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit

from site_assets import image_size

DATABASE = Path(__file__).resolve().parents[1] / "Nythara" / "database"
VISUAL_FIELDS = {"image", "image_alt", "image_kind", "image_note", "image_crop", "image_extras"}


def preview(image: str, kind: str, alt: str, note: str = "", crop: list[int] | None = None) -> dict:
    result = {"image": image, "image_kind": kind, "image_alt": alt}
    if note:
        result["image_note"] = note
    if crop:
        # x, y, width, height, source width, source height; rendered with an SVG viewport.
        result["image_crop"] = crop
    return result


# The approved capture registry is local to the website; generation never reads
# the private game checkout. Each stable ID has exactly one current hero.
CAPTURE_LIBRARY = json.loads(Path(__file__).with_name("nythara-current-captures.json").read_text())
CAPTURES = {entry["stable_id"]: entry for entry in CAPTURE_LIBRARY["entries"]}
CURRENT_PREVIEWS = {
    key: preview(entry["image"], "capture", entry["image_alt"])
    for key, entry in CAPTURES.items() if entry["database_ready"]
}
CAPTURE_TYPES = {
    "monster": ("monster",), "boss": ("monster", "boss"),
    "npc": ("npc",), "city": ("city",), "region": ("region",), "dungeon": ("dungeon",),
}
CREATURES = {key: CURRENT_PREVIEWS[key] for key, entry in CAPTURES.items() if entry["category"] in ("monster", "boss")}
NPCS = {key: CURRENT_PREVIEWS[key] for key, entry in CAPTURES.items() if entry["category"] == "npc"}

# Regions without an approved capture keep clearly labelled public world artwork.
WORLDS = {
    "region_dawnlands": preview("../assets/nythara-banner.jpg", "scene", "Open green valley artwork representing the Dawnlands", "World artwork", [550, 230, 528, 297, 1600, 533]),
    "world_iron_highlands": preview("../assets/nythara-background.webp", "scene", "Rocky mountain artwork representing the Iron Highlands", "World artwork", [140, 220, 640, 360, 1672, 941]),
    "world_mirelands": preview("../assets/nythara-background.webp", "scene", "Misty forest and water artwork representing the Mirelands", "World artwork", [260, 480, 640, 360, 1672, 941]),
    "world_azure_coast": preview("../assets/nythara-background.webp", "scene", "Blue water and distant shore artwork representing the Azure Coast", "World artwork", [750, 480, 640, 360, 1672, 941]),
    "world_frostreach": preview("../assets/nythara-background.webp", "scene", "Cold blue mountain artwork representing Frostreach", "World artwork", [1150, 195, 480, 270, 1672, 941]),
    "world_ashen_wastes": preview("../assets/nythara-background.webp", "scene", "Dark cliffs and ruined arches representing the Ashen Wastes", "World artwork", [150, 280, 640, 360, 1672, 941]),
    "world_astral_frontier": preview("../assets/nythara-background.webp", "scene", "Moonlit sky and arcane light representing the Astral Frontier", "World artwork", [800, 30, 640, 360, 1672, 941]),
}
WORLDS.update({key: CURRENT_PREVIEWS[key] for key, entry in CAPTURES.items() if entry["category"] in ("city", "region", "dungeon")})

FALLBACKS = {
    "item": preview("assets/icons/treasure.svg", "icon", "Item treasure emblem", "Item emblem"),
    "equipment": preview("assets/icons/armor.svg", "icon", "Equipment armor emblem", "Equipment emblem"),
    "monster": preview("assets/icons/monster_drop.svg", "icon", "Creature emblem", "Creature emblem"),
    "boss": preview("assets/icons/monster_drop.svg", "icon", "Boss emblem", "Boss emblem"),
    "dungeon": preview("assets/icons/key.svg", "icon", "Dungeon key emblem", "Dungeon emblem"),
    "region": {**WORLDS["region_dawnlands"], "image_alt": "Representative Nythara landscape artwork"},
    "city": preview("../assets/nythara-background.webp", "scene", "Representative Nythara settlement artwork", "World artwork", [790, 270, 640, 360, 1672, 941]),
    "npc": preview("assets/icons/scroll.svg", "icon", "NPC dialogue emblem", "NPC emblem"),
    "quest": preview("assets/icons/quest.svg", "icon", "Quest parchment icon"),
    "skill": preview("assets/icons/weapon.svg", "icon", "Combat skill emblem", "Skill emblem"),
    "resource": preview("assets/icons/herb.svg", "icon", "Gatherable plant resource emblem", "Resource emblem"),
    "loot": preview("assets/icons/treasure.svg", "icon", "Loot chest icon"),
}

SKILLS = {
    "skill_cleave": "weapon", "skill_guard": "armor", "skill_iron_will": "armor",
    "skill_power_strike": "weapon", "skill_second_wind": "potion", "skill_vital_spark": "herb",
}


def local_asset(image: str, database: Path) -> Path:
    parsed = urlsplit(image)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError(f"Preview must be a local static asset: {image}")
    asset = (database / image).resolve()
    if not asset.is_relative_to(database.parent.resolve()) or not asset.is_file():
        raise ValueError(f"Preview asset does not exist inside Nythara: {image}")
    if asset.name == "missing.svg":
        raise ValueError("The missing-image placeholder is not a preview")
    return asset


def assign_preview(entry: dict, database: Path = DATABASE) -> None:
    """Assign a real preview before any entry is emitted by the exporter."""
    kind, entry_id = entry["type"], entry["id"]
    if kind not in FALLBACKS:
        raise ValueError(f"No preview policy for category {kind}")
    original_image = entry.get("image")
    if kind in ("monster", "boss"):
        visual = CREATURES.get(entry_id)
        if visual is None:
            visual = FALLBACKS[kind]
    elif kind == "npc":
        visual = NPCS.get(entry_id)
        if visual is None:
            visual = FALLBACKS[kind]
    elif kind in ("region", "city", "dungeon"):
        visual = WORLDS.get(entry_id, FALLBACKS[kind])
    elif kind == "skill":
        icon = SKILLS.get(entry_id)
        if not icon:
            effect = next((fact["value"] for fact in entry.get("facts", []) if fact["label"] == "Effect"), "")
            icon = {"Heal": "potion", "Guard": "armor", "Passive stat": "herb"}.get(effect, "weapon")
        visual = preview(f"assets/icons/{icon}.svg", "icon", f"{entry['name']} skill icon")
    elif kind == "quest":
        visual = {**FALLBACKS[kind], "image_alt": f"Quest parchment for {entry['name']}"}
    elif original_image and Path(original_image).name != "missing.svg" and (database / original_image).is_file():
        visual = preview(original_image, "icon", entry.get("image_alt") or entry["name"], entry.get("image_note", ""))
    else:
        visual = FALLBACKS[kind]
        if kind in ("item", "equipment"):
            category = entry.get("filters", {}).get("category")
            default_icon = "armor" if kind == "equipment" else "treasure"
            icon = {"Weapon": "weapon", "Armor": "armor", "Consumable": "potion", "Accessory": "amulet", "Material": "monster_drop"}.get(category, default_icon)
            visual = preview(f"assets/icons/{icon}.svg", "icon", f"{entry['name']} item emblem", "Item emblem")
        elif kind == "resource":
            icon = "ore" if entry.get("filters", {}).get("verb") == "Mine" else "herb"
            visual = preview(f"assets/icons/{icon}.svg", "icon", f"{entry['name']} resource emblem", "Resource emblem")
    for field in VISUAL_FIELDS:
        entry.pop(field, None)
    entry.update(deepcopy(visual))
    local_asset(entry["image"], database)


def apply_previews(categories: dict[str, list[dict]], database: Path = DATABASE) -> None:
    for entries in categories.values():
        for entry in entries:
            assign_preview(entry, database)
    items = {entry["id"]: entry for entry in categories.get("items", [])}
    for entry in categories.get("loot", []):
        drops = [link for section in entry.get("sections", []) for link in section.get("links", []) if link["type"] == "item"]
        images = []
        for link in drops:
            item = items.get(link["id"])
            if item and item["image"] not in {image["image"] for image in images}:
                images.append({"image": item["image"], "image_alt": item["name"]})
        if images:
            entry.update(image=images[0]["image"], image_alt=f"{images[0]['image_alt']}, available from {entry['name']}", image_kind="bundle")
            entry["image_extras"] = images[1:3]


def validate_previews(categories: dict[str, list[dict]], database: Path = DATABASE) -> int:
    count = 0
    for entries in categories.values():
        for entry in entries:
            local_asset(entry.get("image", ""), database)
            if not entry.get("image_alt", "").strip():
                raise ValueError(f"Missing preview alt text for {entry['id']}")
            kind = entry.get("image_kind")
            source = CAPTURES.get(entry["id"], {})
            allowed_type = CAPTURE_TYPES.get(source.get("category"), ())
            if entry["id"] in CURRENT_PREVIEWS and entry["type"] in allowed_type and kind != "capture":
                raise ValueError(f"Current capture missing for approved stable ID: {entry['id']}")
            if kind not in {"sprite", "portrait", "scene", "icon", "bundle", "capture"}:
                raise ValueError(f"Invalid preview kind for {entry['id']}")
            if kind == "capture":
                expected = CURRENT_PREVIEWS.get(entry["id"])
                if not expected or entry["image"] != expected["image"] or entry["type"] not in allowed_type or entry.get("image_crop"):
                    raise ValueError(f"Capture does not match its approved stable ID: {entry['id']}")
                asset = local_asset(entry["image"], database)
                if image_size(asset) != (1600, 900) or sha256(asset.read_bytes()).hexdigest() != source["sha256"]:
                    raise ValueError(f"Unverified capture asset: {entry['id']}")
            elif entry["type"] in ("monster", "boss", "npc") and kind not in ("sprite", "portrait", "icon"):
                raise ValueError(f"Character scene must be an approved current capture: {entry['id']}")
            if crop := entry.get("image_crop"):
                if len(crop) != 6 or not all(isinstance(value, int) for value in crop):
                    raise ValueError(f"Invalid preview crop for {entry['id']}")
                x, y, width, height, source_width, source_height = crop
                if min(x, y) < 0 or min(width, height) <= 0 or x + width > source_width or y + height > source_height:
                    raise ValueError(f"Preview crop outside the image for {entry['id']}")
            for extra in entry.get("image_extras", []):
                local_asset(extra["image"], database)
                if not extra.get("image_alt"):
                    raise ValueError(f"Loot preview without alt text: {entry['id']}")
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Update only preview fields in the existing website snapshot.")
    args = parser.parse_args()
    metadata = json.loads((DATABASE / "data/metadata.json").read_text())
    payloads = {category["key"]: json.loads((DATABASE / "data" / f"{category['key']}.json").read_text()) for category in metadata["categories"]}
    categories = {key: payload["entries"] for key, payload in payloads.items()}
    if args.apply:
        apply_previews(categories)
    count = validate_previews(categories)
    if args.apply:
        for key, payload in payloads.items():
            (DATABASE / "data" / f"{key}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        (DATABASE / "data/preview-fallbacks.json").write_text(json.dumps(FALLBACKS, ensure_ascii=False, indent=2) + "\n")
    print(f"Preview coverage: {count}/{count}; missing assets: 0; approved current captures: {sum(entry.get('image_kind') == 'capture' for entries in categories.values() for entry in entries)}")


if __name__ == "__main__":
    main()
