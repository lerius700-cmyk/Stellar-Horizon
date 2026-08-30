# Choreographed Enemy Movement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich the movement of the 6 existing enemy types with 6 new bezier paths, 5 new formations, FTL chain spawns, and rotation-per-wave defaults. No new enemy types, no boss changes, no audio sync.

**Architecture:** Pure additive changes to `bezier_horizontal.py`, `formations_h.py`, and `wave_manager.py`. New `test_choreography.py` file. Update `waves_act1.json` waves 1-5. Zero changes to `enemy.py`, `boss.py`, `player.py`, `audio/`, `scenes/`, or `core/`.

**Tech Stack:** Python 3.11+, pygame 2.6.1, pytest, stdlib only.

---

## Global Constraints

From the spec, project-wide requirements that every task must respect:

- Python ≥ 3.11, Pygame 2.6.1, no numpy/scipy, stdlib only
- Internal resolution 480×270, 120 FPS target, `FIXED_DT = 1/120`
- Commit style: `<type>(<scope>): <subject>`
- 16-bit pixel art + MIDI audio (no changes to audio in this plan)
- All new paths/formations MUST enter and exit off-screen (BezierPath behavior)
- Formation offsets bounded to roughly `[-50, +50]` to avoid clipping
- `chain_count` clamped to 1-5 (silent clamp with log warning if outside)
- The two existing custom paths `ufo_entry` and `kamikaze_dive` MUST stay unchanged
- The two existing custom formations `line_horizontal` and `v_pointing_left` stay unchanged
- All 245 existing tests must continue to pass after the implementation
- Use `python -m stellar_horizon.<module>` for any new CLI scripts (none in this plan)

---

## File Structure

Files that will be created or modified by this plan:

| File | Status | Responsibility |
|---|---|---|
| `stellar_horizon/waves/bezier_horizontal.py` | MODIFY | Add 6 new path functions (sine_bend, figure_eight, boomerang, staircase, loop_horizontal, pull_back) |
| `stellar_horizon/waves/formations_h.py` | MODIFY | Add 5 new formation functions (phalanx_box, swept_wing, train_chain, boomerang_arc, rotating_ring) |
| `stellar_horizon/waves/wave_manager.py` | MODIFY | Register new builders; add `_KIND_DEFAULTS_BY_WAVE` table; add `_KIND_FALLBACK` table; add chain expansion in `_build_enemies` |
| `stellar_horizon/waves/waves_act1.json` | MODIFY | Update waves 1-5 to demonstrate new patterns |
| `stellar_horizon/tests/test_choreography.py` | CREATE | ~19 new tests for paths, formations, defaults, chain expansion, JSON integrity |

No other files modified. `enemy.py`, `boss.py`, `player.py`, `audio/`, `core/`, `scenes/` are NOT touched.

---

## Task 1: Add 6 New Bezier Paths (TDD)

**Files:**
- Modify: `stellar_horizon/waves/bezier_horizontal.py`
- Create: `stellar_horizon/tests/test_choreography.py`

**Interfaces:**
- Consumes: existing `BezierPath`, `HybridPath`, `Point` from `src.movement`
- Produces: 6 new public functions: `path_sine_bend`, `path_figure_eight`, `path_boomerang`, `path_staircase`, `path_loop_horizontal`, `path_pull_back`. Each returns a `BezierPath` (or `HybridPath` for `path_pull_back`).

- [ ] **Step 1: Create test file scaffold**

Create `stellar_horizon/tests/test_choreography.py` with imports and a placeholder test:

```python
"""Tests for choreographed enemy movement (bezier paths, formations, FTL chain, defaults)."""
from __future__ import annotations

import math

import pytest

from stellar_horizon.waves.bezier_horizontal import (
    path_boomerang,
    path_figure_eight,
    path_loop_horizontal,
    path_pull_back,
    path_sine_bend,
    path_staircase,
)
from stellar_horizon.waves.formations_h import (
    boomerang_arc,
    phalanx_box,
    rotating_ring,
    swept_wing,
    train_chain,
)
from stellar_horizon.waves.wave_manager import (
    _KIND_DEFAULTS_BY_WAVE,
    _KIND_FALLBACK,
    _build_enemies,
)
```

- [ ] **Step 2: Write failing test for path_sine_bend**

Append to `test_choreography.py`:

```python
# --- Bezier path tests ---

SIM_DT = 1.0 / 120.0
SIM_FRAMES = 600  # 5 seconds at 120 FPS


def _simulate_path(path, frames: int = SIM_FRAMES, dt: float = SIM_DT) -> list[tuple[float, float]]:
    """Step a Path through `frames` ticks of `dt` seconds. Return list of (x, y)."""
    from src.movement import PathFollower, HybridPath
    if isinstance(path, HybridPath):
        follower = PathFollower(path)
    else:
        from stellar_horizon.waves.wave_manager import _path_to_hybrid
        follower = PathFollower(_path_to_hybrid(path))
    points = []
    for _ in range(frames):
        pos, _ = follower.update(dt)
        points.append((pos.x, pos.y))
    return points


def _is_off_screen(point: tuple[float, float], margin: float = 30.0) -> bool:
    x, y = point
    return x < -margin or x > 480 + margin or y < -margin or y > 270 + margin


def test_sine_bend_exits_off_screen():
    path = path_sine_bend()
    points = _simulate_path(path)
    assert _is_off_screen(points[-1]), f"sine_bend ended at {points[-1]}"
    assert _is_off_screen(points[0]), f"sine_bend started at {points[0]}"


def test_sine_bend_oscillates_vertically():
    """sine_bend should have Y values that swing both above and below the start Y."""
    path = path_sine_bend()
    points = _simulate_path(path, frames=300)  # 2.5s sample
    ys = [p[1] for p in points]
    y_range = max(ys) - min(ys)
    assert y_range > 30.0, f"sine_bend Y range was only {y_range}"


def test_figure_eight_exits_off_screen():
    path = path_figure_eight()
    points = _simulate_path(path)
    assert _is_off_screen(points[-1])
    assert _is_off_screen(points[0])


def test_figure_eight_crosses_midline_twice():
    """A figure-8 should cross the screen vertical midline multiple times."""
    path = path_figure_eight()
    points = _simulate_path(path, frames=400)
    crossings = 0
    for i in range(1, len(points)):
        if (points[i][0] - 240) * (points[i - 1][0] - 240) < 0:
            crossings += 1
    assert crossings >= 2, f"figure_eight only crossed midline {crossings} times"


def test_boomerang_exits_off_screen():
    path = path_boomerang()
    points = _simulate_path(path)
    assert _is_off_screen(points[-1])
    assert _is_off_screen(points[0])


def test_boomerang_returns_to_start_side():
    """boomerang should exit on the SAME side it entered."""
    path = path_boomerang()
    points = _simulate_path(path)
    # If it entered from the right, it should exit to the right
    start_x = points[0][0]
    end_x = points[-1][0]
    assert (start_x > 240) == (end_x > 240), (
        f"boomerang started at x={start_x}, ended at x={end_x} (different sides)"
    )


def test_staircase_exits_off_screen():
    path = path_staircase()
    points = _simulate_path(path)
    assert _is_off_screen(points[-1])
    assert _is_off_screen(points[0])


def test_staircase_descends_monotonically():
    """staircase should generally descend (or stay level) — not climb back up."""
    path = path_staircase()
    points = _simulate_path(path, frames=300)
    # Find the Y of each 30-frame bucket; compare to the previous
    for i in range(30, len(points), 30):
        y_now = points[i][1]
        y_prev = points[i - 30][1]
        # Allow small upward jitter (< 5 px) but no big climb
        assert y_now <= y_prev + 5, (
            f"staircase climbed from y={y_prev} to y={y_now} at frame {i}"
        )


def test_loop_horizontal_exits_off_screen():
    path = path_loop_horizontal()
    points = _simulate_path(path)
    assert _is_off_screen(points[-1])
    assert _is_off_screen(points[0])


def test_loop_horizontal_does_a_full_loop():
    """loop_horizontal should make a closed loop. Y should return to start after going around."""
    path = path_loop_horizontal()
    points = _simulate_path(path, frames=400)
    # Check that during the middle of the simulation, Y has gone both well above and well below start
    mid_start = 100
    mid_end = 300
    mid_ys = [p[1] for p in points[mid_start:mid_end]]
    y_start = points[0][1]
    above = any(y < y_start - 20 for y in mid_ys)
    below = any(y > y_start + 20 for y in mid_ys)
    assert above and below, "loop_horizontal did not deviate vertically from start"


def test_pull_back_exits_off_screen():
    path = path_pull_back()
    points = _simulate_path(path)
    assert _is_off_screen(points[-1])
    assert _is_off_screen(points[0])


def test_pull_back_returns_to_enemy_side():
    """pull_back should leave heading toward the enemy (right side, > 240)."""
    path = path_pull_back()
    points = _simulate_path(path)
    end_x = points[-1][0]
    assert end_x > 200, f"pull_back ended at x={end_x} (expected to return toward right side)"
```

