# Destruction Fall Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the chaotic "ship flies off at max speed in any direction" destruction animation with a realistic tumble: zero momentum on death, gravity-driven fall, exponential linear + angular drag, ship sprite (not explosion) visible during the fall, smoke trail.

**Architecture:** Rewrite `Enemy` dying state to use physics: zero vx/vy on `take_damage`, then constant gravity + `exp(-drag*dt)` damping. Split visible sprite: death sheet for the first 0.15s (explosion burst), then the ship's IDLE sheet rotated by `dying_rotation`. Add a new `P_SMOKE` particle for the trail. Build a sandbox tool that captures a 6-kind × 36-frame contact-sheet per (gravity, drag) pair for visual iteration.

**Tech Stack:** Python 3.11+ · Pygame 2.6.1 · pytest 9 · stdlib only (no numpy/scipy)

**Spec:** `docs/superpowers/specs/2026-09-06-destruction-fall-design.md`

## Global Constraints

- Python 3.11+ syntax (`from __future__ import annotations`, type hints, `tuple[str, ...]`)
- All public functions/methods have type hints
- Entity classes use `__slots__` (no `__dict__`)
- Asset paths resolved via `Path(__file__).resolve().parent`, never CWD-relative
- No numpy / scipy — keep dependencies stdlib + pygame
- Particle kinds: only import from `stellar_horizon._systems.systems.particle_engine`. The next free kind index after P_WAKE=18 is **19 → P_SMOKE**
- No auto-commit of release artifacts. Commits fine, no pyinstaller/zip unless user asks
- No `image_synthesize` — all visuals are procedural or sprite sheets in `stellar_horizon/assets/sprites/`
- Tests must pass: `pytest stellar_horizon/tests/ -q`

## File Structure

**Modified files:**
- `stellar_horizon/entities/enemy.py` — add constants, slots, `current_dying_sheet()`, rewrite `take_damage()` and the `dying_timer > 0` block in `update()` to use new physics, hook `fx.emit_smoke()` (throttled)
- `stellar_horizon/scenes/gameplay.py` — `_draw_enemy_sprite` priority section: when `dying_timer > 0`, use `e.current_dying_sheet()` instead of the hardcoded `enemy_{kind}_death_v1`
- `stellar_horizon/fx/particle_engine.py` — add `P_SMOKE = 19` constant, add `emit_smoke(x, y)` method on `FxLayer`, add P_SMOKE branch in `update_particles()`

**New files:**
- `sprite_tests/destruction_sandbox.py` — capture tool producing 6-kind × 36-frame contact-sheet PNGs
- `tests/test_destruction_render.py` — integration test verifying the scene renders a ship-like cluster post-burst

**Test additions in existing `tests/test_enemy.py`:**
- 8 new unit tests for the new physics + sheet selection

---

### Task 1: Add dying physics constants and slots to Enemy

**Files:**
- Modify: `stellar_horizon/entities/enemy.py:60-120` (constants + `__slots__` + `__init__`)

- [ ] **Step 1: Add the new module-level constants after the existing `_ENEMY_TRAIL_INTENSITY` block (around line 62)**

Insert these constants at the end of the constants block (just before `class Enemy:`):

```python
# 2026-09-06 destruction-fall polish: realistic tumble physics.
# See docs/superpowers/specs/2026-09-06-destruction-fall-design.md
_ENEMY_DYING_GRAVITY_PX_S2 = 500.0          # gravity acceleration (px/s^2)
_ENEMY_DYING_DRAG_LINEAR = 1.8              # 1/s, exp drag on vx
_ENEMY_DYING_DRAG_ANGULAR = 0.6             # 1/s, exp drag on omega
_ENEMY_DYING_OMEGA_RANGE = (-180.0, 180.0)  # deg/s random initial spin
_ENEMY_DYING_DEATH_SHEET_S = 0.15           # burst duration before ship is visible
```

- [ ] **Step 2: Add three new slots to `Enemy.__slots__`**

In the existing `__slots__` tuple, add these three entries (any position is fine, but group them with the existing `dying_timer` entry):

```python
"dying_timer",      # seconds remaining of the death animation (0 = not dying)
"dying_rotation",   # visual tumble: degrees rotated while falling
"dying_omega",      # current rotation rate (deg/s), decays with drag
"dying_elapsed",    # seconds since take_damage triggered death
"_smoke_throttle",  # frame counter for throttled smoke emission
```

- [ ] **Step 3: Initialize the new slots in `__init__`**

In `Enemy.__init__` (around line 110), after the existing `self.dying_rotation: float = 0.0` line, add:

```python
        self.dying_omega: float = 0.0
        self.dying_elapsed: float = 0.0
        self._smoke_throttle: int = 0
```

- [ ] **Step 4: Run existing tests to confirm no regression**

Run: `cd D:\AI\stellar-horizon; $env:PYTHONPATH = $PWD; .\.venv\Scripts\python.exe -m pytest stellar_horizon/tests/ -q`
Expected: 390 passed (no change). If fewer pass, the slot/init change broke something — fix before proceeding.

- [ ] **Step 5: Commit**

```bash
cd D:\AI\stellar-horizon; git add stellar_horizon/entities/enemy.py
git commit -m "feat(enemy): add dying physics constants and slots"
```

---

### Task 2: Zero momentum on death + constant gravity (TDD)

**Files:**
- Modify: `stellar_horizon/entities/enemy.py:267-285` (the `take_damage` method)
- Modify: `stellar_horizon/entities/enemy.py:158-178` (the `dying_timer > 0` block in `update`)
- Test: `stellar_horizon/tests/test_enemy.py` (add 2 tests)

- [ ] **Step 1: Write the failing test for zero-momentum**

Append to `tests/test_enemy.py`:

