# Stellar Horizon v1.6.0 — "B + SPACE"

**Release date:** 2026-09-08
**Branch:** main
**Commits ahead of v1.4.0:** 7 (47a8c87 → dda2efe)
**Tests:** 487 passing (was 311 in v1.4.0; +176 across all 5 v1.5→v1.6 BLOQUE iterations)
**Build size:** 34.6 MB (similar to v1.4.0)

## Headline

**Two-button control scheme.** Tap fire and charged fire are now
**separate keys**: B for the rapid-fire "metralleta" basic shot, SPACE
for the charged shot. Plus a redesigned charge effect that grows at
the muzzle as a procedural 3-layer energy orb (replaces the v1.5
ship-body aura + long-sheet preview).

## Control scheme (v1.6)

| Key | Action | Per weapon |
|---|---|---|
| **B** (metralleta) | tier-1 basic bullet on cooldown | 0 orange, 1 white, 2 magenta, 3 cyan, 4 rainbow |
| **SPACE** (cargado) | tier-2 charged behavior | 0=continuous beam, 1=Megaman bolt @ 1.2s, 2=boomerang @ 1.5s, 3=piercing stream @ 1.5s, 4=no-op |
| WASD / arrows | movement | — |
| ESC / Q | quit | — |
| 1-5 | switch weapon | 5 weapons total |

## Weapons (5 total, down from 10 in v1.4.0)

The 5 "basic" weapons (yellow plasma, red pulse, blue ion, green acid,
purple void) were removed. Only the 4 charged archetypes + rainbow
streak remain:

| Slot | Name | B (tier-1) | SPACE (tier-2) | Cooldown |
|---|---|---|---|---|
| 0 | ORANGE FIRE | orange bullets | continuous beam (hold) | 0.14s |
| 1 | WHITE PIERCING | white bullets | Megaman bolt on release (damage 3) | 0.09s |
| 2 | MAGENTA HEART | pink bullets | boomerang on release (return at 0.6s, damage 2) | 0.11s |
| 3 | CYAN ICE | cyan bullets | piercing crystals every 1.5s (damage 2, piercing cap 8) | 0.13s |
| 4 | RAINBOW | rainbow bullets | no-op (tap-only) | 0.10s |

## Charge effect (v1.6 redesign)

Replaces the v1.5 `ShipChargeAura` (centered on the ship body) and
the long-sheet preview (horizontal bar ahead of the muzzle) with a
**procedural 3-layer energy orb anchored at the muzzle**:

- **Outer ring**: weapon color, always visible, radius 3 → 38 px
  over the charge ramp time
- **Body**: weapon color shifted 55% toward plasma cyan, appears at
  ~25% charge, fills the inner disc
- **White hot core**: small, bright, appears at ~50% charge, pulses
  at full charge for the "ready" feedback

Per-weapon ring colors:
- 0 orange fire: #FF8C2A
- 1 white piercing: #FFFFFF
- 2 magenta heart: #FF6AB4
- 3 cyan ice: #8CF6FF

Weapon 3 (continuous piercing) does NOT pulse — the stream itself
is the "ready" feedback.

Reference: Wan video (6-frame muzzle orb progression) + Gemini
2x4 grid (small/large variants), 2026-09-08.

## Per-weapon impact bursts

Each weapon has a distinct impact palette when a bullet kills an
enemy (per the v1.5 WEAPON_IMPACT_PARAMS table):
- 0 orange: P_FIRE, very wide (12 particles, 40° spread)
- 1 white: P_SPARK + bright flash (14 particles, 20° spread, +flash)
- 2 magenta: P_GLOW pink (12 particles, 30° spread)
- 3 cyan: P_SPARK ice shards (10 particles, 25° spread)
- 4 rainbow: P_SPARK mixed (10 particles, 20° spread)

## Charged bullets (v1.5)

The 3 special charged bullet behaviors, now triggered by SPACE
release at full charge (was: hold for charged shot in v1.5):
- **Megaman bolt** (weapon 1): 3x damage, single big shot
- **Boomerang heart** (weapon 2): flies out, returns at 0.6s, 2x damage
  on the way out AND 2x on the return
- **Piercing crystal** (weapon 3, continuous): every 1.5s while SPACE
  is held, 2x damage, cap 8 enemy hits per crystal

## Charged bullets — Beam (v1.5 + v1.6 polish)

The weapon 0 (orange fire) beam is now driven by SPACE (was: the
fire key in v1.5). Single non-pooled beam entity, 18-point polygon
body with sinusoidal ondulations, hot tip disc, 0.05s damage tick
interval with per-enemy cooldown. Vertical tolerance 32 px for
target detection.

