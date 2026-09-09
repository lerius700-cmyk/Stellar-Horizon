# Stellar Horizon v1.7.0 — "White Piercing Charged Disc + Re-implemented Rings"

**Release date:** 2026-09-09
**Branch:** main
**Commits ahead of v1.6.0:** 2 (9e20833 + 350c869)
**Tests:** 503 passing (was 487 in v1.6.0; +16 across ChargedDisc + ring re-implementation)
**Build size:** 34.6 MB

## Headline

Two BIG gameplay upgrades:
1. **Weapon 1 (WHITE PIERCING) charged shot is now a StarFox-style piercing disc**, not a generic bullet. Hold SPACE 1.0s, release, watch a 40px white disc fly through up to 4 enemies with 8x first-hit damage.
2. **Power-up rings (gold + silver) are re-implemented** with bigger visuals, drop VFX, idle animation, magnet hint, and floating pickup popups. The 10px tiny rings are gone.

## Control scheme (unchanged from v1.6)

| Key | Action |
|---|---|
| **B** (tap) | tier-1 basic bullet |
| **SPACE** (hold+rel) | tier-2 charged behavior |
| WASD / arrows | movement |
| ESC / Q | quit |
| 1-5 | switch weapon |

## Weapons (unchanged from v1.6)

5 weapons (charged 0-3, basic 4). See v1.6.0 release notes.

## NEW: White Piercing Charged Disc (slot 1)

The v1.6 "Megaman bolt" generic bullet on weapon 1 has been
replaced with a **StarFox 64-inspired piercing disc**:

- **Charge (1.0s)**: a flat white disc of light forms at the
  player's muzzle. It grows from 8px to 40px radius with easing-out.
  At 0.85s, 3 concentric rings appear inside the disc, rotating
  at different speeds (outer +90°/s, middle +180°/s, inner +360°/s).
  At 1.0s the body pulses with `sin(t × 10)` for the "ready" feedback.
- **Release**: the entire disc transforms into a high-velocity
  projectile that flies at **1100 px/s** in +X. The 3 internal
  rings keep spinning in flight, and a white particle trail is
  emitted (8-10 particles, fade-out in 0.2s).
- **Hit (first enemy)**: 8x damage + 14-18 white spark particles
  (splash radial 270°) + **shockwave** (50px white ring expanding
  in 0.2s) + **screen shake** (3px / 0.15s, capped at 6px) +
  **white flash** at the hit location.
- **Hit (2-4)**: 3x damage + 6-8 small splash particles. No
  shockwave, shake, or flash (the "event" already passed).
- **Miss**: after 0.4s without a hit, the disc fades over 0.4s
  with scale 1.0 → 1.3 (alpha 255 → 0). No particle on miss.
- **Off-screen**: dies if `x > INTERNAL_W + 60`.
- **Audio** (placeholders until synth pass): rising hum during
  charge, "BWAAAAAM" sine sweep on release, "krssh" white noise
  on first hit, "pop" on secondary hits.

Visual reference: the v1.7 capture `sprite_tests/captures/charged_disc_v17.png`
shows the 4x4 composite (charge 0/50/85/100%, flying 0.0/0.1/0.2/0.3s,
fading 0/33/66/100%, hit cruising/first/secondary/dead).

## NEW: Power-up rings re-implemented

The v1.6 power-up rings were tiny (10px), dropped rarely (5%/10%),
and had no VFX, no animation, and no pickup feedback. Players could
play for minutes without seeing one. **v1.7 fixes all of that:**

| Aspect | v1.6 | v1.7 |
|---|---|---|
| Ring size | 10px | **18px ring + 22px glow** |
| Drop rate (gold) | 5% | **18%** |
| Drop rate (silver) | 10% | **25%** |
| Drop VFX | none | 8-10 colored particles on spawn |
| Idle animation | 4 dots rotating | dots + vertical bob (1.5Hz, ±3px) |
| Glow pulse | none | alpha 0.85-1.0 @ 0.5Hz |
| Magnet hint | none | ring scales 1.0→1.3 when player <60px |
| Drop physics | static | small random kick + gravity + drag |
| Pickup feedback | sfx "hit" + small sparkle | **floating "+1 LIFE" / "+1 MAX" popup** + bigger sparkle + dedicated sfx |
| Lifetime | 15s | 12s (faster turnover) |

### Floating pickup popups

When you pick up a ring, a small text label floats above the player
for 1.5s, drifting upward (-28 px/s) and fading in the last 40% of
its lifetime. Color matches the ring kind (gold or silver). The
text reads "+1 LIFE" for silver rings and "+1 MAX" for gold rings
that bumped the max-lives cap (3 → 6 → 9).

### Dedicated pickup sfx (placeholders)