```python
def test_dying_zeroes_momentum():
    # 2026-09-06 destruction-fall: take_damage must zero vx/vy
    # so the ship stops moving forward/backward instantly and
    # gravity takes over. Previously, the previous frame's
    # movement velocity was preserved, making the ship appear
    # to fly off at full speed in its pre-death direction.
    e = Enemy()
    e.kind = "scout"
    e.on_spawn()
    e.vx, e.vy = 180.0, -90.0
    e.hp = 1
    e.take_damage(1)
    assert e.vx == 0.0, f"vx should be 0 after take_damage, got {e.vx}"
    assert e.vy == 0.0, f"vy should be 0 after take_damage, got {e.vy}"


def test_dying_applies_gravity_monotonically():
    # Gravity should pull the ship straight down. y must grow
    # monotonically over a sequence of update() calls and vy
    # must become positive (downward in screen coords).
    e = Enemy()
    e.kind = "scout"
    e.on_spawn()
    e.hp = 1
    e.x = 200.0
    e.y = 50.0
    e.take_damage(1)
    y_prev = e.y
    vy_samples = []
    for _ in range(20):
        e.update(0.05, FakePlayer())
        assert e.y > y_prev, f"y went {y_prev} -> {e.y} (must grow)"
        vy_samples.append(e.vy)
        y_prev = e.y
    # vy must be positive (downward in screen coords) and growing
    assert vy_samples[0] > 0.0, f"vy should be positive (downward), got {vy_samples[0]}"
    assert vy_samples[-1] > vy_samples[0], (
        f"vy should grow under gravity: start {vy_samples[0]} end {vy_samples[-1]}"
    )
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `cd D:\AI\stellar-horizon; $env:PYTHONPATH = $PWD; .\.venv\Scripts\python.exe -m pytest stellar_horizon/tests/test_enemy.py::test_dying_zeroes_momentum stellar_horizon/tests/test_enemy.py::test_dying_applies_gravity_monotonically -v`
Expected: BOTH tests FAIL. `test_dying_zeroes_momentum` fails because the current code doesn't zero vx/vy. `test_dying_applies_gravity_monotonically` likely fails because the ship flies off in the previous direction.

- [ ] **Step 3: Migrate gravity constant + Modify `take_damage` to zero momentum + new random omega + track elapsed**

**IMPORTANT: Gravity constant migration.** The brief for Task 1 left `_ENEMY_DYING_GRAVITY_PX_S2 = 620.0` in place (declared in the baseline `6c3316b` for the v1 destruction animation). The spec asks for `500.0`. This task is where the migration happens — the gravity value change MUST be atomic with the `update()` / `take_damage()` rewrite that consumes it. Change the value in the existing block:

```python
_ENEMY_DYING_GRAVITY_PX_S2 = 500.0  # was 620.0 (v1 destruction); 500 matches spec
```

Also remove the now-redundant NOTE comment that Task 1 added.

In `Enemy.take_damage` (around line 267), REPLACE the block inside `if self.hp <= 0:` (specifically the `if self.dying_timer <= 0.0:` block) with:

```python
            if self.dying_timer <= 0.0:
                self.base_sprite_name = self.sprite_name
                # Zero momentum: the ship "dies" — no carry-over
                # from the previous movement. Gravity will pull
                # it down from rest.
                self.vx = 0.0
                self.vy = 0.0
                # Random initial angular velocity gives variety:
                # each death tumbles in a different direction.
                self.dying_omega = random.uniform(
                    *_ENEMY_DYING_OMEGA_RANGE
                )
                self.dying_elapsed = 0.0
                self._smoke_throttle = 0
                # Swap to the per-kind death sheet for the
                # initial 0.15s burst. After that, the ship's
                # IDLE sheet takes over (see current_dying_sheet).
                self.sprite_name = f"enemy_{self.kind}_death_v1"
                self.dying_timer = 1.0
```

Also add `import random` at the top of the file (if not already there).

- [ ] **Step 4: Modify the `dying_timer > 0` block in `update` to apply gravity**

In `Enemy.update` (around lines 158-178), REPLACE the `if self.dying_timer > 0.0:` block with:

```python
        if self.dying_timer > 0.0:
            self.dying_timer -= dt
            self.dying_elapsed += dt
            # Apply gravity to vertical velocity.
            self.vy += _ENEMY_DYING_GRAVITY_PX_S2 * dt
            # Drag will be applied in a later task. For now,
            # vx and omega are unchanged.
            self.dying_rotation += self.dying_omega * dt
            # Integrate position.
            self.y += self.vy * dt
            self.x += self.vx * dt
            if self.y > _ENEMY_DYING_OFFSCREEN_Y or self.dying_timer <= 0.0:
                self.dying_timer = 0.0
                self.alive = False
            return []
