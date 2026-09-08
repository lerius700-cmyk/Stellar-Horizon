# Visual Polish v3 — Asset SF+SM Reorganization + Bullet Regen

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the assets folder as a proper SF+SM sub-silo with per-folder `CONTEXT.md` files, and regenerate the 5 laser sprite sheets so bullets read as visibly animated (not alpha-pulse ghosts).

**Architecture:** 8 tasks. Mechanical reorganization via `git mv` (no data loss). Prefix-based `_sprite_path()` resolver replaces hardcoded paths in `_load_sprites()`. AI regen uses a strip-prompt + PIL postprocess pattern. 2 iteration gates: after Task 4 (1 archetype sample → user OK) and Task 7 (build + visual review → user "listo"). Task 8 is conditional on user release approval.

**Tech Stack:** Python 3.11+, Pygame 2.6.1, PIL 12.3.0, pytest 9, mcode-tools Matrix (`connector__matrix__generate_image`), git 2.x, PowerShell 5.1.

## Global Constraints

These are the spec's project-wide requirements. Every task's requirements implicitly include this section.

- **Path resolution:** All asset paths via `Path(__file__).resolve().parent` (never CWD-relative). Hard rule from project `AGENTS.md` — the v1.1.0 release broke on a CWD-relative path.
- **No `image_synthesize` tool.** Use `connector__matrix__generate_image` via mcode-tools (Matrix). ComfyUI is a fallback if Matrix is down.
- **No `print()` of tokens, credentials, or full paths to user-owned files.** Release scripts log LENGTH only.
- **No auto zip / version.** User controls release cadence. Build the .exe + .zip ONLY when the user explicitly asks. This plan builds the .exe for visual review but does NOT create a v1.4.0 release unless the user approves (Task 8).
- **`__slots__` discipline** on entity classes (`Player`, `Enemy`, `Bullet`). Not directly relevant here but applies if extending.
- **Type hints on all public functions.** `from __future__ import annotations` at top.
- **PIL background removal:** white (255, 255, 255) is the postprocess's chroma key. The AI prompt explicitly asks for white background.
- **Naming convention enforced by `_sprite_path`:** `boss_*` → boss/; `player_*` → player/; `enemy_*` → enemies/{kind}/; `laser_*` + `player_bullet` + `enemy_bullet` → bullets/. Any name not matching a prefix raises `ValueError`.
- **Test count assertion:** `test_animation_and_sparks.py` asserts `len(s._animated) == 52`. Correct count: 5 player + 20 enemy + 1 thrust + 6 attack + 6 death + 7 kind aliases (scout/cruiser/heavy/bomber/ufo/kamikaze/player, sharing instances with v1 variants) + 2 bullets + 5 lasers = 52. Boss states are in `_boss_anims` (separate dict), NOT in `_animated`. Task 2 includes a comment fix but no assertion change.

## File Structure

### New files to create

| Path | Purpose | Task |
|---|---|---|
| `stellar_horizon/assets/CONTEXT.md` | Root "mapa de piso" — TL;DR, layout, conventions, loader entry point | Task 5 |
| `stellar_horizon/assets/sprites/CONTEXT.md` | sprites/ conventions: naming, dims, frame counts | Task 5 |
| `stellar_horizon/assets/sprites/bullets/CONTEXT.md` | Archetype table, WeaponVFX cross-ref | Task 5 |
| `stellar_horizon/assets/sprites/player/CONTEXT.md` | Variant table, animation rules | Task 5 |
| `stellar_horizon/assets/sprites/enemies/CONTEXT.md` | Variant cycle, attack/death states | Task 5 |
| `stellar_horizon/assets/sprites/boss/CONTEXT.md` | State machine, phase→sprite map | Task 5 |
| `stellar_horizon/assets/sprites/_deprecated/CONTEXT.md` | Why each deprecated file is here | Task 5 |
| `stellar_horizon/tests/test_sprite_path_resolver.py` | Unit test of the new resolver | Task 2 |
| `sprite_tests/regen_laser_strips.py` | PIL postprocess: strip image → sheet + reference | Task 3 |
| `sprite_tests/test_regen_laser_strips.py` | Test of the postprocess (using a mock strip) | Task 3 |
| `sprite_tests/captures/laser_contact_sheet.png` | Diagnostic output (one PNG showing all 5 archetype sheets stacked) | Task 4 + Task 6 |
| `RELEASE_NOTES_v1.4.0.md` | Release notes (only created if Task 8 fires) | Task 8 |

### Files to modify

| Path | Change | Task |
|---|---|---|
| `stellar_horizon/scenes/gameplay.py` | Add `_sprite_path()` method; replace 4 path-construction blocks inside `_load_sprites`; remove `sprite_dir` and `bullet_dir` local variables | Task 1 + Task 2 |
| `stellar_horizon/tests/test_animation_and_sparks.py` | Update line 39 to write test sprite to new location; update lines 70-130 to reference new folder structure; fix the 52→51 count assertion | Task 2 |

### Files to move (git mv, no data loss)

| Source | Destination | Count |
|---|---|---:|
| `assets/sprites/player_bullet.png` + `_sheet.png` | `assets/sprites/bullets/` | 2 |
| `assets/sprites/enemy_bullet.png` + `_sheet.png` | `assets/sprites/bullets/` | 2 |
| `assets/sprites/*` (remaining) | `assets/sprites/_deprecated/legacy_sprites/` | 84 |
| `assets/sprites_v2/test_cruiser_*.png` (6 files) | `assets/sprites/_deprecated/test_cruiser/` | 6 |
| `assets/sprites_v2/laser_0[1-5].png` (5 bases) | `assets/sprites/_deprecated/single_frames/` | 5 |
| `assets/sprites_v2/laser_0[1-5]_sheet.png` (5 sheets) | `assets/sprites/bullets/` (overwriting) | 5 |
| `assets/sprites_v2/player_*.png` (5 variants + 1 thrust × 2 = 12) | `assets/sprites/player/` | 12 |
| `assets/sprites_v2/enemy_*.png` (66 files, 6 kinds) | `assets/sprites/enemies/{kind}/` | 66 |
| `assets/sprites_v2/boss_*.png` (6 states × 2 = 12) | `assets/sprites/boss/` | 12 |
| `assets/sprites_v2/` (now empty) | deleted | — |

**Total moves: 194 files into 99 sub-folder + 95 deprecated = 194.** Net new files: 12 (7 CONTEXT.md + 1 new test + 1 regen tool + 1 regen test + 1 contact sheet + 1 release notes conditional).

---

## Task 1: Add `_sprite_path` resolver (TDD)

**Files:**
- Modify: `stellar_horizon/scenes/gameplay.py` (add method, no behavior change yet)
- Create: `stellar_horizon/tests/test_sprite_path_resolver.py`

**Interfaces:**
- Consumes: `self.assets_dir: Path` (already exists on GameplayScene)
- Produces: `self._sprite_path(name: str) -> Path` — method that resolves a sprite name to its new structure path. Raises `ValueError` for unknown prefixes.

This task ONLY adds the resolver. The existing path-construction code inside `_load_sprites` is unchanged. Task 2 will swap the call sites.

- [ ] **Step 1: Write the failing unit test**

Create `stellar_horizon/tests/test_sprite_path_resolver.py`:

```python
"""Unit tests for GameplayScene._sprite_path() resolver.

Spec: docs/superpowers/specs/2026-09-08-visual-polish-v3-design.md section 4.
"""
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from stellar_horizon.scenes.gameplay import GameplayScene


@pytest.fixture
def scene():
    """Construct a GameplayScene with a mocked assets_dir.

    We do NOT call on_enter() — this avoids pygame display + audio init.
    The resolver only needs assets_dir.
    """
    s = GameplayScene.__new__(GameplayScene)
    s.assets_dir = Path("D:/AI/stellar-horizon/stellar_horizon/assets")
    return s


def test_resolves_boss_name(scene):
    p = scene._sprite_path("boss_idle_v1")
    assert p == scene.assets_dir / "sprites" / "boss" / "boss_idle_v1_sheet.png"


def test_resolves_player_name(scene):
    p = scene._sprite_path("player_v1")
    assert p == scene.assets_dir / "sprites" / "player" / "player_v1_sheet.png"


def test_resolves_player_thrust(scene):
    p = scene._sprite_path("player_thrust_v1")
    assert p == scene.assets_dir / "sprites" / "player" / "player_thrust_v1_sheet.png"


def test_resolves_enemy_with_kind_subfolder(scene):
    p = scene._sprite_path("enemy_scout_v1")
    assert p == scene.assets_dir / "sprites" / "enemies" / "scout" / "enemy_scout_v1_sheet.png"
    p = scene._sprite_path("enemy_heavy_attack_v1")
    assert p == scene.assets_dir / "sprites" / "enemies" / "heavy" / "enemy_heavy_attack_v1_sheet.png"
    p = scene._sprite_path("enemy_kamikaze_v1_v2")
    assert p == scene.assets_dir / "sprites" / "enemies" / "kamikaze" / "enemy_kamikaze_v1_v2_sheet.png"


def test_resolves_laser_name(scene):
    for i in range(1, 6):
        p = scene._sprite_path(f"laser_{i:02d}")
        assert p == scene.assets_dir / "sprites" / "bullets" / f"laser_{i:02d}_sheet.png"


def test_resolves_legacy_bullets(scene):
    p = scene._sprite_path("player_bullet")
    assert p == scene.assets_dir / "sprites" / "bullets" / "player_bullet_sheet.png"
    p = scene._sprite_path("enemy_bullet")
    assert p == scene.assets_dir / "sprites" / "bullets" / "enemy_bullet_sheet.png"


def test_unknown_prefix_raises_value_error(scene):
    with pytest.raises(ValueError, match="unknown sprite name"):
        scene._sprite_path("xyz_unknown_thing")
```

