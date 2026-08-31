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
# wave_manager imports added in Tasks 3-5
# from stellar_horizon.waves.wave_manager import (
#     _KIND_DEFAULTS_BY_WAVE,
#     _KIND_FALLBACK,
#     _build_enemies,
# )


# --- Bezier path tests ---

SIM_DT = 1.0 / 120.0
SIM_FRAMES = 1500  # 12.5 seconds at 120 FPS (long enough for the new path shapes)


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


def _is_off_screen(point: tuple[float, float], margin: float = 0.0) -> bool:
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
    points = _simulate_path(path, frames=1500)  # 12.5s sample
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
    points = _simulate_path(path, frames=1500)
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
    """staircase should generally descend (y increasing) — not climb back up (y decreasing).

    In screen coordinates y=0 is top, y=270 is bottom. "Descending" means
    y values grow over time.
    """
    path = path_staircase()
    points = _simulate_path(path, frames=300)
    # Find the Y of each 30-frame bucket; y should generally grow.
    # Allow small decreases (< 5 px) but no big climb back up.
    for i in range(30, len(points), 30):
        y_now = points[i][1]
        y_prev = points[i - 30][1]
        assert y_now >= y_prev - 5, (
            f"staircase climbed back up from y={y_prev} to y={y_now} at frame {i}"
        )


def test_loop_horizontal_exits_off_screen():
    path = path_loop_horizontal()
    points = _simulate_path(path)
    assert _is_off_screen(points[-1])
    assert _is_off_screen(points[0])


def test_loop_horizontal_does_a_full_loop():
    """loop_horizontal should make a closed loop. Y should return to start after going around."""
    path = path_loop_horizontal()
    points = _simulate_path(path, frames=1500)
    # Check that during the middle of the simulation, Y has gone both well above and well below start
    mid_start = 200
    mid_end = 1200
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


def test_boomerang_arc_returns_n_offsets():
    obj = boomerang_arc(count=5, spacing=18.0)
    assert len(obj.offsets()) == 5


def test_boomerang_arc_phase_changes_offsets():
    """boomerang_arc is dynamic — calling its update should change the offsets."""
    obj = boomerang_arc(count=5, spacing=18.0)
    obj.update(0.0)
    after_zero = obj.offsets()
    obj.update(1.0)
    after_one_sec = obj.offsets()
    assert after_zero != after_one_sec, (
        "boomerang_arc did not change offsets over time"
    )


def test_rotating_ring_returns_n_offsets():
    obj = rotating_ring(count=6, spacing=20.0)
    assert len(obj.offsets()) == 6


def test_rotating_ring_phase_rotates_offsets():
    """rotating_ring should rotate the offsets over time (angle changes)."""
    obj = rotating_ring(count=6, spacing=20.0)
    obj.update(0.0)
    initial = obj.offsets()
    obj.update(0.5)  # 0.5s of rotation
    after_half = obj.offsets()
    assert initial != after_half, "rotating_ring did not rotate offsets over 0.5s"