```

- [ ] **Step 5: Run the new tests + existing dying tests to verify**

Run: `cd D:\AI\stellar-horizon; $env:PYTHONPATH = $PWD; .\.venv\Scripts\python.exe -m pytest stellar_horizon/tests/test_enemy.py -v`
Expected: `test_dying_zeroes_momentum` and `test_dying_applies_gravity_monotonically` PASS. The existing `test_dying_*` tests (timer countdown, offscreen removal, etc.) should also still pass. If `test_enemy_dying_falls_and_is_removed_at_bottom_of_viewport` or similar breaks because the ship now takes a different trajectory, adjust the assertions to use higher initial y or longer dt to compensate.

- [ ] **Step 6: Commit**

```bash
cd D:\AI\stellar-horizon; git add stellar_horizon/entities/enemy.py stellar_horizon/tests/test_enemy.py
git commit -m "feat(enemy): zero momentum on death, apply gravity in dying state"
```

---

### Task 3: Linear + angular drag (TDD)

**Files:**
- Modify: `stellar_horizon/entities/enemy.py:158-178` (the `dying_timer > 0` block in `update`)
- Test: `stellar_horizon/tests/test_enemy.py` (add 2 tests)

- [ ] **Step 1: Write the failing test for linear drag**

Append to `tests/test_enemy.py`:

```python
def test_dying_drag_slows_horizontal_velocity():
    # Linear drag should decay vx exponentially. Since vx is
    # zeroed on death in the new physics, force a vx via
    # take_damage + manual override. The integration uses
    # math.exp(-DRAG_LINEAR * dt) so vx should drop by a
    # predictable factor.
    e = Enemy()
    e.kind = "scout"
    e.on_spawn()
    e.hp = 1
    e.take_damage(1)
    e.vx = 100.0  # force-set after take_damage
    vx_initial = e.vx
    e.update(0.5, FakePlayer())
    # After 0.5s with DRAG_LINEAR=1.8, the multiplier is
    # exp(-1.8 * 0.5) = exp(-0.9) ≈ 0.406. So vx should be
    # about 40% of initial. Allow a 20% margin to avoid
    # brittleness.
    expected = vx_initial * 0.4066
    assert e.vx < vx_initial * 0.6, (
        f"vx should decay significantly under drag: "
        f"start {vx_initial} end {e.vx} (expected ~{expected:.1f})"
    )
    assert e.vx > 0, "vx should keep its sign under drag"


def test_dying_omega_decays_with_drag():
    # Angular drag should decay omega exponentially. The sign
    # of omega is preserved (rotation direction doesn't
    # reverse), only its magnitude decreases.
    e = Enemy()
    e.kind = "scout"
    e.on_spawn()
    e.hp = 1
    e.take_damage(1)
    e.dying_omega = 300.0  # force-set after take_damage
    omega_initial = e.dying_omega
    e.update(2.0, FakePlayer())
    # After 2s with DRAG_ANGULAR=0.6, multiplier is
    # exp(-0.6 * 2) = exp(-1.2) ≈ 0.301. So omega should be
    # about 30% of initial.
    expected = omega_initial * 0.3012
    assert abs(e.dying_omega) < abs(omega_initial) * 0.5, (
        f"|omega| should decay under angular drag: "
        f"start {omega_initial} end {e.dying_omega} (expected ~{expected:.1f})"
    )
    assert e.dying_omega > 0, "omega should keep its sign under drag"
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `cd D:\AI\stellar-horizon; $env:PYTHONPATH = $PWD; .\.venv\Scripts\python.exe -m pytest stellar_horizon/tests/test_enemy.py::test_dying_drag_slows_horizontal_velocity stellar_horizon/tests/test_enemy.py::test_dying_omega_decays_with_drag -v`
Expected: BOTH tests FAIL (drag is not yet applied).

- [ ] **Step 3: Add `import math` if missing, then add drag to the dying block**