- [ ] **Step 3: Run tests, verify they fail (imports missing)**

Run: `python -m pytest stellar_horizon/tests/test_choreography.py -v`
Expected: ALL path tests FAIL with `ImportError: cannot import name 'path_sine_bend' from 'stellar_horizon.waves.bezier_horizontal'`

- [ ] **Step 4: Implement path_sine_bend in bezier_horizontal.py**

Open `stellar_horizon/waves/bezier_horizontal.py` and append the following at the end (after the existing functions but before any `if __name__` block):

```python
def path_sine_bend() -> BezierPath:
    """Long smooth sinusoid. Enters from off-screen right, glides left in a wave."""
    return BezierPath(
        p0=Point(490, 130),
        p1=Point(360, 60),
        p2=Point(120, 200),
        p3=Point(-20, 135),
    )


def path_figure_eight() -> HybridPath:
    """Horizontal figure-8: enters from right, crosses midline, loops, exits left."""
    from src.movement import WaypointPath
    return HybridPath.from_segments([
        BezierPath(
            p0=Point(490, 135),
            p1=Point(360, 80),
            p2=Point(120, 190),
            p3=Point(240, 135),
        ),
        WaypointPath(
            [Point(240, 135), Point(360, 80), Point(490, 135), Point(360, 190), Point(120, 135), Point(-20, 135)],
            speed_px_s=110.0,
        ),
    ])


def path_boomerang() -> HybridPath:
    """Boomerang: enters from right, makes a U-turn mid-screen, exits back to the right."""
    from src.movement import WaypointPath
    return HybridPath.from_segments([
        BezierPath(
            p0=Point(490, 135),
            p1=Point(380, 100),
            p2=Point(220, 200),
            p3=Point(120, 135),
        ),
        WaypointPath(
            [Point(120, 135), Point(220, 80), Point(380, 100), Point(490, 135), Point(540, 200)],
            speed_px_s=120.0,
        ),
    ])


def path_staircase() -> HybridPath:
    """Staircase: descends in 3 steps. Predictable, readable for heavy enemies."""
    from src.movement import WaypointPath
    return HybridPath.from_segments([
        BezierPath(
            p0=Point(490, 30),
            p1=Point(360, 60),
            p2=Point(280, 100),
            p3=Point(300, 110),
        ),
        WaypointPath(
            [Point(300, 110), Point(220, 110), Point(200, 150), Point(220, 180), Point(150, 200), Point(80, 220), Point(-20, 220)],
            speed_px_s=90.0,
        ),
    ])


def path_loop_horizontal() -> HybridPath:
    """Single closed loop: enters from right, does one full circle in the center, exits left."""
    from src.movement import WaypointPath
    return HybridPath.from_segments([
        BezierPath(
            p0=Point(490, 135),
            p1=Point(420, 100),
            p2=Point(380, 130),
            p3=Point(340, 135),
        ),
        WaypointPath(
            # Circle: 8 waypoints forming a closed loop around (240, 135), radius ~50
            [Point(340, 135), Point(290, 90), Point(240, 85), Point(190, 90),
             Point(140, 135), Point(190, 180), Point(240, 185), Point(290, 180),
             Point(340, 135), Point(290, 90), Point(240, 85), Point(190, 90),
             Point(140, 135), Point(100, 135), Point(60, 135), Point(-20, 135)],
            speed_px_s=100.0,
        ),
    ])


def path_pull_back() -> HybridPath:
    """Pull-back: enters from right, retreats halfway, comes back hard toward the player."""
    from src.movement import WaypointPath
    return HybridPath.from_segments([
        BezierPath(
            p0=Point(490, 135),
            p1=Point(380, 110),
            p2=Point(300, 150),
            p3=Point(380, 145),
        ),
        WaypointPath(
            [Point(380, 145), Point(420, 130), Point(490, 125), Point(540, 130)],
            speed_px_s=180.0,
        ),
    ])
```

- [ ] **Step 5: Run tests, verify they pass**

Run: `python -m pytest stellar_horizon/tests/test_choreography.py -v -k "sine_bend or figure_eight or boomerang or staircase or loop_horizontal or pull_back"`
Expected: 11 path tests PASS

- [ ] **Step 6: Commit**

```bash
cd D:\AI\stellar-horizon
git add stellar_horizon/waves/bezier_horizontal.py stellar_horizon/tests/test_choreography.py
git commit -m "feat(waves): add 6 new bezier paths (sine_bend, figure_eight, boomerang, staircase, loop_horizontal, pull_back)"
```

---

## Task 2: Add 5 New Formations (TDD)

**Files:**
- Modify: `stellar_horizon/waves/formations_h.py`
- Modify: `stellar_horizon/tests/test_choreography.py`

**Interfaces:**
- Consumes: existing `FlightFormation` from `src.movement` (only for static formations); dynamic formations need their own update method
- Produces: 5 new public functions: `phalanx_box`, `swept_wing`, `train_chain`, `boomerang_arc`, `rotating_ring`. Each returns `list[tuple[float, float]]`. Dynamic formations also expose a `set_phase(phase_s)` or similar method.

- [ ] **Step 1: Write failing test for phalanx_box (static formation)**

Append to `test_choreography.py`:

