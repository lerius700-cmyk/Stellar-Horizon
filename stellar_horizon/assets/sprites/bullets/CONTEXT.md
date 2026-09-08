# bullets/ — Laser sheets + legacy 8x8 bullets

## Contents

| File | Dim | Frames | Notes |
|---|---:|---:|---|
| `laser_01_sheet.png` | 29×7 | 6 | yellow plasma (WEAPON_ARCHETYPE 0) |
| `laser_02_sheet.png` | 29×7 | 6 | red pulse (WEAPON_ARCHETYPE 1) |
| `laser_03_sheet.png` | 29×7 | 6 | blue ion (WEAPON_ARCHETYPE 2) |
| `laser_04_sheet.png` | 29×7 | 6 | green acid (WEAPON_ARCHETYPE 3) |
| `laser_05_sheet.png` | 29×7 | 6 | purple void (WEAPON_ARCHETYPE 4) |
| `player_bullet.png` + `_sheet.png` | 8×8 | 6 | legacy 8x8 player bullet |
| `enemy_bullet.png` + `_sheet.png` | 8×8 | 6 | legacy 8x8 enemy bullet |

The 5 `laser_0[1-5].png` single-frame base images (the pre-regen AI
generations that fed the v1.3.0 procedural sheet expansion) are now
in `_deprecated/single_frames/` — the v1.4.0 regen produced
visually-distinct 6-frame sheets, so the old single frames are
obsolete. See `_deprecated/CONTEXT.md` for why each is kept.

The 5 archetype colors and halo colors (used by the regen prompt):
- `laser_01`: core `#FFEE44`, halo `#FFAA00`
- `laser_02`: core `#FF3344`, halo `#FF8888`
- `laser_03`: core `#4488FF`, halo `#88CCFF`
- `laser_04`: core `#44FF66`, halo `#AAFFAA`
- `laser_05`: core `#AA44FF`, halo `#DDAADD`

## Cross-references

- `stellar_horizon/entities/bullet.py:14-23` — `WEAPON_ARCHETYPE` table
  (10 weapons → 5 archetype indexes, 0-indexed).
- `stellar_horizon/fx/bullet_vfx.py` — `WeaponVFX` dataclass with
  per-archetype `particles_per_frame`, `particle_kind`, `particle_color`,
  `trail_intensity`. The regen prompt and per-weapon particles were
  coordinated in visual-polish-v2 (2026-09-06).
- `stellar_horizon/scenes/gameplay.py:_draw_bullet_sprite` — runtime render.

## Adding a new laser archetype

1. Add a new entry in `WEAPON_ARCHETYPE` (bullet.py) and `WEAPON_VFX_PARAMS`
   (bullet_vfx.py).
2. Generate the 6-frame sheet via AI + `sprite_tests/regen_laser_strips.py`.
3. Save as `laser_0N_sheet.png` (1-indexed filename) and `laser_0N.png`.
4. Update the archetype table above.