- [ ] **Step 2: Run the test to verify it fails (expected: NameError)**

Run:
```powershell
cd D:\AI\stellar-horizon; .\.venv\Scripts\python.exe -m pytest stellar_horizon/tests/test_sprite_path_resolver.py -v
```
Expected: `FAILED ... AttributeError: 'GameplayScene' object has no attribute '_sprite_path'`

- [ ] **Step 3: Add the `_sprite_path` method to `GameplayScene`**

In `stellar_horizon/scenes/gameplay.py`, find the class (search for `class GameplayScene(`). Add the method just BEFORE the `_load_sprites` method (around line 169):

```python
    def _sprite_path(self, name: str) -> Path:
        """Resolve a sprite name to its absolute path under assets/sprites/.

        Prefix-based: the name encodes its folder. This avoids a manifest
        and keeps the resolution explicit. Naming convention (enforced
        here): boss_* -> sprites/boss/; player_* -> sprites/player/;
        enemy_* -> sprites/enemies/{kind}/ (kind = name[6:].split('_')[0]);
        laser_* + player_bullet + enemy_bullet -> sprites/bullets/.

        Raises:
            ValueError: if name does not match any known prefix.
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

Also add `from pathlib import Path` to the imports at the top of the file IF it isn't already imported. Check line 1-35 of `gameplay.py` for the existing imports.

- [ ] **Step 4: Run the test to verify it passes**

Run:
```powershell
cd D:\AI\stellar-horizon; .\.venv\Scripts\python.exe -m pytest stellar_horizon/tests/test_sprite_path_resolver.py -v
```
Expected: 7 tests passed.

- [ ] **Step 5: Run the full test suite to verify nothing else broke**

Run:
```powershell
cd D:\AI\stellar-horizon; .\.venv\Scripts\python.exe -m pytest stellar_horizon/tests/ -q
```
Expected: 413 passed (current baseline). The new test counts as +7, so should be 420 total. Wait — re-read the spec. The test suite currently has 413. Adding 7 new tests = 420. If only 7 new tests added, 420.

- [ ] **Step 6: Commit**

```powershell
cd D:\AI\stellar-horizon; git add stellar_horizon/scenes/gameplay.py stellar_horizon/tests/test_sprite_path_resolver.py
git -c user.email="Lerius@void-hunter.local" -c user.name="Lerius" commit -m "feat(gameplay): add _sprite_path() resolver + unit test

Prefix-based: name encodes its location.
  boss_*       -> sprites/boss/{name}_sheet.png
  player_*     -> sprites/player/{name}_sheet.png
  enemy_*      -> sprites/enemies/{kind}/{name}_sheet.png
  laser_*      -> sprites/bullets/{name}_sheet.png
  player_bullet, enemy_bullet -> sprites/bullets/{name}_sheet.png

This task ONLY adds the resolver. The existing _load_sprites path
construction is unchanged. Task 2 swaps the call sites.

TDD: test_sprite_path_resolver.py with 7 cases, all pass.
Tests: 413 -> 420."
```

---

## Task 2: Refactor `_load_sprites` to use the resolver + update test paths

**Files:**
- Modify: `stellar_horizon/scenes/gameplay.py:_load_sprites` (4 path-construction blocks)
- Modify: `stellar_horizon/tests/test_animation_and_sparks.py` (path update + count fix)

**Interfaces:**
- Consumes: `self._sprite_path(name)` from Task 1
- Produces: `_load_sprites` that resolves ALL paths via the new resolver. The `sprite_dir` and `bullet_dir` local variables are removed.

This task makes the game EXPECT the new path structure. After this commit, the test suite will FAIL because the files haven't been moved yet. This is intentional — Task 3 fixes it.

- [ ] **Step 1: Locate the 4 path-construction blocks in `_load_sprites`**

Open `stellar_horizon/scenes/gameplay.py` and find these blocks (use `Read` with offset to see the file):

- Line 186: `sprite_dir = self.assets_dir / "sprites_v2"`
- Line 215: `bullet_dir = self.assets_dir / "sprites"`
- Line 226-232: `for name in animated_names: path = sprite_dir / f"{name}_sheet.png"`
- Line 259-264: `for name in bullet_names: path = bullet_dir / f"{name}_sheet.png"`
- Line 270-274: `for state in (...): path = sprite_dir / f"boss_{state}_v1_sheet.png"`
- Line 289-310: `for i in range(1, 6): name = f"laser_{i:02d}"; path = sprite_dir / f"{name}_sheet.png"`

- [ ] **Step 2: Refactor the animated_names loop (lines 226-232)**

Replace:
```python
        for name in animated_names:
            path = sprite_dir / f"{name}_sheet.png"
            anim = AnimatedSprite(
                str(path), 29, 29, 10, fps=12.0,
            )
            self._animated[name] = anim
            self._silhouettes[("enemy", name)] = self._make_silhouette_set(anim)
```

With:
```python
        for name in animated_names:
            path = self._sprite_path(name)
            anim = AnimatedSprite(
                str(path), 29, 29, 10, fps=12.0,
            )
            self._animated[name] = anim
            self._silhouettes[("enemy", name)] = self._make_silhouette_set(anim)
```

- [ ] **Step 3: Refactor the bullet_names loop (lines 259-264)**

Replace:
```python
        for name in bullet_names:
            path = bullet_dir / f"{name}_sheet.png"
            self._animated[name] = AnimatedSprite(
                str(path), 8, 8, 6, fps=12.0,
            )
```

With:
```python
        for name in bullet_names:
            path = self._sprite_path(name)
            self._animated[name] = AnimatedSprite(
                str(path), 8, 8, 6, fps=12.0,
            )
```

- [ ] **Step 4: Refactor the boss state loop (lines 270-274)**

Replace:
```python
            path = sprite_dir / f"boss_{state}_v1_sheet.png"
            anim = AnimatedSprite(
                str(path), 72, 72, 10, fps=8.0,
            )
```

With:
```python
            path = self._sprite_path(f"boss_{state}_v1")
            anim = AnimatedSprite(
                str(path), 72, 72, 10, fps=8.0,
            )
```

- [ ] **Step 5: Refactor the laser sheets loop (lines 289-310)**

Replace:
```python
        for i in range(1, 6):
            name = f"laser_{i:02d}"
            path = sprite_dir / f"{name}_sheet.png"
```

With:
```python
        for i in range(1, 6):
            name = f"laser_{i:02d}"
            path = self._sprite_path(name)
```

- [ ] **Step 6: Remove the now-unused `sprite_dir` and `bullet_dir` variables**

Delete these two lines (they were at 186 and 215):
```python
        sprite_dir = self.assets_dir / "sprites_v2"
```
```python
        bullet_dir = self.assets_dir / "sprites"
```

(They will be the only places these names appear; verify with `grep -n "sprite_dir\|bullet_dir" stellar_horizon/scenes/gameplay.py` — should return nothing.)

- [ ] **Step 7: Run the test suite — expect FAILURES (files not yet moved)**

Run:
```powershell
cd D:\AI\stellar-horizon; .\.venv\Scripts\python.exe -m pytest stellar_horizon/tests/test_animation_and_sparks.py -v
```
Expected: `test_gameplay_scene_loads_sprites_split` and other integration tests FAIL because `pathlib.Path(self._sprite_path(name))` returns a path that doesn't exist (files still in `sprites_v2/`).

- [ ] **Step 8: Update `test_animation_and_sparks.py` to reference the new structure**

In `stellar_horizon/tests/test_animation_and_sparks.py`:

- Line 39: change `path = Path("stellar_horizon/assets/sprites/_test_anim.png")` to `path = Path("stellar_horizon/assets/sprites/_test_anim.png")` → `path = tmp_path / "_test_anim.png"`. This writes to a temp dir instead of polluting the assets folder. (The fixture `tmp_path` is provided by pytest; you may need to pass it through to whichever test uses this — check the function signature at line 36.)

- Lines 70-95: update the comment that says "sprites_v2/" to say "sprites/". Specifically:
  - Line 73-77: change "sprites_v2/ library" to "sprites/ library"; the folder names in the assertion section that follow don't need to change (the test uses `s._animated[name]` keys, not paths).

- [ ] **Step 9: Update the test_animation_and_sparks.py comment block**

The assertion `assert len(s._animated) == 52` is CORRECT (the count is 52
including 7 kind aliases that share AnimatedSprite instances with the v1
variants but are separate dict keys). The misleading old comment said
"= 52 total" without explaining the aliases. Replace the comment block:

```python
    # Animated cache: 5 player + 20 enemy + 1 thrust + 6 attack + 6
    # death + 7 kind aliases (scout, cruiser, heavy, bomber, ufo,
    # kamikaze, player — same AnimatedSprite instances as v1 variants
    # but separate dict keys) + 2 bullets + 5 lasers = 52.
    # (Boss states are in _boss_anims, NOT _animated. 2026-09-08.)
    assert len(s._animated) == 52
