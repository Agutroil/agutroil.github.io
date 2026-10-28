# Nythara database

The page at <https://agutroil.github.io/Nythara/database/> is a static snapshot of
the public Nythara game repository. Nothing is queried at runtime: the exporter
reads the game definitions once, writes JSON, and the page loads that JSON with
plain JavaScript on GitHub Pages.

## Regenerate

```bash
cd agutroil.github.io

python3 tools/export_nythara_database.py \
  --nythara-repo ../Nythara \
  --output Nythara/database/data
```

`--nythara-repo` and `--output` are ordinary paths, so the checkout can live
anywhere. Python 3.12+ with the standard library is enough; there is nothing to
install.

The exporter is read-only with respect to the game repository. By default it
exports the committed `main` ref (`--source-ref main`) through `git archive`,
which opens it in a temporary directory. That means:

- unmerged work in other branches never leaks into the published snapshot;
- the recorded `source_commit` in `metadata.json` is a real, public commit;
- the working tree of the game checkout is never touched.

Use `--source-ref HEAD` only for a local preview of unpublished work. Do not
commit data exported that way: the recorded SHA would not exist publicly.

## Output

| File | Contents |
| --- | --- |
| `metadata.json` | Source commit, generation timestamp, category counts, warnings |
| `items.json` | Items with rarity, stats, slot, sources and loot links |
| `equipment.json` | Wearable subset with slot, stats and visual support |
| `monsters.json` | Creatures with stats, archetype, region and loot table |
| `bosses.json` | Boss encounters with phase and attack data |
| `dungeons.json` | Dungeon definitions, boss and quest relationships |
| `regions.json` | WorldGraph regions, connections, portals and inhabitants |
| `cities.json` | Settlements with services, NPCs and connections |
| `npcs.json` | Quest givers, vendors and healers |
| `quests.json` | Objectives, prerequisites, rewards and turn-ins |
| `skills.json` | Ranks, cooldowns, targets and effects |
| `resources.json` | Gatherable nodes and their yields |
| `loot.json` | Loot tables with entries and chances |

Entries are sorted by stable ID and every list is ordered deterministically, so
the same game commit produces byte-identical JSON apart from `generated_at`.

## Validation

The run blocks on structural problems: duplicate stable IDs, entries without a
display name, or a path that is not a Nythara checkout. Those are reported as
errors and exit non-zero.

Relationship problems are reported but do not abort the export: a cross-link
that does not resolve to a generated entry, or an image path missing under
`Nythara/database/`, is printed to stderr as a warning and stored in
`metadata.json` under `warnings`. Publishing with a non-empty `warnings` array
is a bug. The current snapshot exports with zero warnings and zero errors, and
that is the state to check after every regeneration.

## Assets

Images are curated, not mirrored. `Nythara/database/assets/` contains only the
icons and creature previews used by the catalogue plus the site screenshots that
already live in `Nythara/assets/`. When new content needs artwork, add the
individual file and register its path in the exporter's image map; do not copy
the whole game asset tree into this repository.

## Deploy

Commit the regenerated `Nythara/database/data/*.json` together with any asset
changes and push to `main`. GitHub Pages serves the directory as-is; the source
commit shown on the page comes from `metadata.json`.
