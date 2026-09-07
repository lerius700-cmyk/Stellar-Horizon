# Stellar Horizon v1.2.0 — Realistic destruction + visual polish

**Released:** 2026-09-07
**Tag:** `v1.2.0`
**Commit:** `9b772de`
**Build:** `StellarHorizon-v1.2.0-win64.zip` (34.3 MB)

---

## Visual

- **10% smaller ships** for more playfield space. Player/enemy: 32→29 px, boss: 80→72 px, lasers: 32×8→29×7.
- **AI-generated 16-bit sprite sheets** (procedurally expanded to 10 frames each). 6 boss states + 20 enemy variants + 5 player variants.
- **Black silhouette outlines** (1.08× scale) behind every ship for clean edges against any background.
- **Boss clipping fix**: entry start moved from (540, 60) to (480, 60); viewport clip in `_draw_boss_sprite` prevents the silhouette from extending off-screen during entry.
- **Runtime sheet swap in `_draw_enemy_sprite`**: attack sheet on telegraph, death sheet on dying.

## Destruction animation v2

- **Realistic tumble**: zero momentum on death (`vx = vy = 0`), then constant gravity (500 px/s²).
- **Exponential linear + angular drag**: `vx *= exp(-1.8 * dt)`, `dying_omega *= exp(-0.6 * dt)`. Frame-rate independent.
- **Random initial omega** in `[-180, 180]` deg/s — each death tumbles in a unique direction.
- **Death-burst / ship-sprite swap**: 0.15s of explosion sprite, then transitions to the ship's actual IDLE sheet (rotated by `dying_rotation`) so the player sees the ship tumbling, not a static explosion being rotated.
- **P_SMOKE smoke trail** emitted every 2 frames during the fall.
- **Purged at offscreen** (`y > 295`) or after 1.0s, whichever comes first.

## Audio

- **New SFX: `laser_fire`** — sawtooth with strong downward pitch slide. Plays on every player shot.
- **New SFX: `enemy_explode`** — long noise burst with sustain and rumble. Replaces the generic `explode_small/medium` for normal enemy deaths.
- **Hit SFX volume halved** (`volume=0.5` on `sfx.play_event("hit")`) so it doesn't drown the explosion tail.

## Bug fixes

- **Enemy `_trail` deque slice** — was crashing the game on the first frame an enemy was on screen (`trail[:-1]` on a deque). Fixed with `list(trail)[:-1]`.
- **AnimatedSprite `convert_alpha()` in headless** — nested try/except falls back to the raw loaded surface when no display mode is available.

## Tests

- **311 → 400 passing** (+89 tests)
- New: smoke-emit trail, dying sequence (gravity / drag / omega decay / sheet swap), sfx catalog, deque slice regression, integration render test for ship-vs-explosion draw swap

## Build & runtime

- `dist/StellarHorizon.exe` rebuilt and verified
- 400 tests passing
- 9 contact-sheet PNGs in `sprite_tests/captures/` documenting the destruction-fall sweep (3×3 grid over gravity ∈ {400, 500, 600} and drag ∈ {0.5, 1.5, 3.0})

## From the previous release (v1.1.0, never published)

This release also includes the path-fix + initial visual polish that was committed to `main` after v1.1.0 was never published. The full chain from v1.0.0:

- v1.0.0 → 6c3316b: path fix + visual polish (10 commits)
- 6c3316b → 9b772de: destruction-fall v2 (10 commits)
