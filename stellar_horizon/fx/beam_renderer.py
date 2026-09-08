"""Procedural beam body renderer.

2026-09-08 v1.5: draws the beam (weapon 5 = orange fire beam)
as a thick line with variable width + sinusoidal ondulations,
matching the Wan's video reference (flamethrower hitting a wall).

The body is rendered as two stacked polygons:
- Outer body: orange, wider, with ondulations
- Inner core: white-yellow, narrower, no ondulations (so the
  bright "focus" stays centered)

Plus an optional hot tip at the impact point (a brighter disc).

The ondulation phase is `now` so the body wiggles over time even
when the player + impact point are stationary.
"""
from __future__ import annotations

import math

import pygame


# Body sampling — 18 points along the line give a smooth polygon
# without being too expensive.
N_SAMPLES = 18

# Width at the start (muzzle): narrow.
WIDTH_BASE_START = 3
# Width at the end (impact): widest, then a quick fade past 1.0.
WIDTH_BASE_END = 8
# Inner core width (narrower, no ondulation).
INNER_WIDTH_START = 1
INNER_WIDTH_END = 3

# Ondulation amplitude (perpendicular to the line, in px).
ONDULATION_AMP = 2.5
# Ondulation spatial frequency (waves along the beam).
ONDULATION_SPATIAL = 6.0
# Ondulation temporal frequency (Hz).
ONDULATION_TEMPORAL = 10.0

# Hot tip disc at the impact point.
HOT_TIP_RADIUS = 4
HOT_TIP_COLOR = (255, 250, 200)


def draw(surface: pygame.Surface, beam, now: float) -> None:
    """Render the beam's body on `surface`.

    `beam` is a Beam entity. `now` is the scene clock (seconds),
    used to phase the ondulations.
    """
    if not beam.alive:
        return
    dx = beam.end_x - beam.start_x
    dy = beam.end_y - beam.start_y
    length = math.hypot(dx, dy)
    if length < 1.0:
        return
    # Perpendicular unit vector.
    nx = -dy / length
    ny = dx / length
    # Sample the line at N+1 points, computing outer/inner
    # offsets for each.
    outer_left = []
    outer_right = []
    inner_left = []
    inner_right = []
    for i in range(N_SAMPLES + 1):
        t = i / N_SAMPLES
        # Base position along the line.
        bx = beam.start_x + t * dx
        by = beam.start_y + t * dy
        # Width at this point: linear ramp from start to end.
        outer_w = WIDTH_BASE_START + (WIDTH_BASE_END - WIDTH_BASE_START) * t
        inner_w = INNER_WIDTH_START + (INNER_WIDTH_END - INNER_WIDTH_START) * t
        # Ondulation: sinusoidal wave along the beam, animated by now.
        ond = ONDULATION_AMP * math.sin(t * ONDULATION_SPATIAL * math.pi
                                         + now * ONDULATION_TEMPORAL)
        outer_off = outer_w + ond
        # Push outer points out, inner points in.
        outer_left.append((bx + nx * outer_off, by + ny * outer_off))
        outer_right.append((bx - nx * outer_off, by - ny * outer_off))
        inner_left.append((bx + nx * inner_w, by + ny * inner_w))
        inner_right.append((bx - nx * inner_w, by - ny * inner_w))
    # Outer body polygon.
    outer_poly = outer_left + list(reversed(outer_right))
    pygame.draw.polygon(surface, beam.COLOR_BODY, outer_poly)
    # Inner core polygon.
    inner_poly = inner_left + list(reversed(inner_right))
    pygame.draw.polygon(surface, beam.COLOR_INNER, inner_poly)
    # Hot tip at the impact point.
    pygame.draw.circle(surface, HOT_TIP_COLOR,
                       (int(beam.end_x), int(beam.end_y)),
                       HOT_TIP_RADIUS)
