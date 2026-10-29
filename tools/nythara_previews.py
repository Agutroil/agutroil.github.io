#!/usr/bin/env python3
"""Curate and validate static database previews without accessing game sources."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit

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


CREATURES = {
    "enemy_briarling": preview("assets/creatures/briarling.png", "sprite", "Briarling sprite"),
    "enemy_gloom_moth": preview("assets/creatures/gloom_moth.png", "sprite", "Gloom Moth sprite"),
    "mossling": preview("assets/creatures/mossling.png", "sprite", "Mossling sprite"),
    "enemy_root_sentinel": preview("assets/creatures/root_sentinel.png", "sprite", "Root Sentinel sprite"),
    "enemy_stoneback": preview("assets/creatures/stoneback-portrait.webp", "portrait", "Stoneback sprite portrait derived from its in-game appearance", "Sprite portrait"),
    "enemy_thornspitter": preview("assets/creatures/thornspitter-portrait.webp", "portrait", "Illustrated Thornspitter preview in Nythara's forest creature style", "Illustrated preview"),
    "enemy_hollow_warden": preview("assets/creatures/hollow-warden-portrait.webp", "portrait", "The Hollow Warden sprite portrait derived from its in-game appearance", "Sprite portrait"),
    "enemy_rootbound_seer": preview("assets/creatures/rootbound-seer-portrait.webp", "portrait", "The Rootbound Seer sprite portrait derived from its in-game appearance", "Sprite portrait"),
}
CREATURES["enemy_mossling"] = CREATURES["mossling"]

NPCS = {
    "npc_rowan": preview("assets/npcs/rowan-portrait.webp", "portrait", "Rowan's hooded character and staff, based on his in-game appearance", "Sprite portrait"),
    "npc_elara": preview("assets/npcs/elara-portrait.webp", "portrait", "Representative quest giver portrait for Elara, holding a parchment", "Role portrait"),
    "npc_elyra": preview("assets/npcs/elyra-portrait.webp", "portrait", "Representative healer portrait for Elyra, holding a potion", "Role portrait"),
    "npc_mira": preview("assets/npcs/mira-portrait.webp", "portrait", "Representative vendor portrait for Mira, carrying a goods satchel", "Role portrait"),
    "npc_silverwood_keeper": preview("assets/npcs/silverwood-keeper-portrait.webp", "portrait", "Representative forest keeper portrait with a wooden staff", "Role portrait"),
}

# Quiet crops of existing public artwork and scenes. Artwork is deliberately
# labelled as representative instead of being presented as a capture of an unseen region.
WORLDS = {
    "world_silverwood": preview("../assets/world-hero.jpg", "scene", "Silverwood's forest trail and ancient stone arch"),
    "world_whispering_grove": preview("../assets/whispering-grove.jpg", "scene", "The trees, rocks and creatures of Whispering Grove", crop=[330, 35, 880, 495, 1280, 720]),
    "world_prototype_valley": preview("../assets/nythara-banner.jpg", "scene", "Nythara valley artwork representing Prototype Valley", "World artwork", [560, 225, 528, 297, 1600, 533]),
    "region_dawnlands": preview("../assets/nythara-banner.jpg", "scene", "Open green valley artwork representing the Dawnlands", "World artwork", [550, 230, 528, 297, 1600, 533]),
    "world_iron_highlands": preview("../assets/nythara-background.webp", "scene", "Rocky mountain artwork representing the Iron Highlands", "World artwork", [140, 220, 640, 360, 1672, 941]),
    "world_mirelands": preview("../assets/nythara-background.webp", "scene", "Misty forest and water artwork representing the Mirelands", "World artwork", [260, 480, 640, 360, 1672, 941]),
    "world_azure_coast": preview("../assets/nythara-background.webp", "scene", "Blue water and distant shore artwork representing the Azure Coast", "World artwork", [750, 480, 640, 360, 1672, 941]),
    "world_frostreach": preview("../assets/nythara-background.webp", "scene", "Cold blue mountain artwork representing Frostreach", "World artwork", [1150, 195, 480, 270, 1672, 941]),
    "world_ashen_wastes": preview("../assets/nythara-background.webp", "scene", "Dark cliffs and ruined arches representing the Ashen Wastes", "World artwork", [150, 280, 640, 360, 1672, 941]),
    "world_astral_frontier": preview("../assets/nythara-background.webp", "scene", "Moonlit sky and arcane light representing the Astral Frontier", "World artwork", [800, 30, 640, 360, 1672, 941]),
    "world_start_city": preview("../assets/nythara-background.webp", "scene", "Fantasy citadel artwork representing Dawnwatch", "World artwork", [790, 270, 640, 360, 1672, 941]),
    "world_hollow_ruins": preview("../assets/hollow-warden.jpg", "scene", "The Hollow Ruins arena, cropped to the encounter and stone halls", crop=[425, 180, 640, 360, 1280, 720]),
    "world_moonroot_sanctum": preview("../assets/warp-portal.jpg", "scene", "The Moonroot Sanctum entrance portal and its stone ring", crop=[75, 260, 560, 315, 1280, 720]),
}

FALLBACKS = {
    "item": preview("assets/icons/treasure.svg", "icon", "Item treasure emblem", "Item emblem"),
    "equipment": preview("assets/icons/armor.svg", "icon", "Equipment armor emblem", "Equipment emblem"),
    "monster": preview("assets/creatures/mossling.png", "sprite", "Representative Nythara forest creature sprite", "Creature portrait"),
    "boss": {**CREATURES["enemy_rootbound_seer"], "image_alt": "Representative Nythara guardian portrait", "image_note": "Guardian portrait"},
    "dungeon": {**WORLDS["world_hollow_ruins"], "image_alt": "Representative dungeon arena view", "image_note": "Dungeon scenery"},
    "region": {**WORLDS["region_dawnlands"], "image_alt": "Representative Nythara landscape artwork"},
    "city": {**WORLDS["world_start_city"], "image_alt": "Representative Nythara settlement artwork"},
    "npc": {**NPCS["npc_elara"], "image_alt": "Representative Nythara quest giver portrait"},
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
            archetype = entry.get("filters", {}).get("archetype")
            candidate = {"Ranged": "enemy_thornspitter", "Heavy": "enemy_stoneback"}.get(archetype, "mossling")
            visual = {**(FALLBACKS["boss"] if kind == "boss" else CREATURES[candidate]), "image_alt": f"Representative creature portrait for {entry['name']}", "image_note": "Representative portrait"}
    elif kind == "npc":
        visual = NPCS.get(entry_id)
        if visual is None:
            role = entry.get("filters", {}).get("role")
            candidate = {"Healer": "npc_elyra", "Vendor": "npc_mira"}.get(role, "npc_elara")
            visual = {**NPCS[candidate], "image_alt": f"Representative role portrait for {entry['name']}", "image_note": "Role portrait"}
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
            if kind not in {"sprite", "portrait", "scene", "icon", "bundle"}:
                raise ValueError(f"Invalid preview kind for {entry['id']}")
            if entry["type"] in ("monster", "boss", "npc") and kind not in ("sprite", "portrait"):
                raise ValueError(f"Character preview must be sprite based: {entry['id']}")
            if entry["type"] in ("monster", "boss", "npc"):
                image = entry["image"]
                if not image.startswith(("assets/creatures/", "assets/npcs/")) or Path(image).suffix not in (".png", ".webp"):
                    raise ValueError(f"Character preview cannot be a scene: {entry['id']}")
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
    print(f"Preview coverage: {count}/{count}; missing assets: 0; character screenshots: 0")


if __name__ == "__main__":
    main()
