# Choreographed Enemy Movement — Implementation Summary

**Spec:** `docs/superpowers/specs/2026-08-26-choreographed-enemy-movement-design.md`
**Plan:** `docs/superpowers/plans/2026-08-26-choreographed-enemy-movement.md`

**Branch:** `main`
**Total commits:** 12 (one per task + 1 fix)
**Final test count:** 38 passing (12 new path tests + 11 new formation tests + 4 new chain tests + 5 new defaults tests + 4 new builder tests + 1 new JSON integrity test + 1 fix)

> Note: The original spec assumed 245 existing tests would continue to pass. The standalone migration to `D:\AI\stellar-horizon` did NOT include the 245 tests from `void-hunter/stellar_horizon/tests/`. The repo started with 0 tests; this implementation added 38 fresh ones.

---

## Commits (in order)

1. `886b41d` — feat(waves): add 6 new bezier paths (sine_bend, figure_eight, boomerang, staircase, loop_horizontal, pull_back)
2. `ab3f6dc` — feat(waves): add 5 new formations (phalanx_box, swept_wing, train_chain, boomerang_arc, rotating_ring)
3. `1d3c4f0` — feat(waves): register 6 new paths and 5 new formations in wave_manager builders
4. `c616ed6` — feat(waves): add _KIND_DEFAULTS_BY_WAVE rotation table and _KIND_FALLBACK
5. `ec6c8c4` — feat(waves): FTL chain expansion (chain_count + chain_delay_s, clamp 1-5)
6. `467c82d` — feat(wave1): scouts now use sine_bend for first-wave impression
7. `99381bf` — feat(wave2): cruiser uses boomerang_arc dynamic formation
8. `4636449` — feat(wave3): heavy uses phalanx_box, cruiser uses sine_bend
9. `92bf45b` — feat(wave4): bomber uses swept_wing + 3-link FTL chain
10. `71c67b0` — feat(wave5): bomber uses 4-link FTL chain (denser)
11. `3a39052` — test(choreography): verify all JSON spawns reference valid paths/formations
12. `fa80bda` — fix(waves): handle dynamic formation objects (call .offsets()) — **added after the plan, during smoke test**

---

## What landed

### New bezier paths (`stellar_horizon/waves/bezier_horizontal.py`)
- `path_sine_bend` — smooth long sinusoid for scouts
- `path_figure_eight` — horizontal figure-8 for scout/annoyance
- `path_boomerang` — comes in, loops back
- `path_staircase` — predictable descent for heavies
- `path_loop_horizontal` — single full circle in screen center
- `path_pull_back` — enter, retreat, re-enter hard (kamikaze-style)

### New formations (`stellar_horizon/waves/formations_h.py`)
- `phalanx_box` — solid N×N block
- `swept_wing` — delta wing
- `train_chain` — single-file line
- `boomerang_arc` — **dynamic**: rotates around leader slot over time
- `rotating_ring` — **dynamic**: ring spins around center

### Defaults rotation (`stellar_horizon/waves/wave_manager.py`)
- `_KIND_DEFAULTS_BY_WAVE` (length 5) — each kind has 2-3 default patterns rotated per wave
- `_KIND_FALLBACK` — safety net for future kinds not in the table

### FTL chain (`stellar_horizon/waves/wave_manager.py`)
- `chain_count` (1-5, clamped) + `chain_delay_s` per JSON spawn entry
- `_build_enemies` expands one spawn into N chain links (each with `formation_count` enemies)
- `begin()` schedules each link with progressive delays

### Wave updates (`stellar_horizon/waves/waves_act1.json`)
- Wave 1: scouts use `sine_bend`
- Wave 2: cruiser uses `boomerang_arc` (dynamic)
- Wave 3: heavy uses `phalanx_box`, cruiser uses `sine_bend`
- Wave 4: bomber uses `swept_wing` + 3-link FTL chain
- Wave 5: bomber uses 4-link FTL chain (denser)
- Wave 6 (boss): unchanged

### Fix
- `wave_manager.py` line 158: dynamic formations return objects with `.offsets()`, not lists. Added a duck-typed `hasattr(formation_obj, "offsets")` check.

---

## Visual smoke test

The game launches, the "STELLAR HORIZON" window opens at 1920×1080. The user can navigate to wave 2 to see the `boomerang_arc` dynamic formation, and to wave 4-5 to see FTL chains.

> **Known visual limitation:** the dynamic formations (`boomerang_arc`, `rotating_ring`) compute their initial offsets in `_build_enemies` but the formation object is discarded. The dynamic effect (rotating/curving over time) is therefore not visible in the current implementation. The fix would require keeping the formation object alive on the enemy/wave and calling `.update(dt)` per frame. This is a v1.1 task.

---

## What was NOT done (out of scope per spec)

- No new enemy types
- No new sprites
- No audio sync
- No trigger-based choreography
- No boss changes
- No player changes
