"""Formation helpers for horizontal play.

These wrap Void-Hunter's `FlightFormation` by rotating the offsets so the
formation points in the direction enemies move (-X, i.e. right-to-left).
"""
from __future__ import annotations

from stellar_horizon._systems.movement import FlightFormation


def _v_offsets_rotated(count: int, spacing: float) -> list[tuple[float, float]]:
    """VH's V (apex -Y) rotated 90° CW -> wings at +X (apex points -X)."""
    base = FlightFormation.v(count, spacing)
    return [(y, -x) for (x, y) in base.offsets]


def v_pointing_left(count: int = 5, spacing: float = 18.0) -> list[tuple[float, float]]:
    """V formation with apex pointing -X (enemies moving right→left)."""
    if count == 1:
        return [(0.0, 0.0)]
    return _v_offsets_rotated(count, spacing)


def line_horizontal(count: int = 5, spacing: float = 22.0) -> list[tuple[float, float]]:
    """Horizontal line of N slots, perpendicular to the direction of motion."""
    if count == 1:
        return [(0.0, 0.0)]
    half = (count - 1) * spacing / 2.0
    return [(-half + i * spacing, 0.0) for i in range(count)]


def diamond_pointing_left(count: int = 5, spacing: float = 20.0) -> list[tuple[float, float]]:
    """Diamond formation with vertex pointing -X."""
    if count == 1:
        return [(0.0, 0.0)]
    offsets: list[tuple[float, float]] = [(0.0, 0.0)]
    layer = 1
    while len(offsets) < count:
        offsets.append((-spacing * layer, 0.0))            # front (toward -X)
        if len(offsets) >= count: break
        offsets.append((-spacing * 0.5, -spacing * layer))  # top-front
        if len(offsets) >= count: break
        offsets.append((-spacing * 0.5, +spacing * layer))  # bottom-front
        if len(offsets) >= count: break
        offsets.append((+spacing * layer, 0.0))             # back
        layer += 1
    return offsets[:count]


def wedge_pointing_left(count: int = 5, spacing: float = 18.0) -> list[tuple[float, float]]:
    """Wedge (> shape) with tip pointing -X."""
    if count == 1:
        return [(0.0, 0.0)]
    # VH's WEDGE rotated 90° CW: (x, y) -> (y, -x)
    base = FlightFormation.wedge(count, spacing)
    return [(y, -x) for (x, y) in base.offsets]


# --- New formations (Task 2: choreographed enemy movement) ---

import math


def phalanx_box(count: int = 9, spacing: float = 16.0) -> list[tuple[float, float]]:
    """Solid NxN-ish block formation. For count=9 produces 3x3; for count=16 produces 4x4; etc.

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