## Implementation notes

### Code changes (v1.5 + v1.6)

- `entities/player.py`: split `firing` (B) from `charging` (SPACE).
  Renamed `on_fire_pressed/released` → `on_tap_pressed/released` (B).
  Added `on_charge_pressed/released` (SPACE). Captured
  `charge_complete` BEFORE the release-frame reset so the release
  dispatch still fires the charged shot. CHARGE_TIME_S table: 5
  entries, threshold-based.
- `entities/bullet.py`: WEAPON_ARCHETYPE 10→5 (orange→arch6,
  white→arch7, magenta→arch8, cyan→arch5, rainbow→arch4).
  `PlayerBullet.spawn()` accepts `damage / piercing / returning /
  return_at` kwargs for charged bullet variants.
- `entities/beam.py`: single non-pooled Beam entity (was: stream of
  fireballs in v1.4). start = muzzle, end = nearest enemy in line
  of fire (or max range).
- `fx/ship_charge_orb.py`: NEW. 3-layer procedural orb at muzzle.
  Per-weapon ring/body colors, growth ramp, pulse at full charge.
- `fx/beam_renderer.py`: NEW. 18-point polygon body with ondulations,
  hot tip disc, layered rendering (outer orange + inner white core).
- `fx/weapon_impact.py`: WEAPON_IMPACT_PARAMS 10→5, distinct per-weapon
  palettes. `FxLayer.emit_impact_weapon()` does forward-cone math.
- `fx/ship_charge_aura.py`: DEPRECATED (kept on disk per memory
  rule 2026-09-07; gameplay no longer imports it).
- `scenes/gameplay.py`: K_b = tap fire, K_SPACE = charge. Beam
  check: `weapon==0 AND charging`. Removed the v1.5 long-sheet
  loader + render. New orb render call. `_WEAPON_KEYS` 5 keys,
  `_WEAPON_NAMES` 5 names.

### Long sheets disposition

The 4 long sheets (`laser_06..09 _long_sheet.png`, ~90KB total) are
**kept on disk** per the user's decision but are **no longer loaded**.
The procedural orb replaces the visual they were originally for.
Regression test verifies the files exist but are not in
`scene._animated`.

### Test coverage (487 passing)

- 7 new tests in `test_charge_state.py` (charge mechanic dispatch)
- 8 new tests in `test_ship_charge_orb.py` (orb geometry, colors,
  pulse, growth)
- 12 tests in `test_beam.py` (beam entity lifecycle)
- 4 tests in `test_beam_renderer.py` (polygon body, ondulations)
- 11 tests in `test_impact_burst.py` (per-weapon impact params)
- 4 tests in `test_charged_bullets.py` (damage / piercing / returning
  flags)
- 7 tests in `test_ship_charge_aura.py` (DEPRECATED, kept for
  historical reference)
- 9 tests in `test_laser_long_sheet.py` (now: regression test that
  long sheets exist on disk but are NOT loaded)
- Plus 18+ tests across the v1.5 commits (test_bullet, test_bullet_render,
  test_animation_and_sparks, etc.)

## What's next

- More iterations on the orb (size, color ramp, pulse depth) if needed
- More weapon types (current: 5; design space: tier-1 + tier-2 = 10
  unique shot behaviors)
- Boss fight balance with the new weapons
- Level 2 / level 3 waves

## How to use the .exe

```
1. Extract StellarHorizon-v1.6.0-win64.zip anywhere
2. Double-click StellarHorizon.exe
3. Wait for the title screen
4. Press SPACE to start
5. WASD to move, B to fire basic, SPACE to fire charged
6. Press 1-5 to switch weapons (ORANGE FIRE / WHITE PIERCE / PINK
   HEART / CYAN ICE / RAINBOW)
7. ESC or Q to quit
```

## Known issues

- 1 `pytest` test imports a module that the .exe bundles but
  pytest discovers separately (asset path edge case in
  test_sprite_path_resolver). Not user-facing.
- The DEPRECATED `ship_charge_aura.py` is on disk but unused.
  Delete manually if you want to clean up.

## Credits

- Code: Lerius + Mavis (v1.5-v1.6 BLOQUE iterations)
- Long sheets + laser archetypes: AI-generated via Matrix connector
- Charge orb design: Wan video reference + Gemini 2x4 grid reference
- Build: PyInstaller 6.x, Python 3.11.15, pygame 2.6.1