```

The assertion stays at 52; the comment is now accurate.

- [ ] **Step 10: Run the test suite — STILL FAILING (intentional)**

Run:
```powershell
cd D:\AI\stellar-horizon; .\.venv\Scripts\python.exe -m pytest stellar_horizon/tests/ -q
```
Expected: `test_animation_and_sparks.py::test_gameplay_scene_loads_sprites_split` and `test_bullet_render.py::test_*` FAIL. Other 420 - 2 = 418 tests pass. This is the expected "broken window" between Task 2 and Task 3.

- [ ] **Step 11: Commit (with the broken tests)**

```powershell
cd D:\AI\stellar-horizon; git add stellar_horizon/scenes/gameplay.py stellar_horizon/tests/test_animation_and_sparks.py
git -c user.email="Lerius@void-hunter.local" -c user.name="Lerius" commit -m "refactor(gameplay): route _load_sprites through _sprite_path resolver

Replaces 4 hardcoded path blocks:
  - animated_names loop (35 names)
  - bullet_names loop (2 names)
  - boss state loop (6 states)
  - laser sheets loop (5 names)

sprite_dir and bullet_dir local variables removed.

Tests INTENTIONALLY BROKEN: the new paths point to the new folder
structure that Task 3 creates. This commit signals the next task.

Also fixed:
  - test_animation_and_sparks.py:39 writes to tmp_path
  - test_animation_and_sparks.py:95 comment block updated (assertion
    stays at 52 — see Global Constraints for the actual count math)
  - Comments updated sprites_v2/ -> sprites/"
