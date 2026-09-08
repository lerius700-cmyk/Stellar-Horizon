# Visual Polish v3 — Asset SF+SM Reorganization + Bullet Regen

**Date:** 2026-09-08
**Status:** Design (pending user review of written spec)
**Author:** Lerius (with Mavis)
**Baseline:** `v1.3.0` tag (commit `ebf390f`)
**Target:** `v1.4.0` (only if user approves release after visual review)

## Problem

Two related complaints surfaced after the v1.3.0 visual polish pass:

1. **Bullets look like the same frame 4 times.** The 6-frame animated sprite sheets for all 5 laser archetypes (in `stellar_horizon/assets/sprites_v2/laser_0[1-5]_sheet.png`) vary only in alpha (0.85..1.0). On narrow/thin sprites, this alpha delta is invisible. The user said: *"pareciera el mismo frame repetido 4 veces"*. The 3 sample images the user shared confirm: `laser_01_sheet.png` (gray/cyan thin lines) and `laser_02_sheet.png` (yellow/green dot) show 6 nearly identical frames; only `laser_03_sheet.png` (green acid blob) reads as animated because the sprite has dense internal structure (highlight + shadow + edge) where the alpha pulse shows.

2. **The assets folder is a flat 194-file dump with no organization.** Two parallel folders (`sprites/` legacy, `sprites_v2/` current), 88 legacy files of which only 2 are used, 3 `test_cruiser_*` test artifacts in production, 5 single-frame AI base images of which only the procedural sheets are loaded, and no map for the next agent (or the user) to navigate. The user said: *"organiza todos los assets y aislalos por carpetas... de paso para tener un archivo que sirva como mapa de piso... tipo agents.md"*.

## Goal

Bullets read as visibly animated (each of the 6 frames is visually distinct, not the same shape with different alpha). The assets area is organized as a proper SF+SM sub-silo with per-folder `CONTEXT.md` files plus a root `CONTEXT.md` that serves as the "mapa de piso" — so the next session (and the user) can find anything in <30 seconds.

## Decisions made during brainstorming (2026-09-07/08)

The user was presented 4 questions via `ask_user`. The chosen answers are binding:

