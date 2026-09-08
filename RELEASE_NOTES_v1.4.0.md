# Stellar Horizon v1.4.0 — Asset SF+SM reorganization + bullet regen

**Released:** 2026-09-08
**Tag:** `v1.4.0`
**Base:** `ebf390f` (v1.3.0)
**Head:** `a799f47`
**Build:** `StellarHorizon-v1.4.0-win64.zip` (35.95 MB, 34.28 MiB, SHA-256 `49ccdc1f…adb4065`)

---

## Bullet regen — visible 6-frame animation

The v1.3.0 laser sheets varied only in alpha (0.85..1.0). On narrow sprites
this delta is invisible — the user reported "pareciera el mismo frame
repetido 4 veces". v1.4.0 regenerates all 5 archetypes via AI strip
prompt + PIL postprocess:

- **Strip prompt + postprocess pipeline.** `connector__matrix__generate_image`
  generates a 174×42 strip (6 frames of 29×7 on a white-or-black
  background). The new `sprite_tests/regen_laser_strips.py` splits
  the strip, floodfills the background to transparent, crops to
  content + 1px padding, re-centers on a transparent 29×7 canvas,
  and concatenates the 6 frames horizontally into a 174×7 sheet.
- **6 distinct frames per archetype.** Each archetype has real shape
  variation (thin → thicker → peak → contract → trailing → thin)
  plus a per-archetype shape motif (yellow = balls, red/blue/purple
  = horizontal beams, green = diamonds). The user accepted the
  motif variety.
- **Color codes** (per the spec, section 3):
  - `laser_01` yellow plasma: core `#FFEE44`, halo `#FFAA00`
  - `laser_02` red pulse: core `#FF3344`, halo `#FF8888`
  - `laser_03` blue ion: core `#4488FF`, halo `#88CCFF`
  - `laser_04` green acid: core `#44FF66`, halo `#AAFFAA`
  - `laser_05` purple void: core `#AA44FF`, halo `#DDAADD`
- **Postprocess handles both white and black AI backgrounds.** The
  initial Matrix output drew black rectangles around each frame; the
  postprocess's `crop_to_content()` now inspects the (0,0) pixel and
  floodfills whichever background is present (RGB > 200 = white,
  RGB < 50 = black) to transparent.

## Asset SF+SM reorganization

The `assets/` folder is reorganized as a proper SF+SM sub-silo, matching
the project root's SF+SM v3.2 Lite structure:

```
assets/
├── CONTEXT.md                 ← "mapa de piso" — entry point
├── backgrounds/               ← unchanged
├── midi/                      ← unchanged
└── sprites/                   ← all animated sheets
    ├── CONTEXT.md             ← naming, dims, frame counts
    ├── bullets/               ← 5 laser archetypes + 2 legacy bullets
    ├── player/                ← 5 player variants + 1 thrust
    ├── enemies/{kind}/        ← scout, cruiser, heavy, bomber, ufo, kamikaze
    ├── boss/                  ← idle, telegraph, charge, dying, alt_a, alt_b
    └── _deprecated/           ← 95 files no longer loaded (kept for reference)
```

- **7 new CONTEXT.md files.** Each sub-folder has a local context
  file; the root has the entry-point "mapa de piso" matching the
  project root `AGENTS.md` style.
- **194 files moved via `git mv`** (88 from legacy `sprites/`, 106
  from `sprites_v2/`). File history preserved. No data loss.
- **Loader refactor.** `GameplayScene._sprite_path(name)` is a new
  prefix-based resolver. The 4 hardcoded path blocks in `_load_sprites`
  are replaced with the resolver. Unknown prefixes raise `ValueError`.

## Tests

- **400 → 424 passing** (+24 new tests across v1.3.0 → v1.4.0)

  **v1.4.0-specific (+11):**
  - 7 `_sprite_path()` resolver unit tests (boss / player / player_thrust /
    enemy with kind subfolder / laser × 5 / legacy bullets / unknown raises)
  - 4 `regen_laser_strips` postprocess unit tests (split_strip_to_frames,
    crop_to_content, assemble_sheet, save_reference)

  **v1.3.0 → v1.4.0 inherited (+13):** see v1.3.0 release notes.
- **`test_animation_and_sparks.py` count assertion corrected**:
  the spec math originally said 51 but the actual count is 52
  (5 player + 20 enemy + 1 thrust + 6 attack + 6 death + **7 kind
  aliases** + 2 bullets + 5 lasers = 52; the 6 boss states are in
  `_boss_anims` (separate dict), not `_animated`). The fix was a
  revert 51→52 + a comment block that documents the actual math.

## Build & runtime

- `dist/StellarHorizon.exe` rebuilt (36.17 MB) and verified by user
- 424 tests passing
- 5 laser sheets regenerated in `stellar_horizon/assets/sprites/bullets/`
- `sprite_tests/regen_laser_strips.py` postprocess tool added
- `sprite_tests/captures/all_lasers_contact_sheet.png` available for
  visual review of all 5 archetypes

## From the previous release (v1.3.0)

The head of `v1.3.0` was `ebf390f`. v1.4.0 sits on top with 13 commits:
- `659cf27` docs: add visual polish v3 design (asset SF+SM + bullet regen)
- `3e21692` fix(spec): correct file count math in visual-polish-v3-design
- `bbc947f` docs: add visual polish v3 implementation plan
- `8e6a4bc` feat(gameplay): add _sprite_path() resolver + unit test
- `8196b33` fix(spec): reorder resolver checks so 'player_bullet' / 'enemy_bullet' route to bullets/
- `51a608e` refactor(gameplay): route _load_sprites through _sprite_path resolver
- `5ec8e93` fix(test): revert count assertion 51->52 in test_animation_and_sparks
- `ed2b95d` docs: correct test count math in spec/plan (52, not 51)
- `384eee2` refactor(assets): reorganize 194 files into SF+SM sub-silo structure
- `bcad19b` feat(sprite_tests): postprocess for AI-generated laser strips
- `69955e0` docs(assets): add 7 CONTEXT.md files (root 'mapa de piso' + 6 sub)
- `282783c` feat(lasers): ship yellow plasma + postprocess handles black bg
- `8262b7a` feat(lasers): regenerate red/blue/green/purple with AI
- `753c4fe` docs: add v1.4.0 release notes
- `a799f47` tools: add create_v1_4_0_release.py
