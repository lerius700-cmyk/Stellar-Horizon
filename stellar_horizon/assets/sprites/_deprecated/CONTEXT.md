# _deprecated/ — Files no longer loaded, kept for reference

> **DO NOT DELETE.** These files are tracked in git. They are kept here
> for future reference and possible re-prompting. Deleting them is
> reversible only via `git checkout` and loses the link to their
> original folder.

## Contents

| Sub-folder | Count | Why deprecated |
|---|---:|---|
| `legacy_sprites/` | 84 | Pre-v1.1.0 sprite library. Replaced by `sprites_v2/` in the 2026-09-01 SF+SM refactor. Includes `boss.png`, `cruiser.png`, `enemy_01..20`, `heavy.png`, `laser_01..10`, `player.png`, `scout.png`, plus their `_sheet` companions. |
| `test_cruiser/` | 6 | `test_cruiser_A_retro`, `_B_hd`, `_C_modern` — 3 sprites generated as visual A/B/C tests during the v1 ship sprite work. Never used in gameplay. |
| `single_frames/` | 5 | The original `laser_0[1-5].png` AI base images (29×7 single frames) that were the input to the v1.3.0 procedural 6-frame sheet expansion. After the visual-polish-v3 regen (2026-09-08), the new strips come from a different prompt and these are obsolete. Kept for re-prompting reference. |

## Re-introducing

If a deprecated file becomes useful again:

1. Move it back to its proper folder via `git mv`.
2. Update the relevant sub-folder's `CONTEXT.md` to mention it.
3. Remove the entry from this file.
4. If the file needs to be re-prompted for regen, do that BEFORE moving
   it back — the file on disk is the original, possibly outdated, art.