```

---

## Task 3: Atomic `git mv` of all 194 files to the new structure

**Files:**
- Move: 194 files via `git mv` (no data loss)
- Delete: empty `assets/sprites_v2/` and `assets/sprites/` (legacy)

This is the riskiest task. ONE atomic commit. If anything goes wrong, the user can `git revert` and try again.

- [ ] **Step 1: Create the new folder skeleton**

```powershell
cd D:\AI\stellar-horizon; New-Item -ItemType Directory -Path stellar_horizon/assets/sprites/bullets,stellar_horizon/assets/sprites/player,stellar_horizon/assets/sprites/enemies/scout,stellar_horizon/assets/sprites/enemies/cruiser,stellar_horizon/assets/sprites/enemies/heavy,stellar_horizon/assets/sprites/enemies/bomber,stellar_horizon/assets/sprites/enemies/ufo,stellar_horizon/assets/sprites/enemies/kamikaze,stellar_horizon/assets/sprites/boss,stellar_horizon/assets/sprites/_deprecated/legacy_sprites,stellar_horizon/assets/sprites/_deprecated/test_cruiser,stellar_horizon/assets/sprites/_deprecated/single_frames -Force
```

- [ ] **Step 2: Move the 4 active bullet files from legacy `sprites/` to `bullets/`**

```powershell
cd D:\AI\stellar-horizon
git mv stellar_horizon/assets/sprites/player_bullet.png   stellar_horizon/assets/sprites/bullets/
git mv stellar_horizon/assets/sprites/player_bullet_sheet.png stellar_horizon/assets/sprites/bullets/
git mv stellar_horizon/assets/sprites/enemy_bullet.png    stellar_horizon/assets/sprites/bullets/
git mv stellar_horizon/assets/sprites/enemy_bullet_sheet.png  stellar_horizon/assets/sprites/bullets/
```

- [ ] **Step 3: Move the remaining 84 legacy files to `_deprecated/legacy_sprites/`**

Use a glob. From PowerShell:

```powershell
cd D:\AI\stellar-horizon
Get-ChildItem -Path stellar_horizon/assets/sprites/*.png | Where-Object { $_.Name -notmatch '^(player_bullet|enemy_bullet)' } | ForEach-Object {
    git mv $_.FullName stellar_horizon/assets/sprites/_deprecated/legacy_sprites/
}
```

Verify count: `(Get-ChildItem stellar_horizon/assets/sprites/_deprecated/legacy_sprites/ -File).Count` should be 84.

- [ ] **Step 4: Move the 6 test_cruiser files to `_deprecated/test_cruiser/`**

```powershell
cd D:\AI\stellar-horizon
git mv stellar_horizon/assets/sprites_v2/test_cruiser_A_retro.png      stellar_horizon/assets/sprites/_deprecated/test_cruiser/
git mv stellar_horizon/assets/sprites_v2/test_cruiser_A_retro_sheet.png stellar_horizon/assets/sprites/_deprecated/test_cruiser/
git mv stellar_horizon/assets/sprites_v2/test_cruiser_B_hd.png         stellar_horizon/assets/sprites/_deprecated/test_cruiser/
git mv stellar_horizon/assets/sprites_v2/test_cruiser_B_hd_sheet.png    stellar_horizon/assets/sprites/_deprecated/test_cruiser/
git mv stellar_horizon/assets/sprites_v2/test_cruiser_C_modern.png     stellar_horizon/assets/sprites/_deprecated/test_cruiser/
git mv stellar_horizon/assets/sprites_v2/test_cruiser_C_modern_sheet.png stellar_horizon/assets/sprites/_deprecated/test_cruiser/
```

- [ ] **Step 5: Move the 5 laser base singles to `_deprecated/single_frames/`**

```powershell
cd D:\AI\stellar-horizon
git mv stellar_horizon/assets/sprites_v2/laser_01.png stellar_horizon/assets/sprites/_deprecated/single_frames/
git mv stellar_horizon/assets/sprites_v2/laser_02.png stellar_horizon/assets/sprites/_deprecated/single_frames/
git mv stellar_horizon/assets/sprites_v2/laser_03.png stellar_horizon/assets/sprites/_deprecated/single_frames/
git mv stellar_horizon/assets/sprites_v2/laser_04.png stellar_horizon/assets/sprites/_deprecated/single_frames/
git mv stellar_horizon/assets/sprites_v2/laser_05.png stellar_horizon/assets/sprites/_deprecated/single_frames/
```

- [ ] **Step 6: Move the 5 laser sheets to `bullets/`**

```powershell
cd D:\AI\stellar-horizon
git mv stellar_horizon/assets/sprites_v2/laser_01_sheet.png stellar_horizon/assets/sprites/bullets/
git mv stellar_horizon/assets/sprites_v2/laser_02_sheet.png stellar_horizon/assets/sprites/bullets/
git mv stellar_horizon/assets/sprites_v2/laser_03_sheet.png stellar_horizon/assets/sprites/bullets/
git mv stellar_horizon/assets/sprites_v2/laser_04_sheet.png stellar_horizon/assets/sprites/bullets/
git mv stellar_horizon/assets/sprites_v2/laser_05_sheet.png stellar_horizon/assets/sprites/bullets/
```

- [ ] **Step 7: Move all 12 player files to `player/`**

```powershell
cd D:\AI\stellar-horizon
foreach ($name in @('player_v1','player_v2','player_v3','player_v4','player_v5','player_thrust_v1')) {
    git mv "stellar_horizon/assets/sprites_v2/${name}.png"      "stellar_horizon/assets/sprites/player/${name}.png"
    git mv "stellar_horizon/assets/sprites_v2/${name}_sheet.png" "stellar_horizon/assets/sprites/player/${name}_sheet.png"
}
```

- [ ] **Step 8: Move the 66 enemy files to `enemies/{kind}/`**

The kind comes from the second underscore-separated token: `enemy_scout_v1` → kind=`scout`. Map kinds to subfolders:

```powershell
cd D:\AI\stellar-horizon
$kindMap = @{
    'scout'    = 'scout'
    'cruiser'  = 'cruiser'
    'heavy'    = 'heavy'
    'bomber'   = 'bomber'
    'ufo'      = 'ufo'
    'kamikaze' = 'kamikaze'
}
Get-ChildItem -Path stellar_horizon/assets/sprites_v2/enemy_*.png | ForEach-Object {
    $baseName = $_.BaseName
    $kind = ($baseName -split '_')[1]  # enemy_scout_v1 -> "scout"
    $subdir = $kindMap[$kind]
    if ($subdir) {
        git mv $_.FullName "stellar_horizon/assets/sprites/enemies/$subdir/${baseName}.png"
    } else {
        Write-Warning "Unknown kind: $kind in $baseName"
    }
}
```

Verify count per subfolder:
```powershell
Get-ChildItem stellar_horizon/assets/sprites/enemies/ -Recurse -File | Group-Object Directory | Select-Object Name, Count | Format-Table -AutoSize
```
Expected: scout=12, heavy=10, bomber=10, cruiser=12, ufo=10, kamikaze=12 (sum = 66).

- [ ] **Step 9: Move the 12 boss files to `boss/`**

```powershell
cd D:\AI\stellar-horizon
foreach ($state in @('idle','telegraph','charge','dying','alternate_a','alternate_b')) {
    $name = "boss_${state}_v1"
    git mv "stellar_horizon/assets/sprites_v2/${name}.png"      "stellar_horizon/assets/sprites/boss/${name}.png"
    git mv "stellar_horizon/assets/sprites_v2/${name}_sheet.png" "stellar_horizon/assets/sprites/boss/${name}_sheet.png"
}
```

- [ ] **Step 10: Remove the empty `sprites_v2/` directory**

```powershell
cd D:\AI\stellar-horizon
Remove-Item stellar_horizon/assets/sprites_v2/ -Recurse -Force
git add -A
```

(The `git add -A` is needed because removing a directory doesn't always auto-stage.)

- [ ] **Step 11: Verify the tree**

```powershell
cd D:\AI\stellar-horizon; Get-ChildItem -Recurse -File stellar_horizon/assets/ | Measure-Object | Select-Object -ExpandProperty Count
```
Expected: 194 + 0 (no new files yet) = 194. (The 7 CONTEXT.md come in Task 5.)

Cross-check folder structure:
```powershell
cd D:\AI\stellar-horizon; Get-ChildItem stellar_horizon/assets/sprites/ -Directory | Select-Object Name; Get-ChildItem stellar_horizon/assets/sprites/enemies/ -Directory | Select-Object Name
```
Expected: `bullets`, `player`, `enemies`, `boss`, `_deprecated`; enemies subdirs: `scout`, `cruiser`, `heavy`, `bomber`, `ufo`, `kamikaze`.

- [ ] **Step 12: Run the test suite — should now PASS**

```powershell
cd D:\AI\stellar-horizon; .\.venv\Scripts\python.exe -m pytest stellar_horizon/tests/ -q
```
Expected: 420 passed.

- [ ] **Step 13: Commit**

```powershell
cd D:\AI\stellar-horizon
git -c user.email="Lerius@void-hunter.local" -c user.name="Lerius" commit -m "refactor(assets): reorganize 194 files into SF+SM sub-silo structure

New tree:
  assets/sprites/
    bullets/        5 laser sheets + 4 legacy bullets (9)
    player/         5 variants + 1 thrust (12)
    enemies/{kind}/ scout=12 cruiser=12 heavy=10 bomber=10 ufo=10 kamikaze=12 (66)
    boss/           6 states (12)
    _deprecated/
      legacy_sprites/ 84 (old sprites/ minus the 4 active bullets)
      test_cruiser/   6 (test_cruiser_A/B/C)
      single_frames/  5 (laser_0[1-5].png bases)

All moves via git mv — file history preserved. No data loss.
sprites_v2/ and legacy sprites/ removed.

Tests: 420 pass (was broken at end of Task 2, now green)."
```

---

## Task 4: Write the regen tool + test (TDD)

**Files:**
- Create: `sprite_tests/regen_laser_strips.py`
- Create: `sprite_tests/test_regen_laser_strips.py`

**Interfaces:**
- Consumes: A 174×42 strip image (6 frames of 29×7 side-by-side, white background, sprite pixels with alpha)
- Produces: A 174×7 sheet (6 transparent-cropped 29×7 frames concatenated) + a 29×7 reference (frame 1)

This is a PIL-only tool. The AI gen happens in Task 5+ and produces the input strip.

- [ ] **Step 1: Write the failing test**

Create `sprite_tests/test_regen_laser_strips.py`:

```python
"""Tests for sprite_tests/regen_laser_strips.py postprocess."""
from __future__ import annotations

import io
from pathlib import Path
from PIL import Image

from sprite_tests.regen_laser_strips import (
    split_strip_to_frames,
    crop_to_content,
    assemble_sheet,
    save_reference,
)


def _make_test_strip() -> Image.Image:
    """Build a 174x42 strip with a known sprite in each 29x7 column.

    Column 0 (frames 0): single red pixel at (10, 3) (relative).
    Column 1 (frame 1): a horizontal red line of 5 pixels.
    Column 2 (frame 2): a 5x3 red rectangle.
    Column 3 (frame 3): a circle-ish blob (5x5).
    Column 4 (frame 4): the horizontal line.
    Column 5 (frame 5): single pixel.
    """
    strip = Image.new("RGBA", (174, 42), (255, 255, 255, 255))
    for col in range(6):
        x0 = col * 29
        if col in (0, 5):
            strip.putpixel((x0 + 10, 3), (255, 0, 0, 255))
        elif col in (1, 4):
            for dx in range(5):
                strip.putpixel((x0 + 8 + dx, 3), (255, 0, 0, 255))
        elif col == 2:
            for dy in range(3):
                for dx in range(5):
                    strip.putpixel((x0 + 8 + dx, 2 + dy), (255, 0, 0, 255))
        else:  # col == 3
            for dy in range(5):
                for dx in range(5):
                    if (dx - 2) ** 2 + (dy - 2) ** 2 <= 4:
                        strip.putpixel((x0 + 8 + dx, 1 + dy), (255, 0, 0, 255))
    return strip


def test_split_strip_to_frames_returns_6():
    strip = _make_test_strip()
    frames = split_strip_to_frames(strip)
    assert len(frames) == 6
    for f in frames:
        assert f.size == (29, 7)


def test_crop_to_content_keeps_visible_sprite():
    # 29x7 frame with a single red pixel at (10, 3)
    frame = Image.new("RGBA", (29, 7), (255, 255, 255, 255))
    frame.putpixel((10, 3), (255, 0, 0, 255))
    cropped = crop_to_content(frame)
    # bounding box of the red pixel with 1px padding is 11x3 (9..10, 2..3)
    # padded by 1 in each direction -> (8, 2, 11, 4) -> 3 wide, 2 tall
    assert cropped.getpixel((1, 0))[0] == 255  # still red somewhere
    assert cropped.getpixel((0, 0))[3] == 0    # transparent corner


def test_assemble_sheet_produces_174x7():
    frames = [Image.new("RGBA", (29, 7), (0, 0, 0, 0)) for _ in range(6)]
    sheet = assemble_sheet(frames)
    assert sheet.size == (174, 7)


def test_save_reference_writes_first_frame(tmp_path: Path):
    frames = [Image.new("RGBA", (29, 7), (0, 0, 0, 0)) for _ in range(6)]
    frames[0].putpixel((5, 3), (255, 0, 0, 255))
    out = tmp_path / "ref.png"
    save_reference(frames, out)
    assert out.exists()
    ref = Image.open(out)
    assert ref.size == (29, 7)
    assert ref.getpixel((5, 3)) == (255, 0, 0, 255)
```

- [ ] **Step 2: Run the test to verify it fails (expected: ImportError)**

```powershell
cd D:\AI\stellar-horizon; .\.venv\Scripts\python.exe -m pytest sprite_tests/test_regen_laser_strips.py -v
```
Expected: `ModuleNotFoundError: No module named 'sprite_tests.regen_laser_strips'`.

- [ ] **Step 3: Write `regen_laser_strips.py`**

Create `sprite_tests/regen_laser_strips.py`:

```python
"""Postprocess AI-generated laser strip into a sprite sheet + reference.

Spec: docs/superpowers/specs/2026-09-08-visual-polish-v3-design.md section 3.

The AI generation produces a 174x42 strip (6 frames of 29x7 side-by-side
on a white background). This module:

1. Splits the strip into 6 individual 29x7 frames.
2. For each frame: floodfill from (0,0) makes white transparent, then
   crop to the non-transparent bounding box (with 1px padding), and
   re-paste onto a transparent 29x7 canvas centered.
3. Concatenates the 6 frames horizontally -> 174x7 sheet.
4. Saves the first frame as a 29x7 reference.

Usage (from the cmdline):
    python -m sprite_tests.regen_laser_strips <input_strip.png> <output_dir>

Usage (from Python):
    from sprite_tests.regen_laser_strips import process_strip
    sheet, reference = process_strip("input.png", "output_dir")
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

from PIL import Image


FRAME_W = 29
FRAME_H = 7
N_FRAMES = 6
STRIP_W = FRAME_W * N_FRAMES  # 174
STRIP_H = FRAME_H * 6          # 42 (AI may produce 7 or 42; we crop to 42)


def split_strip_to_frames(strip: Image.Image) -> List[Image.Image]:
    """Split a 174xN strip into 6 frames of 29x7.

    Accepts strips where the height is >= 7. The first 7 rows are used.
    """
    if strip.size[0] != STRIP_W:
        raise ValueError(
            f"Expected strip width {STRIP_W}, got {strip.size[0]}"
        )
    if strip.size[1] < FRAME_H:
        raise ValueError(
            f"Expected strip height >= {FRAME_H}, got {strip.size[1]}"
        )
    frames = []
    for i in range(N_FRAMES):
        col = strip.crop((i * FRAME_W, 0, (i + 1) * FRAME_W, FRAME_H))
        frames.append(col)
    return frames


def crop_to_content(frame: Image.Image) -> Image.Image:
    """Remove white background and crop to non-transparent content + 1px pad.

    Returns a tight RGBA image. The output may be smaller than 29x7.
    """
    if frame.mode != "RGBA":
        frame = frame.convert("RGBA")
    # Floodfill from (0, 0) with transparent — white becomes alpha 0.
    # (PIL's ImageDraw.floodfill operates in-place.)
    from PIL import ImageDraw
    work = frame.copy()
    ImageDraw.floodfill(work, (0, 0), value=(0, 0, 0, 0))
    # Find bounding box of non-zero alpha.
    bbox = work.getbbox()  # returns (left, top, right, bottom) or None
    if bbox is None:
        # Frame is fully white — return an empty transparent image.
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    left, top, right, bottom = bbox
    # 1px padding, clamped to non-negative.
    left = max(0, left - 1)
    top = max(0, top - 1)
    right = min(frame.size[0], right + 1)
    bottom = min(frame.size[1], bottom + 1)
    return work.crop((left, top, right, bottom))


def _center_paste(canvas: Image.Image, content: Image.Image) -> None:
    """Paste `content` centered on `canvas` (in place). canvas is 29x7."""
    cw, ch = canvas.size
    iw, ih = content.size
    x = (cw - iw) // 2
    y = (ch - ih) // 2
    canvas.alpha_composite(content, (x, y))


def assemble_sheet(frames: List[Image.Image]) -> Image.Image:
    """Concatenate 6 processed 29x7 frames into a 174x7 sheet."""
    if len(frames) != N_FRAMES:
        raise ValueError(f"Expected {N_FRAMES} frames, got {len(frames)}")
    sheet = Image.new("RGBA", (STRIP_W, FRAME_H), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        # f is already 29x7 with transparent background.
        sheet.paste(f, (i * FRAME_W, 0))
    return sheet


def save_reference(frames: List[Image.Image], out_path: Path) -> None:
    """Save the first frame as a 29x7 reference PNG."""
    if len(frames) == 0:
        raise ValueError("frames list is empty")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(str(out_path), format="PNG")


def process_strip(in_path: Path, out_dir: Path, name: str) -> Tuple[Path, Path]:
    """Full pipeline: read strip -> sheet + reference.

    Returns (sheet_path, reference_path).
    `name` is the laser archetype name (e.g. "laser_01").
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    strip = Image.open(str(in_path))
    if strip.mode != "RGBA":
        strip = strip.convert("RGBA")
    raw_frames = split_strip_to_frames(strip)
    # Each frame: crop to content, re-center on transparent 29x7.
    processed: List[Image.Image] = []
    for f in raw_frames:
        cropped = crop_to_content(f)
        canvas = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
        _center_paste(canvas, cropped)
        processed.append(canvas)
    sheet = assemble_sheet(processed)
    sheet_path = out_dir / f"{name}_sheet.png"
    sheet.save(str(sheet_path), format="PNG")
    ref_path = out_dir / f"{name}.png"
    processed[0].save(str(ref_path), format="PNG")
    return sheet_path, ref_path


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(f"Usage: {argv[0]} <input_strip.png> <output_dir>", file=sys.stderr)
        return 1
    in_path = Path(argv[1])
    out_dir = Path(argv[2])
    # Derive name from input filename: "laser_01_strip.png" -> "laser_01".
    stem = in_path.stem
    if stem.endswith("_strip"):
        name = stem[:-6]
    else:
        name = stem
    sheet, ref = process_strip(in_path, out_dir, name)
    print(f"Sheet: {sheet}")
    print(f"Reference: {ref}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 4: Run the test to verify it passes**

```powershell
cd D:\AI\stellar-horizon; .\.venv\Scripts\python.exe -m pytest sprite_tests/test_regen_laser_strips.py -v
```
Expected: 4 tests passed.

- [ ] **Step 5: Run the full test suite to verify nothing else broke**

```powershell
cd D:\AI\stellar-horizon; .\.venv\Scripts\python.exe -m pytest stellar_horizon/tests/ sprite_tests/ -q
```
Expected: 424 passed (420 + 4 new).

- [ ] **Step 6: Commit**

```powershell
cd D:\AI\stellar-horizon
git add sprite_tests/regen_laser_strips.py sprite_tests/test_regen_laser_strips.py
git -c user.email="Lerius@void-hunter.local" -c user.name="Lerius" commit -m "feat(sprite_tests): postprocess for AI-generated laser strips

regen_laser_strips.py:
  - split_strip_to_frames: 174xN -> 6 frames of 29x7
  - crop_to_content: floodfill white -> transparent, crop to bbox+1px
  - assemble_sheet: 6 frames -> 174x7 sheet
  - save_reference: write first frame as 29x7 reference
  - process_strip: full pipeline (used by Task 5+)
  - main: CLI for ad-hoc regeneration

Tests: 4 unit tests using a mock strip with 6 different sprite shapes.
Total: 420 -> 424."
```

---

## Task 5: Write 7 CONTEXT.md files (root + 6 sub-folders)

**Files:**
- Create: `stellar_horizon/assets/CONTEXT.md`
- Create: `stellar_horizon/assets/sprites/CONTEXT.md`
- Create: `stellar_horizon/assets/sprites/bullets/CONTEXT.md`
- Create: `stellar_horizon/assets/sprites/player/CONTEXT.md`
- Create: `stellar_horizon/assets/sprites/enemies/CONTEXT.md`
- Create: `stellar_horizon/assets/sprites/boss/CONTEXT.md`
- Create: `stellar_horizon/assets/sprites/_deprecated/CONTEXT.md`

One commit with all 7. The format is inspired by the project root `AGENTS.md`.

- [ ] **Step 1: Write the root `assets/CONTEXT.md`**

```markdown
# Stellar Horizon — Assets "Mapa de Piso"

> **For agentic workers:** This is the entry point for the `stellar_horizon/assets/`
> area. Read this first when working on art, sprites, or any binary asset.

## TL;DR

The `assets/` folder holds the binary game data: sprite sheets, backgrounds,
MIDI music. All sprite sheets are loaded by `GameplayScene._load_sprites()` in
`stellar_horizon/scenes/gameplay.py`, which uses a prefix-based resolver
`self._sprite_path(name)` to map a sprite name to its file path.

## Layout

```
assets/
├── CONTEXT.md                 ← you are here
├── backgrounds/               ← bg_*.png, parallax layers
├── midi/                      ← *.mid music files
└── sprites/                   ← all animated sheets
    ├── CONTEXT.md             ← naming conventions, dims, frame counts
    ├── bullets/               ← 5 laser archetypes + 2 legacy bullets
    ├── player/                ← 5 player variants + 1 thrust
    ├── enemies/               ← 6 kinds (scout, cruiser, heavy, bomber, ufo, kamikaze)
    ├── boss/                  ← 6 states (idle, telegraph, charge, dying, alt_a, alt_b)
    └── _deprecated/           ← files no longer loaded; do not delete
```

## Loader entry point

- `stellar_horizon/scenes/gameplay.py:170 _load_sprites()` — loads the whole
  animated cache.
- `stellar_horizon/scenes/gameplay.py:_sprite_path()` — prefix-based resolver.
  See `sprites/CONTEXT.md` for the naming convention.
- `StellarHorizon.spec:8` — PyInstaller globs the entire `assets/` tree. No
  change needed when adding new sub-folders.

## Adding new assets

1. Place the PNG in the appropriate sub-folder (`bullets/`, `player/`,
   `enemies/{kind}/`, `boss/`). If you don't know where, see the
   `sprites/CONTEXT.md` naming convention.
2. If the new asset represents a new kind or category, update the loader
   code in `gameplay.py` (add to `animated_names` or similar) AND the
   relevant sub-folder's `CONTEXT.md`.
3. If the new asset replaces an old one, move the old one to
   `_deprecated/` with a brief note in `_deprecated/CONTEXT.md`.
4. Run the test suite: `pytest stellar_horizon/tests/ -q`.

## Cross-references

- Game scenes: `stellar_horizon/scenes/` (uses `_animated[name]` to draw).
- Sprite animator: `stellar_horizon/ui/animated_sprite.py` (AnimatedSprite
  class, frame timing).
- VFX params: `stellar_horizon/fx/bullet_vfx.py` (per-weapon visual identity).
- Spec: `docs/superpowers/specs/2026-09-08-visual-polish-v3-design.md`.
- Plan: `docs/superpowers/plans/2026-09-08-visual-polish-v3.md`.

## Deprecated

See `sprites/_deprecated/CONTEXT.md` for the list of files that are no
longer loaded but kept on disk for reference.
```

- [ ] **Step 2: Write `sprites/CONTEXT.md`**

```markdown
# sprites/ — Naming, Dimensions, Frame Counts

> **For agentic workers:** The naming convention here is enforced by
> `GameplayScene._sprite_path()`. If you add a name that doesn't match
> the prefix rules, the resolver raises `ValueError`.

## Naming convention

The name encodes the location. The resolver infers the folder from
the name's prefix:

| Prefix | Folder | Example name |
|---|---|---|
| `boss_*` | `boss/` | `boss_idle_v1`, `boss_charge_v1` |
| `player_*` | `player/` | `player_v1`, `player_thrust_v1` |
| `enemy_*` | `enemies/{kind}/` (kind is the 2nd token) | `enemy_scout_v1`, `enemy_heavy_attack_v1` |
| `laser_*` | `bullets/` | `laser_01` .. `laser_05` |
| `player_bullet`, `enemy_bullet` | `bullets/` | (legacy 8x8) |

The kind for `enemy_*` is the second underscore-separated token. For
example, `enemy_kamikaze_v1_v2` is in `enemies/kamikaze/`.

## Dimensions and frame counts

| Entity | Dim (px) | Frames per sheet | FPS |
|---|---:|---:|---:|
| Player + variants | 29×29 | 10 | 12 |
| Player thrust | 29×29 | 10 | 12 |
| Enemy variants (idle/attack/death) | 29×29 | 10 | 12 |
| Boss states | 72×72 | 10 | 8 |
| Lasers (5 archetypes) | 29×7 | 6 | 12 |
| Legacy bullets (player_bullet, enemy_bullet) | 8×8 | 6 | 12 |

The 10-frame sheets for player/enemy/boss are procedurally expanded by
`sprite_tests/generate_sheets.py` from a single AI-generated image. The
6-frame laser sheets are ALSO generated by `sprite_tests/regen_laser_strips.py`
from a 174×42 AI strip output (see Task 4 in the plan).

## File extension

All sprite sheets are `.png` (RGBA, transparent background except for
the laser strip input which is on white for chroma-key postprocess).

The loader appends `_sheet.png` to the name. The base single-frame
(e.g. `player_v1.png` next to `player_v1_sheet.png`) is kept for
reference and possible re-prompting; it is NOT loaded by the runtime.
```

- [ ] **Step 3: Write `bullets/CONTEXT.md`**

```markdown
# bullets/ — Laser sheets + legacy 8x8 bullets

## Contents

| File | Dim | Frames | Notes |
|---|---:|---:|---|
| `laser_01_sheet.png` | 29×7 | 6 | yellow plasma (WEAPON_ARCHETYPE 0) |
| `laser_02_sheet.png` | 29×7 | 6 | red pulse (WEAPON_ARCHETYPE 1) |
| `laser_03_sheet.png` | 29×7 | 6 | blue ion (WEAPON_ARCHETYPE 2) |
| `laser_04_sheet.png` | 29×7 | 6 | green acid (WEAPON_ARCHETYPE 3) |
| `laser_05_sheet.png` | 29×7 | 6 | purple void (WEAPON_ARCHETYPE 4) |
| `laser_0[1-5].png` (5 files) | 29×7 | 1 | base single-frame (reference only, not loaded) |
| `player_bullet.png` + `_sheet.png` | 8×8 | 6 | legacy 8x8 player bullet |
| `enemy_bullet.png` + `_sheet.png` | 8×8 | 6 | legacy 8x8 enemy bullet |

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
```

- [ ] **Step 4: Write `player/CONTEXT.md`**

```markdown
# player/ — 5 player variants + 1 thrust

## Contents

| File | Notes |
|---|---|
| `player_v1.png` + `_sheet.png` | Variant 1 (the default; only one used in gameplay today) |
| `player_v2.png` + `_sheet.png` | Variant 2 (skin pool, unused) |
| `player_v3.png` + `_sheet.png` | Variant 3 (skin pool, unused) |
| `player_v4.png` + `_sheet.png` | Variant 4 (skin pool, unused) |
| `player_v5.png` + `_sheet.png` | Variant 5 (skin pool, unused) |
| `player_thrust_v1.png` + `_sheet.png` | Thrust animation (shown when player is dying, for "loss of control" read) |

All variants are 29×29, 10 frames at 12 fps. Sheets are procedurally
generated by `sprite_tests/generate_sheets.py` from a single AI image.

## Cross-references

- `stellar_horizon/entities/player.py` — Player class. Uses
  `self._animated.get("player_v1")` for the default sprite.
- `stellar_horizon/scenes/gameplay.py:_draw_player_sprite` — render.

## Future work

The 5 variants are a "skin pool" — only v1 is used today. Per the v1.3.0
spec's "Out of scope" section, a future task could randomize the variant
per life/respawn for visual variety.
```

- [ ] **Step 5: Write `enemies/CONTEXT.md`**

```markdown
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
```

- [ ] **Step 6: Write `boss/CONTEXT.md`**

```markdown
# boss/ — 6 boss states

## Contents

| File | Notes |
|---|---|
| `boss_idle_v1.png` + `_sheet.png` | Default idle (used most of the time) |
| `boss_telegraph_v1.png` + `_sheet.png` | Telegraph (warning before an attack) |
| `boss_charge_v1.png` + `_sheet.png` | Charge (winding up for a big attack) |
| `boss_dying_v1.png` + `_sheet.png` | Death sequence |
| `boss_alternate_a_v1.png` + `_sheet.png` | Alternate pattern A |
| `boss_alternate_b_v1.png` + `_sheet.png` | Alternate pattern B |

All boss states are 72×72, 10 frames at 8 fps.

## Cross-references

- `stellar_horizon/entities/boss.py` — Boss class.
- `stellar_horizon/scenes/gameplay.py:_draw_boss_sprite` — picks the
  right state sheet based on `boss.phase + boss.action`. Viewport clip
  is applied here too (the boss can be 80×80 native but we shrunk it 10%
  for playfield space; the clip ensures partial off-screen rendering).

## State machine

```
IDLE -> TELEGRAPH -> CHARGE -> IDLE  (loop)
       TELEGRAPH -> IDLE              (cancel)
IDLE -> DYING                         (terminal)
```

`alternate_a` and `alternate_b` are special attack patterns triggered
by the wave manager; they replace TELEGRAPH+CHARGE for those attacks.
```

- [ ] **Step 7: Write `_deprecated/CONTEXT.md`**

```markdown
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
```

- [ ] **Step 8: Verify all 7 CONTEXT.md files exist**

```powershell
cd D:\AI\stellar-horizon; Get-ChildItem -Path stellar_horizon/assets -Recurse -Filter CONTEXT.md | Select-Object FullName
```
Expected output (7 files):
```
stellar_horizon/assets/CONTEXT.md
stellar_horizon/assets/sprites/CONTEXT.md
stellar_horizon/assets/sprites/bullets/CONTEXT.md
stellar_horizon/assets/sprites/player/CONTEXT.md
stellar_horizon/assets/sprites/enemies/CONTEXT.md
stellar_horizon/assets/sprites/boss/CONTEXT.md
stellar_horizon/assets/sprites/_deprecated/CONTEXT.md
```

- [ ] **Step 9: Run the test suite (sanity check — should still pass)**

```powershell
cd D:\AI\stellar-horizon; .\.venv\Scripts\python.exe -m pytest stellar_horizon/tests/ sprite_tests/ -q
```
Expected: 424 passed.

- [ ] **Step 10: Commit**

```powershell
cd D:\AI\stellar-horizon
git add stellar_horizon/assets/CONTEXT.md stellar_horizon/assets/sprites/CONTEXT.md stellar_horizon/assets/sprites/bullets/CONTEXT.md stellar_horizon/assets/sprites/player/CONTEXT.md stellar_horizon/assets/sprites/enemies/CONTEXT.md stellar_horizon/assets/sprites/boss/CONTEXT.md stellar_horizon/assets/sprites/_deprecated/CONTEXT.md
git -c user.email="Lerius@void-hunter.local" -c user.name="Lerius" commit -m "docs(assets): add 7 CONTEXT.md files (root 'mapa de piso' + 6 sub)

assets/CONTEXT.md — entry point. Layout, loader, cross-refs.
sprites/CONTEXT.md — naming convention, dims, frame counts.
sprites/bullets/CONTEXT.md — 5 archetypes + legacy bullets, color codes.
sprites/player/CONTEXT.md — variants + thrust.
sprites/enemies/CONTEXT.md — 6 kinds, file count table.
sprites/boss/CONTEXT.md — 6 states + state machine.
sprites/_deprecated/CONTEXT.md — 95 files, why each is here, how to reintroduce.

Format inspired by the project root AGENTS.md. No code changes."
```

---

## Task 6: Generate yellow plasma sample (ITERATION GATE)

**Files:**
- Create: `sprite_tests/captures/laser_01_strip_raw.png` (AI output)
- Create: `sprite_tests/captures/laser_01_sheet_preview.png` (post-processed)
- Modify: `stellar_horizon/assets/sprites/bullets/laser_01_sheet.png` (the new sheet)
- Create: `stellar_horizon/assets/sprites/bullets/laser_01.png` (regenerated reference)

**Iteration gate:** SHOW the user the post-processed `laser_01_sheet.png` + a contact-sheet PNG of all 6 frames enlarged. WAIT for "OK" or feedback before Task 7. If feedback, adjust the prompt template and re-generate.

- [ ] **Step 1: Verify Matrix is available**

```powershell
cd D:\AI\stellar-horizon; mcode-tools connector list 2>&1 | Select-String -Pattern 'matrix|Matrix' | Select-Object -First 5
```
Expected: shows `connector__matrix__generate_image` (or similar name).

If Matrix is NOT available, fall back to ComfyUI (which requires the workflow to be set up). For this task, document the failure and ask the user.

- [ ] **Step 2: Build the prompt**

Create `sprite_tests/captures/laser_01_prompt.txt`:

```
6-frame horizontal sprite sheet, 174x42 pixels (6 frames of 29x7), side-by-side without gaps. 16-bit pixel art, sci-fi energy laser. Background: pure white (will be removed by postprocess). Sprite should occupy ~75% of each 29x7 frame.

Animation sequence (frame 1 -> 6):
- Frame 1: thin yellow line, low energy, faint outer glow
- Frame 2: thicker, growing halo, central core brightening
- Frame 3: peak — brightest core, full radial halo, edge bloom
- Frame 4: still bright, slight contraction, halo shifting outward
- Frame 5: contracting, halo dimming, trailing energy
- Frame 6: thin line, fading, faint trailing edge

Color: yellow plasma. Core #FFEE44, halo #FFAA00.
Style: 16-bit shmup laser, neon, saturated, clear silhouette against white.
```

- [ ] **Step 3: Call Matrix to generate the strip**

```powershell
cd D:\AI\stellar-horizon; mcode-tools connector call connector__matrix__generate_image --prompt "$(Get-Content -Raw sprite_tests/captures/laser_01_prompt.txt)" --out sprite_tests/captures/laser_01_strip_raw.png --width 174 --height 42 --ratio "1:1" 2>&1 | Tee-Object -FilePath sprite_tests/captures/laser_01_gen.log
```

If `--width` / `--height` aren't supported, use whatever args the Matrix connector accepts. Check the connector's `--help` first.

- [ ] **Step 4: Verify the raw strip output exists and is 174×something**

```powershell
cd D:\AI\stellar-horizon; Add-Type -AssemblyName System.Drawing; $bmp = [System.Drawing.Image]::FromFile((Resolve-Path 'sprite_tests/captures/laser_01_strip_raw.png')); "Size: $($bmp.Width) x $($bmp.Height)"; $bmp.Dispose()
```
Expected: width = 174, height = any (typically 42 or 84 or 256 depending on the model).

- [ ] **Step 5: Run the postprocess**

```powershell
cd D:\AI\stellar-horizon; .\.venv\Scripts\python.exe -m sprite_tests.regen_laser_strips sprite_tests/captures/laser_01_strip_raw.png sprite_tests/captures/ 2>&1 | Tee-Object -FilePath sprite_tests/captures/laser_01_postprocess.log
```

Expected output: `Sheet: sprite_tests/captures/laser_01_sheet.png`, `Reference: sprite_tests/captures/laser_01.png`.

- [ ] **Step 6: Verify the post-processed sheet is 174×7 and has visible content**

```powershell
cd D:\AI\stellar-horizon; Add-Type -AssemblyName System.Drawing; $bmp = [System.Drawing.Image]::FromFile((Resolve-Path 'sprite_tests/captures/laser_01_sheet.png')); "Size: $($bmp.Width) x $($bmp.Height)"; $bmp.Dispose(); .\.venv\Scripts\python.exe -c "from PIL import Image; im=Image.open('sprite_tests/captures/laser_01_sheet.png'); nonzero=sum(1 for p in im.getdata() if p[3]>0); print(f'Non-transparent pixels: {nonzero} / {im.size[0]*im.size[1]}')"
```
Expected: `Size: 174 x 7`. `Non-transparent pixels: <N>` where N is significant (not 0).

- [ ] **Step 7: Generate a 6x scaled-up preview for visual review**

```powershell
cd D:\AI\stellar-horizon; .\.venv\Scripts\python.exe -c "
from PIL import Image
sheet = Image.open('sprite_tests/captures/laser_01_sheet.png')
# Scale up 6x with nearest neighbor to make the frames visible
scaled = sheet.resize((sheet.size[0] * 6, sheet.size[1] * 6), Image.NEAREST)
# Add a white background to make transparent pixels visible
from PIL import Image as I
bg = I.new('RGB', scaled.size, (40, 40, 40))
bg.paste(scaled, (0, 0), scaled)
bg.save('sprite_tests/captures/laser_01_preview.png')
print('Preview saved.')
"
```

- [ ] **Step 8: Visually inspect the preview**

Open `sprite_tests/captures/laser_01_preview.png` (use Windows Explorer or an image viewer). Verify that the 6 frames are visually distinct — they should NOT look like the same frame 4 times.

The preview is 174×6=1044 wide by 7×6=42 tall. Each frame is 29×6=174 wide by 7×6=42 tall.

- [ ] **Step 9: Show the user the preview and the contact sheet**

Send the user the preview PNG as a media attachment so they can see it inline. Use the `<media>` tag in the chat:

```
<media src="D:/AI/stellar-horizon/sprite_tests/captures/laser_01_preview.png" caption="Yellow plasma (laser_01) — 6 frames after postprocess, 6x scale" />
```

Also use the `bullet_sandbox.py` tool from the v1.3.0 work to render a contact sheet (4×6 grid of frames × 5 archetypes). For this task, just laser_01 alone — the full 5-archetype contact sheet is built in Task 7.

- [ ] **Step 10: WAIT for user "OK" or feedback**

The user will say one of:
- "OK" / "listo" / "sigue" — proceed to Task 7.
- "más X" / "menos Y" / feedback — go back to Step 2, adjust the prompt template, re-generate.

If the prompt needs major rework, document the changes in a comment at the top of `laser_01_prompt.txt` so subsequent archetypes (Task 7) use the refined prompt.

- [ ] **Step 11: Move the approved sheet into the production assets folder**

```powershell
cd D:\AI\stellar-horizon; Copy-Item -Path sprite_tests/captures/laser_01_sheet.png -Destination stellar_horizon/assets/sprites/bullets/laser_01_sheet.png -Force; Copy-Item -Path sprite_tests/captures/laser_01.png -Destination stellar_horizon/assets/sprites/bullets/laser_01.png -Force
```

(The COPY is intentional — these files are now production assets, but we keep the originals in `captures/` for reference. If the user later wants to roll back, the capture is preserved.)

- [ ] **Step 12: Run the test suite to verify the new sheet loads**

```powershell
cd D:\AI\stellar-horizon; .\.venv\Scripts\python.exe -m pytest stellar_horizon/tests/test_bullet_render.py -v
```
Expected: pass.

- [ ] **Step 13: Commit (gated on user OK)**

```powershell
cd D:\AI\stellar-horizon
git add sprite_tests/captures/laser_01_strip_raw.png sprite_tests/captures/laser_01_sheet.png sprite_tests/captures/laser_01.png sprite_tests/captures/laser_01_prompt.txt stellar_horizon/assets/sprites/bullets/laser_01_sheet.png stellar_horizon/assets/sprites/bullets/laser_01.png
git -c user.email="Lerius@void-hunter.local" -c user.name="Lerius" commit -m "feat(laser_01): regenerate yellow plasma strip with AI

Matrix strip prompt -> sprite_tests/regen_laser_strips.py postprocess ->
stellar_horizon/assets/sprites/bullets/laser_01_sheet.png (6 frames
of 29x7, visually distinct stages: thin -> thicker -> peak -> still ->
contracting -> thin).

The previous procedural sheet (alpha-pulse only) read as the same
frame 4 times. The new sheet has real shape/glow variation.

User iteration gate: review at sprite_tests/captures/laser_01_preview.png
before generating the other 4 archetypes."
```

---

## Task 7: Generate remaining 4 archetypes (red pulse, blue ion, green acid, purple void)

**Files:**
- Create: `sprite_tests/captures/laser_0[2-5]_strip_raw.png` (4 AI outputs)
- Create: `sprite_tests/captures/laser_0[2-5]_sheet.png` (4 post-processed)
- Create: `sprite_tests/captures/laser_0[2-5].png` (4 references)
- Modify: `stellar_horizon/assets/sprites/bullets/laser_0[2-5]_sheet.png` (4 production sheets)
- Create: `stellar_horizon/assets/sprites/bullets/laser_0[2-5].png` (4 production refs)
- Create: `sprite_tests/captures/all_lasers_contact_sheet.png` (final visual)

- [ ] **Step 1: For each of laser_02..laser_05, build a prompt file**

For each archetype, create `sprite_tests/captures/laser_0N_prompt.txt` with the same template as Task 6 Step 2, but with the archetype-specific color (from spec section 3).

| Archetype | Color | Core | Halo |
|---|---|---|---|
| `laser_02` | red pulse | `#FF3344` | `#FF8888` |
| `laser_03` | blue ion | `#4488FF` | `#88CCFF` |
| `laser_04` | green acid | `#44FF66` | `#AAFFAA` |
| `laser_05` | purple void | `#AA44FF` | `#DDAADD` |

- [ ] **Step 2: For each laser, generate + postprocess + preview**

For each archetype (laser_02 through laser_05), do:
1. Run Matrix with the prompt.
2. Verify output is 174 wide.
3. Run `regen_laser_strips.py` postprocess.
4. Generate a 6x preview PNG.
5. Visually inspect the preview (just the worker agent does this — full user review at the end of the task).

PowerShell snippet (loop):

```powershell
cd D:\AI\stellar-horizon; foreach ($n in 2,3,4,5) {
    $prompt = Get-Content -Raw "sprite_tests/captures/laser_0${n}_prompt.txt"
    mcode-tools connector call connector__matrix__generate_image --prompt $prompt --out "sprite_tests/captures/laser_0${n}_strip_raw.png" --width 174 --height 42 2>&1 | Out-Null
    .\.venv\Scripts\python.exe -m sprite_tests.regen_laser_strips "sprite_tests/captures/laser_0${n}_strip_raw.png" "sprite_tests/captures/" 2>&1 | Out-Null
    .\.venv\Scripts\python.exe -c "from PIL import Image; s=Image.open('sprite_tests/captures/laser_0${n}_sheet.png'); bg=Image.new('RGB',(s.size[0]*6,s.size[1]*6),(40,40,40)); bg.paste(s.resize((s.size[0]*6,s.size[1]*6),Image.NEAREST),(0,0)); bg.save('sprite_tests/captures/laser_0${n}_preview.png')"
}
```

- [ ] **Step 3: Generate the all-lasers contact sheet**

```powershell
cd D:\AI\stellar-horizon; .\.venv\Scripts\python.exe -c "
from PIL import Image
# Stack 5 sheets vertically with labels (labels via PIL.ImageDraw)
sheets = [Image.open(f'sprite_tests/captures/laser_0{i}_sheet.png') for i in range(1,6)]
SCALE = 6
W = 174 * SCALE
H = sum(s.size[1] for s in sheets) * SCALE + 5 * 10  # 10px gap between rows
out = Image.new('RGB', (W, H), (40, 40, 40))
y = 0
for s in sheets:
    scaled = s.resize((W, s.size[1] * SCALE), Image.NEAREST)
    out.paste(scaled, (0, y))
    y += scaled.size[1] + 10
out.save('sprite_tests/captures/all_lasers_contact_sheet.png')
print('Contact sheet saved.')
"
```

- [ ] **Step 4: Visually inspect each archetype's preview**

Open each of `sprite_tests/captures/laser_0[2-5]_preview.png` and verify the 6 frames are visually distinct. If any archetype still looks like the same frame 4 times, flag it for the user.

- [ ] **Step 5: Show the user the contact sheet**

Send the user the contact sheet as a media attachment. WAIT for "OK" or per-archetype feedback.

```
<media src="D:/AI/stellar-horizon/sprite_tests/captures/all_lasers_contact_sheet.png" caption="All 5 laser archetypes after regen — 6 frames each, 6x scale" />
```

- [ ] **Step 6: Copy the 4 approved sheets into production**

```powershell
cd D:\AI\stellar-horizon; foreach ($n in 2,3,4,5) {
    Copy-Item -Path "sprite_tests/captures/laser_0${n}_sheet.png" -Destination "stellar_horizon/assets/sprites/bullets/laser_0${n}_sheet.png" -Force
    Copy-Item -Path "sprite_tests/captures/laser_0${n}.png" -Destination "stellar_horizon/assets/sprites/bullets/laser_0${n}.png" -Force
}
```

- [ ] **Step 7: Run the full test suite**

```powershell
cd D:\AI\stellar-horizon; .\.venv\Scripts\python.exe -m pytest stellar_horizon/tests/ sprite_tests/ -q
```
Expected: 424 passed.

- [ ] **Step 8: Commit**

```powershell
cd D:\AI\stellar-horizon
git add sprite_tests/captures/ stellar_horizon/assets/sprites/bullets/laser_0[2-5]*.png
git -c user.email="Lerius@void-hunter.local" -c user.name="Lerius" commit -m "feat(lasers): regenerate red/blue/green/purple with AI

4 archetypes (laser_02..laser_05) regenerated via Matrix strip prompt
+ sprite_tests/regen_laser_strips.py postprocess. Each 6-frame sheet
now has real shape/glow variation instead of alpha-pulse-only.

User reviewed contact sheet at sprite_tests/captures/all_lasers_contact_sheet.png
before this commit.

All 5 archetypes: yellow plasma, red pulse, blue ion, green acid, purple void.
Tests: 424 pass."
```

---

## Task 8: Build .exe + final visual review + user "listo" (ITERATION GATE)

**Files:**
- Modify: `dist/StellarHorizon.exe` (rebuilt)

- [ ] **Step 1: Build the .exe**

```powershell
cd D:\AI\stellar-horizon; pyinstaller --noconfirm --clean StellarHorizon.spec 2>&1 | Tee-Object -FilePath build_v1.4.0_pre_release.log
```

Expected: `Building EXE from EXE-00.toc completed successfully.` and the new `.exe` size is similar to v1.3.0 (34-36 MB).

- [ ] **Step 2: Verify the .exe timestamp is after the last commit**

```powershell
cd D:\AI\stellar-horizon; Get-Item dist/StellarHorizon.exe | Select-Object Name, Length, LastWriteTime; git log --oneline -1 --format='%H %ci'
```
Expected: `.exe LastWriteTime` >= last commit time. If not, the build failed silently — re-run with verbose output.

- [ ] **Step 3: Launch the .exe in the background**

```powershell
cd D:\AI\stellar-horizon; Start-Process -FilePath '.\dist\StellarHorizon.exe' -PassThru | Select-Object Id
```

Note the PID. The game window will appear. The user will see the new laser sheets in gameplay.

- [ ] **Step 4: User runs the game, fires each of the 5 weapons, and verifies the visual**

The user looks for:
- The 5 laser archetypes show visibly animated 6-frame sheets (NOT the same frame 4 times).
- The new structure loads without errors (no missing sprite crashes).
- The game runs at 60 fps (the new sheets have the same file size budget, so perf should be unaffected).

- [ ] **Step 5: WAIT for user "listo" / "OK" / feedback**

The user will say:
- "listo" / "OK" / "sigue" — proceed to Task 9 (release).
- Feedback (e.g., "el rojo se ve raro") — re-generate just that archetype (similar to Task 7 but for one specific laser).

- [ ] **Step 6: Kill the .exe (only after user is done reviewing)**

```powershell
cd D:\AI\stellar-horizon; Stop-Process -Id <PID from Step 3> -Force
```

---

## Task 9: Release v1.4.0 (CONDITIONAL on user approval)

**Files:**
- Create: `RELEASE_NOTES_v1.4.0.md`
- Create: `tools/create_v1_4_0_release.py`
- Create: `releases/StellarHorizon-v1.4.0-win64.zip`
- Create: git tag `v1.4.0`
- Modify: GitHub release

**Conditional:** This task ONLY runs if the user explicitly approves the release. Memory rule: "User controls release cadence" — never auto-bundle.

- [ ] **Step 1: Ask the user "OK to release v1.4.0?"**

If the user says "sigue" / "saca la versión" / "release", proceed. If they say "no" / "todavía no" / "espera", skip this entire task and stop.

- [ ] **Step 2: Write `RELEASE_NOTES_v1.4.0.md`**

Mirror the structure of `RELEASE_NOTES_v1.3.0.md`. Key sections:
- **Visual bullet overhaul** — 5 laser sheets regenerated, 6 distinct frames each.
- **Asset SF+SM reorganization** — 194 files moved into `sprites/{bullets,player,enemies/{kind},boss,_deprecated}/` via git mv. No data loss.
- **`CONTEXT.md` "mapa de piso"** — 7 new context files (root + 6 sub-folders).
- **Loader refactor** — `_sprite_path()` prefix-based resolver. 4 hardcoded path blocks in `_load_sprites` replaced.
- **Tests** — 413 → 424 passing (+11 new: 7 resolver, 4 regen postprocess).
- **Build & runtime** — .exe rebuilt.
- **From v1.3.0** — list the 9 commits since `ebf390f`.

- [ ] **Step 3: Commit the release notes**

```powershell
cd D:\AI\stellar-horizon
git add RELEASE_NOTES_v1.4.0.md
git -c user.email="Lerius@void-hunter.local" -c user.name="Lerius" commit -m "docs: add v1.4.0 release notes"
```

- [ ] **Step 4: Create the release script `tools/create_v1_4_0_release.py`**

Mirror `tools/create_v1_3_0_release.py` with the new version. Changes:
- `tag_name = "v1.4.0"`
- `name = "Stellar Horizon v1.4.0 — Asset SF+SM + bullet regen"`
- `notes_path = "RELEASE_NOTES_v1.4.0.md"`
- `zip_path = "releases/StellarHorizon-v1.4.0-win64.zip"`

(Exact diff: just 4 string substitutions. Copy the v1.3.0 script and edit.)

- [ ] **Step 5: Build the .zip**

```powershell
cd D:\AI\stellar-horizon; Compress-Archive -Path dist/StellarHorizon.exe -DestinationPath releases/StellarHorizon-v1.4.0-win64.zip -CompressionLevel Optimal; Get-Item releases/StellarHorizon-v1.4.0-win64.zip | Select-Object Name, Length
```

Expected: ~34-36 MB.

- [ ] **Step 6: Push the release notes commit**

```powershell
cd D:\AI\stellar-horizon; git push origin main
```

- [ ] **Step 7: Create the git tag locally + push to origin**

```powershell
cd D:\AI\stellar-horizon
git tag -a v1.4.0 -m "Stellar Horizon v1.4.0 - Asset SF+SM + bullet regen"
git push origin v1.4.0
```

- [ ] **Step 8: Create the GitHub release + upload the .zip**

```powershell
cd D:\AI\stellar-horizon; .\.venv\Scripts\python.exe tools/create_v1_4_0_release.py
```

Expected output:
```
Release created: https://github.com/lerius700-cmyk/Stellar-Horizon/releases/tag/v1.4.0
Upload URL: https://uploads.github.com/...
Asset uploaded: https://github.com/lerius700-cmyk/Stellar-Horizon/releases/download/v1.4.0/StellarHorizon-v1.4.0-win64.zip
Total size: 34.XX MB
```

- [ ] **Step 9: Verify the release on GitHub**

Web-fetch:
```
https://api.github.com/repos/lerius700-cmyk/Stellar-Horizon/releases/tags/v1.4.0
```

Expected: release exists, asset `StellarHorizon-v1.4.0-win64.zip` is present with size matching Step 5.

- [ ] **Step 10: Done — report to user**

Tell the user:
- The release URL.
- The asset size.
- The git tag SHA.
- That the .exe in `dist/` is the one in the .zip.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-08-visual-polish-v3.md`.

Two execution options:
1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks.
2. **Inline Execution** — execute tasks in this session with checkpoints.

¿ cuál preferís?
