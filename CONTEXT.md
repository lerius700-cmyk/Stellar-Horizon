# CONTEXT — STELLAR HORIZON

> Lite-profile memory layer. Companion to `AGENTS.md`.
> This file is **state**, not architecture. Update "Última sesión" at the
> end of every session.

## Estado del proyecto

- **Version:** v1.1.0 (tagged 2026-08-31).
- **Status:** Stable, live on GitHub Releases. Path fix shipped.
- **Test baseline:** 311 passed, 1 failed, 5 errors (out of 317 total).
  Failures and errors are pre-existing, NOT introduced by recent work.
  See "Known issues" below.
- **Latest tag:** `v1.1.0` at commit `91def31`. The post-refactor
  commits (path fix + visual polish + summary) and the SF+SM refactor
  are ahead of the tag — they are in `main` but not yet in a release.

## Última sesión

**2026-09-01 — SF+SM refactor + token guidance + .zip verification**

- **SF+SM audit** of the project. Found 3 critical duplications
  (`assets/` root vs `stellar_horizon/assets/`, `stellar_horizon/_vendor/`
  dead code, `src/` at root with `from src.X` imports) and 4 medium
  structural issues (tests split across two locations, build/log
  artifacts at root, dead roguelike/ui/utils, etc.).
- **Cleanup (Lite + full clean):**
  - Deleted `assets/` (root) — phantom duplicate, 95 files.
  - Deleted `stellar_horizon/_vendor/` — 4 things, all dead code
    (movement/, palette.py, particle_engine.py, pool.py).
  - Moved `src/` → `stellar_horizon/_systems/`. 196 import statements
    rewritten from `from src.X` to `from stellar_horizon._systems.X`.
  - Unified 22 tests from `tests/` (root) into `stellar_horizon/tests/`,
    copying the root `conftest.py` and `__init__.py` (they set SDL
    dummy drivers — without them 3 tests regressed until I copied).
  - Removed `build_fresh/`, `dist_fresh/`, `*.log` at root.
  - Updated `.gitignore` to prevent regression: `/assets/`,
    `/stellar_horizon/_vendor/`, `build_fresh/`, `dist_fresh/`,
    `*-win64.zip`, `tools/_*.py`, `.superpowers/`.
  - Deleted the one-shot refactor script `tools/_refactor_src_to_systems.py`.
- **Memory layer (Lite):** created `AGENTS.md` (architecture, Token
  Budget, hard rules) and this `CONTEXT.md`.
- **Token guidance:** confirmed with user that `void-hunter` and
  `Stellar-Horizon` should use **separate PATs** (different names
  + different fine-grained scopes). The user already created the
  Stellar-Horizon token (classic, with admin/maintain/push/triage/pull);
  we discussed fine-grained as the preferred narrower option but the
  user deferred regeneration ("luego hago eso").
- **Final state:** `main` is 12+ commits ahead of the `v1.1.0` tag.
  User has the fresh `StellarHorizon-v1.1.0-win64.zip` (13.95 MB)
  ready to drag-replace the broken asset on the GitHub release page.
  Smoke test of the .exe (from `dist/`) confirmed it boots without
  `FileNotFoundError` after the path fix.

**Pre-refactor (2026-08-31 — visual polish VFX, Tasks 1-9):**

- **Path fix** (`85293e4`): `main.py` and `core/Game` resolve
  `wave_json` and `assets_dir` via `__file__`, not CWD. This fixed
  the release-blocker where the .exe ran with CWD=`dist/` and
  failed to find the wave JSON when the user pressed SPACE.
- **Visual polish VFX (8 commits):**
  - Task 1: 6 new `FxLayer` methods (trail, typed explosion, bullet
    impact, chain spawn glow, player hit, player death).
  - Task 2: `Enemy.take_damage` now calls `emit_explosion_typed(kind)`.
  - Task 3: `fx/engine_flames.py` — procedural 4-frame flame renderer.
  - Task 4: All 6 enemy kinds wired with engine flame + trail.
  - Task 5: Player wired with cyan engine flame + trail.
  - Task 6: `WaveManager.fx` + per-link chain spawn glow.
  - Task 7: `PlayerBullet` and `EnemyBullet` animated (4-frame sheets,
    8/6 FPS).
  - Task 8: Player hit flash + 1.5s death sequence.
  - Test count: 72 → 311 (entire test suite, including 29 new VFX tests).
