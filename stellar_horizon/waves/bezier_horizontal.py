"""Horizontal bezier paths for STELLAR HORIZON.

Each path enters from off-screen and exits off-screen, so the enemy visibly
travels across the play area. All paths are tuned for a 480x270 viewport.
"""
from __future__ import annotations

from stellar_horizon._systems.movement import BezierPath, HybridPath, Point, WaypointPath


def path_s_right_to_left(y_offset: float = 0.0) -> BezierPath:
    """S-curve from off-screen right to off-screen left.

    Args:
        y_offset: shifts the curve vertically. Default 0 puts baseline at y=60.
    """
    return BezierPath(
        p0=Point(490, 60 + y_offset),
        p1=Point(380, 60 + y_offset),
        p2=Point(100, 200 - y_offset),
        p3=Point(-20, 200 - y_offset),
    )


def path_top_dive(side: str = "right") -> BezierPath:
    """Arcs down from off-screen top, exits off-screen right (or left).

    Args:
        side: "right" exits at x=490; "left" exits at x=-10.
    """
    end_x = 490 if side == "right" else -10
    return BezierPath(
        p0=Point(200, -20),
        p1=Point(200, 50),
        p2=Point(380 if side == "right" else 100, 150),
        p3=Point(end_x, 240),
    )


def path_zigzag_exit_top() -> HybridPath:
    """Bezier segment + waypoint zigzag, exits off-screen top."""
    return HybridPath.from_segments([
        BezierPath(
            p0=Point(490, 100),
            p1=Point(300, 100),
            p2=Point(200, 180),
            p3=Point(300, 220),
        ),
        WaypointPath(
            [Point(300, 220), Point(380, 150), Point(250, 80), Point(200, -20)],
            speed_px_s=140.0,
        ),
    ])


def path_boss_entry() -> BezierPath:
    """Dramatic S-curve from off-screen right to boss arena (350, 135)."""
    return BezierPath(
        p0=Point(540, 60),
        p1=Point(450, 100),
        p2=Point(380, 200),
        p3=Point(350, 135),
    )


def path_ufo_entry(y_offset: float = 0.0) -> HybridPath:
    """Gentle arc into the play area, then the UFO takes over with its
    own sinuous oscillation (handled in Enemy.update)."""
    return HybridPath.from_segments([
        BezierPath(
            p0=Point(500, 60 + y_offset),
            p1=Point(420, 80 + y_offset),
            p2=Point(360, 110 + y_offset),
            p3=Point(340, 130 + y_offset),
        ),
        # 0.6s of waypoint drift so the UFO "settles" before oscillating.
        WaypointPath(
            [Point(340, 130 + y_offset), Point(330, 130 + y_offset)],
            speed_px_s=40.0,
        ),
    ])


def path_kamikaze_dive(y_offset: float = 0.0) -> BezierPath:
    """Fast straight-ish entry from off-screen right, slightly angled
    down. The enemy then switches to player-homing behavior in
    Enemy._update_kamikaze.
    """
    return BezierPath(
        p0=Point(500, 80 + y_offset),
        p1=Point(420, 95 + y_offset),
        p2=Point(360, 115 + y_offset),
        p3=Point(310, 140 + y_offset),
    )


# --- New paths (Task 1: choreographed enemy movement) ---

def path_sine_bend() -> BezierPath:
    """Long smooth sinusoid. Enters from off-screen right, glides left in a wave."""
    return BezierPath(
        p0=Point(490, 130),
        p1=Point(360, 60),
        p2=Point(120, 200),
        p3=Point(-20, 135),
    )


def path_figure_eight() -> HybridPath:
    """Horizontal figure-8: enters from right, crosses midline, loops back, exits left."""
    return HybridPath.from_segments([
        BezierPath(
            p0=Point(490, 135),
            p1=Point(360, 80),
            p2=Point(120, 190),
            p3=Point(240, 135),
        ),
        WaypointPath(
            # Crosses midline multiple times to form a figure-8 in screen space
            [Point(240, 135), Point(380, 90), Point(450, 130),
             Point(380, 180), Point(240, 135), Point(100, 90),
             Point(50, 130), Point(100, 180), Point(240, 135),
             Point(100, 90), Point(-20, 135)],
            speed_px_s=200.0,
        ),
    ])


def path_boomerang() -> HybridPath:
    """Boomerang: enters from right, makes a U-turn mid-screen, exits back to the right."""
    return HybridPath.from_segments([
        BezierPath(
            p0=Point(490, 135),
            p1=Point(380, 100),
            p2=Point(220, 200),
            p3=Point(120, 135),
        ),
        WaypointPath(
            [Point(120, 135), Point(220, 80), Point(380, 100), Point(490, 135), Point(540, 200)],
            speed_px_s=220.0,
        ),
    ])


def path_staircase() -> HybridPath:
    """Staircase: descends in 3 steps. Predictable, readable for heavy enemies.
    y values INCREASE over time (descending visually = y growing).
    """
    return HybridPath.from_segments([
        BezierPath(
            p0=Point(490, 30),
            p1=Point(360, 60),
            p2=Point(280, 100),
            p3=Point(300, 110),
        ),
        WaypointPath(
            [Point(300, 110), Point(220, 110), Point(200, 150), Point(220, 180), Point(150, 200), Point(80, 220), Point(-20, 240)],
            speed_px_s=180.0,
        ),
    ])


def path_loop_horizontal() -> HybridPath:
    """Single closed loop: enters from right, does one full circle in the center, exits left."""
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
             Point(340, 135), Point(280, 135), Point(180, 135), Point(80, 135), Point(-20, 135)],
            speed_px_s=220.0,
        ),
    ])


def path_pull_back() -> HybridPath:
    """Pull-back: enters from right, retreats halfway, comes back hard toward the player."""
    return HybridPath.from_segments([
        BezierPath(
            p0=Point(490, 135),
            p1=Point(380, 110),
            p2=Point(300, 150),
            p3=Point(380, 145),
        ),
        WaypointPath(
            [Point(380, 145), Point(420, 130), Point(490, 125), Point(540, 130)],
            speed_px_s=280.0,
        ),
    ])
