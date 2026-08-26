# Choreographed Enemy Movement — Design Spec

**Date:** 2026-08-26
**Status:** Draft (awaiting user review)
**Scope:** Movement enrichment for the 6 existing enemy types. **No new enemy types, no new sprites, no boss changes, no audio sync, no trigger-based choreography.**

---

## 1. Goal

Enrich the movement of the 6 existing enemy types (SCOUT, CRUISER, HEAVY, BOMBER, UFO, KAMIKAZE) using:

1. **6 new bezier paths** — more curve variety for entry/exit/loops
2. **5 new formations** — including 2 that are dynamically animated during flight
3. **Follow-the-Leader (FTL) chain** — a chain spawns N enemies on the same path with progressive time delays (visual "snake"/"train")
4. **Rotation per type per wave** — each enemy type has 2-3 default patterns and rotates through them across waves (avoids monotony)
5. **JSON overrides** — wave JSON can override any default (full flexibility)

Update `waves_act1.json` waves 1-5 (excluding wave 6 boss) to showcase the new patterns.

---

## 2. New Bezier Paths (`stellar_horizon/waves/bezier_horizontal.py`)

All paths tuned for the 480×270 internal viewport, enter from off-screen and exit off-screen.

| Function | Shape | Visual feel | Default for |
|---|---|---|---|
| `path_loop_horizontal` | Single loop in screen center | Enters, does one full circle, exits | Available in path builders (not a default for any kind — UFO keeps `ufo_entry`) |
| `path_figure_eight` | Horizontal figure-8 | Enters, loops twice, exits | SCOUT (rotation slot 1) |
| `path_pull_back` | Enter, retreat halfway, re-enter | Comes in, hesitates, comes back harder | Available in path builders (not a default for any kind — KAMIKAZE keeps `kamikaze_dive`) |
| `path_staircase` | Step-down zigzag | Predictable, readable descent | HEAVY (rotation slot 0) |
| `path_sine_bend` | Long smooth sinusoid | Glides like a wave | SCOUT (rotation slot 0) |
| `path_boomerang` | Enter, 180° turn, exit via entry | Comes in, loops back where it came | SCOUT (rotation slot 2) |

All paths are `BezierPath` instances (existing API), so no new code in `src/movement/`.

---

## 3. New Formations (`stellar_horizon/waves/formations_h.py`)

| Function | Shape | Default for | Dynamic? |
|---|---|---|---|
| `boomerang_arc` | Curved line that rotates around the leader slot during flight | CRUISER (rotation slot 0) | **Yes** — offsets recomputed every frame |
| `rotating_ring` | 6-8 enemies in a circle that spins | Available in formation builders (not a default — UFO keeps `line_horizontal`) | **Yes** — angle += dt × spin_rate |
| `phalanx_box` | Solid 3×3 or 4×4 block | HEAVY (rotation slot 1) | No |
| `swept_wing` | Delta wing (stretched V) | BOMBER (rotation slot 1) | No |
| `train_chain` | N enemies in a line, single slot per enemy, time-delayed entry (see FTL) | BOMBER (rotation slot 0) | No (the chain effect comes from the spawn pattern, not the formation) |

Dynamic formations expose a `update_offsets(elapsed_s)` method that the wave manager calls per frame.

---

## 4. Follow-the-Leader (FTL) Chain

**Simplified design (post-brainstorming):** A "chain" is **not** a leader-follower runtime dependency. It's a spawn pattern: N enemies of the same kind on the same path with progressive time delays.

**Behavior:**
- The wave JSON declares a single spawn entry with `chain_count: 3` and `chain_delay_s: 0.4`
- The wave manager expands this into 3 separate enemies:
  - Enemy 0 spawns at `delay_s` (the original delay)
  - Enemy 1 spawns at `delay_s + 0.4`
  - Enemy 2 spawns at `delay_s + 0.8`
- All 3 share the same path, same formation offsets, same kind
- If any one dies, the others continue their path independently (no runtime coupling)
- The "chain" is purely a temporal + visual pattern (you see a snake of N enemies entering sequentially)

**No visual indicator** — no line, no color tint. The player learns by experience that certain spawns are chains.

**No Enemy.py changes needed for chain state** — the chain is fully expressed in the spawn entries, not on the Enemy class.

**Cap and validation:** `chain_count` clamped to 1-5 in the wave manager (5 max enemies per chain). If a wave designer writes `chain_count: 10`, it gets clamped silently with a log warning. If `chain_count <= 1` or is missing, the spawn is treated as a single enemy (no chain expansion). If `chain_count` is negative, it gets clamped to 1 with a warning.

