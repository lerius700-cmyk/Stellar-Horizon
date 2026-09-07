# Stellar Horizon v1.3.0 — Visual polish v2

**Released:** 2026-09-07
**Tag:** `v1.3.0`
**Base:** `9b772de` (v1.2.0)
**Head:** `e90550d`
**Build:** `StellarHorizon-v1.3.0-win64.zip` (TBD)

---

## Visual destruction polish

- **Enemy engine flame + comet-tail cut on death.** When a ship is killed, the engine flame and the light trail stop rendering immediately. The ship falls as an inert hull (just the sprite + the new P_SMOKE smoke trail from the destruction-fall v2). The visual reads as "motor cortado" — the ship is dead, the fire is out.
- **Player 2-layer trail.** A faint cyan aura (intensity 0.30) emits every frame the player is alive, regardless of movement. A bright light-cyan destello (intensity 1.0) emits at 30Hz when the player is thrusting. Result: the player always reads as "main character" with a constant presence, and movement feels impactful.

## Bullet visual overhaul

- **6-frame animated sprite sheets** for all 5 laser archetypes. Each sheet is 174×7 (6 frames of 29×7). Frames vary in alpha (0.85..1.0, peak in middle) so the bullet reads as "energy" in flight, not a static sprite.
- **Per-weapon particles + trail.** Each weapon emits per-frame particles (P_SPARK, P_DUST, P_GLOW, P_FIRE) with its own color and intensity:
  - yellow plasma: yellow sparks, 2.0/frame, trail 0.6
  - red pulse: red sparks, 2.5/frame, trail 0.7 (with red halo)
  - blue ion: blue sparks, 1.0/frame, no trail
  - green acid: green dust, 3.0/frame, trail 0.8 (erratic alpha)
  - purple void: purple glow, 0.5/frame, trail 0.3
  - orange fireball: orange fire, 2.0/frame, trail 0.5
  - pink heart: pink sparks, 1.5/frame, trail 0.4
  - cyan ice: cyan sparks, 1.0/frame, trail 0.5
  - rainbow: white sparks, 2.0/frame, trail 0.6
  - white piercing: no VFX (its identity is speed)
- **No-op convention: `particles_per_frame == 0`** (not `particle_kind == 0`, which collides with P_SPARK=0). The convention is documented in the WeaponVFX docstring.

## Tests

- **400 → 413 passing** (+13 new tests)
- New: 2 enemy death cleanup, 3 player 2-layer trail, 3 WeaponVFX dataclass, 3 bullet animation state, 2 bullet render + particle emission
- Per-weapon particle invariants: every weapon with `particles_per_frame > 0` has a non-None `particle_color`

## Build & runtime

- `dist/StellarHorizon.exe` rebuilt and verified
- 413 tests passing
- 5 laser sheets in `stellar_horizon/assets/sprites_v2/` (laser_01..laser_05)
- New `sprite_tests/bullet_sandbox.py` tool for visual review of the bullet VFX

## From the previous release (v1.2.0)

The head of `v1.2.0` was `9b772de`. v1.3.0 sits on top with 9 commits:
- `60b3b7a` feat(visual): cut enemy engine flame + trail during death-fall
- `d322b24` feat(player): 2-layer trail (base always, thrust at 30Hz)
- `3af5102` feat(assets): add 5 laser sprite sheets (6 frames each, 29x7)
- `46dff9f` feat(fx): per-weapon bullet particles + trail intensity
- `6503e90` feat(bullet): 6-frame animation state + weapon_archetype map
- `825cb10` feat(scene): render bullets with 6-frame sheet + per-weapon particles
- `0360009` feat(sprite_tests): bullet VFX sandbox for visual review
- `c8ab472` fix(fx): decouple intensity from particles_per_frame in emit_bullet_particle
- `e90550d` docs: add visual-polish-v2 spec and plan
