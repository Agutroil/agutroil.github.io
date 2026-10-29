#!/usr/bin/env python3
"""Export the Nythara game database from the Godot project.

The Nythara repository stays read-only. This script parses the authored
`.tres` resources, the WorldGraph, the world scenes and the city document,
normalises the public fields and writes deterministic JSON for the static
GitHub Pages database.

Usage:
    python3 tools/export_nythara_database.py \
        --nythara-repo ../Nythara \
        --output Nythara/database/data
"""

from __future__ import annotations

import argparse
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from nythara_previews import CREATURES, FALLBACKS, assign_preview, apply_previews, validate_previews

# ---------------------------------------------------------------------------
# Presentation vocabulary
# ---------------------------------------------------------------------------

ITEM_CATEGORIES = {0: "Material", 1: "Weapon", 2: "Armor", 3: "Consumable", 4: "Accessory"}
ITEM_RARITIES = {0: "Common", 1: "Uncommon", 2: "Rare", 3: "Epic", 4: "Legendary", 5: "Mythic"}
RARITY_TONES = {
    "Common": "muted",
    "Uncommon": "forest",
    "Rare": "cyan",
    "Epic": "violet",
    "Legendary": "gold",
    "Mythic": "danger",
}
ARCHETYPES = {0: "Melee", 1: "Ranged", 2: "Heavy"}
SKILL_TYPES = {0: "Active", 1: "Passive"}
SKILL_TARGETS = {0: "Self", 1: "Current target", 2: "Nearby enemies"}
SKILL_EFFECTS = {0: "Damage", 1: "Heal", 2: "Passive stat", 3: "Guard"}
QUEST_OBJECTIVES = {0: "Defeat", 1: "Collect", 2: "Interact"}
SLOT_LABELS = {
    "weapon": "Weapon",
    "body": "Body",
    "accessory": "Accessory",
    "offhand": "Offhand",
    "head": "Head",
    "chest": "Chest",
    "hands": "Hands",
    "legs": "Legs",
    "feet": "Feet",
    "ring_left": "Ring (left)",
    "ring_right": "Ring (right)",
    "amulet": "Amulet",
    "trinket": "Trinket",
}
BIOME_LABELS = {
    "plains": "Plains",
    "forest": "Forest",
    "mountain": "Mountain",
    "swamp": "Swamp",
    "coast": "Coast",
    "tundra": "Tundra",
    "ash": "Ash",
    "astral": "Astral",
    "ruins": "Ruins",
    "interior": "Interior",
}

CATEGORY_META = [
    ("items", "item", "Items", "Every item in the current game build, from moss materials to the Warden Blade."),
    ("equipment", "equipment", "Equipment", "Wearable gear with slots, stats and visual support."),
    ("monsters", "monster", "Monsters", "Creatures with authored stats, territories and loot."),
    ("bosses", "boss", "Bosses", "The authored multi-phase encounters beneath the forest."),
    ("dungeons", "dungeon", "Dungeons", "Authored cooperative dungeons with rooms, bosses and first clears."),
    ("regions", "region", "Fields & Regions", "Regions, landmarks and the paths that connect them."),
    ("cities", "city", "Cities & Settlements", "Settlements, districts and their world connections."),
    ("npcs", "npc", "NPCs", "Quest givers, vendors and healers."),
    ("quests", "quest", "Quests", "Objectives, rewards, turn-ins and prerequisites."),
    ("skills", "skill", "Skills", "Active and passive skills with their rank tables."),
    ("resources", "resource", "Resources", "Gatherable resource nodes and what they yield."),
    ("loot", "loot", "Loot Tables", "Monster loot tables with chances, quantities and links."),
]

# Curated mapping of real in-game captures that already ship with the website.
SITE_IMAGES = {
    "silverwood": ("../assets/coop-silverwood.jpg", "Two adventurers on the Silverwood forest trail"),
    "whispering_grove": ("../assets/whispering-grove.jpg", "Rowan and Mosslings in the Whispering Grove"),
    "prototype_valley": ("../assets/world-hero.jpg", "The old stone arch and a Mossling in the valley"),
    "hollow_ruins": ("../assets/hollow-warden.jpg", "The Hollow Warden in its arena beneath the ruins"),
    "moonroot_sanctum": ("../assets/rootbound-seer.jpg", "The Rootbound Seer in the Moonroot Sanctum"),
}

ICON_FALLBACK = "assets/icons/missing.svg"


# ---------------------------------------------------------------------------
# Godot resource parsing
# ---------------------------------------------------------------------------


def _unescape(value: str) -> str:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def refs(value: str | None, kind: str = "SubResource") -> list[str]:
    if not value:
        return []
    return re.findall(rf'{kind}\("([^"]+)"\)', value)


def ref(value: str | None, kind: str = "ExtResource") -> str | None:
    found = refs(value, kind)
    return found[0] if found else None


def string_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [_unescape(match) for match in re.findall(r'"((?:[^"\\]|\\.)*)"', value)]


def scalar(value: str | None, default: Any = None) -> Any:
    if value is None:
        return default
    if not isinstance(value, str):
        return value
    value = value.strip()
    if value.startswith('&"'):
        return _unescape(value[1:])
    if value.startswith('"'):
        return _unescape(value)
    if value in ("true", "false"):
        return value == "true"
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    return value


class Tres:
    """Small, purpose-built parser for the resource files used by Nythara."""

    def __init__(self, path: Path):
        self.path = path
        self.ext: dict[str, dict[str, str]] = {}
        self.sub: dict[str, dict[str, str]] = {}
        self.sub_types: dict[str, str] = {}
        self.res: dict[str, str] = {}
        self._parse(path.read_text(encoding="utf-8"))

    def _parse(self, text: str) -> None:
        current: dict[str, str] = {}
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith(";"):
                continue
            if line.startswith("[ext_resource "):
                attrs = dict(re.findall(r'(\w+)="((?:[^"\\]|\\.)*)"', line))
                if "id" in attrs:
                    self.ext[attrs["id"]] = attrs
                continue
            if line.startswith("[sub_resource "):
                attrs = dict(re.findall(r'(\w+)="((?:[^"\\]|\\.)*)"', line))
                sid = attrs.get("id", "")
                current = {}
                self.sub[sid] = current
                self.sub_types[sid] = attrs.get("type", "")
                continue
            if line == "[resource]":
                current = self.res
                continue
            if line.startswith("[gd_resource"):
                current = {}
                continue
            if "=" in line and current is not None:
                key, value = line.split("=", 1)
                current[key.strip()] = value.strip()

    def get(self, key: str, default: Any = None) -> Any:
        return scalar(self.res.get(key), default)

    def ext_path(self, key: str) -> Path | None:
        ext_id = ref(self.res.get(key))
        if not ext_id or ext_id not in self.ext:
            return None
        path = self.ext[ext_id].get("path")
        return resolve_res_path(path) if path else None

    def sub_dict(self, value: str | None) -> dict[str, str]:
        sub_id = ref(value, "SubResource")
        return self.sub.get(sub_id or "", {})


def resolve_res_path(path: str) -> Path:
    return NYTHARA / path.replace("res://", "")


def load_tres(path: Path | None) -> Tres | None:
    if path is None or not path.exists():
        return None
    return Tres(path)


def get_id(tres: Tres | None) -> str:
    return str(tres.get("id", "")) if tres else ""


def fmt_range(lo: Any, hi: Any) -> str:
    if lo is None and hi is None:
        return ""
    if hi is None or lo == hi:
        return str(lo)
    return f"{lo}\u2013{hi}"


def fmt_number(value: Any) -> str:
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:g}"
    return str(value)


def fmt_duration(value: Any) -> str:
    if value in (None, "", 0, 0.0):
        return "Instant"
    return f"{fmt_number(value)} s"


def humanize_identifier(value: Any) -> str:
    """Turn an internal ability id into a readable label for the database."""
    words = [word for word in re.split(r"[_\s]+", str(value).strip()) if word]
    if not words:
        return ""
    labels = []
    for index, word in enumerate(words):
        if word.lower() in ("aoe", "hp", "xp", "id"):
            labels.append({"aoe": "AoE", "hp": "HP", "xp": "XP", "id": "ID"}[word.lower()])
        elif index == 0:
            labels.append(word[:1].upper() + word[1:].lower())
        else:
            labels.append(word.lower())
    return " ".join(labels)


def add_fact(facts: list[dict[str, str]], label: str, value: Any) -> None:
    if value is None:
        return
    text = fmt_number(value) if isinstance(value, (int, float)) else str(value).strip()
    if not text:
        return
    facts.append({"label": label, "value": text})


def add_link_section(
    sections: list[dict[str, Any]],
    title: str,
    links: Iterable[dict[str, Any] | None],
) -> None:
    cleaned = [link for link in links if link]
    if cleaned:
        sections.append({"title": title, "links": cleaned})


def link_entity(kind: str, entity_id: str, name: str, meta: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"type": kind, "id": entity_id, "name": name}
    if meta:
        result["meta"] = meta
    return result


# ---------------------------------------------------------------------------
# Scene parsing
# ---------------------------------------------------------------------------


@dataclass
class SceneNode:
    name: str
    parent: str | None
    path: str
    definition: str | None
    enemy_path: str | None
    level: int | None
    target_world: str | None
    portal_id: str | None
    label: str | None
    instance_path: str | None
    order: int
    encounter: str | None = None


