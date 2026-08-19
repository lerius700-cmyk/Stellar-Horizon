# CHANGELOG — STELLAR HORIZON

All notable changes to this project are documented here. Format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org).

## [1.0.0] - 2026-08-18 — First public release

### Added

#### Core
- Single-act vertical slice: 6 enemy waves + boss fight
- 6 enemy types (scout, cruiser, heavy, bomber, ufo, kamikaze)
- 10 weapons with per-weapon VFX (alpha pulse, scale pulse, halo)
- 480x270 internal resolution scaled 4x to 1920x1080 @ 120 FPS

#### Boss — Asteroid Guardian
- 600 HP (10x prototype), 2 phases (300/300 threshold)
- 5-action state machine (IDLE_PATROL -> TELEGRAPH -> CHARGE ->
  RETREAT -> COOLDOWN)
- Charge attack with telegraph line + thruster particles, 250 px/s
  dash
- 4-frame AI animation set (IDLE, TELEGRAPH, CHARGE, DYING) at
  8 FPS, 6 frames each
- All boss damage = 2 hearts (contact + bullets)
- Hit-streak ring drop (50% chance on 20 hits within 7 s; resets
  on timeout or player taking boss damage)

#### Power-up rings (Starfox-64 style)
- Silver rings: heal 1 life, 10% enemy drop, code-rendered at
  10 px, magneto pickup at 30 px, 15 s lifetime + 3 s fade-out
- Gold rings: heal 2 lives, 5% drop, count toward the gold stack
- Gold stack system: 3 golds = +3 max lives (3 -> 6 -> 9 max), 2
  stacks total

#### HUD
- 9 heart slots (filled = current life, outline = unused cap)
- 2 gold ring slots (filled = stack earned)
- 10-icon weapon selector strip with active highlight
- Boss HP bar with quarter ticks
- PTS / wave / enemy counter

#### Audio
- 4 MIDI tracks (title, act1, boss, game_over)
- 30+ synthesized SFX (shoot, hit, explode_small/medium/boss, bomb,
  boss_warning, thruster_*, etc.)
- Per-ship thruster loops with dynamic compression (1/sqrt(N))
- 7-channel thruster cap

#### Technical
- 22 test files, 239 tests, 100% pass rate
- 11 quality gates in `smoke.py` (settings, movement, boss, HUD,
  etc.)
- Pool-based entity management (player bullets 32, enemy bullets
  64, particles 600)
- Code-driven bullet VFX (`stellar_horizon/fx/bullet_vfx.py`)
  with per-weapon parameters
- Procedural mountain parallax (3 layers) + dust stream
- Vendored `src/` subset of Void-Hunter libraries (movement,
  particles, audio synth, palette) for true self-containment

### Notes

- 2 of 24 test files require the optional `mido` dependency; they
  skip cleanly when it's not installed
- The 4 boss animation sheets are AI-generated; legacy
  `boss_sheet.png` is kept as a fallback
