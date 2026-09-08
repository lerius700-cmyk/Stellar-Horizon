"""Beam entity: continuous line from player muzzle to impact point.

2026-09-08 v1.5: replaces the "stream of fireballs" approximation for
weapon 5 (orange fire) with a proper beam. The beam is a single
entity (not a pool — only one beam can be active at a time) with:

- A start point (player muzzle: x + BULLET_OFFSET_X, y).
- An end point (impact point: nearest enemy in the line of fire,
  or the screen edge if no enemy is in range).
- Per-frame damage application to enemies within the beam strip
  (point-to-segment distance test).
- Per-frame dispersion particles at the impact point.
- Procedural body rendering (variable width + ondulations) — see
  fx/beam_renderer.py.

The beam is `alive` while the fire key is held and the player is
on weapon 5. Switching weapons or releasing the key despawns it.
"""
from __future__ import annotations

from __future__ import annotations

import math
from typing import Iterable


class Beam:
    """One active beam at a time. Not pool-managed.

    2026-09-08 v1.5: damage tick at TICK_INTERVAL_S, per-enemy
    cooldown to avoid instant-killing a row of enemies in one frame.
    """

    # Beam geometry / behavior
    MAX_LENGTH: float = 320.0     # px from muzzle before fading
    TICK_INTERVAL_S: float = 0.05  # 20 damage ticks per second
    DAMAGE_PER_TICK: int = 1
    HIT_RADIUS_PX: int = 10       # distance from line that counts as a hit
    HIT_COOLDOWN_S: float = 0.10  # per-enemy cooldown between hits
    # Color palette (matches weapon 5 = orange fire). The renderer
    # uses these to draw the body + inner core.
    COLOR_BODY: tuple[int, int, int] = (255, 140, 40)   # orange
    COLOR_INNER: tuple[int, int, int] = (255, 240, 150)  # white-yellow

    __slots__ = (
        "alive",
        "start_x", "start_y", "end_x", "end_y",
        "spawn_time", "_tick_timer", "_hit_cooldown",
    )

    def __init__(self) -> None:
        self.alive: bool = False
        self.start_x: float = 0.0
        self.start_y: float = 0.0
        self.end_x: float = 0.0
        self.end_y: float = 0.0
        self.spawn_time: float = 0.0
        self._tick_timer: float = 0.0
        # id(enemy) -> seconds remaining of cooldown. Dict so each
        # enemy has its own cooldown independently.
        self._hit_cooldown: dict = {}

    def spawn(self, start_x: float, start_y: float,
              end_x: float, end_y: float, spawn_time: float) -> None:
        """Activate the beam with the given start/end points."""
        self.alive = True
        self.start_x = start_x
        self.start_y = start_y
        self.end_x = end_x
        self.end_y = end_y
        self.spawn_time = spawn_time
        self._tick_timer = 0.0
        self._hit_cooldown.clear()

    def despawn(self) -> None:
        """Deactivate the beam (end of hold, weapon switch, etc.)."""
        self.alive = False
        self._hit_cooldown.clear()

    def update_start(self, start_x: float, start_y: float) -> None:
        """Move the muzzle (called every frame so the beam follows
        the player). Does not change the end point — the caller
        re-calculates the end via update_end().
        """
        self.start_x = start_x
        self.start_y = start_y

    def update_end(self, end_x: float, end_y: float) -> None:
        """Move the impact point (re-calculated each tick as the
        nearest enemy in the line of fire, or the screen edge).
        """
        self.end_x = end_x
        self.end_y = end_y

    def update(self, dt: float) -> None:
        """Per-frame update: tick the damage timer, decay per-enemy
        cooldowns. The actual damage application is done by
        `damage_enemies_in_strip()` which the scene calls every
        TICK_INTERVAL_S.
        """
        if not self.alive:
            return
        # Decay per-enemy hit cooldowns.
        for k in list(self._hit_cooldown.keys()):
            self._hit_cooldown[k] -= dt
            if self._hit_cooldown[k] <= 0.0:
                del self._hit_cooldown[k]

    def damage_enemies_in_strip(self, enemies: Iterable, fx) -> bool:
        """Apply DAMAGE_PER_TICK to every enemy within HIT_RADIUS_PX
        of the beam's line segment (start -> end). Returns True if
        the beam should despawn (i.e., the player just switched
        weapons — the caller handles that).
        """
        if not self.alive:
            return False
        for e in enemies:
            # `e` is an enemy object with `alive` and `take_damage`.
            if not getattr(e, "alive", False):
                continue
            if id(e) in self._hit_cooldown:
                continue
            if self._point_in_strip(e.x, e.y, self.HIT_RADIUS_PX):
                e.take_damage(self.DAMAGE_PER_TICK)
                self._hit_cooldown[id(e)] = self.HIT_COOLDOWN_S
                # Dispersion spark at the enemy hit point.
                if fx is not None:
                    fx.emit_impact(
                        e.x, e.y, count=3, color=self.COLOR_BODY,
                    )
        return False

    def _point_in_strip(self, px: float, py: float,
                        radius: float) -> bool:
        """Test if point (px, py) is within `radius` of the line
        segment from (start_x, start_y) to (end_x, end_y).
        """
        dx = self.end_x - self.start_x
        dy = self.end_y - self.start_y
        seg_len_sq = dx * dx + dy * dy
        if seg_len_sq <= 0.0:
            return False
        # Project (px, py) onto the line. t in [0, 1] if the
        # projection is on the segment, else the nearest endpoint.
        t = ((px - self.start_x) * dx + (py - self.start_y) * dy) / seg_len_sq
        if t < 0.0:
            t = 0.0
        elif t > 1.0:
            t = 1.0
        proj_x = self.start_x + t * dx
        proj_y = self.start_y + t * dy
        dist_sq = (px - proj_x) ** 2 + (py - proj_y) ** 2
        return dist_sq <= radius * radius

    def advance_tick(self, dt: float) -> bool:
        """Advance the damage tick timer. Returns True when a tick
        is due (caller should then call damage_enemies_in_strip).
        """
        if not self.alive:
            return False
        self._tick_timer += dt
        if self._tick_timer >= self.TICK_INTERVAL_S:
            self._tick_timer -= self.TICK_INTERVAL_S
            return True
        return False