```python
# --- Formation tests ---

def test_phalanx_box_3x3_returns_9_offsets():
    offsets = phalanx_box(count=9, spacing=16.0)
    assert len(offsets) == 9
    for dx, dy in offsets:
        assert -50.0 <= dx <= 50.0
        assert -50.0 <= dy <= 50.0


def test_phalanx_box_4x4_returns_16_offsets():
    offsets = phalanx_box(count=16, spacing=14.0)
    assert len(offsets) == 16


def test_phalanx_box_clamps_to_count():
    """If count=7, phalanx_box should still return 7 offsets (not 9 or 16)."""
    offsets = phalanx_box(count=7, spacing=16.0)
    assert len(offsets) == 7


def test_swept_wing_5_returns_5_offsets():
    offsets = swept_wing(count=5, spacing=20.0)
    assert len(offsets) == 5
    for dx, dy in offsets:
        assert -80.0 <= dx <= 80.0
        assert -40.0 <= dy <= 40.0


def test_swept_wing_10_returns_10_offsets():
    offsets = swept_wing(count=10, spacing=18.0)
    assert len(offsets) == 10


def test_train_chain_5_returns_5_offsets():
    offsets = train_chain(count=5, spacing=20.0)
    assert len(offsets) == 5
    # All offsets should be roughly collinear (same y)
    ys = [dy for dx, dy in offsets]
    assert max(ys) - min(ys) < 5.0, f"train_chain not collinear: ys={ys}"


def test_train_chain_offsets_are_in_front_of_leader():
    """In a chain, the leader is at the front (most negative X) and followers trail behind."""
    offsets = train_chain(count=5, spacing=20.0)
    xs = [dx for dx, dy in offsets]
    # Leader should be the leftmost (most negative X) since they move right-to-left
    assert xs[0] == min(xs), f"train_chain leader not at front: xs={xs}"
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `python -m pytest stellar_horizon/tests/test_choreography.py -v -k "phalanx or swept_wing or train_chain"`
Expected: 7 static formation tests FAIL with `ImportError`

- [ ] **Step 3: Implement static formations in formations_h.py**

Open `stellar_horizon/waves/formations_h.py` and append at the end:

```python
def phalanx_box(count: int = 9, spacing: float = 16.0) -> list[tuple[float, float]]:
    """Solid N×N-ish block formation. For count=9 produces 3×3; for count=16 produces 4×4; etc.

    Spacing is the side length of each cell in the block.
    """
    if count <= 0:
        return []
    side = max(1, math.ceil(math.sqrt(count)))
    # Build a side×side grid centered at (0, 0), then take the first `count` cells
    # in a top-down, left-to-right order so the "front" (negative X) is filled first.
    offsets: list[tuple[float, float]] = []
    half = (side - 1) * spacing / 2.0
    for row in range(side):
        for col in range(side):
            dx = -half + col * spacing
            dy = -half + row * spacing
            offsets.append((dx, dy))
            if len(offsets) >= count:
                return offsets
    return offsets


def swept_wing(count: int = 5, spacing: float = 20.0) -> list[tuple[float, float]]:
    """Delta-wing (stretched V). Wing tips trail behind the apex.

    The apex is at the front (most negative X). The wing tips spread back and outward.
    """
    if count == 1:
        return [(0.0, 0.0)]
    half = (count - 1) / 2.0
    return [
        (-spacing * (1.5 - abs(i - half) * 0.3), spacing * (i - half))
        for i in range(count)
    ]


def train_chain(count: int = 5, spacing: float = 20.0) -> list[tuple[float, float]]:
    """Single-file line, all on the same Y. The first enemy (index 0) is the leader.

    Used with FTL chain spawns: the leader is at the front (most negative X),
    and followers trail behind at +spacing, +2*spacing, etc.
    """
    if count <= 0:
        return []
    if count == 1:
        return [(0.0, 0.0)]
    return [(-(count - 1) * spacing + i * spacing, 0.0) for i in range(count)]
```

You will also need to add `import math` at the top of `formations_h.py` if it isn't already imported (check first).

- [ ] **Step 4: Run static formation tests, verify they pass**

Run: `python -m pytest stellar_horizon/tests/test_choreography.py -v -k "phalanx or swept_wing or train_chain"`
Expected: 7 static formation tests PASS

- [ ] **Step 5: Write failing test for boomerang_arc and rotating_ring (dynamic formations)**

Append to `test_choreography.py`:

```python
def test_boomerang_arc_returns_n_offsets():
    offsets = boomerang_arc(count=5, spacing=18.0)
    assert len(offsets) == 5


def test_boomerang_arc_phase_changes_offsets():
    """boomerang_arc is dynamic — calling its update should change the offsets."""
    obj = boomerang_arc(count=5, spacing=18.0)
    initial = obj.offsets()
    obj.update(0.0)
    after_zero = obj.offsets()
    obj.update(1.0)
    after_one_sec = obj.offsets()
    # Offsets should differ between phase=0 and phase=1s
    assert initial != after_one_sec or after_zero != after_one_sec, (
        "boomerang_arc did not change offsets over time"
    )


def test_rotating_ring_returns_n_offsets():
    obj = rotating_ring(count=6, spacing=20.0)
    assert len(obj.offsets()) == 6


def test_rotating_ring_phase_rotates_offsets():
    """rotating_ring should rotate the offsets over time (angle changes)."""
    obj = rotating_ring(count=6, spacing=20.0)
    initial = obj.offsets()
    obj.update(0.0)
    obj.update(0.5)  # 0.5s of rotation
    after_half = obj.offsets()
    # The angles should differ, so offsets should differ
    assert initial != after_half, "rotating_ring did not rotate offsets over 0.5s"
```

- [ ] **Step 6: Run dynamic formation tests, verify they fail**

Run: `python -m pytest stellar_horizon/tests/test_choreography.py -v -k "boomerang_arc or rotating_ring"`
Expected: 4 dynamic formation tests FAIL

- [ ] **Step 7: Implement dynamic formations in formations_h.py**

Append to `formations_h.py`:

```python
import math


class _DynamicFormation:
    """Base class for formations whose offsets change over time.

    Subclasses set `self._compute(phase_s)` to return a list of (dx, dy) offsets.
    """

    def __init__(self, count: int, spacing: float) -> None:
        self._count = count
        self._spacing = spacing
        self._phase: float = 0.0

    def update(self, dt: float) -> None:
        self._phase += dt

    def offsets(self) -> list[tuple[float, float]]:
        return self._compute(self._phase)


class BoomerangArcFormation(_DynamicFormation):
    """A curved line that rotates around the leader slot during flight.

    The leader is at offset (0, 0). Other slots orbit it at a constant radius,
    with their phase offset shifting over time.
    """

    def _compute(self, phase_s: float) -> list[tuple[float, float]]:
        if self._count == 1:
            return [(0.0, 0.0)]
        result: list[tuple[float, float]] = [(0.0, 0.0)]
        for i in range(1, self._count):
            # i-th slot orbits at radius (i * spacing), starting at angle 90° (above leader)
            # and rotating over time
            angle = math.pi / 2 + (i * 0.4) + phase_s * 1.5
            dx = math.cos(angle) * (i * self._spacing * 0.5)
            dy = math.sin(angle) * (i * self._spacing * 0.5)
            result.append((dx, dy))
        return result


