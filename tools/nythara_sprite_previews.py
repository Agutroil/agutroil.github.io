#!/usr/bin/env python3
"""Generate the Nythara database sprite previews from the authored sprite sets.

The generator reads the game checkout read-only, follows every character's
``*_frames.tres`` to the front-facing idle frame (``idle_s_0``) and writes one
uniform 256x256 transparent cutout per database subject. It also records the
provenance of every preview in ``tools/nythara-sprite-previews.json``.

The website build never reads the game repository: it consumes the committed
previews and the provenance registry only.

Usage:
    python3 tools/nythara_sprite_previews.py
    python3 tools/nythara_sprite_previews.py --check
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "Nythara" / "database"
REGISTRY = Path(__file__).with_name("nythara-sprite-previews.json")
DEFAULT_GAME = ROOT.parent / "Nythara"
CANVAS = 256
PADDING = 16

# stable database id, category, display name, SpriteFrames resource,
# output folder below Nythara/database/assets/previews, file stem
CHARACTERS: list[tuple[str, str, str, str, str, str]] = [
    ("mossling", "monster", "Mossling", "res://assets/creatures/mossling/mossling_8way_frames.tres", "creatures", "mossling"),
    ("enemy_briarling", "monster", "Briarling", "res://assets/creatures/briarling/briarling_8way_frames.tres", "creatures", "briarling"),
    ("enemy_gloom_moth", "monster", "Gloom Moth", "res://assets/creatures/gloom_moth/gloom_moth_8way_frames.tres", "creatures", "gloom-moth"),
    ("enemy_root_sentinel", "monster", "Root Sentinel", "res://assets/creatures/root_sentinel/root_sentinel_8way_frames.tres", "creatures", "root-sentinel"),
    ("enemy_stoneback", "monster", "Stoneback", "res://assets/creatures/stoneback/stoneback_8way_frames.tres", "creatures", "stoneback"),
    ("enemy_thornspitter", "monster", "Thornspitter", "res://assets/creatures/thornspitter/thornspitter_8way_frames.tres", "creatures", "thornspitter"),
    ("enemy_hollow_warden", "boss", "The Hollow Warden", "res://assets/creatures/hollow_warden/hollow_warden_8way_frames.tres", "creatures", "hollow-warden"),
    ("enemy_rootbound_seer", "boss", "The Rootbound Seer", "res://assets/creatures/rootbound_seer/rootbound_seer_8way_frames.tres", "creatures", "rootbound-seer"),
    ("npc_elara", "npc", "Elara", "res://assets/characters/npcs/elara_sprite_frames.tres", "npcs", "elara"),
    ("npc_elyra", "npc", "Elyra", "res://assets/characters/npcs/elyra_sprite_frames.tres", "npcs", "elyra"),
    ("npc_mira", "npc", "Mira", "res://assets/characters/npcs/mira_sprite_frames.tres", "npcs", "mira"),
    ("npc_rowan", "npc", "Rowan", "res://assets/characters/npcs/rowan_sprite_frames.tres", "npcs", "rowan"),
    ("npc_silverwood_keeper", "npc", "Silverwood Keeper", "res://assets/characters/npcs/silverwood_keeper_sprite_frames.tres", "npcs", "silverwood-keeper"),
]

FRAME_ID = "idle_s_0"


def alt_text(category: str, name: str) -> str:
    """Describe the new artwork without inventing details the sheet lacks."""
    if category == "npc":
        return f"{name} sprite preview, front-facing idle frame from the NPC character sheet."
    if category == "boss":
        return f"{name} boss sprite preview, front-facing idle frame from the eight-direction boss sheet."
    return f"{name} sprite preview, front-facing idle frame from the eight-direction creature sheet."


def read_frames(path: Path) -> tuple[str, list[int]]:
    """Return the sheet resource path and the idle front frame region of a SpriteFrames file."""
    text = path.read_text(encoding="utf-8")
    textures = {sid: res for res, sid in re.findall(r'\[ext_resource type="Texture2D" path="res://([^"]+)" id="([^"]+)"\]', text)}
    blocks = re.findall(r'\[sub_resource type="AtlasTexture" id="([^"]+)"\]\n(.*?)(?=\n\[|\Z)', text, re.S)
    for frame_id, body in blocks:
        if not frame_id.endswith(FRAME_ID):
            continue
        atlas = re.search(r'atlas = ExtResource\("([^"]+)"\)', body)
        region = re.search(r'region = Rect2\(([^)]+)\)', body)
        if not atlas or not region or atlas.group(1) not in textures:
            continue
        values = [float(value) for value in region.group(1).split(",")]
        if len(values) != 4:
            continue
        return textures[atlas.group(1)], [int(round(value)) for value in values]
    raise ValueError(f"No {FRAME_ID} frame in {path}")


def render(game: Path, frames: str) -> tuple[Image.Image, Path, list[int]]:
    frames_path = game / frames.replace("res://", "")
    if not frames_path.is_file():
        raise ValueError(f"Missing SpriteFrames resource: {frames}")
    sheet_resource, region = read_frames(frames_path)
    sheet_path = game / sheet_resource
    if not sheet_path.is_file():
        raise ValueError(f"Missing sheet for {frames}: {sheet_path.name}")
    x, y, width, height = region
    sheet = Image.open(sheet_path).convert("RGBA")
    frame = sheet.crop((x, y, x + width, y + height))
    if (bbox := frame.getchannel("A").getbbox()) is not None:
        frame = frame.crop(bbox)
    if frame.width <= 0 or frame.height <= 0:
        raise ValueError(f"Empty sprite frame for {frames}")
    scale = max(1, (CANVAS - 2 * PADDING) // max(frame.width, frame.height))
    scaled = frame.resize((frame.width * scale, frame.height * scale), Image.NEAREST)
    canvas = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    canvas.paste(scaled, ((CANVAS - scaled.width) // 2, (CANVAS - scaled.height) // 2), scaled)
    return canvas, sheet_path, region


def build(game: Path) -> dict:
    entries = []
    for stable_id, category, name, frames, folder, stem in CHARACTERS:
        canvas, sheet_path, region = render(game, frames)
        relative = f"assets/previews/{folder}/{stem}.png"
        target = DATABASE / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(target, "PNG", optimize=True)
        entries.append(
            {
                "stable_id": stable_id,
                "category": category,
                "name": name,
                "image": relative,
                "image_alt": alt_text(category, name),
                "source_frames": frames,
                "source_sheet": "res://" + str(sheet_path.relative_to(game)),
                "source_sha256": sha256(sheet_path.read_bytes()).hexdigest(),
                "frame": FRAME_ID,
                "region": region,
                "width": CANVAS,
                "height": CANVAS,
                "sha256": sha256(target.read_bytes()).hexdigest(),
            }
        )
    return {
        "generator": "tools/nythara_sprite_previews.py",
        "frame": FRAME_ID,
        "canvas": CANVAS,
        "entries": entries,
    }


def verify(game: Path) -> list[str]:
    if not REGISTRY.is_file():
        return [f"Missing {REGISTRY.name}"]
    registry = json.loads(REGISTRY.read_text())
    errors = []
    if [entry["stable_id"] for entry in registry["entries"]] != [character[0] for character in CHARACTERS]:
        errors.append("Sprite preview registry does not match the character list")
    if registry.get("canvas") != CANVAS:
        errors.append("Sprite preview canvas changed")
    for entry in registry["entries"]:
        asset = DATABASE / entry["image"]
        if not asset.is_file():
            errors.append(f"Missing sprite preview: {entry['image']}")
            continue
        if sha256(asset.read_bytes()).hexdigest() != entry["sha256"]:
            errors.append(f"Changed sprite preview: {entry['image']}")
        if Image.open(asset).size != (CANVAS, CANVAS):
            errors.append(f"Wrong preview size: {entry['image']}")
        sheet = game / entry["source_sheet"].replace("res://", "")
        if not sheet.is_file() or sha256(sheet.read_bytes()).hexdigest() != entry["source_sha256"]:
            errors.append(f"Source sheet changed: {entry['source_sheet']}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nythara-repo", type=Path, default=DEFAULT_GAME, help="Read-only Nythara game checkout.")
    parser.add_argument("--check", action="store_true", help="Verify the committed previews; write nothing.")
    args = parser.parse_args()
    game = args.nythara_repo.resolve()
    if not (game / "project.godot").is_file():
        raise SystemExit(f"Not a Nythara checkout: {game}")
    if args.check:
        errors = verify(game)
        if errors:
            raise SystemExit("Sprite previews need regeneration: " + "; ".join(errors))
        print(f"Sprite previews verified: {len(CHARACTERS)} assets; canvas {CANVAS}x{CANVAS}.")
        return
    registry = build(game)
    REGISTRY.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n")
    print(f"Sprite previews written: {len(registry['entries'])} assets into Nythara/database/assets/previews/.")


if __name__ == "__main__":
    main()