@dataclass
class Scene:
    path: Path
    ext: dict[str, str] = field(default_factory=dict)
    nodes: list[SceneNode] = field(default_factory=list)

    def __post_init__(self) -> None:
        text = self.path.read_text(encoding="utf-8")
        for attrs in re.findall(r'^\[ext_resource [^\]]*\]', text, re.M):
            parsed = dict(re.findall(r'(\w+)="((?:[^"\\]|\\.)*)"', attrs))
            if "id" in parsed:
                self.ext[parsed["id"]] = parsed.get("path", "").replace("res://", "")
        pattern = re.compile(r"^\[node ([^\]]*)\]\n(.*?)(?=^\[|\Z)", re.S | re.M)
        by_path: dict[str, SceneNode] = {}
        for order, match in enumerate(pattern.finditer(text)):
            attrs = dict(re.findall(r'(\w+)="((?:[^"\\]|\\.)*)"', match.group(1)))
            body = match.group(2)
            name = attrs.get("name", "")
            parent = attrs.get("parent")
            path = name if parent in (None, ".") else f"{parent}/{name}"
            definition = None
            enemy_path = None
            instance_path = None
            def_match = re.search(r'^definition = ExtResource\("([^"]+)"\)', body, re.M)
            if def_match:
                definition = self.ext.get(def_match.group(1))
            enemy_match = re.search(r'^enemy_definition = ExtResource\("([^"]+)"\)', body, re.M)
            if enemy_match:
                enemy_path = self.ext.get(enemy_match.group(1))
            instance_match = re.search(r'instance=ExtResource\("([^"]+)"\)', match.group(1))
            if instance_match:
                instance_path = self.ext.get(instance_match.group(1))
            level_match = re.search(r"^level = (\d+)", body, re.M)
            target_match = re.search(r'^target_world_id = &"([^"]+)"', body, re.M)
            portal_match = re.search(r'^portal_id = &"([^"]+)"', body, re.M)
            label_match = re.search(r'^transition_label = "([^"]*)"', body, re.M)
            node = SceneNode(
                name=name,
                parent=parent,
                path=path,
                definition=definition,
                enemy_path=enemy_path,
                level=int(level_match.group(1)) if level_match else None,
                target_world=target_match.group(1) if target_match else None,
                portal_id=portal_match.group(1) if portal_match else None,
                label=label_match.group(1) if label_match else None,
                instance_path=instance_path,
                order=order,
            )
            by_path[path] = node
            self.nodes.append(node)

        # Resolve the nearest encounter ancestor for every spawn marker.
        for node in self.nodes:
            if not node.enemy_path:
                continue
            parent_path = node.parent
            while parent_path and parent_path != ".":
                ancestor = by_path.get(parent_path)
                if ancestor is None:
                    break
                if ancestor.definition and ancestor.definition.startswith("data/encounters/"):
                    node.encounter = ancestor.path
                    break
                parent_path = ancestor.parent
            else:
                pass
            if node.encounter is None:
                for ancestor in self.nodes:
                    if ancestor.definition and ancestor.definition.startswith("data/encounters/") and node.path.startswith(ancestor.path + "/"):
                        node.encounter = ancestor.path
                        break

    def encounter_nodes(self) -> list[SceneNode]:
        return [
            node
            for node in self.nodes
            if node.definition and node.definition.startswith("data/encounters/")
        ]

    def spawns(self) -> list[SceneNode]:
        return [node for node in self.nodes if node.enemy_path]

    def npcs(self) -> list[SceneNode]:
        return [
            node
            for node in self.nodes
            if node.definition and node.definition.startswith("data/npcs/")
        ]

    def transitions(self) -> list[SceneNode]:
        return [node for node in self.nodes if node.target_world]


# ---------------------------------------------------------------------------
# Source reading
# ---------------------------------------------------------------------------


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def materialize_source(repo: Path, ref: str) -> tuple[Path, str, str]:
    """Return a read-only tree for *ref*, without touching the game checkout.

    The default is the public ``main`` commit. That keeps unmerged work in a
    parallel branch out of the website snapshot and makes the recorded source
    commit meaningful.
    """
    global TEMP_SNAPSHOT  # noqa: PLW0603
    if ref in ("", "HEAD", "WORKTREE"):
        commit = git(repo, "rev-parse", "HEAD")
        return repo, commit, git(repo, "rev-parse", "--short=7", commit)

    commit = git(repo, "rev-parse", f"{ref}^{{commit}}")
    short = git(repo, "rev-parse", "--short=7", commit)
    archive = subprocess.check_output(["git", "-C", str(repo), "archive", commit])
    temp_dir = Path(tempfile.mkdtemp(prefix="nythara-db-"))
    TEMP_SNAPSHOT = temp_dir
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
        tar.extractall(temp_dir, filter="data")
    return temp_dir, commit, short


def load_worlds() -> dict[str, dict[str, Any]]:
    worlds: dict[str, dict[str, Any]] = {}
    for path in sorted((NYTHARA / "data" / "worlds").rglob("*.tres")):
        tres = Tres(path)
        wid = get_id(tres)
        if not wid:
            continue
        scene_path = tres.ext_path("scene")
        worlds[wid] = {
            "id": wid,
            "name": tres.get("display_name", wid),
            "description": tres.get("description", ""),
            "scene": str(scene_path.relative_to(NYTHARA)) if scene_path else None,
            "path": str(path.relative_to(NYTHARA)),
        }
    return worlds


def load_scenes(worlds: dict[str, dict[str, Any]]) -> tuple[dict[str, Scene], dict[str, str]]:
    scene_worlds: dict[str, str] = {}
    for world in worlds.values():
        if world["scene"]:
            scene_worlds[world["scene"]] = world["id"]
    scenes: dict[str, Scene] = {}
    for scene_path, _world_id in sorted(scene_worlds.items()):
        path = NYTHARA / scene_path
        if path.exists():
            scenes[scene_path] = Scene(path)
    return scenes, scene_worlds


def load_resource_scene_definitions() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for path in sorted((NYTHARA / "scenes" / "resources").glob("*.tscn")):
        text = path.read_text(encoding="utf-8")
        match = re.search(r'path="res://(data/resources/[^"]+\.tres)"', text)
        if match:
            mapping[str(path.relative_to(NYTHARA))] = match.group(1)
    return mapping


# ---------------------------------------------------------------------------
# Entry helpers
# ---------------------------------------------------------------------------


def make_entry(
    *,
    entry_id: str,
    kind: str,
    name: str,
    subtitle: str = "",
    description: str = "",
    image: str | None = None,
    image_alt: str | None = None,
    badges: list[dict[str, str]] | None = None,
    facts: list[dict[str, str]] | None = None,
    sections: list[dict[str, Any]] | None = None,
    filters: dict[str, Any] | None = None,
    level: int | None = None,
    rarity: int | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "id": entry_id,
        "type": kind,
        "name": name,
        "subtitle": subtitle,
        "badges": badges or [],
        "facts": facts or [],
        "sections": sections or [],
        "filters": filters or {},
        "sort": {
            "name": name.casefold(),
            "level": level if level is not None else 0,
            "rarity": rarity if rarity is not None else 0,
            "category": (category or "").casefold(),
        },
    }
    if description.strip():
        entry["description"] = description.strip()
    if image:
        entry["image"] = image
        entry["image_alt"] = image_alt or name
    assign_preview(entry, OUTPUT.parent)
    return entry


# ---------------------------------------------------------------------------
# Main export
# ---------------------------------------------------------------------------


SOURCE_REPO: Path
SOURCE_REF: str
SOURCE_COMMIT: str
SOURCE_SHORT: str
NYTHARA: Path
OUTPUT: Path
TEMP_SNAPSHOT: Path | None = None
WARNINGS: list[str] = []
ERRORS: list[str] = []


def warn(message: str) -> None:
    WARNINGS.append(message)
    print(f"warning: {message}", file=sys.stderr)


def error(message: str) -> None:
    ERRORS.append(message)
    print(f"error: {message}", file=sys.stderr)


def image_exists(relative: str) -> bool:
    # Image paths are relative to the database root (the parent of data/),
    # so ../assets/... resolves to the existing Nythara site assets.
    return (OUTPUT.parent / relative).resolve().exists()


def check_image(entry: dict[str, Any]) -> None:
    image = entry.get("image")
    if image and not image_exists(image):
        warn(f"{entry['type']} {entry['id']} references missing image {image}")