| Axis | Choice | Why |
|---|---|---|
| 1. Visual direction | **Regenerate 6 distinct frames with AI** | User rejected pure-procedural (no real shape change) and hybrid (too much work for unclear gain). Pure AI regen gives the biggest "frame changes between 0 and 5" delta. |
| 2. Generation strategy | **1 strip-prompt per archetype (5 generations)** | Cheapest viable option. 1 AI generation per archetype asking for a 6-frame horizontal strip. Trade-off: AI may not respect frame boundaries, mitigated by postprocess. |
| 3. Cleanup | **Organize into folders (don't delete)** | The user pivoted from "delete dead" to "organize and isolate" after seeing the 194-file audit. Killing the file via deletion was less valuable than isolating it for future review. |
| 4. Folder structure | **Granular: per enemy subclase, per bullet, per player, per boss, `_deprecated/`** | Maximum isolation. 3 levels deep at most. Loader uses prefix-based resolver. |
| 5. Methodology | **SF+SM Lite (sub-silo with per-folder `CONTEXT.md`)** | Project is already SF+SM v3.2 Lite. The user explicitly asked for the "agents.md-style" floor map. Reusing the same pattern keeps the cognitive model consistent. |

## Architecture

### Folder tree (target end state)

```
stellar_horizon/
└── assets/
    ├── CONTEXT.md                   ← NEW. "Mapa de piso" — top-level entry
    ├── backgrounds/                 ← unchanged
    ├── midi/                        ← unchanged
    └── sprites/                     ← REPLACES sprites_v2/. ABSORBS legacy sprites/.
        ├── CONTEXT.md               ← NEW. Naming convention, frame counts, dims
        ├── bullets/
        │   ├── CONTEXT.md           ← NEW. Archetype table, WeaponVFX cross-ref
        │   ├── laser_01_sheet.png   ← REGENERATED (strip prompt)
        │   ├── laser_01.png         ← base single-frame, kept for reference
        │   ├── laser_02_sheet.png   ← REGENERATED
        │   ├── laser_02.png
        │   ├── laser_03_sheet.png   ← REGENERATED
        │   ├── laser_03.png
        │   ├── laser_04_sheet.png   ← REGENERATED
        │   ├── laser_04.png
        │   ├── laser_05_sheet.png   ← REGENERATED
        │   ├── laser_05.png
        │   ├── player_bullet.png    ← MOVED from sprites/ (legacy)
        │   ├── player_bullet_sheet.png
        │   ├── enemy_bullet.png     ← MOVED from sprites/ (legacy)
        │   └── enemy_bullet_sheet.png
        ├── player/
        │   ├── CONTEXT.md           ← NEW. Variant table, animation rules
        │   ├── player_v1_sheet.png  ← unchanged
        │   ├── player_v1.png
        │   ├── player_v2_sheet.png
        │   ├── player_v2.png
        │   ├── player_v3_sheet.png
        │   ├── player_v3.png
        │   ├── player_v4_sheet.png
        │   ├── player_v4.png
        │   ├── player_v5_sheet.png
        │   ├── player_v5.png
        │   ├── player_thrust_v1_sheet.png
        │   └── player_thrust_v1.png
        ├── enemies/
        │   ├── CONTEXT.md           ← NEW. Variant cycle, attack/death states
        │   ├── scout/               (4 variants + attack + death + 1 base)
        │   │   ├── enemy_scout_v1_sheet.png .. _v4_sheet.png
        │   │   ├── enemy_scout_attack_v1_sheet.png
        │   │   ├── enemy_scout_death_v1_sheet.png
        │   │   └── enemy_scout_v1.png (base)
        │   ├── heavy/    (3 variants + attack + death + 1 base)
        │   ├── bomber/   (3 variants + attack + death + 1 base)
        │   ├── cruiser/  (4 variants + attack + death + 1 base)
        │   ├── ufo/      (3 variants + attack + death + 1 base)
        │   └── kamikaze/ (3 variants + attack + death + 1 base)
        ├── boss/
        │   ├── CONTEXT.md           ← NEW. State machine, phase→sprite map
        │   ├── boss_idle_v1_sheet.png
        │   ├── boss_telegraph_v1_sheet.png
        │   ├── boss_charge_v1_sheet.png
        │   ├── boss_dying_v1_sheet.png
        │   ├── boss_alternate_a_v1_sheet.png
        │   ├── boss_alternate_b_v1_sheet.png
        │   └── boss_*.png           ← base single-frames (6)
        └── _deprecated/
            ├── CONTEXT.md           ← NEW. Why each file is deprecated
            ├── legacy_sprites/      ← 86 files from old sprites/ (NOT 2 bullets)
            │                         the 2 active bullets went to bullets/
            ├── test_cruiser/        ← 6 files: test_cruiser_A_retro, _B_hd, _C_modern
            └── single_frames/       ← 5 files: laser_0[1-5].png
                                       (original AI bases, kept for re-prompting)
```

### File count delta

| | Before | After | Delta |
|---|---:|---:|---:|
| `sprites/` (legacy, mostly dead) | 88 | 0 | -88 |
| `sprites_v2/` (current, all active) | 106 | 0 | -106 |
| `sprites/_deprecated/` | 0 | 97 | +97 |
| `sprites/{bullets,player,enemies,boss}/` | 0 | 99 | +99 |
| `CONTEXT.md` files | 0 | 7 | +7 |
| **Total tracked files** | **194** | **196** | **+2** (only the 7 CONTEXT.md files; rest is just reorganization) |

The 2-file net increase is the new `CONTEXT.md` files (6 for sub-folders + 1 root = 7). The other 99 files are relocated, not added. Git history is preserved via `git mv`.

## Components

### 1. `stellar_horizon/assets/CONTEXT.md` (root "mapa de piso")

Modelled on the project `AGENTS.md`. Sections:

- **TL;DR** — what lives in `assets/`, how code loads it.
- **Layout** — ASCII tree of the whole `assets/` folder.
- **Loader entry point** — points to `stellar_horizon/scenes/gameplay.py:_load_sprites()` and the new `_sprite_path()` resolver.
- **Conventions** — naming pattern (`{entity}_{kind?}_{action?}_v{N}`), dimensions (29x29 player/enemy, 29x7 laser, 72x72 boss, 8x8 bullet), frame counts (10 for player/enemy/boss, 6 for laser, 6 for legacy bullets), fps (12 for player/enemy/laser, 8 for boss).
- **Adding new assets** — workflow (drop file, update CONTEXT.md, update test).
- **Cross-references** — maps each asset to the code slot that loads it (`_animated[name]`, `_silhouettes[(cat, name)]`, `_laser_sprites[name]`).
- **Deprecated** — link to `_deprecated/CONTEXT.md`.

Estimated size: ~5 KB (the project `AGENTS.md` is ~13 KB; this is scoped to assets only).

### 2. Per-folder `CONTEXT.md` files

Each of `bullets/`, `player/`, `enemies/`, `boss/`, `_deprecated/` gets a local `CONTEXT.md` with:
- What's in this folder (table).
- Local conventions (e.g., enemy cycle order, bullet archetype table).
- How to add to this folder.
- Cross-refs to the loader code for these specific names.

### 3. Bullet regen — strip prompt per archetype

5 generations, 1 per archetype. The Matrix `connector__matrix__generate_image` skill is used (same as v1 ship generation; ComfyUI is fallback). Each prompt requests a 6-frame horizontal strip where each frame is a *visually distinct stage* of an energy pulse, not just an alpha variation.

**Prompt template (per archetype):**

```
6-frame horizontal sprite sheet, 174x42 pixels (6 frames of 29x7),
side-by-side without gaps. 16-bit pixel art, sci-fi energy laser.
Background: pure white (will be removed by postprocess).
Sprite should occupy ~75% of each 29x7 frame.

Animation sequence (frame 1 -> 6):
- Frame 1: thin {color} line, low energy, faint outer glow
- Frame 2: thicker, growing halo, central core brightening
- Frame 3: peak — brightest core, full radial halo, edge bloom
- Frame 4: still bright, slight contraction, halo shifting outward
- Frame 5: contracting, halo dimming, trailing energy
- Frame 6: thin line, fading, faint trailing edge

Color: {color} ({rgb hex}).
Style: 16-bit shmup laser, neon, saturated, clear silhouette against white.
```

`{color}` is filled per archetype:
- `laser_01` (yellow plasma): `#FFEE44` core, `#FFAA00` halo
- `laser_02` (red pulse): `#FF3344` core, `#FF8888` halo
- `laser_03` (blue ion): `#4488FF` core, `#88CCFF` halo
- `laser_04` (green acid): `#44FF66` core, `#AAFFAA` halo
- `laser_05` (purple void): `#AA44FF` core, `#DDAADD` halo

**Postprocess (PIL, in `sprite_tests/regen_laser_strips.py`):**

1. Load the 174×42 strip output.
2. For each of 6 columns (29px wide):
   - Crop to (i*29, 0, (i+1)*29, 7).
   - Floodfill from (0,0) with white → transparent (white becomes alpha=0).
   - Find non-transparent bounding box, crop to it (with 1px padding).
   - Re-paste onto a transparent 29×7 canvas, centered.
3. Concatenate the 6 frames horizontally → `laser_NN_sheet.png` (174×7).
4. Save the first frame as `laser_NN.png` (29×7 reference).

**Iteration gate:** generate 1 archetype (yellow plasma) first, show the user the sheet + a contact-sheet PNG of all 6 frames. Wait for "OK" or feedback before generating the other 4.

### 4. Loader refactor — prefix-based resolver

**File:** `stellar_horizon/scenes/gameplay.py`

**Current code (lines 186, 215, 226-232, 244-274, 289-310):**
```python
sprite_dir = self.assets_dir / "sprites_v2"
bullet_dir = self.assets_dir / "sprites"

# 35+ hardcoded path constructions like:
path = sprite_dir / f"{name}_sheet.png"
path = sprite_dir / f"boss_{state}_v1_sheet.png"
path = bullet_dir / f"{name}_sheet.png"
path = sprite_dir / f"{name}_sheet.png"  # for lasers
```

**Target code:**

```python
def _sprite_path(self, name: str) -> Path:
    """Resolve a sprite name to its absolute path under assets/sprites/.

    Prefix-based: the name encodes its folder. This avoids a manifest
    and keeps the resolution explicit.

    Naming convention (enforced here):
      boss_*       -> sprites/boss/{name}_sheet.png
      player_*     -> sprites/player/{name}_sheet.png
      enemy_*      -> sprites/enemies/{kind}/{name}_sheet.png  (kind = name[6:].split('_')[0])
      laser_*      -> sprites/bullets/{name}_sheet.png
      player_bullet, enemy_bullet -> sprites/bullets/{name}_sheet.png
    """
    if name.startswith("boss_"):
        return self.assets_dir / "sprites" / "boss" / f"{name}_sheet.png"
    if name.startswith("player_"):
        return self.assets_dir / "sprites" / "player" / f"{name}_sheet.png"
    if name.startswith("enemy_"):
        kind = name.split("_")[1]  # enemy_scout_v1 -> "scout"
        return self.assets_dir / "sprites" / "enemies" / kind / f"{name}_sheet.png"
    if name.startswith("laser_") or name in ("player_bullet", "enemy_bullet"):
        return self.assets_dir / "sprites" / "bullets" / f"{name}_sheet.png"
    raise ValueError(f"_sprite_path: unknown sprite name '{name}'")
```

All path constructions inside `_load_sprites()` (lines 226-232, 259-264, 270-274, 289-310) become `path = self._sprite_path(name)`. The `sprite_dir` and `bullet_dir` local variables are removed.

### 5. Cleanup of legacy

| Source | Destination | Method |
|---|---|---|
| `assets/sprites/player_bullet.png` + `_sheet.png` | `assets/sprites/bullets/` | `git mv` |
| `assets/sprites/enemy_bullet.png` + `_sheet.png` | `assets/sprites/bullets/` | `git mv` |
| `assets/sprites/*` (remaining 86 files) | `assets/sprites/_deprecated/legacy_sprites/` | `git mv` |
| `assets/sprites_v2/test_cruiser_*.png` (6 files) | `assets/sprites/_deprecated/test_cruiser/` | `git mv` |
| `assets/sprites_v2/laser_0[1-5].png` (5 files) | `assets/sprites/_deprecated/single_frames/` | `git mv` |
| `assets/sprites_v2/{all other files}` | `assets/sprites/{bullets,player,enemies,boss}/` per their kind | `git mv` |
| `assets/sprites_v2/` (now empty) | deleted | `git rm --empty-dir` (or rmdir + git) |

`git mv` preserves the file history. No file is destroyed.

### 6. PyInstaller spec — `StellarHorizon.spec`

**Current (line 8):**
```python
datas=[('stellar_horizon/assets', 'stellar_horizon/assets'),
       ('stellar_horizon/waves', 'stellar_horizon/waves'),
       ('stellar_horizon/settings.py', 'stellar_horizon')],
```

This globs the entire `assets/` tree, so the new sub-folder structure is included automatically. **No change needed** to the spec. The `test_post_refactor_exe.py:43-52` regression guard still passes.

### 7. Test updates

**File:** `stellar_horizon/tests/test_animation_and_sparks.py`

- Line 39: `path = Path("stellar_horizon/assets/sprites/_test_anim.png")` — this writes a temp file to the legacy `sprites/` dir. Update to write to the new structure or to `tmp_path`.
- Lines 70-95: comments reference `sprites_v2/`. Update to `sprites/{bullets,player,enemies,boss}` per the new structure. The 52-count assertion stays the same (the 5 lasers + 1 thrust + 6 attacks + 6 deaths + 5 player + 20 enemy + 2 bullets + 6 boss = 51 actual entries; if the count was 52 before, reconcile the math — see Risks).

**File:** `stellar_horizon/tests/test_bullet_render.py`

- Line 39: `s._animated.get("laser_01")` — the dict key is the name, not the path. No change needed. The test should still pass as long as the resolver loads the new `laser_01_sheet.png` from `bullets/`.

**File:** `stellar_horizon/tests/test_post_refactor_exe.py`

- Verifies `StellarHorizon.spec` includes required directories. No change needed (assets tree is still globbed as a single entry).

**New tests:**

- `test_sprite_path_resolver.py` — table-driven test of the new `_sprite_path()` function. For each known name, assert the path is correct. For an unknown prefix, assert `ValueError`.

## Risks

1. **AI strip-prompt may not respect frame boundaries.** The 6 frames in the output image may have inconsistent widths, white gaps, or shared edges. Mitigation: postprocess uses column-based cropping at fixed 29px intervals. If a frame's content overflows into the next column, postprocess widens that frame at the expense of the next. Worst case: regenerate the archetype with a stronger prompt.

2. **The animation might still read as static after regen.** If the AI produces 6 frames that are all visually similar (just rotated or recolored), we still have the original problem. Mitigation: the iteration gate (show user 1 archetype first) catches this before the full 5-archetype regen.

3. **Existing test count math is brittle.** The `_animated` count comment says 52, but actual is 51 (5 player + 20 enemy + 1 thrust + 6 attacks + 6 deaths + 5 lasers + 2 bullets + 6 boss = 51). The test may be passing with a magic number that's wrong. Need to recount after the refactor and fix the assertion. This is **discovered during the implementation** — flag for the implementer.

4. **`_make_silhouette_set` (gameplay.py:778) might fail for new laser frames.** The current silhouette uses 1.08× scale of the sprite. If the new laser frames have transparent pixels at the edges (postprocess), the silhouette may pick up unexpected pixels. Mitigation: silhouette is a render backdrop; visual review will catch issues.

5. **PyInstaller build may miss the new sub-folders if the spec glob changes.** The current spec is a top-level glob (`stellar_horizon/assets`) which recurses. If someone tightens the spec to only ship `sprites/`, the sub-folders won't be in the .exe. Mitigation: leave the spec as-is and add a post-build smoke test that verifies a sample file from each new sub-folder is present in the .exe.

## Out of scope

- Boss death-fall v2 (boss doesn't use new physics).
- Player ship sprite variety (5 variants exist, only 1 used).
- Explosion VFX variety per kind.
- Boss telegraph visual.
- Power-up sparkles.
- Screen shake feedback per weapon.
- Hit-stop / freeze frame.
- Muzzle flash.
- Cockpit HUD elements.
- Camera shake on big explosions.

These were listed in the v1.3.0 spec's "Out of scope" section and remain deferred.

## Order of operations

1. Create the new folder skeleton (empty dirs).
2. `git mv` all files to their new locations.
3. Update `gameplay.py` with the `_sprite_path` resolver.
4. Update `test_animation_and_sparks.py` paths and recount assertion.
5. Add `test_sprite_path_resolver.py`.
6. Run the full test suite — must be green.
7. Build the .exe — must launch.
8. **Generate 1 archetype sample (yellow plasma) — show user — wait for "OK".**
9. Generate the other 4 archetypes.
10. Re-build .exe and run a visual review session.
11. **Wait for user "listo".**
12. Commit + tag v1.4.0 (only if user approves release).

## References

- Project `AGENTS.md` (root) — SF+SM onboarding, hard rules, conventions.
- `docs/superpowers/specs/2026-09-06-visual-polish-v2-design.md` — previous design (the laser sheet + per-weapon particles that this spec builds on).
- `stellar_horizon/scenes/gameplay.py:170-310` — current `_load_sprites` (the code being refactored).
- `stellar_horizon/entities/bullet.py:14-23` — `WEAPON_ARCHETYPE` table (the source of truth for the 5 archetypes).
- `stellar_horizon/fx/bullet_vfx.py` — `WeaponVFX` dataclass and `WEAPON_VFX_PARAMS` (the visual identity per archetype that the regen must respect).