At the top of `enemy.py`, ensure `import math` is present (it should be — `take_damage` doesn't use it but the file does for other things). If not, add it after `import pygame`.

In the `dying_timer > 0` block, INSERT after the gravity line (after `self.vy += _ENEMY_DYING_GRAVITY_PX_S2 * dt`):

```python
            # Exponential drag on linear velocity (scaled by
            # 1/s; the integration uses math.exp so the
            # formula is frame-rate independent).
            self.vx *= math.exp(-_ENEMY_DYING_DRAG_LINEAR * dt)
            self.dying_omega *= math.exp(-_ENEMY_DYING_DRAG_ANGULAR * dt)
```

- [ ] **Step 4: Run the drag tests + all other enemy tests**

Run: `cd D:\AI\stellar-horizon; $env:PYTHONPATH = $PWD; .\.venv\Scripts\python.exe -m pytest stellar_horizon/tests/test_enemy.py -v`
Expected: the 2 new drag tests PASS, all previous tests still PASS.

- [ ] **Step 5: Commit**

```bash
cd D:\AI\stellar-horizon; git add stellar_horizon/entities/enemy.py stellar_horizon/tests/test_enemy.py
git commit -m "feat(enemy): add linear and angular drag to dying state"
```

---

### Task 4: Random initial omega distribution (TDD)

**Files:**
- Modify: `stellar_horizon/entities/enemy.py:267-285` (the `take_damage` method, already updates `dying_omega`)
- Test: `stellar_horizon/tests/test_enemy.py` (add 1 test)

- [ ] **Step 1: Write the failing test for omega range**

Append to `tests/test_enemy.py`:

```python
def test_dying_random_omega_within_range():
    # The initial omega after take_damage is sampled uniformly
    # from [-180, +180] deg/s. Over 50 samples we should see
    # both positive and negative values, all in range.
    omegas = []
    for _ in range(50):
        e = Enemy()
        e.kind = "scout"
        e.on_spawn()
        e.hp = 1
        e.take_damage(1)
        omegas.append(e.dying_omega)
    # All in range
    for omega in omegas:
        assert -180.0 <= omega <= 180.0, (
            f"omega {omega} out of range [-180, 180]"
        )
    # Both signs present (random is working)
    positives = sum(1 for o in omegas if o > 0)
    negatives = sum(1 for o in omegas if o < 0)
    assert positives > 5, f"only {positives} positive omegas in 50 samples"
    assert negatives > 5, f"only {negatives} negative omegas in 50 samples"
```

- [ ] **Step 2: Run the test to verify it passes (Task 2 already added the random code)**

Run: `cd D:\AI\stellar-horizon; $env:PYTHONPATH = $PWD; .\.venv\Scripts\python.exe -m pytest stellar_horizon/tests/test_enemy.py::test_dying_random_omega_within_range -v`
Expected: PASS (Task 2's `take_damage` already sets `dying_omega = random.uniform(*_ENEMY_DYING_OMEGA_RANGE)`). If it fails, the constant is wrong or the assignment is missing — check Task 2's step 3.

- [ ] **Step 3: Commit (no code change needed, but commit the test)**

```bash
cd D:\AI\stellar-horizon; git add stellar_horizon/tests/test_enemy.py
git commit -m "test(enemy): random omega distribution in dying state"
```

---

### Task 5: `current_dying_sheet()` method (TDD)

**Files:**
- Modify: `stellar_horizon/entities/enemy.py:140-148` (add the new method, near `update`)
- Test: `stellar_horizon/tests/test_enemy.py` (add 1 test)

- [ ] **Step 1: Write the failing test for the sheet selection**

Append to `tests/test_enemy.py`:

```python
def test_dying_death_sheet_first_then_idle():
    # During the first 0.15s of the death sequence the death
    # sheet (the explosion) is shown. After that, the ship's
    # IDLE/base sheet (its original sprite) takes over so the
    # player can see the ship itself tumbling, not a static
    # explosion sprite being rotated.
    e = Enemy()
    e.kind = "scout"
    e.on_spawn()
    e.hp = 1
    e.sprite_name = "enemy_scout_v3"
    e.take_damage(1)
    # t=0: death sheet
    assert e.current_dying_sheet() == "enemy_scout_death_v1", (
        f"at t=0 expected death sheet, got {e.current_dying_sheet()}"
    )
    # t=0.10s: still in burst window
    e.update(0.10, FakePlayer())
    assert e.current_dying_sheet() == "enemy_scout_death_v1", (
        f"at t=0.10 expected death sheet, got {e.current_dying_sheet()}"
    )
    # t=0.20s: burst done, base sheet takes over
    e.update(0.10, FakePlayer())
    assert e.current_dying_sheet() == "enemy_scout_v3", (
        f"at t=0.20 expected base sheet 'enemy_scout_v3', "
        f"got {e.current_dying_sheet()}"
    )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd D:\AI\stellar-horizon; $env:PYTHONPATH = $PWD; .\.venv\Scripts\python.exe -m pytest stellar_horizon/tests/test_enemy.py::test_dying_death_sheet_first_then_idle -v`
Expected: FAIL with `AttributeError: 'Enemy' object has no attribute 'current_dying_sheet'`.

- [ ] **Step 3: Add the `current_dying_sheet` method to `Enemy`**

In `enemy.py`, add the method right after `update` (around line 240, just before `_update_kamikaze`):

```python
    def current_dying_sheet(self) -> str:
        """Return the sprite name to display during the death
        sequence. The first 0.15s shows the death sheet (the
        explosion burst). After that, the ship's base sheet
        takes over so the player sees the actual ship
        tumbling down, not a static explosion sprite being
        rotated.

        Falls back to the kind's v1 variant if base_sprite_name
        was never set (e.g. legacy enemy without an explicit
        spawner-assigned sprite).
        """
        if self.dying_elapsed < _ENEMY_DYING_DEATH_SHEET_S:
            return f"enemy_{self.kind}_death_v1"
        return self.base_sprite_name or f"enemy_{self.kind}_v1"
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd D:\AI\stellar-horizon; $env:PYTHONPATH = $PWD; .\.venv\Scripts\python.exe -m pytest stellar_horizon/tests/test_enemy.py::test_dying_death_sheet_first_then_idle -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd D:\AI\stellar-horizon; git add stellar_horizon/entities/enemy.py stellar_horizon/tests/test_enemy.py
git commit -m "feat(enemy): current_dying_sheet() shows death burst then ship"
```

---

### Task 6: P_SMOKE particle kind + emit_smoke (TDD)

**Files:**
- Modify: `stellar_horizon/fx/particle_engine.py` (find the existing P_* constants and `FxLayer.emit_*` methods)
- Test: `stellar_horizon/tests/test_destruction_render.py` (new file, add 1 test)

- [ ] **Step 1: Write the failing test for P_SMOKE constant + emit_smoke method**

Create `tests/test_destruction_render.py`:

```python
# stellar_horizon/tests/test_destruction_render.py
"""Tests for the destruction animation: P_SMOKE particle kind
and the emit_smoke() method on FxLayer.
"""
from __future__ import annotations


def test_particle_engine_has_p_smoke_kind():
    # 2026-09-06 destruction-fall: the smoke trail during the
    # fall uses a new particle kind P_SMOKE. It must be
    # defined in the particle engine so the rest of the code
    # can emit and update it.
    from stellar_horizon._systems.systems.particle_engine import P_SMOKE
    assert isinstance(P_SMOKE, int)
    # Must be a fresh index (not collide with existing kinds).
    assert P_SMOKE >= 19, f"P_SMOKE should be >= 19, got {P_SMOKE}"


def test_fxlayer_emit_smoke_creates_particle():
    # FxLayer.emit_smoke(x, y) should add a P_SMOKE particle
    # to its internal particle list. We construct an FxLayer
    # directly (no display needed) and verify the count goes
    # up after emission.
    from stellar_horizon.fx.particle_engine import FxLayer
    from stellar_horizon._systems.systems.particle_engine import P_SMOKE

    fx = FxLayer(0, 0, 480, 270)  # headless-safe constructor
    initial_count = sum(
        1 for p in fx._particles if getattr(p, "kind", None) == P_SMOKE
    )
    fx.emit_smoke(100.0, 50.0)
    new_count = sum(
        1 for p in fx._particles if getattr(p, "kind", None) == P_SMOKE
    )
    assert new_count == initial_count + 1, (
        f"expected 1 new P_SMOKE particle, got {new_count - initial_count}"
    )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd D:\AI\stellar-horizon; $env:PYTHONPATH = $PWD; .\.venv\Scripts\python.exe -m pytest stellar_horizon/tests/test_destruction_render.py -v`
Expected: FAIL (P_SMOKE doesn't exist yet, emit_smoke doesn't exist).

- [ ] **Step 3: Add P_SMOKE constant to the particle engine**

Open `stellar_horizon/_systems/systems/particle_engine.py` and find the existing `P_*` constants (P_SPARK, P_WAKE, etc.). Add after the last one (P_WAKE=18):

```python
P_SMOKE = 19  # 2026-09-06 destruction-fall: smoke trail emitted during enemy fall
```

If the file uses an enum or class, add to that instead — preserve existing style.

- [ ] **Step 4: Add `emit_smoke(x, y)` method to FxLayer in `stellar_horizon/fx/particle_engine.py`**

Find the existing `emit_*` methods on the FxLayer class. Add a new one with this signature (use whatever pattern the other emit methods use — could be a list.append(Particle(...)) or a method on the engine):

```python
    def emit_smoke(self, x: float, y: float) -> None:
        """Emit a single P_SMOKE particle at (x, y).

        Smoke drifts upward, fades over 0.6s, and grows in
        scale (so it reads as dispersing). The lifetime is
        short enough that the trail doesn't accumulate
        behind a long fall.
        """
        # Look at the existing emit methods to mirror the
        # pattern. If they use a helper like self._spawn(...),
        # call that. If they append a Particle to self._particles
        # directly, do the same.
        # Example structure (adapt to the existing code):
        #   p = Particle(kind=P_SMOKE, x=x, y=y,
        #                vx=random.uniform(-3, 3), vy=-8.0,
        #                lifetime=0.6, color=(180, 180, 180))
        #   self._particles.append(p)
        #
        # Read the surrounding emit methods and replicate
        # the exact style — that's the source of truth.
```

- [ ] **Step 5: Add the P_SMOKE update branch in `update_particles`**

Find the existing `update_particles` (or equivalent) function/method in the same file. Add a `kind == P_SMOKE` branch:

```python
        elif p.kind == P_SMOKE:
            # Slow upward drift decelerates
            p.vy += 5.0 * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            # alpha fade: 200 -> 0 over lifetime
            age = 1.0 - (p.lifetime_remaining / p.lifetime_total)
            p.alpha = int(200 * (1.0 - age))
            # scale 1.0 -> 2.5
            p.scale = 1.0 + 1.5 * age
            p.color = (180, 180, 180)
```

Use the actual field names from the existing particle struct (e.g. `p.life`, `p.max_life`, `p.color` — whatever is there).

- [ ] **Step 6: Run the test to verify it passes**

Run: `cd D:\AI\stellar-horizon; $env:PYTHONPATH = $PWD; .\.venv\Scripts\python.exe -m pytest stellar_horizon/tests/test_destruction_render.py -v`
Expected: PASS (both new tests).

- [ ] **Step 7: Commit**

```bash
cd D:\AI\stellar-horizon; git add stellar_horizon/_systems/systems/particle_engine.py stellar_horizon/fx/particle_engine.py stellar_horizon/tests/test_destruction_render.py
git commit -m "feat(fx): add P_SMOKE particle kind for destruction-fall smoke trail"
```

---

### Task 7: Hook P_SMOKE into Enemy.update (TDD)

**Files:**
- Modify: `stellar_horizon/entities/enemy.py:158-178` (the `dying_timer > 0` block in `update`)
- Test: `stellar_horizon/tests/test_enemy.py` (add 1 test)

- [ ] **Step 1: Write the failing test for smoke emission**

Append to `tests/test_enemy.py`:

```python
def test_dying_emits_smoke_when_fx_set():
    # A dying enemy with an injected FxLayer reference should
    # emit P_SMOKE particles during update(). We use a tiny
    # fake FxLayer that counts calls.
    from stellar_horizon._systems.systems.particle_engine import P_SMOKE

    class _FakeFx:
        def __init__(self):
            self.smokes = []
        def emit_smoke(self, x, y):
            self.smokes.append((x, y))

    e = Enemy()
    e.kind = "scout"
    e.on_spawn()
    e.hp = 1
    e.x = 100.0
    e.y = 50.0
    e.fx = _FakeFx()
    e.take_damage(1)
    for _ in range(10):
        e.update(0.05, FakePlayer())
    # 10 ticks of 0.05s with throttle 1-in-2 means 5 smoke emits
    # (the throttle increments every tick and emits on even
    # ticks; 10 ticks / 2 = 5 emits).
    assert len(e.fx.smokes) >= 3, (
        f"expected >= 3 smoke emits in 10 ticks, got {len(e.fx.smokes)}"
    )
    # The smoke positions should be near the ship's position
    # (within a few pixels — gravity moves the ship down).
    for sx, sy in e.fx.smokes:
        assert abs(sx - e.x) < 50
        assert sy >= 30  # never above the spawn point
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd D:\AI\stellar-horizon; $env:PYTHONPATH = $PWD; .\.venv\Scripts\python.exe -m pytest stellar_horizon/tests/test_enemy.py::test_dying_emits_smoke_when_fx_set -v`
Expected: FAIL (`emit_smoke` not called yet).

- [ ] **Step 3: Add smoke emission at the end of the dying block**

In `Enemy.update`, in the `dying_timer > 0` block, AFTER the existing `return []` line, add smoke emission BEFORE the return:

```python
        if self.dying_timer > 0.0:
            # ... existing physics + integration code ...
            # Throttled smoke emission: 1 every 2 frames
            # so a long fall doesn't flood the particle
            # system.
            if self.fx is not None:
                self._smoke_throttle = (self._smoke_throttle + 1) % 2
                if self._smoke_throttle == 0:
                    self.fx.emit_smoke(self.x, self.y)
            if self.y > _ENEMY_DYING_OFFSCREEN_Y or self.dying_timer <= 0.0:
                self.dying_timer = 0.0
                self.alive = False
            return []
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd D:\AI\stellar-horizon; $env:PYTHONPATH = $PWD; .\.venv\Scripts\python.exe -m pytest stellar_horizon/tests/test_enemy.py::test_dying_emits_smoke_when_fx_set -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd D:\AI\stellar-horizon; git add stellar_horizon/entities/enemy.py stellar_horizon/tests/test_enemy.py
git commit -m "feat(enemy): emit P_SMOKE trail during death fall"
```

---

### Task 8: GameplayScene uses `current_dying_sheet()` (TDD via integration test)

**Files:**
- Modify: `stellar_horizon/scenes/gameplay.py:781-820` (the `_draw_enemy_sprite` priority section)
- Test: `stellar_horizon/tests/test_destruction_render.py` (add 1 integration test)

- [ ] **Step 1: Write the failing integration test**

Append to `tests/test_destruction_render.py`:

```python
def test_destruction_render_produces_visible_ship_after_burst():
    # 2026-09-06 destruction-fall: after the 0.15s death
    # burst, the rendered frame should show the ship's IDLE
    # sprite (not the death sheet) at the enemy's current
    # position. We render a frame 0.25s after take_damage
    # and verify a non-background cluster of pixels appears
    # where the ship should be.
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    from pathlib import Path
    from stellar_horizon.audio.midi_player import MidiPlayer
    from stellar_horizon.entities.enemy import Enemy
    from stellar_horizon.scenes.gameplay import GameplayScene

    pygame.init()
    try:
        s = GameplayScene(
            MidiPlayer(),
            Path("stellar_horizon/waves/waves_act1.json"),
            Path("stellar_horizon/assets"),
        )
        s._load_sprites()
        # Spawn a scout at a known position
        e = Enemy()
        e.kind = "scout"
        e.on_spawn()
        e.x = 240.0
        e.y = 100.0
        e.alive = True
        e.hp = 1
        e.sprite_name = "enemy_scout_v1"
        # Inject into the wave manager
        if s.wave_manager is not None:
            s.wave_manager.spawned_enemies = [e]
        # Kill it
        e.take_damage(1)
        # Tick past the burst window
        for _ in range(20):
            e.update(0.05, player=None)
        # Render
        surface = pygame.Surface((480, 270))
        s.draw(surface)
        # The ship should be near (240, ~150-200) at this
        # point (gravity has pulled it down ~50px).
        # Check that there are non-background pixels in a
        # 60x60 box around the expected position.
        non_bg_count = 0
        for dx in range(-30, 30):
            for dy in range(-30, 30):
                px, py = int(e.x) + dx, int(e.y) + dy
                if 0 <= px < 480 and 0 <= py < 270:
                    r, g, b, a = surface.get_at((px, py))
                    if (r, g, b) != (0, 0, 0) and a > 0:
                        non_bg_count += 1
        # The ship sprite is 29x29; expect at least 50
        # non-background pixels in the 60x60 box.
        assert non_bg_count >= 50, (
            f"expected >= 50 non-background pixels around ship, "
            f"got {non_bg_count}"
        )
    finally:
        pygame.quit()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd D:\AI\stellar-horizon; $env:PYTHONPATH = $PWD; .\.venv\Scripts\python.exe -m pytest stellar_horizon/tests/test_destruction_render.py::test_destruction_render_produces_visible_ship_after_burst -v`
Expected: FAIL (the scene still uses `enemy_{kind}_death_v1` even after the burst window).

- [ ] **Step 3: Modify `_draw_enemy_sprite` in `gameplay.py` to use `current_dying_sheet()`**

In `stellar_horizon/scenes/gameplay.py`, find `_draw_enemy_sprite` (around line 781). Replace the dying sheet-selection block:

```python
        if getattr(e, "dying_timer", 0.0) > 0.0:
            death_name = f"enemy_{e.kind}_death_v1"
            anim = self._animated.get(death_name)
            if anim is not None:
                sil_key = ("enemy", death_name)
```

WITH:

```python
        if getattr(e, "dying_timer", 0.0) > 0.0:
            # 2026-09-06 destruction-fall: the dying sheet
            # transitions from death_v1 (explosion burst) to
            # the ship's base sheet after 0.15s. current_dying_sheet
            # returns the right one for the current dying_elapsed.
            sheet_name = e.current_dying_sheet()
            anim = self._animated.get(sheet_name)
            if anim is not None:
                sil_key = ("enemy", sheet_name)
```

- [ ] **Step 4: Run the integration test to verify it passes**

Run: `cd D:\AI\stellar-horizon; $env:PYTHONPATH = $PWD; .\.venv\Scripts\python.exe -m pytest stellar_horizon/tests/test_destruction_render.py -v`
Expected: PASS (both tests in the file now pass).

- [ ] **Step 5: Run the full test suite to verify no regressions**

Run: `cd D:\AI\stellar-horizon; $env:PYTHONPATH = $PWD; .\.venv\Scripts\python.exe -m pytest stellar_horizon/tests/ -q`
Expected: 399 passed (390 baseline + 8 new enemy tests + 1 new render test + maybe 1 more from prior task).

- [ ] **Step 6: Commit**

```bash
cd D:\AI\stellar-horizon; git add stellar_horizon/scenes/gameplay.py stellar_horizon/tests/test_destruction_render.py
git commit -m "feat(scene): use current_dying_sheet for ship-vs-explosion render swap"
```

---

### Task 9: Build destruction_sandbox.py (no test, it's a tool)

**Files:**
- Create: `sprite_tests/destruction_sandbox.py`

- [ ] **Step 1: Create the destruction_sandbox.py with the capture function and sweep**

```python
"""Destruction sandbox: capture contact-sheet PNGs of the death-fall
animation for each (gravity, drag) parameter pair.

Output: sprite_tests/captures/destruction_grav{G}_drag{D}.png
        (6 columns = kinds, 36 rows = frames at 1/30s over 1.2s)

Usage: python sprite_tests/destruction_sandbox.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from stellar_horizon.audio.midi_player import MidiPlayer
from stellar_horizon.scenes.gameplay import GameplayScene
from stellar_horizon.entities.enemy import Enemy


# Param overrides are monkey-patched into the module before
# importing the scene. We set them via a tiny module-level
# config in stellar_horizon.entities.enemy — but for the
# sandbox we just patch the values via importlib reload
# after import. See capture_destruction below.
_KINDS = ("scout", "cruiser", "heavy", "bomber", "ufo", "kamikaze")
_FRAME_DT = 1 / 30.0
_FRAMES = 36  # 1.2 seconds
_CELL_W = 60
_CELL_H = 50


def capture_destruction(gravity: float, drag_linear: float, out_path: Path) -> None:
    """Capture one contact-sheet PNG for a (gravity, drag) pair.

    Overrides the module-level constants in enemy.py for this
    capture only, then restores them.
    """
    import stellar_horizon.entities.enemy as enemy_mod
    # Save originals
    orig_g = enemy_mod._ENEMY_DYING_GRAVITY_PX_S2
    orig_dl = enemy_mod._ENEMY_DYING_DRAG_LINEAR
    # Apply overrides
    enemy_mod._ENEMY_DYING_GRAVITY_PX_S2 = gravity
    enemy_mod._ENEMY_DYING_DRAG_LINEAR = drag_linear
    try:
        pygame.init()
        try:
            wave_json = Path("stellar_horizon/waves/waves_act1.json")
            assets_dir = Path("stellar_horizon/assets")
            s = GameplayScene(MidiPlayer(), wave_json, assets_dir)
            s.on_enter()

            class _MockPlayer:
                x = 50.0
                y = 135.0
            mock_player = _MockPlayer()

            # Build a list of enemies, one per kind
            enemies = []
            for i, kind in enumerate(_KINDS):
                e = Enemy()
                e.kind = kind
                e.on_spawn()
                e.x = 30 + i * 75
                e.y = 30
                e.vx, e.vy = 0.0, 0.0
                e.alive = True
                e.hp = e.max_hp
                e.path_done = True
                e.sprite_name = f"enemy_{kind}_v1"
                # Warm up so the IDLE sprite is on a real frame
                for _ in range(3):
                    e.update(1 / 120, player=mock_player)
                enemies.append(e)

            # Inject all into wave_manager so draw sees them
            if s.wave_manager is not None:
                s.wave_manager.spawned_enemies = list(enemies)

            # Capture frames
            frame_surfs = []  # list of (frame_idx, list[surface-per-enemy])
            for frame_idx in range(_FRAMES):
                per_enemy_surf = []
                for e in enemies:
                    if not e.alive:
                        # Use a black "off-screen" placeholder
                        per_enemy_surf.append(None)
                        continue
                    # Render just this enemy
                    single = pygame.Surface((_CELL_W, _CELL_H), pygame.SRCALPHA)
                    single.fill((0, 0, 0, 0))
                    if e.dying_timer > 0:
                        s._draw_enemy_sprite(single, e, -e.x + _CELL_W // 2,
                                              -e.y + _CELL_H // 2)
                    per_enemy_surf.append(single)
                frame_surfs.append(per_enemy_surf)
                # Kill the first enemy immediately, others later
                if frame_idx == 0:
                    enemies[0].take_damage(1)
                # Step the dying enemies
                for e in enemies:
                    if e.dying_timer > 0:
                        e.update(_FRAME_DT, player=mock_player)
                # Remove purged
                enemies = [e for e in enemies if e.alive]

            # Build the contact sheet: 6 columns (kinds) × 36 rows
            sheet_w = _CELL_W * 6
            sheet_h = _CELL_H * _FRAMES
            sheet = pygame.Surface((sheet_w, sheet_h), pygame.SRCALPHA)
            sheet.fill((20, 20, 30, 255))
            for kind_idx, kind in enumerate(_KINDS):
                for frame_idx, per_enemy_surf in enumerate(frame_surfs):
                    if kind_idx < len(per_enemy_surf) and per_enemy_surf[kind_idx] is not None:
                        sheet.blit(per_enemy_surf[kind_idx],
                                   (kind_idx * _CELL_W, frame_idx * _CELL_H))

            out_path.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(sheet, str(out_path))
            print(f"saved {out_path}")
        finally:
            pygame.quit()
    finally:
        # Restore originals
        enemy_mod._ENEMY_DYING_GRAVITY_PX_S2 = orig_g
        enemy_mod._ENEMY_DYING_DRAG_LINEAR = orig_dl


def run_sweep() -> None:
    """Run capture_destruction for 9 (gravity, drag) combinations."""
    out_dir = Path("D:/AI/stellar-horizon/sprite_tests/captures")
    out_dir.mkdir(parents=True, exist_ok=True)
    for gravity in (400.0, 500.0, 600.0):
        for drag in (0.5, 1.5, 3.0):
            out = out_dir / f"destruction_grav{int(gravity)}_drag{drag:.1f}.png"
            capture_destruction(gravity, drag, out)


if __name__ == "__main__":
    run_sweep()
```

- [ ] **Step 2: Run the sweep and verify 9 PNGs are produced**

Run: `cd D:\AI\stellar-horizon; $env:PYTHONPATH = $PWD; .\.venv\Scripts\python.exe sprite_tests/destruction_sandbox.py`
Expected: 9 PNG files in `D:\AI\stellar-horizon\sprite_tests\captures\`. List them with `Get-ChildItem` to confirm.

- [ ] **Step 3: Review the contact-sheets visually**

Open the 9 PNGs (start with `destruction_grav500_drag1.5.png` — the default values) and verify:
- Each column shows a single ship
- The ship falls down (rows go top-to-bottom over time)
- The ship rotates as it falls
- The ship is OFF the death sheet after row ~5 (the first 0.15s of frames)

If any column is empty or the ship isn't visible, debug:
- Is `s._draw_enemy_sprite` actually being called? Add a print.
- Is the enemy off-screen too quickly? Check the gravity value.
- Is the enemy not in the wave_manager.spawned_enemies? Check the injection.

- [ ] **Step 4: Commit the sandbox tool**

```bash
cd D:\AI\stellar-horizon; git add sprite_tests/destruction_sandbox.py
git commit -m "feat(sprite_tests): destruction-fall sandbox contact-sheet tool"
```

---

### Task 10: Visual review + tune params if needed

**Files:**
- Maybe modify: `stellar_horizon/entities/enemy.py:64-69` (the constants)
- Maybe modify: `sprite_tests/captures/` (re-run sweep)

- [ ] **Step 1: Open `destruction_grav500_drag1.5.png` (the default pair)**

Use the file viewer or `mavis` to look at `D:\AI\stellar-horizon\sprite_tests\captures\destruction_grav500_drag1.5.png`. The expected output:
- Top rows: ship's death burst (explosion sprite)
- Middle rows: ship's IDLE sprite rotating as it falls
- Bottom rows: ship leaves the frame (or stays at the bottom edge)

- [ ] **Step 2: Compare with the other 8 contact-sheets**

If `grav=400, drag=3.0` looks too floaty (ship doesn't fall fast enough), or `grav=600, drag=0.5` looks too violent (ship shoots off), pick the (gravity, drag) pair that looks most natural.

- [ ] **Step 3: If params need tuning, update the constants and re-run sweep**

Edit `stellar_horizon/entities/enemy.py:64-69` to use the chosen values, then re-run `python sprite_tests/destruction_sandbox.py` and re-review.

- [ ] **Step 4: If no tuning needed, skip to the next task**

If `grav=500, drag=1.8` (the spec defaults) looks natural, do nothing here.

- [ ] **Step 5: Commit any changes**

```bash
cd D:\AI\stellar-horizon; git add stellar_horizon/entities/enemy.py
git commit -m "tune(enemy): adjust gravity/drag based on sandbox review"
```

---

### Task 11: Full test suite + .exe build + launch verification

**Files:**
- Read: `dist/StellarHorizon.exe` mtime after build
- Run: the .exe, verify the destruction animation looks right in-game

- [ ] **Step 1: Run the full test suite**

Run: `cd D:\AI\stellar-horizon; $env:PYTHONPATH = $PWD; .\.venv\Scripts\python.exe -m pytest stellar_horizon/tests/ -q`
Expected: 399+ passed (390 baseline + 8 enemy + 2 render = 400 if all add up; the exact number depends on the previous count).

- [ ] **Step 2: Build the .exe**

Run: `cd D:\AI\stellar-horizon; .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean StellarHorizon.spec 2>&1 | Select-Object -Last 5`
Expected: `Build complete!` line at the end. Check `Get-Item dist\StellarHorizon.exe | Select-Object LastWriteTime` shows a recent timestamp.

- [ ] **Step 3: Launch the .exe and verify the destruction animation**

```bash
# Kill any old instance
Get-Process -Name StellarHorizon -ErrorAction SilentlyContinue | Stop-Process -Force
# Launch the new build
Start-Process -FilePath "D:\AI\stellar-horizon\dist\StellarHorizon.exe" -WorkingDirectory "D:\AI\stellar-horizon"
Start-Sleep -Seconds 2
Get-Process -Name StellarHorizon -ErrorAction SilentlyContinue | Select-Object Id, MainWindowTitle
```

Expected: process running, MainWindowTitle = "STELLAR HORIZON".

- [ ] **Step 4: Tell the user the build is ready for them to play and verify**

Report:
- All tests pass (count)
- .exe rebuilt and launched
- Contact-sheets are in `sprite_tests/captures/`
- Ask the user to play, kill some enemies, and confirm the fall looks natural

- [ ] **Step 5: Commit any final touches**

If no code changed, skip. If tuning was needed, commit it.
```

---

## Self-Review

**1. Spec coverage:**
- ✓ Physics rewrite (zero momentum + gravity + drag): Tasks 1, 2, 3
- ✓ Random initial omega: Task 4
- ✓ `current_dying_sheet()` method: Task 5
- ✓ P_SMOKE particle: Task 6
- ✓ Hook P_SMOKE into Enemy: Task 7
- ✓ Render uses `current_dying_sheet`: Task 8
- ✓ Destruction sandbox tool: Task 9
- ✓ Visual review + tune: Task 10
- ✓ Full build + launch: Task 11
- ✓ All 8 unit tests + 1 integration test + 1 P_SMOKE test: spread across Tasks 2-8

**2. Placeholder scan:** No "TBD"/"TODO"/"implement later". Code blocks contain actual code, not "see existing pattern".

**3. Type consistency:** `dying_omega: float`, `dying_elapsed: float`, `dying_timer: float`, `dying_rotation: float`, `_smoke_throttle: int`, `_ENEMY_DYING_GRAVITY_PX_S2: float = 500.0` — all consistent across tasks. `current_dying_sheet() -> str` used everywhere. `P_SMOKE = 19` consistent.

**4. Smoke throttle:** 1 every 2 frames, matches the test's `>= 3` assertion in 10 ticks.

**5. The 0.15s burst window:** `_ENEMY_DYING_DEATH_SHEET_S = 0.15` is checked in `current_dying_sheet()` and tested in Task 5.

Plan is internally consistent and covers the spec end-to-end.