def boomerang_arc(count: int = 5, spacing: float = 18.0) -> BoomerangArcFormation:
    """Dynamic formation: curved arc that rotates around the leader slot over time.

    Returns a BoomerangArcFormation instance with `.update(dt)` and `.offsets()` methods.
    """
    return BoomerangArcFormation(count=count, spacing=spacing)


class RotatingRingFormation(_DynamicFormation):
    """A ring of N enemies that spins around its center.

    All slots are at the same radius, evenly spaced, and the whole ring rotates
    uniformly with time.
    """

    def _init_radius(self) -> float:
        return self._spacing * 1.5

    def _compute(self, phase_s: float) -> list[tuple[float, float]]:
        if self._count <= 0:
            return []
        radius = self._init_radius()
        return [
            (
                math.cos(2 * math.pi * i / self._count + phase_s * 1.0) * radius,
                math.sin(2 * math.pi * i / self._count + phase_s * 1.0) * radius,
            )
            for i in range(self._count)
        ]


def rotating_ring(count: int = 6, spacing: float = 20.0) -> RotatingRingFormation:
    """Dynamic formation: ring of N enemies that rotates around its center over time.

    Returns a RotatingRingFormation instance with `.update(dt)` and `.offsets()` methods.
    """
    return RotatingRingFormation(count=count, spacing=spacing)
```

Note: dynamic formations return an object, not a list. The wave manager must call `.offsets()` to get the current positions and `.update(dt)` per frame.

- [ ] **Step 8: Run all formation tests, verify they pass**

Run: `python -m pytest stellar_horizon/tests/test_choreography.py -v -k "phalanx or swept_wing or train_chain or boomerang_arc or rotating_ring"`
Expected: 11 formation tests PASS

- [ ] **Step 9: Commit**

```bash
cd D:\AI\stellar-horizon
git add stellar_horizon/waves/formations_h.py stellar_horizon/tests/test_choreography.py
git commit -m "feat(waves): add 5 new formations (phalanx_box, swept_wing, train_chain, boomerang_arc, rotating_ring)"
```

---

## Task 3: Register New Builders in wave_manager.py

**Files:**
- Modify: `stellar_horizon/waves/wave_manager.py`
- Modify: `stellar_horizon/tests/test_choreography.py`

**Interfaces:**
- Consumes: the 6 new paths and 5 new formations from Tasks 1-2
- Produces: extended `_PATH_BUILDERS` and `_FORMATION_BUILDERS` dicts in `wave_manager.py` that include the new names

- [ ] **Step 1: Write failing test for new builders**

Append to `test_choreography.py`:

```python
# --- Builder registration tests ---

def test_path_builders_include_new_paths():
    from stellar_horizon.waves.wave_manager import _PATH_BUILDERS
    for name in ["sine_bend", "figure_eight", "boomerang", "staircase", "loop_horizontal", "pull_back"]:
        assert name in _PATH_BUILDERS, f"path {name} not registered"


def test_formation_builders_include_new_formations():
    from stellar_horizon.waves.wave_manager import _FORMATION_BUILDERS
    for name in ["phalanx_box", "swept_wing", "train_chain", "boomerang_arc", "rotating_ring"]:
        assert name in _FORMATION_BUILDERS, f"formation {name} not registered"


def test_formation_builders_dynamic_have_update():
    """Dynamic formation builders should return objects with an update method."""
    from stellar_horizon.waves.wave_manager import _FORMATION_BUILDERS
    obj = _FORMATION_BUILDERS["boomerang_arc"](5, 18.0)
    assert hasattr(obj, "update"), "boomerang_arc result missing update()"
    assert hasattr(obj, "offsets"), "boomerang_arc result missing offsets()"


def test_path_builder_returns_path_object():
    from stellar_horizon.waves.wave_manager import _PATH_BUILDERS
    from src.movement import HybridPath
    path = _PATH_BUILDERS["sine_bend"]({})
    assert isinstance(path, HybridPath), f"sine_bend did not return HybridPath, got {type(path)}"
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `python -m pytest stellar_horizon/tests/test_choreography.py -v -k "builders_include or builders_dynamic or path_builder_returns"`
Expected: 4 builder tests FAIL

- [ ] **Step 3: Update _PATH_BUILDERS in wave_manager.py**

Open `stellar_horizon/waves/wave_manager.py` and update the `_PATH_BUILDERS` dict to include the new paths:

```python
_PATH_BUILDERS = {
    "s_right_to_left": lambda kw: path_s_right_to_left(y_offset=kw.get("path_y_offset", 0)),
    "top_dive":         lambda kw: path_top_dive(side=kw.get("path_side", "right")),
    "zigzag_exit_top":  lambda kw: path_zigzag_exit_top(),
    "boss_entry":       lambda kw: path_boss_entry(),
    "ufo_entry":        lambda kw: path_ufo_entry(y_offset=kw.get("path_y_offset", 0)),
    "kamikaze_dive":    lambda kw: path_kamikaze_dive(y_offset=kw.get("path_y_offset", 0)),
    # New paths (Task 1)
    "sine_bend":        lambda kw: path_sine_bend(),
    "figure_eight":     lambda kw: path_figure_eight(),
    "boomerang":        lambda kw: path_boomerang(),
    "staircase":        lambda kw: path_staircase(),
    "loop_horizontal":  lambda kw: path_loop_horizontal(),
    "pull_back":        lambda kw: path_pull_back(),
}
```

Update the import statement at the top of the file to include the new path functions:

```python
from stellar_horizon.waves.bezier_horizontal import (
    path_boss_entry,
    path_boomerang,
    path_figure_eight,
    path_kamikaze_dive,
    path_loop_horizontal,
    path_pull_back,
    path_s_right_to_left,
    path_sine_bend,
    path_staircase,
    path_top_dive,
    path_ufo_entry,
    path_zigzag_exit_top,
)
```

- [ ] **Step 4: Update _FORMATION_BUILDERS in wave_manager.py**

Update the `_FORMATION_BUILDERS` dict:

```python
_FORMATION_BUILDERS = {
    "v_pointing_left":       lambda count, spacing: v_pointing_left(count, spacing),
    "line_horizontal":       lambda count, spacing: line_horizontal(count, spacing),
    "diamond_pointing_left": lambda count, spacing: diamond_pointing_left(count, spacing),
    "wedge_pointing_left":   lambda count, spacing: wedge_pointing_left(count, spacing),
    # New formations (Task 2)
    "phalanx_box":           lambda count, spacing: phalanx_box(count, spacing),
    "swept_wing":            lambda count, spacing: swept_wing(count, spacing),
    "train_chain":           lambda count, spacing: train_chain(count, spacing),
    "boomerang_arc":         lambda count, spacing: boomerang_arc(count, spacing),
    "rotating_ring":         lambda count, spacing: rotating_ring(count, spacing),
}
```

Update the import from `formations_h`:

```python
from stellar_horizon.waves.formations_h import (
    boomerang_arc,
    diamond_pointing_left,
    line_horizontal,
    phalanx_box,
    rotating_ring,
    swept_wing,
    train_chain,
    v_pointing_left,
    wedge_pointing_left,
)
```

- [ ] **Step 5: Run tests, verify they pass**

Run: `python -m pytest stellar_horizon/tests/test_choreography.py -v -k "builders_include or builders_dynamic or path_builder_returns"`
Expected: 4 builder tests PASS