- `ring_pickup_gold` — 0.12s chime, gold triad (C5+E5+G5), vol 0.55
- `ring_pickup_silver` — 0.10s chime, silver triad (C5+Eb5+G5), vol 0.50

The .wav files are pending a synth pass; the events dispatch
silently for now (the same pattern as ChargedDisc).

Visual reference: `sprite_tests/captures/powerup_rings_v17.png`
shows the 2x3 grid (gold + silver × drop / idle / magnet) plus
the pickup popup text row.

## Implementation notes

### New files (v1.7)

- `stellar_horizon/entities/charged_disc.py` — ChargedDisc entity
  (FLYING / FADING state machine, AABB 80×80, register_hit /
  hits / fade_alpha / fade_scale)
- `stellar_horizon/fx/charged_disc_renderer.py` — procedural
  body + charging preview + emit_trail()
- `stellar_horizon/fx/shockwave.py` — reusable expanding ring
  primitive (dataclass)
- `stellar_horizon/tests/test_charged_disc.py` — 21 tests
  (entity + FxLayer + Player integration)
- `sprite_tests/capture_charged_disc.py` — visual evidence
- `sprite_tests/captures/charged_disc_v17.png` — 4x4 composite
- `sprite_tests/capture_powerup_rings.py` — visual evidence
- `sprite_tests/captures/powerup_rings_v17.png` — 2x3 + popup
- `stellar_horizon/tests/test_powerup.py` — 11 tests (bob, pulse,
  magnet, pickup, lifetime, alpha, drop rates, sfx, drop velocity,
  drag)

### Modified files (v1.7)

- `stellar_horizon/entities/player.py` —
  - CHARGE_TIME_S[1] 1.2s → 1.0s
  - new `charged_disc_pool` parameter to update()
  - weapon 1 release spawns ChargedDisc (was: PlayerBullet with
    damage 3)
- `stellar_horizon/entities/powerup.py` — full rewrite of draw()
  + new physics + new is_magnet_active() + new drop rates
- `stellar_horizon/fx/particles.py` — FxLayer gained
  emit_shockwave(), add_screen_shake(amp, dur) (capped at 6px),
  add_flash(x, y, r, color, dur)
- `stellar_horizon/scenes/gameplay.py` —
  - ChargedDisc pool of 2
  - ChargedDisc update + trail + collision vs enemies + boss
  - Render combines the trauma-based ScreenShake + the FxLayer shake
  - Weapon 1 uses the ChargedDisc preview instead of the
    ShipChargeOrb
  - new `_popups` list, `_draw_popups()`, `_spawn_popup()`
  - `_spawn_powerup()` emits 8-10 drop particles
  - `_on_powerup_pickup()` uses new sfx + creates popups
- `stellar_horizon/audio/sfx.py` — 6 new placeholder events
  (4 ChargedDisc + 2 ring pickups)
- `stellar_horizon/settings.py` — CHARGED_DISC_POOL = 2
- `stellar_horizon/tests/test_charge_state.py` — updated for v1.7

### Known issues / pending

- 6 sfx events are placeholder names; the .wav generation is
  scheduled for a follow-up synth pass. Events dispatch as
  silent no-op until the synth pass generates the files.
- The DEPRECATED `ship_charge_aura.py` module is on disk but
  unused. Delete manually if you want to clean up.

## How to use the .exe

```
1. Extract StellarHorizon-v1.7.0-win64.zip anywhere
2. Double-click StellarHorizon.exe
3. Wait for the title screen
4. Press SPACE to start
5. WASD to move, B for basic shot, SPACE for charged shot
6. Press 1-5 to switch weapons
7. ESC or Q to quit
```

## Try the new disc (slot 1)

1. Press `2` to select WHITE PIERCING
2. Hold B for a moment to see the basic shot (unchanged from v1.6)
3. Now hold SPACE for 1.0s. Watch the disc grow at your muzzle.
4. Release SPACE. The disc flies forward and pierces through enemies.
5. The first enemy takes 8x damage + shockwave + shake + flash.

## Try the re-implemented rings

Kill enemies. You'll see gold and silver rings drop more often
(18% / 25%). The ring has a colored burst on drop, bobs up and
down, and lights up when you get close. When you pick one up,
you'll see "+1 LIFE" (silver) or "+1 MAX" (gold) float above your
ship, plus a chime. The HUD's life counter updates in real time.

## Credits

- Code: Lerius + Mavis (v1.7 BLOQUE iterations)
- Long sheets + laser archetypes: AI-generated via Matrix connector
- Charge orb design: Wan video reference + Gemini 2x4 grid reference
- StarFox-style disc: inspiration from StarFox 64 (Nintendo, 1997)
- Build: PyInstaller 6.x, Python 3.11.15, pygame 2.6.1