---

## 5. Defaults per Type per Wave

A new module-level constant in `wave_manager.py`:

```python
_KIND_DEFAULTS_BY_WAVE: list[dict[EnemyKind, dict]] = [
    # Wave 1 — intro
    {
        EnemyKind.SCOUT:    {"path": "sine_bend",       "formation": "line_horizontal"},
        EnemyKind.CRUISER:  {"path": "s_right_to_left", "formation": "boomerang_arc"},
        EnemyKind.HEAVY:    {"path": "staircase",       "formation": "phalanx_box"},
        EnemyKind.BOMBER:   {"path": "s_right_to_left", "formation": "train_chain",   "chain_count": 3, "chain_delay_s": 0.5},
        EnemyKind.UFO:      {"path": "ufo_entry",       "formation": "line_horizontal"},  # keep ufo_entry
        EnemyKind.KAMIKAZE: {"path": "kamikaze_dive",   "formation": "v_pointing_left"},  # keep kamikaze_dive
    },
    # Wave 2 — scouts + cruisers
    {
        EnemyKind.SCOUT:    {"path": "figure_eight",     "formation": "line_horizontal"},
        EnemyKind.CRUISER:  {"path": "s_right_to_left",  "formation": "boomerang_arc"},
        ...
    },
    # ... waves 3, 4, 5
]
```

**How the wave manager uses it:**
- When a spawn entry in the JSON does **not** specify `path` or `formation`, the manager looks up the default for the spawn's kind from the wave-index entry of `_KIND_DEFAULTS_BY_WAVE`.
- When the JSON specifies `path` or `formation`, the JSON value wins (override).
- This means the JSON stays short and readable, but you can always override for a specific spawn.
- **Fallback for missing entries:** if a kind has no entry in `_KIND_DEFAULTS_BY_WAVE[wave_index]` (e.g. a new enemy type added later), the wave manager uses a hardcoded `_KIND_FALLBACK = { SCOUT: s_right_to_left + line_horizontal, ... }` so the game doesn't crash. Logged as a warning.

**Rotation logic:** Each enemy type has 2-3 patterns in the rotation table. Across waves 1-5, the rotation ensures:
- SCOUT sees `sine_bend` → `figure_eight` → `boomerang` → (next) across 3 waves
- CRUISER sees `boomerang_arc` twice (dynamic) and `s_right_to_left` once
- HEAVY sees `staircase` → `phalanx_box` patterns
- BOMBER uses `train_chain` with FTL in 2 waves
- UFO keeps `ufo_entry` (the built-in custom path) in all waves — **NEW** `path_loop_horizontal` is available in the path builders but **not assigned as UFO default** (per user decision: keep ufo_entry)
- KAMIKAZE keeps `kamikaze_dive` in all waves (per user decision: keep kamikaze_dive) — **NEW** `path_pull_back` is available in path builders but not the default

---

## 6. Wave JSON Updates (`waves/waves_act1.json`)

Update waves 1-5 (NOT wave 6 — boss fight stays untouched). Touch as few existing spawn entries as possible; instead, modify a small number of `path` and `formation` values to showcase the new patterns.

**Wave 1 (`w1_intro_scouts`):** Currently 5 scouts in V formation on `s_right_to_left`. Change path to `sine_bend` for first impression of the new movement. Keep formation as V.

**Wave 2 (`w2_scouts_and_cruisers`):** 3 spawns (cruiser line, scout V via top_dive, scout line). Change the first spawn (cruiser) to use `boomerang_arc` formation. Keep others.

**Wave 3 (`w3_heavies_join`):** 4 spawns. Change the first (heavy diamond) to use `phalanx_box` formation. Change the third (cruiser wedge) to use `sine_bend` path.

**Wave 4 (`w4_bombers_introduced`):** 4 spawns including bombers. Change one bomber spawn to use `chain_count: 3, chain_delay_s: 0.4` to demonstrate the FTL chain. Change formation to `swept_wing`.

**Wave 5 (`w5_ufo_and_kamikaze`):** 5 spawns. Keep ufo_entry and kamikaze_dive as-is. Change the third spawn (bomber) to use `chain_count: 4, chain_delay_s: 0.3` for a denser FTL chain.

**Risk:** Touching the JSON may break tests that assert specific spawn counts or timings. Mitigation: run full test suite after each wave change.

---

## 7. Files to Touch