def export() -> None:
    global NYTHARA, OUTPUT  # noqa: PLW0603

    if not (NYTHARA / "data" / "world" / "world_graph.json").exists():
        raise SystemExit(f"not a Nythara repository: {NYTHARA}")

    world_graph = json.loads((NYTHARA / "data" / "world" / "world_graph.json").read_text(encoding="utf-8"))
    graph_regions = {region["world_id"]: region for region in world_graph["regions"]}
    portals = world_graph["portals"]
    worlds = load_worlds()
    scenes, scene_worlds = load_scenes(worlds)
    resource_scene_defs = load_resource_scene_definitions()

    # --- authored resources -------------------------------------------------
    item_defs: dict[str, dict[str, Any]] = {}
    item_order: list[str] = []
    for path in sorted((NYTHARA / "data" / "items").glob("*.tres")):
        tres = Tres(path)
        item_id = get_id(tres)
        if not item_id:
            continue
        icon_id = str(tres.get("icon_id", ""))
        icon_name = icon_id.split(".")[-1] if icon_id else ""
        icon_path = f"assets/icons/{icon_name}.svg" if icon_name else ICON_FALLBACK
        category = int(tres.get("category", 0))
        rarity = int(tres.get("rarity", 0))
        item_defs[item_id] = {
            "id": item_id,
            "name": tres.get("display_name", item_id),
            "description": tres.get("description", ""),
            "category": category,
            "category_label": ITEM_CATEGORIES.get(category, "Item"),
            "rarity": rarity,
            "rarity_label": ITEM_RARITIES.get(rarity, "Common"),
            "max_stack": int(tres.get("max_stack", 99)),
            "sell_value": int(tres.get("sell_value", 0)),
            "slot": str(tres.get("equipment_slot", "") or ""),
            "attack": int(tres.get("attack_bonus", 0)),
            "armor": int(tres.get("armor_bonus", 0)),
            "health": int(tres.get("max_health_bonus", 0)),
            "heal": int(tres.get("heal_amount", 0)),
            "level_requirement": int(tres.get("level_requirement", 1)),
            "level_authored": "level_requirement" in tres.res,
            "visual_id": str(tres.get("equipment_visual_id", "") or ""),
            "icon": icon_path,
            "icon_id": icon_id,
            "path": str(path.relative_to(NYTHARA)),
        }
        item_order.append(item_id)
    item_order.sort(key=lambda value: item_defs[value]["name"].casefold())

    enemy_defs: dict[str, dict[str, Any]] = {}
    for path in sorted((NYTHARA / "data" / "definitions" / "enemies").glob("*.tres")):
        if path.name.endswith("_appearance.tres") or path.name.endswith("_stats.tres"):
            continue
        tres = Tres(path)
        enemy_id = get_id(tres)
        if not enemy_id:
            continue
        stats = load_tres(tres.ext_path("combat_stats"))
        appearance = load_tres(tres.ext_path("appearance"))
        loot = load_tres(tres.ext_path("loot_table"))
        status = load_tres(tres.ext_path("status_effect"))
        boss_sub = tres.sub_dict(tres.res.get("boss_definition"))
        phases: list[dict[str, Any]] = []
        for phase_id in refs(boss_sub.get("phases")):
            phase = tres.sub.get(phase_id)
            if not phase:
                continue
            phases.append(
                {
                    "phase": int(scalar(phase.get("phase"), 1)),
                    "threshold": float(scalar(phase.get("health_threshold"), 1.0)),
                    "abilities": string_list(phase.get("abilities")),
                    "attacks": string_list(phase.get("attacks")),
                }
            )
        phases.sort(key=lambda value: value["phase"])
        enemy_defs[enemy_id] = {
            "id": enemy_id,
            "name": tres.get("display_name", enemy_id),
            "archetype": int(tres.get("archetype", 0)),
            "level": int(tres.get("level", 1)),
            "max_level": int(tres.get("max_level", 1)),
            "xp": int(tres.get("xp_reward", 0)),
            "health": int(stats.get("max_health", 0)) if stats else 0,
            "attack": int(stats.get("attack_power", 0)) if stats else 0,
            "armor": int(stats.get("armor", 0)) if stats else 0,
            "attack_range": scalar(stats.get("attack_range")) if stats else None,
            "attack_cooldown": scalar(stats.get("attack_cooldown")) if stats else None,
            "move_speed": scalar(stats.get("move_speed")) if stats else None,
            "aggro": scalar(tres.get("aggro_range")),
            "leash": scalar(tres.get("leash_range")),
            "respawn": scalar(tres.get("respawn_delay")),
            "telegraph": scalar(tres.get("telegraph_duration")),
            "recovery": scalar(tres.get("recovery_duration")),
            "attack_zone": scalar(tres.get("attack_zone_radius")),
            "cleave_range": scalar(tres.get("cleave_range")),
            "cleave_angle": scalar(tres.get("cleave_angle_degrees")),
            "projectile_speed": scalar(tres.get("projectile_speed")),
            "visual_id": str(appearance.get("visual_id", "")) if appearance else "",
            "height": scalar(appearance.get("character_height")) if appearance else None,
            "status": str(status.get("display_name", "")) if status else "",
            "loot": get_id(loot),
            "loot_name": str(loot.get("display_name", "")) if loot else "",
            "boss_id": str(boss_sub.get("id", "")) if boss_sub else "",
            "phases": phases,
            "path": str(path.relative_to(NYTHARA)),
        }

    loot_defs: dict[str, dict[str, Any]] = {}
    loot_item_entries: dict[str, list[dict[str, Any]]] = {}
    for path in sorted((NYTHARA / "data" / "loot").glob("*.tres")):
        tres = Tres(path)
        loot_id = get_id(tres)
        if not loot_id:
            continue
        entries: list[dict[str, Any]] = []
        for sub_id in refs(tres.res.get("entries")):
            sub = tres.sub.get(sub_id, {})
            item_id = str(scalar(sub.get("item_id"), ""))
            entries.append(
                {
                    "item_id": item_id,
                    "chance": float(scalar(sub.get("chance_percent"), 0)),
                    "min": int(scalar(sub.get("min_quantity"), 1)),
                    "max": int(scalar(sub.get("max_quantity"), 1)),
                }
            )
        loot_defs[loot_id] = {
            "id": loot_id,
            "name": tres.get("display_name", loot_id),
            "entries": entries,
        }
        for entry in entries:
            loot_item_entries.setdefault(entry["item_id"], []).append({"loot": loot_id, **entry})

    npc_defs: dict[str, dict[str, Any]] = {}
    for path in sorted((NYTHARA / "data" / "npcs").glob("*.tres")):
        tres = Tres(path)
        npc_id = get_id(tres)
        if not npc_id:
            continue
        vendor_path = tres.ext_path("vendor_definition")
        vendor = load_tres(vendor_path)
        vendor_paths: list[dict[str, Any]] = []
        if vendor:
            for sub_id in refs(vendor.res.get("offers")):
                sub = vendor.sub.get(sub_id, {})
                item_id = str(scalar(sub.get("item_id"), ""))
                if item_id:
                    vendor_paths.append(
                        {
                            "item_id": item_id,
                            "price": int(scalar(sub.get("price"), 0)),
                        }
                    )
        dialogue_path = tres.ext_path("dialogue")
        dialogue = load_tres(dialogue_path)
        opening = ""
        if dialogue:
            start_ids = refs(dialogue.res.get("start_node_ids"))
            for node_id in start_ids:
                node = dialogue.sub.get(node_id, {})
                if node.get("text"):
                    opening = str(scalar(node.get("text"), ""))
                    break
        elif isinstance(tres.res.get("dialogue"), str) and "SubResource" in tres.res.get("dialogue", ""):
            dialogue_sub = tres.sub_dict(tres.res.get("dialogue"))
            for sub_id in refs(dialogue_sub.get("start_node_ids")):
                node = tres.sub.get(sub_id, {})
                if node.get("text"):
                    opening = str(scalar(node.get("text"), ""))
                    break
        npc_defs[npc_id] = {
            "id": npc_id,
            "name": tres.get("display_name", npc_id),
            "interaction": str(tres.get("interaction_label", "Talk to")),
            "appearance_id": str(tres.get("appearance_id", "")),
            "service": str(tres.get("service_id", "")),
            "quest_id": str(tres.get("quest_id", "")),
            "vendor": [offer for offer in vendor_paths],
            "vendor_name": str(vendor.get("display_name", "")) if vendor else "",
            "greeting": str(vendor.get("greeting", "")) if vendor else "",
            "opening": opening,
            "path": str(path.relative_to(NYTHARA)),
        }

    quest_defs: dict[str, dict[str, Any]] = {}
    for path in sorted((NYTHARA / "data" / "quests").glob("*.tres")):
        tres = Tres(path)
        quest_id = get_id(tres)
        if not quest_id:
            continue
        objectives: list[dict[str, Any]] = []
        for sub_id in refs(tres.res.get("objectives")):
            sub = tres.sub.get(sub_id, {})
            objectives.append(
                {
                    "id": str(scalar(sub.get("id"), "")),
                    "type": int(scalar(sub.get("type"), 0)),
                    "target_id": str(scalar(sub.get("target_id"), "")),
                    "count": int(scalar(sub.get("required_count"), 1)),
                    "description": str(scalar(sub.get("description"), "")),
                }
            )
        rewards: list[dict[str, Any]] = []
        for sub_id in refs(tres.res.get("rewards")):
            sub = tres.sub.get(sub_id, {})
            rewards.append(
                {
                    "item_id": str(scalar(sub.get("item_id"), "")),
                    "quantity": int(scalar(sub.get("quantity"), 1)),
                    "currency": int(scalar(sub.get("currency_amount"), 0)),
                    "xp": int(scalar(sub.get("xp_amount"), 0)),
                }
            )
        quest_defs[quest_id] = {
            "id": quest_id,
            "name": tres.get("title", quest_id),
            "description": tres.get("description", ""),
            "objectives": objectives,
            "rewards": rewards,
            "turn_in": str(tres.get("turn_in_npc_id", "")),
            "prerequisites": string_list(tres.res.get("prerequisite_quests")),
            "path": str(path.relative_to(NYTHARA)),
        }

    skill_defs: dict[str, dict[str, Any]] = {}
    for path in sorted((NYTHARA / "data" / "skills").glob("*.tres")):
        tres = Tres(path)
        skill_id = get_id(tres)
        if not skill_id:
            continue
        skill_defs[skill_id] = {
            "id": skill_id,
            "name": tres.get("display_name", skill_id),
            "description": tres.get("description", ""),
            "type": int(tres.get("type", 0)),
            "target": int(tres.get("target", 0)),
            "effect": int(tres.get("effect", 0)),
            "cost": int(tres.get("skill_point_cost", 1)),
            "required_level": int(tres.get("required_level", 1)),
            "cooldown": scalar(tres.get("cooldown")),
            "range": scalar(tres.get("range")),
            "damage_multiplier": scalar(tres.get("damage_multiplier")),
            "heal_percent": int(tres.get("heal_percent", 0)),
            "attack_bonus": int(tres.get("attack_bonus", 0)),
            "armor_bonus": int(tres.get("armor_bonus", 0)),
            "health_bonus": int(tres.get("max_health_bonus", 0)),
            "required_skill": str(tres.get("required_skill_id", "")),
            "guard_duration": scalar(tres.get("guard_duration")),
            "max_targets": int(tres.get("max_targets", 5)),
            "rank_damage": [float(value) for value in re.findall(r"[\d.]+", str(tres.res.get("rank_damage_multipliers", "")))],
            "rank_heal": [int(value) for value in re.findall(r"\d+", str(tres.res.get("rank_heal_percents", "")))],
            "rank_guard": [int(value) for value in re.findall(r"\d+", str(tres.res.get("rank_guard_armor", "")))],
            "icon_id": str(tres.get("icon_id", "")),
        }

    resource_defs: dict[str, dict[str, Any]] = {}
    for path in sorted((NYTHARA / "data" / "resources").glob("*.tres")):
        tres = Tres(path)
        resource_id = get_id(tres)
        if not resource_id:
            continue
        texture = tres.ext_path("appearance_texture")
        resource_defs[resource_id] = {
            "id": resource_id,
            "name": tres.get("display_name", resource_id),
            "verb": str(tres.get("interaction_verb", "Gather")),
            "item_id": str(tres.get("item_id", "")),
            "min": int(tres.get("min_amount", 1)),
            "max": int(tres.get("max_amount", 1)),
            "respawn": scalar(tres.get("respawn_seconds")),
            "texture": str(texture.relative_to(NYTHARA)) if texture else "",
            "path": str(path.relative_to(NYTHARA)),
        }

    recipes: list[dict[str, Any]] = []
    for path in sorted((NYTHARA / "data" / "recipes").glob("*.tres")):
        tres = Tres(path)
        ingredients = []
        for sub_id in refs(tres.res.get("ingredients")):
            sub = tres.sub.get(sub_id, {})
            ingredients.append(
                {
                    "item_id": str(scalar(sub.get("item_id"), "")),
                    "quantity": int(scalar(sub.get("quantity"), 1)),
                }
            )
        outputs = []
        for sub_id in refs(tres.res.get("outputs")):
            sub = tres.sub.get(sub_id, {})
            outputs.append(
                {
                    "item_id": str(scalar(sub.get("item_id"), "")),
                    "quantity": int(scalar(sub.get("quantity"), 1)),
                }
            )
        recipes.append(
            {
                "id": get_id(tres),
                "name": str(tres.get("display_name", get_id(tres))),
                "description": str(tres.get("description", "")),
                "station": str(tres.get("station_type", "")),
                "ingredients": ingredients,
                "outputs": outputs,
            }
        )

    # --- scene indexes ------------------------------------------------------
    enemy_locations: dict[str, list[dict[str, Any]]] = {}
    enemy_encounters: dict[str, list[dict[str, Any]]] = {}
    world_encounters: dict[str, list[dict[str, Any]]] = {}
    world_npcs: dict[str, list[str]] = {}
    world_resources: dict[str, list[str]] = {}
    scene_transitions: list[dict[str, Any]] = []

    for scene_path, scene in scenes.items():
        world_id = scene_worlds.get(scene_path)
        if not world_id:
            continue
        world_name = worlds[world_id]["name"]
        for node in scene.spawns():
            enemy_path = node.enemy_path or ""
            enemy_id = get_id(load_tres(NYTHARA / enemy_path)) if enemy_path.startswith("data/") else ""
            if not enemy_id:
                continue
            enemy_locations.setdefault(enemy_id, []).append(
                {"world_id": world_id, "name": world_name, "level": node.level}
            )
        for encounter_node in scene.encounter_nodes():
            encounter = load_tres(NYTHARA / encounter_node.definition) if encounter_node.definition else None
            members = [node for node in scene.spawns() if node.encounter == encounter_node.path]
            if not members:
                continue
            counts: list[dict[str, Any]] = []
            for member in members:
                enemy_path = member.enemy_path or ""
                enemy = load_tres(NYTHARA / enemy_path) if enemy_path.startswith("data/") else None
                if enemy:
                    counts.append(
                        {
                            "name": enemy.get("display_name", ""),
                            "id": get_id(enemy),
                            "level": member.level,
                        }
                    )
                    enemy_encounters.setdefault(get_id(enemy), []).append(
                        {
                            "world_id": world_id,
                            "encounter": str(encounter.get("display_name", encounter_node.name)) if encounter else encounter_node.name,
                            "level": member.level,
                        }
                    )
            room = {
                "name": re.sub(r"(?<!^)(?=[A-Z])", " ", encounter_node.name),
                "id": get_id(encounter),
                "members": counts,
            }
            world_encounters.setdefault(world_id, []).append(room)
        for npc_node in scene.npcs():
            npc_path = npc_node.definition or ""
            npc = load_tres(NYTHARA / npc_path) if npc_path.startswith("data/") else None
            if npc:
                world_npcs.setdefault(world_id, []).append(get_id(npc))
        for node in scene.nodes:
            if node.definition and node.definition.startswith("data/resources/"):
                world_resources.setdefault(world_id, []).append(get_id(load_tres(NYTHARA / node.definition)))
            if node.instance_path and node.instance_path in resource_scene_defs:
                resource_path = resource_scene_defs[node.instance_path]
                resource = load_tres(NYTHARA / resource_path)
                if resource:
                    world_resources.setdefault(world_id, []).append(get_id(resource))
        for transition in scene.transitions():
            scene_transitions.append(
                {
                    "source": world_id,
                    "target": transition.target_world,
                    "label": transition.label or "",
                    "portal_id": transition.portal_id or "",
                }
            )

    # --- lookup registries --------------------------------------------------
    world_names = {wid: worlds[wid]["name"] for wid in worlds}
    region_ids = [
        wid
        for wid, region in graph_regions.items()
        if region.get("kind") == "region"
    ] + (["world_prototype_valley"] if "world_prototype_valley" in worlds else [])
    region_ids = sorted(set(region_ids), key=lambda wid: world_names.get(wid, wid).casefold())

    # Dawnwatch is both the start-city world and the Dawnlands region. Give the
    # region its own stable record id so it cannot collide with the city entry.
    def region_record_id(world_id: str) -> str:
        return "region_dawnlands" if world_id == "world_start_city" else world_id

    authored_regions = {
        "world_start_city",
        "world_prototype_valley",
        "world_whispering_grove",
        "world_silverwood",
    }

    dungeon_ids = [
        wid
        for wid, region in graph_regions.items()
        if region.get("kind") == "dungeon" and wid in ("world_hollow_ruins", "world_moonroot_sanctum")
    ]

    city_ids = ["world_start_city"] if "world_start_city" in worlds else []

    refs_by_type: dict[str, dict[str, str]] = {
        "item": {iid: item_defs[iid]["name"] for iid in item_defs},
        "equipment": {
            iid: item_defs[iid]["name"] for iid in item_defs if item_defs[iid]["slot"]
        },
        "monster": {eid: enemy_defs[eid]["name"] for eid in enemy_defs},
        "boss": {
            eid: enemy_defs[eid]["name"] for eid in enemy_defs if enemy_defs[eid]["boss_id"]
        },
        "dungeon": {wid: world_names[wid] for wid in dungeon_ids},
        "region": {region_record_id(wid): world_names[wid] for wid in region_ids},
        "city": {wid: world_names[wid] for wid in city_ids},
        "npc": {nid: npc_defs[nid]["name"] for nid in npc_defs},
        "quest": {qid: quest_defs[qid]["name"] for qid in quest_defs},
        "skill": {sid: skill_defs[sid]["name"] for sid in skill_defs},
        "resource": {rid: resource_defs[rid]["name"] for rid in resource_defs},
        "loot": {lid: loot_defs[lid]["name"] for lid in loot_defs},
    }

    entity_kind = {}
    for wid in region_ids:
        entity_kind[wid] = ("region", region_record_id(wid))
    for wid in dungeon_ids:
        entity_kind[wid] = ("dungeon", wid)
    for wid in city_ids:
        entity_kind[wid] = ("city", wid)

    def entity_link(world_id: str, meta: str | None = None) -> dict[str, Any] | None:
        kind, entity_id = entity_kind.get(world_id, (None, None))
        if not kind or not entity_id:
            return None
        return link_entity(kind, entity_id, world_names.get(world_id, entity_id), meta)

    def enemy_world_links(enemy_id: str) -> list[dict[str, Any]]:
        links = []
        seen = set()
        for location in enemy_locations.get(enemy_id, []):
            wid = location["world_id"]
            if wid in seen:
                continue
            seen.add(wid)
            link = entity_link(wid)
            if link:
                links.append(link)
        return links

    def enemy_levels(enemy_id: str) -> str:
        levels = sorted({loc["level"] for loc in enemy_locations.get(enemy_id, []) if loc["level"] is not None})
        return ", ".join(f"Lv {level}" for level in levels)

    def loot_meta(entry: dict[str, Any]) -> str:
        chance = entry["chance"]
        quantity = (
            str(entry["min"])
            if entry["min"] == entry["max"]
            else f"{entry['min']}\u2013{entry['max']}"
        )
        chance_text = "Guaranteed" if chance >= 100 else f"{fmt_number(chance)}%"
        return f"{chance_text} \u00b7 {quantity}\u00d7"

    # --- quest relationships ------------------------------------------------
    quest_regions: dict[str, set[str]] = {}
    quest_dungeons: dict[str, set[str]] = {}
    monster_quests: dict[str, set[str]] = {}
    for quest in quest_defs.values():
        for objective in quest["objectives"]:
            target = objective["target_id"]
            if target in enemy_defs:
                monster_quests.setdefault(target, set()).add(quest["id"])
                locations = {loc["world_id"] for loc in enemy_locations.get(target, [])}
                # A generic monster that appears in several regions does not
                # identify one quest area. Only a unique spawn location (or a
                # boss tied to one dungeon) is evidence enough.
                if enemy_defs[target]["boss_id"] or len(locations) == 1:
                    for wid in locations:
                        if wid in dungeon_ids:
                            quest_dungeons.setdefault(quest["id"], set()).add(wid)
                        elif wid in region_ids:
                            quest_regions.setdefault(quest["id"], set()).add(wid)
            elif target.startswith("poi_"):
                slug = target.removeprefix("poi_")
                for wid in region_ids:
                    if wid.removeprefix("world_") in slug or slug.startswith(wid.removeprefix("world_")):
                        quest_regions.setdefault(quest["id"], set()).add(wid)
        for wid in list(quest_dungeons.get(quest["id"], set())):
            region = None
            for portal in portals:
                if portal["destination_world_id"] == wid:
                    region = portal["source_world_id"]
                    break
            if region:
                quest_regions.setdefault(quest["id"], set()).add(region)

    # --- item reverse indexes ----------------------------------------------
    item_drops: dict[str, list[dict[str, Any]]] = {}
    for enemy in enemy_defs.values():
        loot = loot_defs.get(enemy["loot"])
        if not loot:
            continue
        for entry in loot["entries"]:
            item_drops.setdefault(entry["item_id"], []).append(
                {"enemy": enemy, "loot": loot, "entry": entry}
            )

    item_vendors: dict[str, list[dict[str, Any]]] = {}
    for npc in npc_defs.values():
        for offer in npc["vendor"]:
            item_vendors.setdefault(offer["item_id"], []).append({"npc": npc, "price": offer["price"]})

    item_recipes: dict[str, list[dict[str, Any]]] = {}
    for recipe in recipes:
        for output in recipe["outputs"]:
            item_recipes.setdefault(output["item_id"], []).append({"recipe": recipe, "role": "output"})
        for ingredient in recipe["ingredients"]:
            item_recipes.setdefault(ingredient["item_id"], []).append({"recipe": recipe, "role": "ingredient"})

    quest_rewards_items: dict[str, list[dict[str, Any]]] = {}
    for quest in quest_defs.values():
        for reward in quest["rewards"]:
            if reward["item_id"]:
                quest_rewards_items.setdefault(reward["item_id"], []).append({"quest": quest, "reward": reward})

    # --- entries: items and equipment --------------------------------------
    def build_item_facts(item: dict[str, Any]) -> list[dict[str, str]]:
        facts: list[dict[str, str]] = []
        add_fact(facts, "Stable ID", item["id"])
        add_fact(facts, "Category", item["category_label"])
        add_fact(facts, "Rarity", item["rarity_label"])
        add_fact(facts, "Max stack", item["max_stack"])
        add_fact(facts, "Sell value", f"{item['sell_value']} Crowns")
        if item["slot"]:
            add_fact(facts, "Equipment slot", SLOT_LABELS.get(item["slot"], item["slot"].replace("_", " ").title()))
        if item["attack"]:
            add_fact(facts, "Attack", f"+{item['attack']}")
        if item["armor"]:
            add_fact(facts, "Armor", f"+{item['armor']}")
        if item["health"]:
            add_fact(facts, "Max health", f"+{item['health']}")
        if item["heal"]:
            add_fact(facts, "Restores", f"{item['heal']} health")
        if item["slot"] and item["level_authored"]:
            add_fact(facts, "Level requirement", item["level_requirement"])
        if item["slot"]:
            add_fact(facts, "Wearable visual", "Yes \u2014 " + item["visual_id"] if item["visual_id"] else "No \u2014 stat-only")
        return facts

    def build_item_sections(item: dict[str, Any]) -> list[dict[str, Any]]:
        sections: list[dict[str, Any]] = []
        drops = []
        for drop in item_drops.get(item["id"], []):
            drops.append(
                link_entity(
                    "monster",
                    drop["enemy"]["id"],
                    drop["enemy"]["name"],
                    loot_meta(drop["entry"]),
                )
            )
        add_link_section(sections, "Dropped by", drops)

        sold = []
        for offer in item_vendors.get(item["id"], []):
            sold.append(
                link_entity("npc", offer["npc"]["id"], offer["npc"]["name"], f"{offer['price']} Crowns")
            )
        add_link_section(sections, "Sold by", sold)

        if item["id"] in quest_rewards_items:
            add_link_section(
                sections,
                "Quest reward",
                [
                    link_entity("quest", reward["quest"]["id"], reward["quest"]["name"])
                    for reward in quest_rewards_items[item["id"]]
                ],
            )

        recipe_entries = item_recipes.get(item["id"], [])
        if recipe_entries:
            recipe_facts = []
            for entry in recipe_entries:
                recipe = entry["recipe"]
                ingredients = " \u00b7 ".join(
                    f"{item_defs.get(ing['item_id'], {}).get('name', ing['item_id'])} \u00d7{ing['quantity']}"
                    for ing in recipe["ingredients"]
                )
                outputs = " \u00b7 ".join(
                    f"{item_defs.get(out['item_id'], {}).get('name', out['item_id'])} \u00d7{out['quantity']}"
                    for out in recipe["outputs"]
                )
                add_fact(recipe_facts, recipe["name"], f"{recipe['station'].title()} \u00b7 requires {ingredients} \u00b7 yields {outputs}")
            if recipe_facts:
                sections.append({"title": "Crafting", "facts": recipe_facts})
        return sections

    items: list[dict[str, Any]] = []
    for item_id in item_order:
        item = item_defs[item_id]
        badges = [
            {"label": item["category_label"], "tone": "cyan"},
            {"label": item["rarity_label"], "tone": RARITY_TONES.get(item["rarity_label"], "muted")},
        ]
        entry = make_entry(
            entry_id=item_id,
            kind="item",
            name=item["name"],
            subtitle=f"{item['category_label']} \u00b7 {item['rarity_label']}",
            description=item["description"],
            image=item["icon"],
            image_alt=f"{item['name']} inventory icon",
            badges=badges,
            facts=build_item_facts(item),
            sections=build_item_sections(item),
            filters={
                "category": item["category_label"],
                "rarity": item["rarity_label"],
                **({"slot": SLOT_LABELS.get(item["slot"], item["slot"].title())} if item["slot"] else {}),
            },
            level=item["level_requirement"] if item["level_authored"] else None,
            rarity=item["rarity"],
            category=item["category_label"],
        )
        check_image(entry)
        items.append(entry)

    equipment: list[dict[str, Any]] = []
    for item_id in item_order:
        item = item_defs[item_id]
        if not item["slot"]:
            continue
        facts = build_item_facts(item)
        sections = build_item_sections(item)
        sections.insert(0, {
            "title": "Item record",
            "links": [link_entity("item", item_id, item["name"], item["rarity_label"])],
        })
        entry = make_entry(
            entry_id=item_id,
            kind="equipment",
            name=item["name"],
            subtitle=f"{SLOT_LABELS.get(item['slot'], item['slot'].title())} \u00b7 {item['rarity_label']}",
            description=item["description"],
            image=item["icon"],
            image_alt=f"{item['name']} inventory icon",
            badges=[
                {"label": SLOT_LABELS.get(item["slot"], item["slot"].title()), "tone": "gold"},
                {"label": item["rarity_label"], "tone": RARITY_TONES.get(item["rarity_label"], "muted")},
            ],
            facts=facts,
            sections=sections,
            filters={
                "slot": SLOT_LABELS.get(item["slot"], item["slot"].title()),
                "rarity": item["rarity_label"],
                "category": item["category_label"],
            },
            level=item["level_requirement"],
            rarity=item["rarity"],
            category=item["category_label"],
        )
        check_image(entry)
        equipment.append(entry)

    # --- monsters and bosses ------------------------------------------------
    def monster_sections(enemy: dict[str, Any], boss: bool) -> list[dict[str, Any]]:
        sections: list[dict[str, Any]] = []
        locations = enemy_world_links(enemy["id"])
        add_link_section(sections, "Found in", locations)

        loot = loot_defs.get(enemy["loot"])
        if loot:
            add_link_section(
                sections,
                "Loot table",
                [link_entity("loot", loot["id"], loot["name"])],
            )
            drops = [
                link_entity(
                    "item",
                    entry["item_id"],
                    item_defs.get(entry["item_id"], {}).get("name", entry["item_id"]),
                    loot_meta(entry),
                )
                for entry in loot["entries"]
            ]
            add_link_section(sections, "Loot", drops)

        encounters = []
        for record in enemy_encounters.get(enemy["id"], []):
            link = entity_link(record["world_id"], f"{record['encounter']} \u00b7 Lv {record['level']}")
            if link and all(existing["id"] != link["id"] or existing.get("meta") != link.get("meta") for existing in encounters):
                encounters.append(link)
        add_link_section(sections, "Encounters", encounters)

        if enemy["id"] in monster_quests:
            add_link_section(
                sections,
                "Quests",
                [link_entity("quest", qid, quest_defs[qid]["name"]) for qid in sorted(monster_quests[enemy["id"]] if enemy["id"] in monster_quests else set())],
            )

        if boss:
            ordered = sorted(enemy["phases"], key=lambda value: value["phase"])
            phases = []
            for index, phase in enumerate(ordered):
                upper = int(round(phase["threshold"] * 100))
                lower = int(round(ordered[index + 1]["threshold"] * 100)) if index + 1 < len(ordered) else 0
                bits = [f"{lower}\u2013{upper}% health"]
                abilities = ", ".join(humanize_identifier(value) for value in phase["abilities"])
                attacks = ", ".join(humanize_identifier(value) for value in phase["attacks"])
                if abilities:
                    bits.append(f"Abilities: {abilities}")
                if attacks:
                    bits.append(f"Heavy attack cycle: {attacks}")
                phases.append({"label": f"Phase {phase['phase']}", "value": " \u00b7 ".join(bits)})
            if phases:
                sections.append({"title": "Phases", "facts": phases})
        return sections

    monsters: list[dict[str, Any]] = []
    bosses: list[dict[str, Any]] = []
    for enemy_id in sorted(enemy_defs, key=lambda eid: enemy_defs[eid]["name"].casefold()):
        enemy = enemy_defs[enemy_id]
        is_boss = bool(enemy["boss_id"])
        classification = "Boss" if is_boss else "Normal"
        archetype = ARCHETYPES.get(enemy["archetype"], "Melee")
        location_names = []
        for link in enemy_world_links(enemy_id):
            location_names.append(link["name"])
        loot = loot_defs.get(enemy["loot"])
        facts: list[dict[str, str]] = []
        add_fact(facts, "Stable ID", enemy_id)
        add_fact(facts, "Classification", classification)
        add_fact(facts, "Archetype", archetype)
        add_fact(facts, "Levels", fmt_range(enemy["level"], enemy["max_level"]))
        add_fact(facts, "Health", enemy["health"])
        add_fact(facts, "Attack", enemy["attack"])
        add_fact(facts, "Armor", enemy["armor"])
        add_fact(facts, "XP reward", enemy["xp"])
        if enemy["attack_cooldown"] is not None:
            add_fact(facts, "Attack cooldown", fmt_duration(enemy["attack_cooldown"]))
        if enemy["move_speed"] is not None:
            add_fact(facts, "Move speed", f"{fmt_number(enemy['move_speed'])} m/s")
        if enemy["aggro"] is not None:
            add_fact(facts, "Aggro range", f"{fmt_number(enemy['aggro'])} m")
        if enemy["leash"] is not None:
            add_fact(facts, "Leash range", f"{fmt_number(enemy['leash'])} m")
        if enemy["respawn"] is not None:
            add_fact(facts, "Respawn", fmt_duration(enemy["respawn"]))
        if enemy["status"]:
            add_fact(facts, "Status effect", enemy["status"])
        if enemy["loot"]:
            add_fact(facts, "Loot table", enemy["loot_name"])

        visual = CREATURES.get(enemy_id, {})
        image = visual.get("image")
        image_alt = visual.get("image_alt")

        filters = {
            "classification": classification,
            "archetype": archetype,
            "region": location_names,
        }
        entry = make_entry(
            entry_id=enemy_id,
            kind="monster",
            name=enemy["name"],
            subtitle=f"{classification} \u00b7 {archetype}",
            image=image,
            image_alt=image_alt,
            badges=[
                {"label": classification, "tone": "gold" if is_boss else "muted"},
                {"label": archetype, "tone": "forest"},
            ],
            facts=facts,
            sections=monster_sections(enemy, is_boss),
            filters=filters,
            level=enemy["level"],
            category=archetype,
        )
        check_image(entry)
        monsters.append(entry)

        if is_boss:
            dungeon_id = None
            for wid, rooms in world_encounters.items():
                for room in rooms:
                    if any(member["id"] == enemy_id for member in room["members"]) and wid in dungeon_ids:
                        dungeon_id = wid
                        break
                if dungeon_id:
                    break
            boss_facts = list(facts)
            if dungeon_id:
                add_fact(boss_facts, "Dungeon", world_names[dungeon_id])
            if enemy["phases"]:
                add_fact(boss_facts, "Phases", len(enemy["phases"]))
            boss_sections: list[dict[str, Any]] = []
            if dungeon_id:
                boss_sections.append({
                    "title": "Dungeon",
                    "links": [link_entity("dungeon", dungeon_id, world_names[dungeon_id])],
                })
            boss_sections.extend(monster_sections(enemy, True))
            source_region = None
            if dungeon_id:
                entry_portal = next((p for p in portals if p["destination_world_id"] == dungeon_id and p["source_world_id"] != dungeon_id), None)
                source_region = world_names.get(entry_portal["source_world_id"]) if entry_portal else None
            boss_entry = make_entry(
                entry_id=enemy_id,
                kind="boss",
                name=enemy["name"],
                subtitle=f"Boss \u00b7 {archetype}",
                image=image,
                image_alt=image_alt,
                badges=[
                    {"label": "Boss", "tone": "gold"},
                    {"label": archetype, "tone": "forest"},
                ],
                facts=boss_facts,
                sections=boss_sections,
                filters={
                    "region": [source_region] if source_region else [],
                    "dungeon": world_names.get(dungeon_id, ""),
                },
                level=enemy["level"],
                category=archetype,
            )
            check_image(boss_entry)
            bosses.append(boss_entry)

    # --- dungeons -----------------------------------------------------------
    dungeons: list[dict[str, Any]] = []
    dungeon_regions: dict[str, str] = {}
    for dungeon_id in sorted(dungeon_ids, key=lambda wid: world_names[wid].casefold()):
        region = graph_regions.get(dungeon_id, {})
        rooms = world_encounters.get(dungeon_id, [])
        boss = next((e for e in enemy_defs.values() if e["boss_id"] and any(room for room in rooms if any(m["id"] == e["id"] for m in room["members"]))), None)
        entry_portal = next(
            (portal for portal in portals if portal["destination_world_id"] == dungeon_id and portal["source_world_id"] != dungeon_id),
            None,
        )
        source_world = entry_portal["source_world_id"] if entry_portal else None
        if source_world:
            dungeon_regions[dungeon_id] = source_world
        facts: list[dict[str, str]] = []
        add_fact(facts, "World ID", dungeon_id)
        if source_world:
            add_fact(facts, "Region", world_names.get(source_world, source_world))
        add_fact(facts, "Levels", fmt_range(region.get("level_range", [None, None])[0], region.get("level_range", [None, None])[1]))
        add_fact(facts, "Biome", BIOME_LABELS.get(region.get("biome", ""), region.get("biome", "")))
        if entry_portal:
            add_fact(facts, "Entry", entry_portal["display_name"])
            requirement = []
            if entry_portal.get("required_quest") and entry_portal["required_quest"] in quest_defs:
                requirement.append(quest_defs[entry_portal["required_quest"]]["name"])
            if entry_portal.get("required_level", 1) > 1:
                requirement.append(f"Level {entry_portal['required_level']}")
            add_fact(facts, "Requirement", " \u00b7 ".join(requirement) if requirement else "None")
        elif region.get("level_range"):
            add_fact(facts, "Requirement", "None")

        sections: list[dict[str, Any]] = []
        if rooms:
            room_facts = []
            for room in rooms:
                names = {}
                for member in room["members"]:
                    names.setdefault(member["name"], []).append(member["level"])
                parts = []
                for name, levels in names.items():
                    level_text = ", ".join(str(level) for level in levels if level is not None)
                    parts.append(f"{len(levels)} \u00d7 {name}" + (f" \u00b7 Lv {level_text}" if level_text else ""))
                room_facts.append({"label": room["name"], "value": " \u00b7 ".join(parts)})
            if room_facts:
                sections.append({"title": "Encounter sequence", "facts": room_facts})
        if boss:
            sections.append({
                "title": "Boss",
                "links": [link_entity("boss", boss["id"], boss["name"], f"Lv {boss['level']}\u2013{boss['max_level']}")],
            })
        if boss:
            loot = loot_defs.get(boss["loot"])
            if loot:
                add_link_section(
                    sections,
                    "Loot",
                    [
                        link_entity(
                            "item",
                            entry["item_id"],
                            item_defs.get(entry["item_id"], {}).get("name", entry["item_id"]),
                            loot_meta(entry),
                        )
                        for entry in loot["entries"]
                    ],
                )
        quest_links = [
            link_entity("quest", qid, quest_defs[qid]["name"])
            for qid in sorted({qid for qid, ids in quest_dungeons.items() if dungeon_id in ids})
        ]
        add_link_section(sections, "Related quests", quest_links)
        if source_world:
            add_link_section(sections, "Region", [entity_link(source_world)])
        boss_filter = boss["name"] if boss else "None"
        requirement_label = "None"
        if entry_portal:
            if entry_portal.get("required_quest") in quest_defs:
                requirement_label = quest_defs[entry_portal["required_quest"]]["name"]
            elif entry_portal.get("required_level", 1) > 1:
                requirement_label = f"Level {entry_portal['required_level']}"
        dungeon = make_entry(
            entry_id=dungeon_id,
            kind="dungeon",
            name=world_names[dungeon_id],
            subtitle=f"Authored dungeon \u00b7 {BIOME_LABELS.get(region.get('biome', ''), region.get('biome', '')).title()}",
            description=worlds[dungeon_id].get("description", ""),
            image=SITE_IMAGES["hollow_ruins"][0] if dungeon_id == "world_hollow_ruins" else SITE_IMAGES["moonroot_sanctum"][0],
            image_alt=SITE_IMAGES["hollow_ruins"][1] if dungeon_id == "world_hollow_ruins" else SITE_IMAGES["moonroot_sanctum"][1],
            badges=[
                {"label": "Dungeon", "tone": "violet"},
                {"label": f"Levels {fmt_range(region.get('level_range', [None, None])[0], region.get('level_range', [None, None])[1])}", "tone": "muted"},
            ],
            facts=facts,
            sections=sections,
            filters={
                "region": world_names.get(source_world, "") if source_world else "",
                "boss": boss_filter,
                "requirement": requirement_label,
            },
            level=region.get("level_range", [0])[0],
            category="Dungeon",
        )
        check_image(dungeon)
        dungeons.append(dungeon)

    # --- region connections ------------------------------------------------
    connection_map: dict[str, dict[str, dict[str, Any]]] = {}
    # Travel is directional. Each world scene / portal owns the label for the
    # exit it offers, so a region never claims another zone's return label.
    for portal in portals:
        source = portal["source_world_id"]
        target = portal["destination_world_id"]
        link = entity_link(target)
        if link:
            connection_map.setdefault(source, {})[target] = {
                **link,
                "meta": portal["display_name"],
            }
    for transition in scene_transitions:
        source = transition["source"]
        target = transition["target"]
        link = entity_link(target)
        if link:
            connection_map.setdefault(source, {})[target] = {
                **link,
                "meta": transition["label"] or "World path",
            }

    # --- regions ------------------------------------------------------------
    regions: list[dict[str, Any]] = []
    for region_id in sorted(region_ids, key=lambda wid: world_names[wid].casefold()):
        region = graph_regions.get(region_id, {})
        world = worlds[region_id]
        authored_scene = region_id in authored_regions
        level_range = region.get("level_range")
        biome = region.get("biome", "")
        facts: list[dict[str, str]] = []
        add_fact(facts, "World ID", region_id)
        add_fact(facts, "Realm", "Mortal" if region.get("realm_id") == "realm_mortal" else region.get("realm_id", ""))
        add_fact(facts, "Biome", BIOME_LABELS.get(biome, biome))
        if level_range:
            add_fact(facts, "Levels", fmt_range(level_range[0], level_range[1]))
        add_fact(facts, "World type", "Playable region" if authored_scene else "World map")
        if region.get("map_id"):
            add_fact(facts, "Map ID", region["map_id"])

        sections: list[dict[str, Any]] = []
        connections = list(connection_map.get(region_id, {}).values())
        add_link_section(sections, "Connected areas", connections)

        monster_links = []
        for enemy in enemy_defs.values():
            locations = [loc for loc in enemy_locations.get(enemy["id"], []) if loc["world_id"] == region_id]
            if locations:
                monster_links.append(
                    link_entity("monster", enemy["id"], enemy["name"], f"Lv {enemy['level']}\u2013{enemy['max_level']}")
                )
        add_link_section(sections, "Creatures", monster_links)

        npc_links = [
            link_entity("npc", nid, npc_defs[nid]["name"])
            for nid in sorted(set(world_npcs.get(region_id, [])))
        ]
        add_link_section(sections, "NPCs", npc_links)

        resource_links = [
            link_entity("resource", rid, resource_defs[rid]["name"])
            for rid in sorted(set(world_resources.get(region_id, [])))
            if rid in resource_defs
        ]
        add_link_section(sections, "Resources", resource_links)

        quest_links = [
            link_entity("quest", qid, quest_defs[qid]["name"])
            for qid, ids in sorted(quest_regions.items())
            if region_id in ids
        ]
        add_link_section(sections, "Quests", quest_links)

        dungeon_links = [
            link_entity("dungeon", did, world_names[did])
            for did in dungeon_ids
            if dungeon_regions.get(did) == region_id
        ]
        add_link_section(sections, "Dungeons", dungeon_links)

        city_links = [entity_link(cid) for cid in city_ids if cid == region_id]
        add_link_section(sections, "Settlement", [link for link in city_links if link])

        image = None
        image_alt = None
        slug = region_id.removeprefix("world_")
        if slug in SITE_IMAGES:
            image, image_alt = SITE_IMAGES[slug]
        display_name = region.get("display_name") or world_names[region_id]
        description = world.get("description", "")
        # World-definition descriptions that merely describe the generator are not
        # player-facing prose. Keep the authored facts and leave the field empty.
        if re.search(r"generated from WorldGraph", description, re.IGNORECASE):
            description = ""
        subtitle_parts = []
        if biome:
            subtitle_parts.append(BIOME_LABELS.get(biome, biome).title())
        if level_range:
            subtitle_parts.append(f"Levels {fmt_range(level_range[0], level_range[1])}")
        if not subtitle_parts:
            subtitle_parts.append("Playable region" if authored_scene else "World map")
        entry = make_entry(
            entry_id=region_record_id(region_id),
            kind="region",
            name=display_name,
            subtitle=" \u00b7 ".join(subtitle_parts),
            description=description,
            image=image,
            image_alt=image_alt,
            badges=[
                {"label": "Region", "tone": "forest"},
                {"label": "Playable" if authored_scene else "World map", "tone": "muted"},
            ],
            facts=facts,
            sections=sections,
            filters={
                **(({"biome": BIOME_LABELS.get(biome, biome)}) if biome else {}),
                "type": "Playable region" if authored_scene else "World map",
                "realm": "Mortal",
            },
            level=level_range[0] if level_range else None,
            category="Region",
        )
        check_image(entry)
        regions.append(entry)

    # --- cities -------------------------------------------------------------
    cities: list[dict[str, Any]] = []
    for city_id in city_ids:
        world = worlds[city_id]
        city_doc_path = NYTHARA / "data" / "cities" / "start_city.json"
        city_doc = json.loads(city_doc_path.read_text(encoding="utf-8")) if city_doc_path.exists() else {}
        districts = city_doc.get("districts", [])
        district_names = [re.sub(r"(?<!^)(?=[A-Z])", " ", value) for value in districts]
        facts: list[dict[str, str]] = []
        add_fact(facts, "World ID", city_id)
        region_world = "world_start_city"
        add_fact(facts, "Region", "Dawnlands")
        add_fact(facts, "Districts", len(districts))
        if city_doc.get("bounds"):
            add_fact(facts, "City bounds", f"\u00b1{fmt_number(city_doc['bounds'])} m")
        if district_names:
            add_fact(facts, "District names", " \u00b7 ".join(district_names))
        sections: list[dict[str, Any]] = []
        add_link_section(sections, "Region", [
            link_entity("region", region_record_id("world_start_city"), "Dawnlands")
        ])
        connections = list(connection_map.get(city_id, {}).values())
        add_link_section(sections, "Connections", connections)
        npc_links = [
            link_entity("npc", nid, npc_defs[nid]["name"])
            for nid in sorted(set(world_npcs.get(city_id, [])))
        ]
        add_link_section(sections, "NPCs", npc_links)
        entry = make_entry(
            entry_id=city_id,
            kind="city",
            name=world_names[city_id],
            subtitle="City \u00b7 Dawnlands",
            description=world.get("description", ""),
            badges=[
                {"label": "City", "tone": "gold"},
                {"label": "Dawnlands", "tone": "forest"},
            ],
            facts=facts,
            sections=sections,
            filters={"region": "Dawnlands"},
            level=1,
            category="City",
        )
        check_image(entry)
        cities.append(entry)

    # --- NPCs ---------------------------------------------------------------
    npc_world: dict[str, str] = {}
    for world_id, npc_ids in world_npcs.items():
        for npc_id in npc_ids:
            npc_world.setdefault(npc_id, world_id)

    npcs: list[dict[str, Any]] = []
    for npc_id in sorted(npc_defs, key=lambda nid: npc_defs[nid]["name"].casefold()):
        npc = npc_defs[npc_id]
        roles = []
        if npc["vendor"]:
            roles.append("Vendor")
        if npc["service"] == "healer":
            roles.append("Healer")
        if npc["quest_id"] or any(q["turn_in"] == npc_id for q in quest_defs.values()):
            roles.append("Quest giver")
        if not roles:
            roles.append("NPC")
        world_id = npc_world.get(npc_id)
        location = world_names.get(world_id, "") if world_id else "Not placed in a world scene"
        facts: list[dict[str, str]] = []
        add_fact(facts, "Stable ID", npc_id)
        add_fact(facts, "Role", " \u00b7 ".join(roles))
        add_fact(facts, "Location", location)
        add_fact(facts, "Interaction", npc["interaction"])
        if npc["appearance_id"]:
            add_fact(facts, "Appearance ID", npc["appearance_id"])
        if npc["opening"]:
            add_fact(facts, "Opening line", npc["opening"])
        elif npc["greeting"]:
            add_fact(facts, "Greeting", npc["greeting"])
        sections: list[dict[str, Any]] = []
        if world_id:
            add_link_section(sections, "Location", [entity_link(world_id)])
        if npc["quest_id"] and npc["quest_id"] in quest_defs:
            add_link_section(sections, "Quest", [link_entity("quest", npc["quest_id"], quest_defs[npc["quest_id"]]["name"])])
        turn_in_quests = [
            link_entity("quest", quest["id"], quest["name"])
            for quest in quest_defs.values()
            if quest["turn_in"] == npc_id
        ]
        add_link_section(sections, "Quest turn-in", turn_in_quests)
        if npc["vendor"]:
            add_link_section(
                sections,
                "Vendor stock",
                [
                    link_entity(
                        "item",
                        offer["item_id"],
                        item_defs.get(offer["item_id"], {}).get("name", offer["item_id"]),
                        f"{offer['price']} Crowns",
                    )
                    for offer in npc["vendor"]
                ],
            )
        entry = make_entry(
            entry_id=npc_id,
            kind="npc",
            name=npc["name"],
            subtitle=" \u00b7 ".join(roles),
            badges=[{"label": role, "tone": "cyan"} for role in roles],
            facts=facts,
            sections=sections,
            filters={"role": roles[0], "location": location},
            category=roles[0],
        )
        check_image(entry)
        npcs.append(entry)

    # --- quests -------------------------------------------------------------
    quests: list[dict[str, Any]] = []
    for quest_id in sorted(quest_defs, key=lambda qid: quest_defs[qid]["name"].casefold()):
        quest = quest_defs[quest_id]
        facts: list[dict[str, str]] = []
        add_fact(facts, "Stable ID", quest_id)
        if quest["turn_in"] in npc_defs:
            add_fact(facts, "Turn in", npc_defs[quest["turn_in"]]["name"])
        add_fact(facts, "Objectives", len(quest["objectives"]))
        if quest["prerequisites"]:
            add_fact(facts, "Prerequisites", len(quest["prerequisites"]))
        else:
            add_fact(facts, "Prerequisites", "None")
        reward_parts = []
        for reward in quest["rewards"]:
            if reward["currency"]:
                reward_parts.append(f"{reward['currency']} Crowns")
            if reward["xp"]:
                reward_parts.append(f"{reward['xp']} XP")
            if reward["item_id"]:
                reward_parts.append(f"{item_defs.get(reward['item_id'], {}).get('name', reward['item_id'])} \u00d7{reward['quantity']}")
        if reward_parts:
            add_fact(facts, "Rewards", " \u00b7 ".join(reward_parts))
        sections: list[dict[str, Any]] = []
        if quest["objectives"]:
            objective_facts = []
            for objective in quest["objectives"]:
                label = objective["description"] or quest["objectives"][0]["description"]
                objective_facts.append(
                    {"label": f"{QUEST_OBJECTIVES.get(objective['type'], 'Objective')} \u00d7{objective['count']}", "value": objective["description"] or objective["target_id"]}
                )
            sections.append({"title": "Objectives", "facts": objective_facts})
        reward_links = [
            link_entity(
                "item",
                reward["item_id"],
                item_defs.get(reward["item_id"], {}).get("name", reward["item_id"]),
                f"\u00d7{reward['quantity']}",
            )
            for reward in quest["rewards"]
            if reward["item_id"]
        ]
        add_link_section(sections, "Item rewards", reward_links)
        if quest["turn_in"] in npc_defs:
            add_link_section(sections, "Turn in", [link_entity("npc", quest["turn_in"], npc_defs[quest["turn_in"]]["name"])])
        add_link_section(sections, "Prerequisites", [
            link_entity("quest", qid, quest_defs[qid]["name"])
            for qid in quest["prerequisites"]
            if qid in quest_defs
        ])
        related_dungeons = [
            link_entity("dungeon", did, world_names[did])
            for did in sorted(quest_dungeons.get(quest_id, set()))
        ]
        add_link_section(sections, "Dungeon", related_dungeons)
        related_regions = [
            link_entity("region", rid, world_names[rid])
            for rid in sorted(quest_regions.get(quest_id, set()))
            if rid in region_ids
        ]
        add_link_section(sections, "Region", related_regions)
        entry = make_entry(
            entry_id=quest_id,
            kind="quest",
            name=quest["name"],
            subtitle="Quest",
            description=quest["description"],
            badges=[{"label": "Quest", "tone": "gold"}],
            facts=facts,
            sections=sections,
            filters={
                "turn_in": npc_defs.get(quest["turn_in"], {}).get("name", "Unknown"),
                "prerequisite": "Required" if quest["prerequisites"] else "None",
            },
            category="Quest",
        )
        check_image(entry)
        quests.append(entry)

    # --- skills -------------------------------------------------------------
    def skill_effect_text(skill: dict[str, Any], rank: int | None = None) -> str:
        effect = skill["effect"]
        index = (rank or 1) - 1
        if effect == 0:
            multiplier = skill["damage_multiplier"]
            if skill["rank_damage"]:
                multiplier = skill["rank_damage"][min(index, len(skill["rank_damage"]) - 1)]
            return f"{fmt_number(round(float(multiplier or 1) * 100))}% weapon damage"
        if effect == 1:
            percent = skill["heal_percent"]
            if skill["rank_heal"]:
                percent = skill["rank_heal"][min(index, len(skill["rank_heal"]) - 1)]
            return f"Restores {percent}% max health"
        if effect == 3:
            armor = 0
            if skill["rank_guard"]:
                armor = skill["rank_guard"][min(index, len(skill["rank_guard"]) - 1)]
            return f"+{armor} armor for {fmt_number(skill['guard_duration'])} s"
        parts = []
        if skill["attack_bonus"]:
            parts.append(f"+{skill['attack_bonus']} attack")
        if skill["armor_bonus"]:
            parts.append(f"+{skill['armor_bonus']} armor")
        if skill["health_bonus"]:
            parts.append(f"+{skill['health_bonus']} max health")
        return " \u00b7 ".join(parts) if parts else "Passive stat"

    skills: list[dict[str, Any]] = []
    for skill_id in sorted(skill_defs, key=lambda sid: skill_defs[sid]["name"].casefold()):
        skill = skill_defs[skill_id]
        max_rank = max(len(skill["rank_damage"]), len(skill["rank_heal"]), len(skill["rank_guard"]), 1)
        facts: list[dict[str, str]] = []
        add_fact(facts, "Stable ID", skill_id)
        add_fact(facts, "Type", SKILL_TYPES.get(skill["type"], "Active"))
        add_fact(facts, "Target", SKILL_TARGETS.get(skill["target"], "Self"))
        add_fact(facts, "Effect", SKILL_EFFECTS.get(skill["effect"], "Effect"))
        add_fact(facts, "Required level", skill["required_level"])
        add_fact(facts, "Skill point cost", skill["cost"])
        add_fact(facts, "Cooldown", fmt_duration(skill["cooldown"]))
        add_fact(facts, "Ranks", max_rank)
        add_fact(facts, "Current effect", skill_effect_text(skill))
        if skill["required_skill"]:
            add_fact(facts, "Prerequisite", skill_defs.get(skill["required_skill"], {}).get("name", skill["required_skill"]))
        sections: list[dict[str, Any]] = []
        ranks = []
        for rank in range(1, max_rank + 1):
            ranks.append({"label": f"Rank {rank}", "value": skill_effect_text(skill, rank)})
        if ranks:
            sections.append({"title": "Rank table", "facts": ranks})
        if skill["required_skill"] and skill["required_skill"] in skill_defs:
            add_link_section(sections, "Requires", [link_entity("skill", skill["required_skill"], skill_defs[skill["required_skill"]]["name"])])
        icon_name = skill["icon_id"].split(".")[-1] if skill["icon_id"] else ""
        entry = make_entry(
            entry_id=skill_id,
            kind="skill",
            name=skill["name"],
            subtitle=f"{SKILL_TYPES.get(skill['type'], 'Active')} \u00b7 {SKILL_EFFECTS.get(skill['effect'], 'Effect')}",
            description=skill["description"],
            image=f"assets/icons/{icon_name}.svg" if icon_name else None,
            image_alt=f"{skill['name']} skill icon",
            badges=[
                {"label": SKILL_TYPES.get(skill["type"], "Active"), "tone": "cyan"},
                {"label": f"Rank {max_rank}", "tone": "muted"},
            ],
            facts=facts,
            sections=sections,
            filters={
                "type": SKILL_TYPES.get(skill["type"], "Active"),
                "target": SKILL_TARGETS.get(skill["target"], "Self"),
            },
            level=skill["required_level"],
            category=SKILL_TYPES.get(skill["type"], "Active"),
        )
        check_image(entry)
        skills.append(entry)

    # --- resources ----------------------------------------------------------
    resource_worlds: dict[str, list[str]] = {}
    for world_id, resource_ids in world_resources.items():
        for resource_id in resource_ids:
            if resource_id:
                resource_worlds.setdefault(resource_id, []).append(world_id)

    resources: list[dict[str, Any]] = []
    for resource_id in sorted(resource_defs, key=lambda rid: resource_defs[rid]["name"].casefold()):
        resource = resource_defs[resource_id]
        facts: list[dict[str, str]] = []
        add_fact(facts, "Stable ID", resource_id)
        add_fact(facts, "Interaction", resource["verb"])
        add_fact(facts, "Yield", f"{resource['min']}\u2013{resource['max']} \u00d7 {item_defs.get(resource['item_id'], {}).get('name', resource['item_id'])}")
        add_fact(facts, "Respawn", fmt_duration(resource["respawn"]))
        sections: list[dict[str, Any]] = []
        add_link_section(sections, "Item", [
            link_entity("item", resource["item_id"], item_defs.get(resource["item_id"], {}).get("name", resource["item_id"]))
        ] if resource["item_id"] else [])
        add_link_section(sections, "Found in", [
            entity_link(wid) for wid in sorted(set(resource_worlds.get(resource_id, [])))
        ])
        icon = "assets/icons/ore.svg" if "iron" in resource_id else "assets/icons/herb.svg"
        entry = make_entry(
            entry_id=resource_id,
            kind="resource",
            name=resource["name"],
            subtitle=f"{resource['verb']} node",
            badges=[{"label": resource["verb"], "tone": "forest"}],
            facts=facts,
            sections=sections,
            filters={"verb": resource["verb"]},
            category="Resource",
            image=icon,
            image_alt=f"{resource['name']} resource icon",
        )
        check_image(entry)
        resources.append(entry)

    # --- loot tables --------------------------------------------------------
    loot_entries: list[dict[str, Any]] = []
    for loot_id in sorted(loot_defs, key=lambda lid: loot_defs[lid]["name"].casefold()):
        loot = loot_defs[loot_id]
        monster = next((enemy for enemy in enemy_defs.values() if enemy["loot"] == loot_id), None)
        facts: list[dict[str, str]] = []
        add_fact(facts, "Stable ID", loot_id)
        add_fact(facts, "Entries", len(loot["entries"]))
        add_fact(facts, "Guaranteed drops", sum(1 for entry in loot["entries"] if entry["chance"] >= 100))
        if monster:
            add_fact(facts, "Dropped by", monster["name"])
        sections: list[dict[str, Any]] = []
        drop_links = [
            link_entity(
                "item",
                entry["item_id"],
                item_defs.get(entry["item_id"], {}).get("name", entry["item_id"]),
                loot_meta(entry),
            )
            for entry in loot["entries"]
        ]
        add_link_section(sections, "Drops", drop_links)
        if monster:
            add_link_section(sections, "Dropped by", [link_entity("monster", monster["id"], monster["name"], f"Lv {monster['level']}\u2013{monster['max_level']}")])
        entry = make_entry(
            entry_id=loot_id,
            kind="loot",
            name=loot["name"],
            subtitle="Loot table",
            badges=[{"label": "Loot", "tone": "gold"}],
            facts=facts,
            sections=sections,
            filters={"monster": monster["name"] if monster else "Unassigned"},
            category="Loot",
            image="assets/icons/treasure.svg",
            image_alt="Loot chest icon",
        )
        check_image(entry)
        loot_entries.append(entry)

    # --- counts, validation and output -------------------------------------
    categories = {
        "items": items,
        "equipment": equipment,
        "monsters": monsters,
        "bosses": bosses,
        "dungeons": dungeons,
        "regions": regions,
        "cities": cities,
        "npcs": npcs,
        "quests": quests,
        "skills": skills,
        "resources": resources,
        "loot": loot_entries,
    }

    # Preview coverage is required, including character-only artwork and loot bundles.
    # This also applies to entries introduced in a future game data revision.
    apply_previews(categories, OUTPUT.parent)
    validate_previews(categories, OUTPUT.parent)

    # Stable IDs must be unique and every entry needs a display name.
    for key, entries in categories.items():
        ids = [entry["id"] for entry in entries]
        duplicates = sorted({value for value in ids if ids.count(value) > 1})
        if duplicates:
            error(f"{key} has duplicate stable IDs: {', '.join(duplicates)}")
        for entry in entries:
            if not str(entry.get("name", "")).strip():
                error(f"{key} {entry['id']} has no display name")

    # Every internal link must resolve to a generated entry.
    entry_ids = {kind: {entry["id"] for entry in entries} for kind, entries in categories.items()}
    type_to_category = {
        "item": "items",
        "equipment": "equipment",
        "monster": "monsters",
        "boss": "bosses",
        "dungeon": "dungeons",
        "region": "regions",
        "city": "cities",
        "npc": "npcs",
        "quest": "quests",
        "skill": "skills",
        "resource": "resources",
        "loot": "loot",
    }
    for key, entries in categories.items():
        for entry in entries:
            for section in entry.get("sections", []):
                for link in section.get("links", []):
                    target_category = type_to_category.get(link["type"])
                    if not target_category or link["id"] not in entry_ids[target_category]:
                        warn(f"{key} {entry['id']} has unresolved link {link['type']}/{link['id']}")

    counts = {key: len(entries) for key, entries in categories.items()}
    primary_total = sum(
        len(entries)
        for key, entries in categories.items()
        if key not in ("equipment", "bosses")
    )

    source_commit = SOURCE_COMMIT
    source_short = SOURCE_SHORT
    metadata = {
        "title": "Nythara Database",
        "source_commit": source_commit,
        "source_short_commit": source_short,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "generator": "tools/export_nythara_database.py",
        "counts": counts,
        "total_primary_entries": primary_total,
        "categories": [
            {
                "key": key,
                "type": type_name,
                "label": label,
                "description": description,
                "count": counts[key],
            }
            for key, type_name, label, description in CATEGORY_META
        ],
        "warnings": WARNINGS,
        "errors": ERRORS,
    }

    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "preview-fallbacks.json").write_text(json.dumps(FALLBACKS, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUTPUT / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for key, entries in categories.items():
        payload = {"count": len(entries), "entries": entries}
        (OUTPUT / f"{key}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"source: {source_short}")
    print(f"output: {OUTPUT}")
    for key, entries in categories.items():
        print(f"  {key:10} {len(entries):3}")
    print(f"  {'total':10} {primary_total:3} primary entries")
    if WARNINGS:
        print(f"  warnings   {len(WARNINGS)}", file=sys.stderr)
    if ERRORS:
        print(f"  errors     {len(ERRORS)}", file=sys.stderr)
        raise SystemExit(1)


def main() -> None:
    global NYTHARA, OUTPUT  # noqa: PLW0603
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--nythara-repo",
        default="../Nythara",
        help="Path to the read-only Nythara Godot repository (default: ../Nythara).",
    )
    parser.add_argument(
        "--output",
        default="Nythara/database/data",
        help="Output directory for the JSON files (default: Nythara/database/data).",
    )
    parser.add_argument(
        "--source-ref",
        default="main",
        help="Committed ref to export (default: main). Use HEAD to read the working tree.",
    )
    args = parser.parse_args()
    global SOURCE_REPO, SOURCE_REF, SOURCE_COMMIT, SOURCE_SHORT, NYTHARA, OUTPUT  # noqa: PLW0603
    SOURCE_REPO = Path(args.nythara_repo).expanduser().resolve()
    SOURCE_REF = args.source_ref
    OUTPUT = Path(args.output).expanduser().resolve()
    NYTHARA, SOURCE_COMMIT, SOURCE_SHORT = materialize_source(SOURCE_REPO, SOURCE_REF)
    try:
        export()
    finally:
        if TEMP_SNAPSHOT is not None:
            shutil.rmtree(TEMP_SNAPSHOT, ignore_errors=True)


if __name__ == "__main__":
    main()
