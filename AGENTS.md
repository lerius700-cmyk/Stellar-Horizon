# STELLAR HORIZON — Agent Onboarding

> Memory layer for AI agents (and human collaborators) entering this repo.
> Profiled **Lite** under SF+SM v3.2 + SM v2.2. No `.synapse` per silo.
> Read this first. Pair with `CONTEXT.md` for current state.

## TL;DR

- **What:** Horizontal 16-bit shoot-em-up, Pygame, 480×270 internal → SCALED.
- **Stack:** Python 3.11+ · Pygame 2.6.1 · pytest 9 · stdlib only (no numpy/scipy).
- **Repo:** `lerius700-cmyk/Stellar-Horizon` (GitHub).
- **Latest release:** v1.1.0 (path fix + visual polish VFX, 2026-08-31).

## Key commands

| Action | Command |
|---|---|
| Run game | `python main.py` (or `run.ps1` / `run.bat`) |
| Run game with auto-exit | `python main.py --duration 30` |
| Validate imports | `python main.py --check` |
| Run full test suite | `pytest stellar_horizon/tests/ -q` |
| Run one test file | `pytest stellar_horizon/tests/test_visual_vfx.py -v` |
| Build Windows .exe | `pyinstaller --noconfirm --clean StellarHorizon.spec` |
| Build release zip | `Compress-Archive dist/StellarHorizon.exe StellarHorizon-vX.Y.Z-win64.zip` |

## Architecture (silo map)

| Silo | Role | Lives in |
|---|---|---|
| **core** | `Game`, `SceneManager`, `Scene` base class, settings | `stellar_horizon/core/` |
| **entities** | `Player`, `Enemy`, `Boss`, `Bullet`, `PowerUp` | `stellar_horizon/entities/` |
| **scenes** | `TitleScene`, `GameplayScene`, `GameOverScene` | `stellar_horizon/scenes/` |
| **fx** | `FxLayer` (particles), `EngineFlame`, `ScreenShake`, `DustStream`, bullet VFX | `stellar_horizon/fx/` |
| **audio** | `MidiPlayer`, `sfx` event handler, `ThrusterManager` | `stellar_horizon/audio/` |
| **ui** | `Hud`, animated sprites, backgrounds, mountains | `stellar_horizon/ui/` |
| **waves** | `WaveManager`, formations, bezier paths, JSON loader | `stellar_horizon/waves/` |
| **\_systems** | Foundational library code (movement, synth, particle_engine, dead code) | `stellar_horizon/_systems/` |
| **tools** | Refactor scripts, MIDI generator, helpers | `stellar_horizon/tools/` |
| **tests** | pytest suite (311 passing) | `stellar_horizon/tests/` |

**Silo ownership:** A change to `Enemy.take_damage` lives in `entities/`. New
particle kind → `fx/`. New scene → `scenes/`. **Don't add cross-silo hacks.**

## Token Budget (Lite profile)

L = full read of the silo, S = standard reader view, R = summary.
Estimates based on `Get-ChildItem -Recurse` size; treat as a guide, not a
contract. Recompute if you add >2 files to a silo.

| Silo | Files | Bytes (code) | L tokens | S tokens | R tokens |
|---|---|---|---|---|---|
| core | 4 | ~7 KB | ~2.0K | ~1.0K | ~0.2K |
| audio | 4 | ~10 KB | ~2.9K | ~1.5K | ~0.3K |
| entities | 6 | ~47 KB | ~13.3K | ~6.7K | ~1.3K |
| fx | 6 | ~26 KB | ~7.5K | ~3.7K | ~0.7K |
| scenes | 4 | ~49 KB | ~14.1K | ~7.0K | ~1.4K |
| ui | 5 | ~21 KB | ~6.1K | ~3.0K | ~0.6K |
| waves | 6 | ~27 KB | ~7.6K | ~3.8K | ~0.8K |
| \_systems | 77 | ~1.0 MB | ~290K | ~145K | ~29K |
| tools | 6 | ~21 KB | ~5.9K | ~3.0K | ~0.6K |
| tests | 28 | ~129 KB | ~37K | ~18K | ~3.7K |
| **TOTAL** | 152 | ~1.4 MB | **~387K** | ~194K | ~39K |

`_systems/` is heavy because it carries dead code (audio, entities, fx, ui
duplicates from before the refactor). If you don't need it for your task,
read only `movement/`, `audio/synth.py`, `systems/particle_engine.py`.

## Hard rules (don't violate)

1. **Path resolution via `__file__`** — never CWD-relative. The
   `Path("stellar_horizon/waves/waves_act1.json")` pattern broke the
   v1.1.0 release (exited on SPACE because the JSON wasn't found from
   `dist/`). All asset and wave-JSON lookups use
   `Path(__file__).resolve().parent` (or `.parent.parent` for the
   package's perspective).
2. **No `image_synthesize`** — this tool isn't available in this
   environment. All VFX is procedural (pygame primitives) or sprite
   sheets in `stellar_horizon/assets/sprites/`. If you need a new
   sprite, ask the user.
3. **Particle kinds** — only import from `stellar_horizon._systems.systems.particle_engine`.
   The kind list is `P_SPARK=0 … P_WAKE=18`. There is **no `P_SHARD`**
   (was a typo in an early draft). If you need a new kind, add it
   there and document.
4. **No auto zip / version** — user controls release cadence
   (memory rule 2026-08-14). Don't run pyinstaller unless asked.
5. **No print of tokens / credentials** — release scripts log LENGTH
   only. Don't paste tokens in chat (memory rule 2026-08-31).

## Conventions

- **Type hints** on all public functions. `from __future__ import annotations` at top.
- **`__slots__`** on entity classes (`Player`, `Enemy`, `Bullet`) — memory bound.
- **No numpy/scipy** — keep dependencies stdlib + pygame.
- **Test names** start with `test_` and describe behavior, not implementation.
- **Headless tests** work — `conftest.py` sets `SDL_VIDEODRIVER=dummy` and pre-inits pygame.
- **Asset paths** in code: `Path(__file__).resolve().parent.parent / "assets"`.

## What to read first (when joining a session)

1. `CONTEXT.md` — current state, what was just done, what's pending.
2. `stellar_horizon/settings.py` — FPS, screen size, pool sizes, weapon tables.
3. `stellar_horizon/waves/waves_act1.json` — the actual level data.
4. Then drill down by silo per the task.

## Pitfalls (what NOT to do)

- **Don't recreate `assets/` at root** or `stellar_horizon/_vendor/`.
  Both are gitignored + removed; reintroducing them breaks the build.
- **Don't `from src.X` imports** — moved to `stellar_horizon._systems.X`
  on 2026-09-01. The top-level `src/` namespace no longer exists.
- **Don't bypass `on_enter()`** — that's where sprites, audio, FX, and
  wave state are wired. Constructing a scene without calling it
  leaves everything as `None`.
- **Don't modify the engine flame** in `fx/engine_flames.py` without
  checking `color` — it's an extension point for per-kind palettes.
- **Don't add a new `P_SHARD` particle kind** — it's a phantom.

## When a new session starts

1. Run `git log --oneline -10` to see the latest commits.
2. Run `pytest stellar_horizon/tests/ -q` to verify the baseline (expect 311 pass / 1 fail / 5 errors — see `CONTEXT.md` "Known issues").
3. Read `CONTEXT.md` to learn where the last session left off.
4. Proceed per the user's instructions.