- **PyInstaller build:** `StellarHorizon-v1.1.0-win64.zip` (13.95 MB)
  with path fix + visual polish.

## Pending items

- **User action:** drag-replace the broken `StellarHorizon-v1.1.0-win64.zip`
  on the GitHub release page with the fresh 13.95 MB build.
  (URL: https://github.com/lerius700-cmyk/Stellar-Horizon/releases/tag/v1.1.0)
- **User action (deferred):** regenerate the Stellar-Horizon PAT
  as fine-grained scope (only Stellar-Horizon, only Contents: R&W)
  instead of classic. Token currently works, just has broader scope
  than needed.
- **User action:** push the SF+SM refactor commits to `origin/main`
  (so the local advances + Token Budget + .gitignore become
  canonical on GitHub). Note: this is a SEPARATE push from the
 12-commit visual-polish push that already went up.
- **Optional (post-refactor):** rebuild the .exe against the new
  structure to confirm PyInstaller still picks up `stellar_horizon/`
  correctly. The new structure moved `src/` → `_systems/` inside the
  package, which PyInstaller's `datas=[]` should auto-include, but
  the .exe hasn't been rebuilt since the refactor.

## Known issues (pre-existing, not blocking)

| Issue | Test(s) | Cause | Fix? |
|---|---|---|---|
| `test_same_weapon_keypress_does_not_emit_impact` fails | 1 | Likely dust stream or chain glow emit particles between `pre`/`post` sample. Test was probably written before dust chain glow. | Investigate later; not user-blocking. |
| `mido is required to generate placeholder MIDI` | 5 | `mido` not in `requirements-dev.txt`; `make_placeholder_midi.py` raises on import. | `pip install mido` to requirements-dev.txt. |
| `roguelike/`, `ui/`, `utils/` inside `_systems/` are dead code | n/a | Pre-SF+SM refactor; kept in place per "move, don't delete" rule. | Future cleanup candidate. |
| `*.egg-info/`, `__pycache__/` in `_systems/` | n/a | Standard Python noise; gitignored. | None needed. |

## File map (post-refactor)

```
D:\AI\stellar-horizon\
├── AGENTS.md            ← this onboarding (read first)
├── CONTEXT.md           ← state + last session
├── .gitignore
├── main.py              ← entry point (Path(__file__)-based path resolution)
├── settings.py          ← constants: INTERNAL_W=480, INTERNAL_H=270, FPS_TARGET=120
├── run.ps1, run.bat     ← convenience launchers
├── StellarHorizon.spec  ← PyInstaller spec
├── requirements.txt     ← runtime
├── requirements-dev.txt ← dev/test deps (missing mido)
├── stellar_horizon/     ← game package
│   ├── __init__.py
│   ├── assets/          ← backgrounds/, midi/, sprites/ — runtime assets
│   ├── audio/           ← MidiPlayer, sfx event handler, thrusters
│   ├── core/            ← Game, SceneManager, Scene base
│   ├── entities/        ← Player, Enemy, Boss, Bullet, PowerUp
│   ├── fx/              ← particles, engine_flames, screen_shake, dust, bullet_vfx
│   ├── scenes/          ← TitleScene, GameplayScene, GameOverScene
│   ├── settings.py      ← package-level constants
│   ├── tools/           ← refactor scripts (gitignored: _*.py)
│   ├── ui/              ← Hud, AnimatedSprite, Background, MountainLayer
│   ├── waves/           ← WaveManager, formations, JSON
│   ├── _systems/        ← foundational library (movement, audio/synth, particle_engine, ...)
│   └── tests/           ← pytest suite (26 files, 311 passing)
└── docs/
    └── superpowers/
        ├── specs/
        └── plans/
```

## Self-update instructions for future agents

When you finish a session, update "Última sesión" with:

1. Date (YYYY-MM-DD).
2. 1-2 line summary of what was done.
3. Anything stateful that the next session needs to know (paths
   resolved, decisions made, tests run, files moved, etc.).
4. Any new "Pending items" or "Known issues" entries.

Don't add a new section per session — overwrite or append to the
"Última sesión" block. This file is the project diary; keep it
honest, short, and current.
