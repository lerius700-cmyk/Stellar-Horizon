"""Shockwave: an expanding white ring used as a high-impact
visual feedback for weapon hits.

v1.7: introduced for the ChargedDisc's first-hit splash, but
designed as a reusable primitive so future weapons can also use
it (e.g., a charged-orb detonation, a boss phase change).

A Shockwave is a short-lived entity that:
  - Starts at (x, y) with radius 0 and grows toward max_radius.
  - Fades its alpha from 255 to 0 over max_life.
  - Renders as a hollow circle (stroke 2) on the FxLayer.
  - Is not pool-managed -- the FxLayer keeps a small list and
    reaps dead ones each frame (list is bounded by the
    simultaneous-shockwave count, typically <5 in normal play).

Pattern follows stellar_horizon/entities/beam.py: a simple
data-carrying object that the FxLayer ticks and renders. No
entity state machine; just `life` ticking down to 0.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Shockwave:
    """One expanding ring. The FxLayer holds a list of these.

    Fields:
      x, y            -- center in playfield coordinates (px)
      radius          -- current radius (px). Grows from 0 toward max_radius
      max_radius      -- final radius when life = 0
      life            -- seconds remaining (counts down to 0)
      max_life        -- total lifetime (seconds)
      color           -- RGB, used for the stroke color
      width           -- stroke width in px (default 2)
    """
    x: float
    y: float
    radius: float
    max_radius: float
    life: float
    max_life: float
    color: tuple[int, int, int] = (255, 255, 255)
    width: int = 2

    def update(self, dt: float) -> None:
        """Advance life by dt, scale radius proportionally to the
        remaining life fraction (so radius == max_radius when
        life == 0). No-op if already dead (life <= 0).
        """
        if self.life <= 0.0:
            return
        self.life = max(0.0, self.life - dt)
        # Linear radius growth: from 0 at spawn to max_radius at
        # the end of life. We use 1 - (life / max_life) as the
        # progress so the ring is small at spawn and big at death.
        if self.max_life > 0.0:
            progress = 1.0 - (self.life / self.max_life)
        else:
            progress = 1.0
        self.radius = self.max_radius * progress

    @property
    def alive(self) -> bool:
        return self.life > 0.0

    def alpha_255(self) -> int:
        """Compute the current alpha (0..255) as a linear lerp from
        255 at spawn to 0 at death. Used by the FxLayer.draw() to
        stroke the ring with the correct transparency.
        """
        if self.max_life <= 0.0:
            return 0
        if self.life <= 0.0:
            return 0
        # progress = 1 - life/max_life; alpha = 255 * (1 - progress)
        progress = 1.0 - (self.life / self.max_life)
        return int(255 * (1.0 - progress))


__all__ = ["Shockwave"]
