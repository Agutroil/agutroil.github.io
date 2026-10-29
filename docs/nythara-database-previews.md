# Nythara database previews

The static catalogue has 74 category records (63 primary entries). Preview refreshes do not change game facts, category counts, relationships or the game data revision.

## Refresh and check

```bash
python3 tools/nythara_previews.py --apply
python3 tools/nythara_previews.py
python3 -B -m unittest discover -s tools -p 'test_*.py'
```

These commands read and write only the website snapshot. The regular exporter calls the same preview policy before emitting entries and validates complete coverage. New categories require an explicit policy; new entries receive a category or role appropriate representative preview.

`image_kind` distinguishes `sprite`, `portrait`, `icon`, `scene` and `bundle`. The renderer uses the same policy for cards and details. Scene crops are SVG viewports over existing local images; their pixels and source files remain unchanged. Character records never use scene or gameplay screenshot previews. Runtime fallbacks come from the generated static `data/preview-fallbacks.json`.

## Asset provenance

- Briarling, Gloom Moth, Mossling and Root Sentinel retain their existing PNG sprites. Both `mossling` and `enemy_mossling` resolve to the same public sprite.
- Stoneback, Hollow Warden, Rootbound Seer and Rowan use transparent sprite portraits derived from their existing public in-game captures with the built-in Imagegen tool. These are reconstructed presentation assets, not bit-exact extractions of original game textures.
- Thornspitter uses a representative sprite illustration because the website has no isolated original sprite.
- Elara, Elyra, Mira and Silverwood Keeper use representative role portraits based on the public Rowan character style. The UI labels them **Role portrait**; they do not claim to reproduce an unavailable canonical character asset.
- New character assets are saved under `Nythara/database/assets/creatures/*-portrait.webp` and `Nythara/database/assets/npcs/*-portrait.webp`. Transparent padding was trimmed and outputs were encoded to 256 × 256 WebP for delivery; all nine total less than 100 KB. Existing original sprites are untouched.
- Items, equipment, skills and resources reuse the public inventory/icon set. Loot bundles show actual linked drops rather than an empty or universal placeholder.
- Regions and Dawnwatch without direct captures use labelled **World artwork** crops of the existing banner and shared background. These depict a theme, not a verified region screenshot. Dungeon crops show the Hollow Ruins arena and Moonroot entrance without the full gameplay HUD.
- `Nythara/assets/nythara-background.webp` keeps the same artwork and dimensions. The website quality pass re-encoded this older representative artwork as WebP at quality 90 (2,430,781 → 308,546 bytes). SHA-256: `5eefbf29c4047958ff1f18acc66578f08369829190f0b94ce6acdecd6e8272fe`. The two green page backgrounds are separate assets and remain unchanged.

## Generation prompts

The built-in Imagegen tool was used with a transparent background for each of the following assets. References are public files already present in the website. No private game files or API credentials were used.

### stoneback

Reference: `Nythara/assets/rootbound-seer.jpg`

```text
Use case: background-extraction. Asset type: transparent sprite portrait for the Nythara game database. Edit target: supplied in-game capture. Extract ONLY the Stoneback enemy at left center, around x=335–425 y=295–438, immediately below the label 'Stoneback Lv 5'. Preserve its actual tall rounded moss-green body, leaflike broad upper silhouette, dark outline and simple pixel/sprite style. Remove all environment, HUD, labels, numbers, shadows on the ground, other characters and scenery. Show this single enemy, entire body visible, centered, upright, comfortably filling the frame. Do not redesign the creature or add armor, eyes, limbs or effects absent from the reference. Actual transparent background, no backdrop or text.
```

### hollow-warden

Reference: `Nythara/assets/hollow-warden.jpg`

```text
Use case: background-extraction. Asset type: transparent enemy sprite portrait. Extract ONLY the Hollow Warden boss in the center of the supplied Nythara screenshot: the very dark green tall rounded creature below its name label, with broad outward leaflike antlers and the small yellow eye/flower detail. Preserve its actual shape, proportions, colors and stepped sprite style. Remove the nearby human players even where they overlap; complete only the small occluded sprite edges consistently. Remove arena, circle, HUD, floating labels and damage numbers. Single complete enemy centered, filling 80% of frame. True transparent background. No invented armor, weapons, realistic textures, scenery or text.
```

### rootbound-seer

Reference: `Nythara/assets/rootbound-seer.jpg`

