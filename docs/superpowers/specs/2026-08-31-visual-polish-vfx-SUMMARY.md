# Visual Polish VFX — Implementation Summary

**Date:** 2026-08-31
**Scope:** Make the choreographed enemy movement *visible* through procedural engine
flames, trail particles, FTL chain entry glow, animated bullet sheets, all-enemy
explosions, bullet-hit impact, and player hit/death sequences.

**User direction:** "no en contraste y brillo, sino en detalles" (details, not
contrast/brightness).

## Plan & spec

- **Spec:** `docs/superpowers/specs/2026-08-31-visual-polish-vfx-design.md`
  (commit `6d6434d`)
- **Plan:** `docs/superpowers/plans/2026-08-31-visual-polish-vfx.md`
  (commit `9fad870`)

## Commit list (9 commits)

| Task | Commit  | Description |
|------|---------|-------------|
| 1    | `8c47363` | feat(fx): add 6 new FxLayer VFX methods (TDD) |
| 2    | `aa596db` | feat(vfx): emit typed explosion on all 6 enemy death kinds |
| 3    | `054c3fa` | feat(fx): procedural engine flame renderer |
| 4    | `295177e` | feat(vfx): wire engine flames + trail particles to enemy |
| 5    | `fd7301f` | feat(vfx): wire engine flame + trail to player |
| 6    | `c8a1414` | feat(vfx): emit FTL chain spawn glow per link |
| 7    | `b288d57` | feat(vfx): animate bullet sprite sheets |
| 8    | `178beaa` | feat(vfx): player hit flash + 1.5s death sequence |

## Test results

**Before visual polish:** 43 tests
**After visual polish:** 72 tests (29 new VFX tests, 0 regressions)

```
72 passed in 3.60s
```

New test coverage spans:
- Trail particle emission + lifecycle + color + zero-intensity no-op
- Typed explosion for all 6 enemy kinds + heavy > scout scale
- Bullet impact particle emission + damage-scaled count
- FTL chain spawn glow + fast fade
- Player hit + death particle bursts
- Enemy explosion on death for all kinds
- EngineFlame construction + frame advance + render + size scaling
- Per-enemy-kind engine flame color
- Enemy trail emission while moving
- Player engine flame + trail emission when thrusting
- WaveManager chain glow per link
- Player + enemy bullet frame advance in update
- Player damage decrements HP
- Fatal damage starts death sequence (dying=True, dead=False, particles emit)
- Non-fatal hit emits particles via injected FxLayer
- Hit during death sequence is ignored (no spam)

## Visual verification

- **Procedural engine flames:** 4 pre-rendered frames at 12 FPS, per-kind color
  tables, `size_scale` scales by `min(2.0, speed/100)`. Cyan for player, hot
  palette for enemy kinds. `EngineFlame.base_color` is the extension point if
  AI-generated sprites become available later (currently unavailable).
- **Trail particles:** gated on movement (enemy `speed > 30`; player
  `thrusting=True`). Different intensities per enemy kind.
- **FTL chain spawn glow:** `WaveManager.fx` injected; per-link glow emission
  fades quickly (~1s).
- **Animated bullet sheets:** 4-frame loop at 8 FPS (player) / 6 FPS (enemy);
  falls back to single-sprite blit if width isn't divisible by 4.
- **Typed explosion on death:** `Enemy.take_damage` calls
  `fx.emit_explosion_typed(kind, x, y)`. Each kind has its own particle mix
  and scale. Removed duplicate emit from `GameplayScene`.
- **Player hit + death:** 0.3s red `hit_flash` on non-fatal; on fatal, `dying`
  sequence ticks for 1.5s before `dead=True` triggers `GameOverScene`. Death
  VFX (`emit_player_death`) is a large multi-particle burst. Trail emission
  is gated on `alive` so the death ship doesn't leave a comet trail.

## Files touched

- `stellar_horizon/fx/particles.py` — 6 new methods + `particles` property
- `stellar_horizon/fx/engine_flames.py` — new file (procedural flame renderer)
- `stellar_horizon/entities/enemy.py` — `flame` + `fx` slots, per-kind tables,
  trail emission in `update`, typed explosion in `take_damage`
- `stellar_horizon/entities/player.py` — engine flame, trail emission, hit
  flash, 1.5s death sequence
- `stellar_horizon/entities/bullet.py` — `frame`/`frame_time` slots, animated
  loop in `update`
- `stellar_horizon/waves/wave_manager.py` — `fx` attribute, per-link chain
  glow in `begin()`
- `stellar_horizon/scenes/gameplay.py` — inject `fx` into player/enemies,
  render engine flames, wait for `player.dead` before game-over transition
- `stellar_horizon/tests/test_visual_vfx.py` — 25 → 29 VFX tests

## Release artifacts

- **PyInstaller `.exe`:** `dist/StellarHorizon.exe` (13.5 MB) — built after
  Tasks 1-8 + the path-resolution fix from `85293e4`.
- **Zip:** `StellarHorizon-v1.1.0-win64.zip` (13.95 MB) — supersedes the
  release-page binary which crashed on SPACE because it ran with
  CWD = `dist/` and the wave JSON was resolved via the old CWD-relative
  default. The fresh build resolves `wave_json` and `assets_dir` via
  `__file__`, so it boots from any CWD.

## What ships in this v1.1.0 refresh

- Path resolution fix (commits `85293e4`) — `.exe` boots without
  `FileNotFoundError` when run from `dist/`.
- Choreographed enemy movement (12 commits, 38 tests) — from the previous
  v1.1.0 tag.
- Visual polish VFX (8 commits, 29 new tests) — this batch.

Total v1.1.0 effort: 21 commits, 67 tests, 0 regressions.