| File | Change | Estimated LOC |
|---|---|---|
| `stellar_horizon/waves/bezier_horizontal.py` | +6 path functions | +90 |
| `stellar_horizon/waves/formations_h.py` | +5 formation functions, 2 with dynamic update | +120 |
| `stellar_horizon/waves/wave_manager.py` | Register 6 new paths, 5 new formations, add `_KIND_DEFAULTS_BY_WAVE`, add `chain_count` parsing + chain expansion | +80 |
| `stellar_horizon/waves/waves_act1.json` | Update 5 waves (1 entry per wave) | +20 (modified) |
| `stellar_horizon/tests/test_choreography.py` | NEW: tests for new paths, new formations, chain expansion, defaults table | +200 |
| **Total** | | **~510 LOC** |

**No changes to:** `entities/enemy.py`, `entities/boss.py`, `entities/player.py`, `core/game.py`, `scenes/`, `audio/`, `settings.py`, `tests/test_gameplay.py`, `tests/test_smoke.py`.

---

## 8. Testing Strategy

New file `tests/test_choreography.py` with:

1. **Path tests (~6 tests, 1 per new path):** build the path, simulate 5 seconds of update at 120 FPS, assert the final position is off-screen on the expected side, and the path's bounding box stays within reasonable screen bounds.

2. **Formation tests (~5 tests, 1 per new formation):** build the formation with N=5, assert N offsets returned, assert offsets are bounded. For dynamic formations (`boomerang_arc`, `rotating_ring`), call `update_offsets(elapsed_s)` and assert offsets actually change.

3. **Chain expansion test (~3 tests):** given a spawn with `chain_count: 3, chain_delay_s: 0.4`, assert the wave manager expands it to 3 enemies with the right `(delay_s + k*0.4)`. Test the cap (chain_count: 10 → clamped to 5). Test chain_count: 1 (single enemy, no expansion).

4. **Defaults table test (~3 tests):** given a wave index, assert the defaults are present and have valid path/formation names. Given a JSON spawn entry with explicit path, assert the JSON value wins over the default.

5. **JSON integrity test (~2 tests):** parse waves_act1.json, assert all referenced `path` and `formation` values exist in the builder registries. Assert no spawn entry references an unknown path or formation.

**Total: ~19 new tests.**

**Run the full suite after implementation:** 245 existing tests + 19 new = 264 expected to pass. If any existing test breaks due to wave changes, the test gets updated (with justification) rather than reverted.

---

## 9. Out of Scope (Explicit)

- ❌ New enemy types
- ❌ New sprites or visual upgrades
- ❌ Audio sync (no MIDI beat triggers for movement)
- ❌ Trigger-based choreography (e.g. "kill the leader → chain breaks")
- ❌ Changes to boss behavior
- ❌ Changes to player behavior
- ❌ Save/load system changes
- ❌ Score / HP rebalancing

---

## 10. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Wave JSON changes break existing tests | Medium | Medium | Run full test suite per wave change; update tests with justification if the change is intentional |
| Dynamic formations are CPU-heavy | Low | Medium | `boomerang_arc` and `rotating_ring` do simple math (rotation per frame). Profile if FPS < 110 in waves 3-4 |
| Chain cap of 5 is too restrictive | Low | Low | Increase to 8 if needed; documented in code |
| New paths are visually too similar to existing paths | Medium | Low | Visual review: capture screenshots via `tools/capture_boss_v2.py` style for each new path; if too similar, adjust control points |
| Player doesn't notice the choreography | Medium | Medium | The 5-wave update puts new patterns in 100% of waves 1-5, ensuring the player sees them |
| `_KIND_DEFAULTS_BY_WAVE` rotation feels forced | Low | Low | If a rotation entry feels off during testing, the user can override in the JSON or we adjust the rotation table |

---

## 11. Implementation Order

1. Add 6 new bezier paths + tests (no wave changes yet)
2. Add 5 new formations + tests (no wave changes yet)
3. Add `_KIND_DEFAULTS_BY_WAVE` to `wave_manager.py` + test
4. Add `chain_count` / `chain_delay_s` parsing + chain expansion + test
5. Update `waves_act1.json` waves 1-5 (one wave at a time, run tests between each)
6. Run full test suite (expect 264 passing)
7. Visual smoke test: launch the game, verify new patterns visible

---

## 12. Acceptance Criteria

The implementation is done when:
- ✅ All 19 new tests pass
- ✅ All 245 existing tests pass
- ✅ `smoke.py` 11/11 gates pass
- ✅ Game launches and waves 1-5 visibly show the new movement patterns
- ✅ FTL chain is visible in waves 4 and 5 (a train of 3-4 enemies entering sequentially)
- ✅ Dynamic formations (`boomerang_arc`, `rotating_ring`) visibly rotate/curve during flight