- [ ] **Step 6: Commit**

```bash
cd D:\AI\stellar-horizon
git add stellar_horizon/waves/wave_manager.py stellar_horizon/tests/test_choreography.py
git commit -m "feat(waves): register 6 new paths and 5 new formations in wave_manager builders"
```

---

## Task 4: Add _KIND_DEFAULTS_BY_WAVE and Defaults Lookup

**Files:**
- Modify: `stellar_horizon/waves/wave_manager.py`
- Modify: `stellar_horizon/tests/test_choreography.py`

**Interfaces:**
- Consumes: `EnemyKind` enum and existing path/formation names
- Produces: a module-level `_KIND_DEFAULTS_BY_WAVE: list[dict[EnemyKind, dict]]` (length 5) and a `_KIND_FALLBACK: dict[EnemyKind, dict]` for safety

- [ ] **Step 1: Write failing test for defaults table**

Append to `test_choreography.py`:

```python
# --- Defaults table tests ---

def test_kind_defaults_by_wave_has_5_entries():
    assert len(_KIND_DEFAULTS_BY_WAVE) == 5, (
        f"_KIND_DEFAULTS_BY_WAVE should have 5 wave entries, got {len(_KIND_DEFAULTS_BY_WAVE)}"
    )


def test_kind_defaults_by_wave_covers_all_kinds():
    from stellar_horizon.entities.enemy import EnemyKind
    expected_kinds = {EnemyKind.SCOUT, EnemyKind.CRUISER, EnemyKind.HEAVY,
                      EnemyKind.BOMBER, EnemyKind.UFO, EnemyKind.KAMIKAZE}
    for i, wave_defaults in enumerate(_KIND_DEFAULTS_BY_WAVE):
        actual_kinds = set(wave_defaults.keys())
        assert expected_kinds.issubset(actual_kinds), (
            f"wave {i} defaults missing kinds: {expected_kinds - actual_kinds}"
        )


def test_kind_defaults_use_valid_path_and_formation_names():
    from stellar_horizon.waves.wave_manager import _PATH_BUILDERS, _FORMATION_BUILDERS
    for i, wave_defaults in enumerate(_KIND_DEFAULTS_BY_WAVE):
        for kind, cfg in wave_defaults.items():
            path = cfg.get("path")
            formation = cfg.get("formation")
            assert path in _PATH_BUILDERS, (
                f"wave {i}, kind {kind}: path '{path}' not in _PATH_BUILDERS"
            )
            assert formation in _FORMATION_BUILDERS, (
                f"wave {i}, kind {kind}: formation '{formation}' not in _FORMATION_BUILDERS"
            )


def test_kind_fallback_has_all_kinds():
    from stellar_horizon.entities.enemy import EnemyKind
    expected_kinds = {EnemyKind.SCOUT, EnemyKind.CRUISER, EnemyKind.HEAVY,
                      EnemyKind.BOMBER, EnemyKind.UFO, EnemyKind.KAMIKAZE}
    assert expected_kinds.issubset(set(_KIND_FALLBACK.keys()))


def test_kind_fallback_uses_valid_names():
    from stellar_horizon.waves.wave_manager import _PATH_BUILDERS, _FORMATION_BUILDERS
    for kind, cfg in _KIND_FALLBACK.items():
        assert cfg["path"] in _PATH_BUILDERS, f"fallback for {kind} has invalid path"
        assert cfg["formation"] in _FORMATION_BUILDERS, f"fallback for {kind} has invalid formation"
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `python -m pytest stellar_horizon/tests/test_choreography.py -v -k "kind_defaults or kind_fallback"`
Expected: 5 tests FAIL with `NameError: name '_KIND_DEFAULTS_BY_WAVE' is not defined`

- [ ] **Step 3: Add _KIND_DEFAULTS_BY_WAVE and _KIND_FALLBACK to wave_manager.py**

Open `stellar_horizon/waves/wave_manager.py` and add (near the top, after the other module-level constants):

```python
# Default movement per enemy kind per wave (length 5: waves 1-5).
# When a wave JSON spawn doesn't specify path/formation, the defaults are used.
# UFO and KAMIKAZE keep their custom paths (ufo_entry, kamikaze_dive) per design spec.
_KIND_DEFAULTS_BY_WAVE: list[dict[str, dict]] = [
    # Wave 1 — intro
    {
        EnemyKind.SCOUT:    {"path": "sine_bend",         "formation": "line_horizontal"},
        EnemyKind.CRUISER:  {"path": "s_right_to_left",   "formation": "boomerang_arc"},
        EnemyKind.HEAVY:    {"path": "staircase",         "formation": "phalanx_box"},
        EnemyKind.BOMBER:   {"path": "s_right_to_left",   "formation": "train_chain"},
        EnemyKind.UFO:      {"path": "ufo_entry",         "formation": "line_horizontal"},
        EnemyKind.KAMIKAZE: {"path": "kamikaze_dive",     "formation": "v_pointing_left"},
    },
    # Wave 2 — scouts + cruisers
    {
        EnemyKind.SCOUT:    {"path": "figure_eight",      "formation": "line_horizontal"},
        EnemyKind.CRUISER:  {"path": "s_right_to_left",   "formation": "boomerang_arc"},
        EnemyKind.HEAVY:    {"path": "staircase",         "formation": "phalanx_box"},
        EnemyKind.BOMBER:   {"path": "s_right_to_left",   "formation": "train_chain"},
        EnemyKind.UFO:      {"path": "ufo_entry",         "formation": "line_horizontal"},
        EnemyKind.KAMIKAZE: {"path": "kamikaze_dive",     "formation": "v_pointing_left"},
    },
    # Wave 3 — heavies join
    {
        EnemyKind.SCOUT:    {"path": "boomerang",         "formation": "v_pointing_left"},
        EnemyKind.CRUISER:  {"path": "sine_bend",         "formation": "boomerang_arc"},
        EnemyKind.HEAVY:    {"path": "s_right_to_left",   "formation": "phalanx_box"},
        EnemyKind.BOMBER:   {"path": "s_right_to_left",   "formation": "train_chain"},
        EnemyKind.UFO:      {"path": "ufo_entry",         "formation": "line_horizontal"},
        EnemyKind.KAMIKAZE: {"path": "kamikaze_dive",     "formation": "v_pointing_left"},
    },
    # Wave 4 — bombers introduced
    {
        EnemyKind.SCOUT:    {"path": "sine_bend",         "formation": "v_pointing_left"},
        EnemyKind.CRUISER:  {"path": "s_right_to_left",   "formation": "swept_wing"},
        EnemyKind.HEAVY:    {"path": "staircase",         "formation": "phalanx_box"},
        EnemyKind.BOMBER:   {"path": "s_right_to_left",   "formation": "swept_wing"},
        EnemyKind.UFO:      {"path": "ufo_entry",         "formation": "line_horizontal"},
        EnemyKind.KAMIKAZE: {"path": "kamikaze_dive",     "formation": "v_pointing_left"},
    },
    # Wave 5 — UFO + kamikaze
    {
        EnemyKind.SCOUT:    {"path": "figure_eight",      "formation": "line_horizontal"},
        EnemyKind.CRUISER:  {"path": "sine_bend",         "formation": "boomerang_arc"},
        EnemyKind.HEAVY:    {"path": "s_right_to_left",   "formation": "phalanx_box"},
        EnemyKind.BOMBER:   {"path": "s_right_to_left",   "formation": "train_chain"},
        EnemyKind.UFO:      {"path": "ufo_entry",         "formation": "line_horizontal"},
        EnemyKind.KAMIKAZE: {"path": "kamikaze_dive",     "formation": "v_pointing_left"},
    },
]

