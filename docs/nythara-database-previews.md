# Current runtime previews

The public game snapshot remains `b2bac4d03207db30e3d8e0314056b9f96a64e0e0`.
Capture provenance: `678c47d5268b716cca0deed41b452b1b963019a7`.
The capture revision records presentation work; it is not a game release.

## Approved library

The website contains 35 approved 1600×900 runtime captures, encoded as WebP at quality 86, effort 6. Full frames, names and stable IDs follow the supplied capture manifest. Masters are preserved in their original repository. No raw game art or generated replacement art is added.

`tools/nythara-current-captures.json` records stable IDs, approved roles, master SHA-256, delivery SHA-256, dimensions and alt text. It contains no checkout paths, credentials, identities or private URLs. It is excluded from Pages with the rest of the development tools.

## Database coverage

| Category | Current captures | Total records |
| --- | ---: | ---: |
| Cities | 1 | 1 |
| Regions | 3 | 10 |
| Dungeons | 2 | 2 |
| Bosses | 2 | 2 |
| Monsters | 8 | 8 |
| Npcs | 5 | 5 |

Monsters include the two boss aliases already present in that category. There are 21 capture-backed category records and 19 distinct photographed database entities. Seven regions without an approved current capture retain their existing explicitly labelled world illustrations. Unknown future entities receive a neutral category emblem rather than an unrelated runtime scene.

## Stable ID mapping

| Stable ID | Current public image |
| --- | --- |
| `world_start_city` | `current-city-dawnwatch.webp` |
| `world_prototype_valley` | `current-region-prototype-valley.webp` |
| `world_whispering_grove` | `current-region-whispering-grove.webp` |
| `world_silverwood` | `current-region-silverwood.webp` |
| `world_hollow_ruins` | `current-dungeon-hollow-ruins.webp` |
| `world_moonroot_sanctum` | `current-dungeon-moonroot-sanctum.webp` |
| `mossling` | `current-monster-mossling.webp` |
| `enemy_stoneback` | `current-monster-stoneback.webp` |
| `enemy_thornspitter` | `current-monster-thornspitter.webp` |
| `enemy_briarling` | `current-monster-briarling.webp` |
| `enemy_gloom_moth` | `current-monster-gloom-moth.webp` |
| `enemy_root_sentinel` | `current-monster-root-sentinel.webp` |
| `npc_elara` | `current-npc-elara.webp` |
| `npc_mira` | `current-npc-mira.webp` |
| `npc_rowan` | `current-npc-rowan.webp` |
| `npc_silverwood_keeper` | `current-npc-silverwood-keeper.webp` |
| `npc_elyra` | `current-npc-elyra.webp` |
| `enemy_hollow_warden` | `current-hollow-warden.webp` |
| `enemy_rootbound_seer` | `current-rootbound-seer.webp` |

Dungeon environments and boss encounters are separate assets for both The Hollow Ruins and Moonroot Sanctum. No current screenshot is cropped. Cards, interactive details, static permalinks and the landing-page Codex all use the same preview mapping.

## Migration and checks

The landing page keeps its green backgrounds, key art, navigation and gameplay sections. Its curated gallery has 12 current views. Equipment and player captures replace the previous skill-panel illustration; captions describe the actual displayed views.

46 obsolete public runtime images, sprite previews and portrait previews were removed after confirming zero production references. Historical website QA notes are retained as development history and excluded from Pages; historical game documentation was untouched.

Regenerate only presentation fields with:

```bash
python3 tools/nythara_previews.py --apply
python3 tools/build_nythara_pages.py
python3 -m unittest discover -s tools -p 'test_*.py'
python3 tools/check_website.py
```

Validation requires the approved image for each matching stable ID, rejects swapped subjects and cropped captures, verifies checksums and dimensions for all 35 images, and preserves nonvisual game fields. The original green-background guards and file-size budgets remain; creature asset guards now protect their current replacements.

Sprint 27 and Sprint 28 are outside the public feature ceiling. The game data revision must not be replaced by the capture revision.
