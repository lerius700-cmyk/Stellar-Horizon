# STELLAR HORIZON

A horizontal 16-bit space shooter. 480x270 internal scaled 4x to
1920x1080, 120 FPS, single act with 6 waves + boss fight.

The only third-party runtime dependency is `pygame 2.6+`. The
`src/` directory at the project root is a vendored subset of the
[Void-Hunter](https://github.com/lerius700-cmyk/Void-Hunter)
libraries (movement, particles, audio synthesis) — copied into
this repo so Stellar-Horizon is fully self-contained and can be
cloned / run on its own.

## Run

```bash
# Smoke test (11 quality gates, ~5 seconds)
python smoke.py

# Play the game
python -m stellar_horizon.main

# Play for N seconds then auto-quit (good for screenshots)
python -m stellar_horizon.main --duration 60

# Validate imports + settings (no display needed)
python -m stellar_horizon.main --check
```

Or use the launchers in the project root:

```bat
run.bat
```

```powershell
.\run.ps1
```

## Controls

- **WASD / Arrows** — move the ship
- **Space** — fire
- **1-9, 0** — switch weapon (1 = yellow plasma, 0 = rainbow)
- **Esc / window close** — quit

## Tests

```bash
python -m pytest tests/ -v
```

The current test suite runs 239 tests with 100% pass rate.
2 of the 24 test files (`test_scenes_gameplay.py`,
`test_midi_player.py`) require the optional `mido` dependency;
they're skipped cleanly when `mido` is not installed.

## Spec

- `docs/REPORT_v1.0.0.md` — full project report (architecture,
  layout, features, stats, how to run, controls, known
  limitations, roadmap)
- `docs/RELEASE_NOTES_v1.0.0.md` — release notes for v1.0.0
- `docs/superpowers/specs/2026-08-15-stellar-horizon-design.md` —
  original design spec
- `docs/superpowers/plans/2026-08-15-stellar-horizon-phase1.md` —
  phase 1 implementation plan

## What's in v1.0.0

- **6 enemy types** (scout, cruiser, heavy, bomber, ufo, kamikaze) +
  **20 enemy sprite variants** + **5 player variants**
- **10 weapons** with per-weapon VFX (alpha pulse, scale pulse,
  halo) and per-weapon tuning
- **Boss — Asteroid Guardian** with:
  - 600 HP (10x prototype), 2 phases (300/300 threshold)
  - 5-action state machine (IDLE_PATROL → TELEGRAPH → CHARGE →
    RETREAT → COOLDOWN)
  - Charge attack with telegraph line + thruster particles
  - 4-frame AI animation set (IDLE, TELEGRAPH, CHARGE, DYING) at
    8 FPS
  - Hit-streak ring drop (50% chance on 20 hits within 7 seconds)
- **Starfox-64 style power-up rings**:
  - Silver: +1 life, 10% enemy drop
  - Gold: +2 life + stack, 5% drop
  - Gold stack: 3 golds = +3 max lives (3 → 6 → 9 max)
  - Magneto pickup at 30 px (no button)
  - 15 s lifetime + 3 s fade-out
- **HUD**: 9 heart slots + 2 gold ring slots, 10-icon weapon
  selector, boss HP bar, PTS / wave / enemy counter
- **Audio**: 4 MIDI tracks, 30+ synthesized SFX, per-ship thruster
  loops with dynamic compression

## Project layout

```
stellar-horizon/
├── main.py                  # CLI entry (--check, --duration N)
├── settings.py              # Display + pool sizes
├── smoke.py                 # 11 quality gates
├── run.bat / run.ps1        # launchers
├── src/                     # Vendored Void-Hunter libraries
│   ├── movement/            # bezier paths, flight formations, follower
│   ├── systems/             # pool, particle engine
│   ├── audio/               # synth
│   ├── utils/               # palette, easing
│   ├── core/                # settings + frame loop
│   └── ...
├── stellar_horizon/         # game package
│   ├── audio/               # MIDI + SFX, thrusters
│   ├── core/                # game loop, scene manager, clock
│   ├── entities/            # player, enemies, boss, bullets, powerups
│   ├── scenes/              # title, gameplay, game over
│   ├── ui/                  # HUD, backgrounds, animated sprite
│   ├── waves/               # wave data + bezier paths
│   ├── fx/                  # particles, bullet VFX, dust, screen shake
│   ├── tools/               # visual capture + asset processing
│   └── assets/              # sprites, backgrounds, MIDI
├── tests/                   # 22 test files
└── docs/                    # report, release notes, design specs
```

## Requirements

- Python 3.11+
- pygame 2.6.1 (only third-party runtime dependency)
- pytest, Pillow (test/dev only)
- mido (optional — only needed by 2 of 24 test files for
  placeholder MIDI generation; the game itself doesn't need it)

## License

Personal project. See `docs/REPORT_v1.0.0.md` for full project
context.