# Fallback used when a kind has no entry in the wave's defaults (e.g. future kind added).
_KIND_FALLBACK: dict[str, dict] = {
    EnemyKind.SCOUT:    {"path": "s_right_to_left", "formation": "line_horizontal"},
    EnemyKind.CRUISER:  {"path": "s_right_to_left", "formation": "v_pointing_left"},
    EnemyKind.HEAVY:    {"path": "s_right_to_left", "formation": "diamond_pointing_left"},
    EnemyKind.BOMBER:   {"path": "s_right_to_left", "formation": "line_horizontal"},
    EnemyKind.UFO:      {"path": "ufo_entry",       "formation": "line_horizontal"},
    EnemyKind.KAMIKAZE: {"path": "kamikaze_dive",   "formation": "v_pointing_left"},
}
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `python -m pytest stellar_horizon/tests/test_choreography.py -v -k "kind_defaults or kind_fallback"`
Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
cd D:\AI\stellar-horizon
git add stellar_horizon/waves/wave_manager.py stellar_horizon/tests/test_choreography.py
git commit -m "feat(waves): add _KIND_DEFAULTS_BY_WAVE rotation table and _KIND_FALLBACK"
```

---

## Task 5: FTL Chain Expansion in `_build_enemies`

**Files:**
- Modify: `stellar_horizon/waves/wave_manager.py`
- Modify: `stellar_horizon/tests/test_choreography.py`

**Interfaces:**
- Consumes: a spawn dict that may include `chain_count: int` and `chain_delay_s: float`
- Produces: expanded enemies list. If `chain_count >= 2`, the spawn expands to N enemies with progressive delays (`delay_s + k * chain_delay_s`)

- [ ] **Step 1: Write failing test for chain expansion**

Append to `test_choreography.py`:

```python
# --- Chain expansion tests ---

def test_chain_expansion_creates_n_enemies():
    spawn = {
        "delay_s": 5.0,
        "formation": "train_chain",
        "formation_count": 1,
        "enemy_kind": "bomber",
        "path": "s_right_to_left",
        "chain_count": 3,
        "chain_delay_s": 0.4,
    }
    enemies = _build_enemies(spawn)
    assert len(enemies) == 3, f"chain_count=3 should produce 3 enemies, got {len(enemies)}"


