# enemies/ — 6 kinds, each in its own sub-folder

## Contents

Per kind, the file pattern is `enemy_{kind}_v{N}_sheet.png` (variants)
+ `enemy_{kind}_attack_v1_sheet.png` + `enemy_{kind}_death_v1_sheet.png`
+ `enemy_{kind}_v1.png` (single-frame base for re-prompting).

| Kind | Variants | Attack sheet | Death sheet | Total in sub-folder |
|---|---:|---:|---:|---:|
| `scout/` | 4 (v1..v4) | yes | yes | 12 |
| `cruiser/` | 4 (v1..v4) | yes | yes | 12 |
| `heavy/` | 3 (v1..v3) | yes | yes | 10 |
| `bomber/` | 3 (v1..v3) | yes | yes | 10 |
| `ufo/` | 3 (v1..v3) | yes | yes | 10 |
| `kamikaze/` | 3 (v1..v3) + `v1_v2` (special) | yes | yes | 12 |
| **Total** | 20 + 1 special | 6 | 6 | 66 |

The `kamikaze/v1_v2` is a special variant (different silhouette from
the others) — the loader treats it as a normal sheet.

## Cross-references

- `stellar_horizon/entities/enemy.py` — Enemy class. The draw code
  uses `self._animated.get(e.sprite_name)` to pick the sheet, falling
  back to `self._animated.get(e.kind)` if no sprite_name is set.
- `stellar_horizon/scenes/gameplay.py:_ENEMY_SPRITE_CYCLE` — defines
  the variant cycle per kind (e.g. `scout -> [v1, v2, v3, v4]`).
- `stellar_horizon/scenes/gameplay.py:_load_sprites` — loads all sheets
  via the resolver.

## Action sheets (attack / death)

The attack sheet is shown when the enemy is telegraphing/about to fire.
The death sheet is shown during the death sequence (replaces the
idle/v1 sheet for the duration). The runtime swap is in
`gameplay.py:_draw_enemy_sprite`.