```text
Use case: background-extraction. Asset type: transparent enemy sprite portrait. Extract ONLY the Rootbound Seer boss in the upper center of this Nythara screenshot, below damage numbers 1 5 3: the tall dark forest-green rounded creature with wide curling leaf/antler upper silhouette and simple yellow flowerlike eye detail. Preserve its actual appearance and stepped sprite rendering. Remove Stoneback at left, human players, ground, all environment, labels, HUD and floating numbers. Complete small occluded outline portions without redesign. Single complete enemy, centered, fills 80% of frame. True transparent background. No added weapons, armor, limbs, text or scene.
```

### thornspitter

Reference: `Nythara/database/assets/creatures/mossling.png`

```text
Use case: stylized-concept. Asset type: transparent sprite-based illustrated fallback for the Nythara creature Thornspitter. The reference is a STYLE AND PALETTE reference only: an existing tiny Nythara Mossling sprite. Create one distinct small thorn-covered forest creature suggesting a ranged attacker, with a compact dark moss-green plant body, a few clearly visible thorn points and a small seed-spitting opening. Keep the same restrained green, brown and muted gold palette, coarse stepped pixel/sprite shapes and simple readable silhouette as the reference. Full body visible, centered, 80% of frame. This is a representative portrait, not a gameplay screenshot. Actual transparent background. No scenery, UI, text, projectile, circle or icon frame; do not simply duplicate the Mossling.
```

### rowan

Reference: `Nythara/assets/whispering-grove.jpg`

```text
Use case: background-extraction. Asset type: transparent full-body NPC sprite portrait for Nythara. Extract ONLY the NPC Rowan standing in the middle distance at approximately x=668 y=235, immediately below the ROWAN label. The NPC wears a teal-green hooded robe, pale face and holds a simple staff. Preserve the actual modest geometric sprite design and clothing. Remove the foreground player at x640 y370, environment, labels, HUD, all scenery and all text. Center the complete upright NPC and staff alone, comfortably fills frame. Preserve clean stepped pixel edges. Actual transparent background, no floor or glow.
```

### elara

Reference: `Nythara/assets/whispering-grove.jpg`

```text
Use case: stylized-concept. Asset type: transparent NPC role portrait, an illustrated fallback for Elara, a Nythara quest giver. Use the small teal-robed NPC Rowan near the center of this screenshot ONLY as the visual style reference. Create a single modest forest quest giver with a green hooded robe and a small parchment scroll held in both hands, simple pale face and minimal blocky features. Full body, front three-quarter view, coarse stepped pixel/sprite shapes matching Nythara. Keep props and detail minimal; this is a clearly representative character portrait, not a claim of an exact game asset. Actual transparent background. No backdrop, floor, frame, text, scenery, HUD or additional characters.
```

### elyra

Reference: `Nythara/assets/whispering-grove.jpg`

```text
Use case: stylized-concept. Asset type: transparent NPC role portrait, an illustrated fallback for Elyra, a Nythara healer. Use the small teal-robed NPC Rowan near the center of the screenshot ONLY as style reference. Create one modest healer in a pale blue and teal hooded robe holding a small potion vial, simple pale face, minimal blocky features, full body. Match the game's restrained coarse stepped pixel/sprite shapes, no realistic texture. This is a representative role portrait, not an exact game asset. Actual transparent background. No crosses, floating symbols, frame, text, floor, scenery, HUD or extra characters.
```

### mira

Reference: `Nythara/assets/whispering-grove.jpg`

```text
Use case: stylized-concept. Asset type: transparent NPC role portrait, an illustrated fallback for Mira, a Nythara vendor. Use the small teal-robed NPC Rowan near the screenshot center ONLY as visual style reference. Create one modest traveler/vendor in a brown and muted green hooded robe carrying a small leather goods satchel. Simple pale face, minimal features, full body front three-quarter view, coarse stepped pixel/sprite shapes matching Nythara. This is a representative role portrait, not an exact game asset. Actual transparent background. No frame, text, shop, floor, scenery, HUD or extra characters.
```

### silverwood-keeper

Reference: `Nythara/assets/whispering-grove.jpg`

```text
Use case: stylized-concept. Asset type: transparent NPC role portrait, an illustrated fallback for the Silverwood Keeper, a Nythara quest giver. Use the small teal-robed NPC Rowan near the center of the screenshot ONLY as style reference. Create one modest forest keeper in a dark green and moon-blue hooded robe holding a simple wooden staff. Minimal pale face, small muted gold belt clasp, full body, clean coarse stepped pixel/sprite shapes matching Nythara. This is a representative role portrait, not an exact game asset. Actual transparent background. No antlers, elaborate armor, glow, frame, text, floor, scenery, HUD or extra characters.
```
