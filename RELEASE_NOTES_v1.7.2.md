# Stellar Horizon v1.7.2 — "Ring Pickup SFX: real audio"

**Release date:** 2026-09-09
**Branch:** main
**Commits ahead of v1.7.1:** 1 (94c59e7)
**Tests:** 514 passing (was 510 in v1.7.1; +4 from ring pickup synth pass)
**Build size:** 34.6 MB (same as v1.7.1)

## Headline

The 2 ring pickup SFX events that v1.7.0 added (`ring_pickup_gold`,
`ring_pickup_silver`) are now backed by real `.wav` files generated
by the synth module. v1.7.0 and v1.7.1 dispatched these as silent
no-ops; v1.7.2 plays the audio.

## What changed

### Ring pickup SFX: from placeholder to real

- `ring_pickup_gold` — triangle 523.25Hz (C5 fundamental), 0.12s,
  vol 0.55. The triangle wave's soft 3rd harmonic approximates the
  bell/chime character of the full C5+E5+G5 gold triad. Gold is
  brighter, slightly longer, slightly louder than silver (more
  reward weight since the gold ring is rarer).
- `ring_pickup_silver` — triangle 523.25Hz (C5 fundamental), 0.10s,
  vol 0.50. The C5+Eb5+G5 silver triad approximated similarly.
  Soft, short, quiet.

### Why triangle and not sine

The synth module has no pure SINE voice; **triangle** is the
smoothest available and reads as a sustained energy tone. The
soft 3rd harmonic of a triangle wave approximates a bell/chime
character, which is what we want for pickup feedback.

### Why one fundamental and not 3 notes

A single `_SfxSpec` has a single `freq_hz`. To play a true triad
(C5+E5+G5 simultaneously), the synth would need a polyphonic
voice — which it doesn't have. The closest approximation is to
play the fundamental (C5) and let the triangle's natural harmonic
content carry the "chime" character.

## Tests

- 4 new tests in `tests/test_powerup.py`:
  - `test_synth_catalog_has_2_ring_pickup_entries` (catalog presence)
  - `test_ring_pickup_gold_spec_matches_design` (spec accuracy)
  - `test_ring_pickup_silver_spec_matches_design` (spec accuracy)
  - `test_synth_ring_pickup_events_in_sfx_names` (paranoia check
    that SFX_CATALOG and SFX_NAMES are in sync)

## All 6 SFX placeholders now real

| Event | v1.7.0 / v1.7.1 | v1.7.2 |
|---|---|---|
| `charge_hum_white` | silent no-op | ✅ real (v1.7.1) |
| `charged_release` | silent no-op | ✅ real (v1.7.1) |
| `charged_hit` | silent no-op | ✅ real (v1.7.1) |
| `charged_hit_secondary` | silent no-op | ✅ real (v1.7.1) |
| `ring_pickup_gold` | silent no-op | ✅ real (v1.7.2) |
| `ring_pickup_silver` | silent no-op | ✅ real (v1.7.2) |

All 6 v1.7+ events are now real SFX, not silent no-ops.

## How to use the .exe

```
1. Extract StellarHorizon-v1.7.2-win64.zip anywhere
2. Double-click StellarHorizon.exe
3. Press SPACE to start
4. Kill enemies. Gold and silver rings drop from kills.
5. Walk into a ring. You should hear:
   - A bright chime (gold) or a soft chime (silver).
6. The HUD's life counter updates in real time.
```

## What didn't change

- Power-up ring visual / animation / popups (unchanged from v1.7.0)
- ChargedDisc behavior (unchanged from v1.7.0)
- All other v1.7.1 features

## Credits

- Synth pass: 2 new `_SfxSpec` entries in
  `stellar_horizon/_systems/audio/synth.py` + 4 new tests in
  `tests/test_powerup.py` (commit 94c59e7)
- Code: Lerius + Mavis
- Build: PyInstaller 6.x, Python 3.11.15, pygame 2.6.1
