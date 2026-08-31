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
# Formation imports added in Task 2
# from stellar_horizon.waves.formations_h import (
#     boomerang_arc,
#     phalanx_box,
#     rotating_ring,
#     swept_wing,
#     train_chain,
# )
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