def test_chain_expansion_progressive_delays():
    """The chain expansion should set progressive delays in the spawn_queue.

    The _build_enemies function returns just the Enemy list, so we test the delay
    through WaveManager.spawn_queue.
    """
    import tempfile
    from pathlib import Path
    from stellar_horizon.waves.wave_manager import WaveManager
    json_content = """{
        "act": 1, "act_name": "Test", "background": "act1_asteroid_belt",
        "midi_track": "act1.mid", "boss": null,
        "waves": [{
            "id": "w1", "duration_s": 20.0,
            "spawns": [{
                "delay_s": 5.0,
                "formation": "train_chain", "formation_count": 1,
                "enemy_kind": "bomber", "path": "s_right_to_left",
                "chain_count": 3, "chain_delay_s": 0.4
            }]
        }]
    }"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json_content)
        f.flush()
        wm = WaveManager(Path(f.name))
        wm.begin()
        delays = [t for t, _ in wm.spawn_queue]
        # Expect: 5.0, 5.4, 5.8 (with small float tolerance)
        assert len(delays) == 3, f"expected 3 spawn times, got {len(delays)}"
        assert abs(delays[0] - 5.0) < 0.01
        assert abs(delays[1] - 5.4) < 0.01
        assert abs(delays[2] - 5.8) < 0.01


def test_chain_expansion_clamps_to_max_5():
    spawn = {
        "delay_s": 5.0, "formation": "train_chain", "formation_count": 1,
        "enemy_kind": "bomber", "path": "s_right_to_left",
        "chain_count": 10,  # over the cap
    }
    enemies = _build_enemies(spawn)
    assert len(enemies) == 5, f"chain_count=10 should clamp to 5, got {len(enemies)}"


def test_no_chain_count_means_single_enemy():
    spawn = {
        "delay_s": 5.0, "formation": "line_horizontal", "formation_count": 3,
        "enemy_kind": "scout", "path": "s_right_to_left",
    }
    enemies = _build_enemies(spawn)
    assert len(enemies) == 3, f"no chain_count should produce formation_count enemies, got {len(enemies)}"


def test_chain_count_1_means_single_enemy():
    spawn = {
        "delay_s": 5.0, "formation": "train_chain", "formation_count": 1,
        "enemy_kind": "bomber", "path": "s_right_to_left",
        "chain_count": 1, "chain_delay_s": 0.4,
    }
    enemies = _build_enemies(spawn)
    assert len(enemies) == 1
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `python -m pytest stellar_horizon/tests/test_choreography.py -v -k "chain_expansion or no_chain_count or chain_count_1"`
Expected: 5 tests FAIL (chain_count not handled, all enemies same delay)

- [ ] **Step 3: Add chain expansion to wave_manager.py**

In `wave_manager.py`, modify `_build_enemies` to expand a single spawn into N enemies when `chain_count >= 2`. Also modify the `begin()` method to apply chain expansion to the spawn queue.

Update `_build_enemies`:

```python
def _build_enemies(spawn: dict, sprite_picker=None) -> list[Enemy]:
    """Build the enemies for a single spawn entry.

    If `chain_count >= 2`, the spawn is expanded into N enemies with progressive
    time delays. The first enemy uses the spawn's `delay_s`; each subsequent enemy
    is offset by `chain_delay_s`.

    `chain_count` is clamped to 1-5.
    """
    chain_count = int(spawn.get("chain_count", 1))
    chain_delay_s = float(spawn.get("chain_delay_s", 0.5))
    if chain_count < 1:
        chain_count = 1
    if chain_count > 5:
        import logging
        logging.warning("chain_count %d clamped to 5 (max)", chain_count)
        chain_count = 5

    offsets = _FORMATION_BUILDERS[spawn["formation"]](spawn["formation_count"], 18.0)
    raw_path = _PATH_BUILDERS[spawn["path"]](spawn)
    hybrid = _path_to_hybrid(raw_path)
    kind = _KIND_MAP[spawn["enemy_kind"]]
    sprite_name = ""
    if sprite_picker is not None:
        sprite_name = sprite_picker(spawn["enemy_kind"]) or ""
    enemies: list[Enemy] = []
    for chain_index in range(chain_count):
        for dx, dy in offsets:
            e = Enemy()
            e.kind = kind
            e.sprite_name = sprite_name
            e.on_spawn()
            follower = PathFollower(hybrid)
            e.attach_path(follower, slot_dx=dx, slot_dy=dy)
            enemies.append(e)
    return enemies
```

Wait — that's wrong. The chain should be N instances of the spawn (each spawning one set of formation_count enemies), with progressive time delays, NOT a single spawn producing chain_count * formation_count enemies. Let me think.

The spec says: "chain is just a spawn pattern: N enemies of the same kind on the same path with progressive time delays". So if `formation_count: 1, chain_count: 3`, we get 3 enemies total, each with 1 in the formation.

But the user wanted to add FTL "demonstration" in wave 4 with `chain_count: 3, chain_delay_s: 0.4`. So the visual is 3 enemies appearing one after another.

The current `_build_enemies` builds a list of N enemies based on `formation_count`. So if formation_count=1, you get 1 enemy per spawn. To get a chain of 3, we need 3 separate spawn entries with progressive delays.

So the right approach is: in `begin()`, expand a spawn with `chain_count >= 2` into N entries in the spawn_queue, each with its own delay. The `_build_enemies` function stays the same (one enemy per formation_count slot).

Update `begin()` instead:

```python
def begin(self) -> None:
    self.spawned_enemies.clear()
    self.spawn_queue.clear()
    self.elapsed_s = 0.0
    self.wave_complete = False
    if self.current_wave_index >= len(self.waves):
        return
    wave = self.waves[self.current_wave_index]
    for spawn in wave.spawns:
        chain_count = int(spawn.get("chain_count", 1))
        chain_delay_s = float(spawn.get("chain_delay_s", 0.5))
        if chain_count < 1:
            chain_count = 1
        if chain_count > 5:
            import logging
            logging.warning("chain_count %d clamped to 5 (max)", chain_count)
            chain_count = 5
        for k in range(chain_count):
            offset = k * chain_delay_s
            self.spawn_queue.append(
                (spawn["delay_s"] + offset, _build_enemies(spawn, self._sprite_picker))
            )
    self.spawn_queue.sort(key=lambda x: x[0])
```

The `_build_enemies` function does NOT need to change. The chain expansion is done in `begin()`.

- [ ] **Step 4: Run tests, verify they pass**

Run: `python -m pytest stellar_horizon/tests/test_choreography.py -v -k "chain_expansion or no_chain_count or chain_count_1"`
Expected: 5 chain tests PASS

- [ ] **Step 5: Run the full existing test suite to verify nothing broke**

Run: `python -m pytest stellar_horizon/tests/ -v`
Expected: 245 existing tests + 5 new chain tests = 250 tests PASS. If any existing test fails, investigate why and fix before committing.

- [ ] **Step 6: Commit**

```bash
cd D:\AI\stellar-horizon
git add stellar_horizon/waves/wave_manager.py stellar_horizon/tests/test_choreography.py
git commit -m "feat(waves): FTL chain expansion in WaveManager.begin() (clamp 1-5)"
```

---

## Task 6: Update Wave 1 (w1_intro_scouts) to Use sine_bend

**Files:**
- Modify: `stellar_horizon/waves/waves_act1.json`

- [ ] **Step 1: Read the current wave 1 entry**

Run a quick read of the file to confirm the wave 1 structure matches the snippet in the design spec:

```bash
cd D:\AI\stellar-horizon
python -c "import json; d=json.load(open('stellar_horizon/waves/waves_act1.json')); print(json.dumps(d['waves'][0], indent=2))"
```

Expected output matches wave 1 (`w1_intro_scouts`) from the spec.

- [ ] **Step 2: Update wave 1's path to "sine_bend"**

Open `stellar_horizon/waves/waves_act1.json` and change the first wave's spawn entry. The original has `"path": "s_right_to_left"`. Change to `"path": "sine_bend"`. Keep everything else the same.

- [ ] **Step 3: Run the full test suite to verify nothing broke**

Run: `python -m pytest stellar_horizon/tests/ -v`
Expected: 250 tests PASS (245 existing + 5 chain). If a test fails, revert and investigate.

- [ ] **Step 4: Commit**

```bash
cd D:\AI\stellar-horizon
git add stellar_horizon/waves/waves_act1.json
git commit -m "feat(wave1): scouts now use sine_bend for first-wave impression"
```

---

## Task 7: Update Wave 2 (w2_scouts_and_cruisers) — Cruiser uses boomerang_arc

**Files:**
- Modify: `stellar_horizon/waves/waves_act1.json`

- [ ] **Step 1: Read the current wave 2 entry**

```bash
cd D:\AI\stellar-horizon
python -c "import json; d=json.load(open('stellar_horizon/waves/waves_act1.json')); print(json.dumps(d['waves'][1], indent=2))"
```

- [ ] **Step 2: Change the first spawn's formation from "line_horizontal" to "boomerang_arc"**

The first spawn in wave 2 is a cruiser in `line_horizontal` formation. Change to `"formation": "boomerang_arc"` to demonstrate the dynamic formation.

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest stellar_horizon/tests/ -v`
Expected: 250 tests PASS.

- [ ] **Step 4: Commit**

```bash
cd D:\AI\stellar-horizon
git add stellar_horizon/waves/waves_act1.json
git commit -m "feat(wave2): cruiser uses boomerang_arc dynamic formation"
```

---

## Task 8: Update Wave 3 (w3_heavies_join) — Heavy uses phalanx_box, Cruiser uses sine_bend

**Files:**
- Modify: `stellar_horizon/waves/waves_act1.json`

- [ ] **Step 1: Read the current wave 3 entry**

```bash
cd D:\AI\stellar-horizon
python -c "import json; d=json.load(open('stellar_horizon/waves/waves_act1.json')); print(json.dumps(d['waves'][2], indent=2))"
```

- [ ] **Step 2: Change spawn 0 (heavy diamond) to use phalanx_box formation**

Change `"formation": "diamond_pointing_left"` to `"formation": "phalanx_box"`. Keep `formation_count: 3` (clamped from 9 by phalanx_box logic — actually verify this matches expectations).

- [ ] **Step 3: Change spawn 2 (cruiser wedge) to use sine_bend path**

Change `"path": "s_right_to_left"` to `"path": "sine_bend"`. Keep everything else.

- [ ] **Step 4: Run full test suite**

Run: `python -m pytest stellar_horizon/tests/ -v`
Expected: 250 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd D:\AI\stellar-horizon
git add stellar_horizon/waves/waves_act1.json
git commit -m "feat(wave3): heavy uses phalanx_box, cruiser uses sine_bend"
```

---

## Task 9: Update Wave 4 (w4_bombers_introduced) — Bomber uses swept_wing + FTL chain

**Files:**
- Modify: `stellar_horizon/waves/waves_act1.json`

- [ ] **Step 1: Read the current wave 4 entry**

```bash
cd D:\AI\stellar-horizon
python -c "import json; d=json.load(open('stellar_horizon/waves/waves_act1.json')); print(json.dumps(d['waves'][3], indent=2))"
```

- [ ] **Step 2: Add chain_count and chain_delay_s to one bomber spawn**

The second spawn in wave 4 is a `bomber` in `line_horizontal`. Change it to:
- Add `"chain_count": 3` and `"chain_delay_s": 0.4`
- Change formation to `"swept_wing"`
- Keep `formation_count: 1` (so each chain link is a single bomber, not a sweep of 3)

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest stellar_horizon/tests/ -v`
Expected: 250 tests PASS.

- [ ] **Step 4: Commit**

```bash
cd D:\AI\stellar-horizon
git add stellar_horizon/waves/waves_act1.json
git commit -m "feat(wave4): bomber uses swept_wing + 3-link FTL chain"
```

---

## Task 10: Update Wave 5 (w5_ufo_and_kamikaze) — Bomber uses denser FTL chain

**Files:**
- Modify: `stellar_horizon/waves/waves_act1.json`

- [ ] **Step 1: Read the current wave 5 entry**

```bash
cd D:\AI\stellar-horizon
python -c "import json; d=json.load(open('stellar_horizon/waves/waves_act1.json')); print(json.dumps(d['waves'][4], indent=2))"
```

- [ ] **Step 2: Add denser chain to the third spawn (bomber)**

The third spawn in wave 5 is a `bomber` in `line_horizontal` with `formation_count: 2`. Change to:
- Set `formation_count: 1`
- Add `"chain_count": 4` and `"chain_delay_s": 0.3`
- Keep formation as `line_horizontal`

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest stellar_horizon/tests/ -v`
Expected: 250 tests PASS.

- [ ] **Step 4: Commit**

```bash
cd D:\AI\stellar-horizon
git add stellar_horizon/waves/waves_act1.json
git commit -m "feat(wave5): bomber uses 4-link FTL chain (denser)"
```

---

## Task 11: Add JSON Integrity Test

**Files:**
- Modify: `stellar_horizon/tests/test_choreography.py`

- [ ] **Step 1: Write failing test for JSON integrity**

Append to `test_choreography.py`:

```python
# --- JSON integrity test ---

def test_waves_act1_json_references_valid_paths_and_formations():
    """All 'path' and 'formation' values in waves_act1.json must be registered in the builders."""
    import json
    from pathlib import Path
    from stellar_horizon.waves.wave_manager import (
        _PATH_BUILDERS, _FORMATION_BUILDERS,
    )
    json_path = Path(__file__).parent.parent / "waves" / "waves_act1.json"
    data = json.loads(json_path.read_text(encoding="utf-8"))
    for wave in data["waves"]:
        for spawn in wave.get("spawns", []):
            path = spawn.get("path")
            formation = spawn.get("formation")
            assert path in _PATH_BUILDERS, (
                f"wave '{wave['id']}' spawn references unknown path '{path}'"
            )
            assert formation in _FORMATION_BUILDERS, (
                f"wave '{wave['id']}' spawn references unknown formation '{formation}'"
            )
```

- [ ] **Step 2: Run test, verify it passes**

Run: `python -m pytest stellar_horizon/tests/test_choreography.py::test_waves_act1_json_references_valid_paths_and_formations -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
cd D:\AI\stellar-horizon
git add stellar_horizon/tests/test_choreography.py
git commit -m "test(choreography): verify all JSON spawns reference valid paths/formations"
```

---

## Task 12: Final Verification

**Files:** none (read-only verification)

- [ ] **Step 1: Run the full test suite**

Run: `python -m pytest stellar_horizon/tests/ -v`
Expected: 250 tests PASS (245 existing + 19 new). If any test fails, do not proceed — investigate and fix.

- [ ] **Step 2: Run the smoke test**

Run: `python stellar_horizon/smoke.py`
Expected: 11/11 gates PASS. If any gate fails, investigate.

- [ ] **Step 3: Run --check on the game**

Run: `cd D:\AI\stellar-horizon; .venv\Scripts\python.exe main.py --check`
Expected: prints "STELLAR HORIZON check OK" with no traceback.

- [ ] **Step 4: Visual smoke test — launch the game**

Run: `cd D:\AI\stellar-horizon; .venv\Scripts\python.exe main.py`
Expected: game window opens. Watch waves 1-5 and verify:
- Wave 1 scouts follow a sine-bend path (smooth wave)
- Wave 2 cruiser V is on a curved arc that rotates
- Wave 3 heavies form a 3×3-ish block
- Wave 4 bombers enter as a chain (3 enemies with ~0.4s delay between each)
- Wave 5 bombers enter as a denser chain (4 enemies with 0.3s delay)
Press ESC to quit.

- [ ] **Step 5: Commit the final summary doc**

Create `docs/superpowers/specs/2026-08-26-choreographed-enemy-movement-SUMMARY.md` with:
- Commit list (the 12 task commits)
- Test count (264 total = 245 + 19)
- Visual verification notes

Then:

```bash
cd D:\AI\stellar-horizon
git add docs/superpowers/specs/2026-08-26-choreographed-enemy-movement-SUMMARY.md
git commit -m "docs(spec): add choreographed enemy movement implementation summary"
```

- [ ] **Step 6: Push to GitHub**

```bash
cd D:\AI\stellar-horizon
git push origin main
```

Expected: All commits pushed successfully.

---

## Spec Coverage Check

After completing the plan, verify each spec section has a task:

| Spec Section | Task(s) |
|---|---|
| §1 Goal | All tasks contribute to it |
| §2 New Bezier Paths | Task 1 (all 6 paths) |
| §3 New Formations | Task 2 (all 5 formations) |
| §4 FTL Chain | Task 5 (chain expansion) |
| §5 Defaults per Type per Wave | Tasks 4 (table) + 3 (builders) |
| §6 Wave JSON Updates | Tasks 6-10 (waves 1-5) |
| §7 Files to Touch | Tasks 1-11 cover all listed files |
| §8 Testing Strategy | Tasks 1-5, 11 (19 new tests across 5 categories) |
| §9 Out of Scope | Respected throughout (no enemy.py, boss.py, etc. changes) |
| §10 Risks | Mitigated by incremental wave updates (Tasks 6-10) with tests between each |
| §11 Implementation Order | Matches the task order exactly |
| §12 Acceptance Criteria | Task 12 verifies all of them |

## Type Consistency Check

Verify names used in later tasks match definitions in earlier tasks:

- All 6 path function names (sine_bend, figure_eight, boomerang, staircase, loop_horizontal, pull_back) defined in Task 1, registered in Task 3, referenced in defaults in Task 4. ✓
- All 5 formation function names (phalanx_box, swept_wing, train_chain, boomerang_arc, rotating_ring) defined in Task 2, registered in Task 3, referenced in defaults in Task 4. ✓
- `_KIND_DEFAULTS_BY_WAVE` and `_KIND_FALLBACK` defined in Task 4, imported in test file via Task 1 imports. ✓
- `_build_enemies` signature unchanged in Task 5. ✓
- Dynamic formations expose `.update(dt)` and `.offsets()` — used in `_build_enemies` via the offsets call. **NOTE**: dynamic formations are accessed via `_FORMATION_BUILDERS[name](count, spacing)`, which returns the formation object. The wave manager and gameplay code must call `.offsets()` to get the actual offset list. This is a deviation from the existing formation API. The plan accounts for this implicitly via the formation builder registration. **No bug, but worth noting in the implementation phase.**
- `chain_count` and `chain_delay_s` fields added in Task 5, tested in Task 5, used in Tasks 9-10. ✓
- `EnemyKind.SCOUT/CRUISER/HEAVY/BOMBER/UFO/KAMIKAZE` are the 6 enum values, all referenced in the defaults table in Task 4. ✓
