"""ChargedDisc: a large piercing energy disc fired by weapon 1 (white
piercing) on SPACE release after a full charge.

2026-09-08 v1.7 design: replaces the v1.6 "Megaman bolt" with a
StarFox-64-style energy disc that:
  - Grows on the muzzle during the 1.0s charge (preview rendered
    by fx/charged_disc_renderer.py).
  - On release, spawns a 40px-radius disc that flies +X at 1100 px/s.
  - Pierces up to 4 enemies: first hit deals 8x damage with full
    splash + shockwave + screen shake + flash, secondary hits
    deal 3x with the standard per-weapon impact.
  - After 0.4s with no further possible hits, fades to alpha 0
    over FADE_DURATION_S while scaling 1.0 -> 1.3 (the "burst"
    before disappearance).
  - Dies immediately if it leaves the playfield (x > INTERNAL_W + 60).

State machine:
  FLYING  -> move +X, check hits, count toward MAX_HITS
  FADING  -> no movement, no hits, alpha lerp 255 -> 0, scale 1.0 -> 1.3
            over FADE_DURATION_S
Transitions:
  spawn                  -> FLYING
  off-screen (x > cap)   -> alive = False (no fade; just gone)
  no hits, elapsed >= 0.4s                -> FADING
  MAX_HITS reached, 0.4s since last hit   -> FADING

NOT pool-managed through PlayerBullet -- this is a separate entity
class with its own pool of 2 instances managed by GameplayScene.
Pattern mirrors stellar_horizon/entities/beam.py: single-purpose
entity with alive, spawn, update, hitbox().
"""
from __future__ import annotations

from enum import Enum, auto

import pygame


class State(Enum):
    FLYING = auto()
    FADING = auto()


class ChargedDisc:
    """One active disc at a time (per pool slot). The pool size of 2
    allows the edge case where the player spams SPACE on the same
    frame (rare -- second spawn fails silently if no slot is free).
    """
    # --- Tunables (per spec section 3.1) ---
    SPEED_PX_S: float = 1100.0
    RADIUS: int = 40             # hitbox is 80x80
    MAX_HITS: int = 4            # secondary hits after the first
    FADE_DURATION_S: float = 0.4
    # 0.4s of "no more hits" before transitioning to FADING. For the
    # miss case (no hits at all), this is the same 0.4s timeout.
    LAST_HIT_SETTLE_S: float = 0.4
    # Off-screen kill: disc.x > INTERNAL_W + OFFSCREEN_MARGIN.
    # The render skips it, so no fade needed -- it just vanishes.
    OFFSCREEN_MARGIN: int = 60

    __slots__ = (
        "x", "y", "vx", "vy", "alive",
        "state", "hit_count", "elapsed", "fade_elapsed",
        "last_hit_time", "spawn_time",
    )

    def __init__(self) -> None:
        self.x: float = 0.0
        self.y: float = 0.0
        self.vx: float = 0.0
        self.vy: float = 0.0
        self.alive: bool = False
        self.state: State = State.FLYING
        self.hit_count: int = 0
        self.elapsed: float = 0.0
        # Time since state transitioned to FADING. Used by the
        # renderer to lerp alpha 255 -> 0 and scale 1.0 -> 1.3.
        self.fade_elapsed: float = 0.0
        # Elapsed at the moment of the most recent hit. -1 = no hits
        # yet. Used to defer the FLYING -> FADING transition by
        # LAST_HIT_SETTLE_S after the last meaningful hit.
        self.last_hit_time: float = -1.0
        # Scene time (seconds) when this disc was spawned. For tests
        # and for any future VFX that wants a global timestamp.
        self.spawn_time: float = 0.0

    def spawn(self, x: float, y: float, scene_time: float) -> None:
        """Activate this disc at the muzzle. Always spawns at +X
        velocity = SPEED_PX_S; the disc is a pure horizontal shot.
        """
        self.x = x
        self.y = y
        self.vx = self.SPEED_PX_S
        self.vy = 0.0
        self.alive = True
        self.state = State.FLYING
        self.hit_count = 0
        self.elapsed = 0.0
        self.fade_elapsed = 0.0
        self.last_hit_time = -1.0
        self.spawn_time = scene_time

    def update(self, dt: float) -> None:
        """Per-frame tick. Three cases:
          FLYING: move +X, decide if we should start fading.
          FADING: tick fade_elapsed, kill at FADE_DURATION_S.
          dead:   no-op (alive = False).
        """
        if not self.alive:
            return
        self.elapsed += dt
        if self.state is State.FLYING:
            # Move +X only while flying -- the fade-out should hold
            # its position so the splash has a fixed anchor.
            self.x += self.vx * dt
            # Off-screen kill: instantaneous, no fade.
            from stellar_horizon.settings import INTERNAL_W
            if self.x > INTERNAL_W + self.OFFSCREEN_MARGIN:
                self.alive = False
                return
            # Decide if we should start fading. Three sub-cases:
            # 1) Miss timeout: no hits at all and elapsed >= settle.
            # 2) Cap reached: MAX_HITS done and 0.4s since last hit.
            # 3) Both rely on the same settle threshold.
            if self.hit_count == 0 and self.elapsed >= self.LAST_HIT_SETTLE_S:
                self._begin_fade()
            elif (self.hit_count >= self.MAX_HITS
                  and (self.elapsed - self.last_hit_time)
                      >= self.LAST_HIT_SETTLE_S):
                self._begin_fade()
        elif self.state is State.FADING:
            self.fade_elapsed += dt
            if self.fade_elapsed >= self.FADE_DURATION_S:
                self.alive = False

    def _begin_fade(self) -> None:
        """Internal helper: transition FLYING -> FADING."""
        self.state = State.FADING
        self.fade_elapsed = 0.0
        # Freeze position by zeroing velocity. The render will still
        # draw the disc at (x, y) for FADE_DURATION_S while it fades.
        self.vx = 0.0
        self.vy = 0.0

    def register_hit(self) -> None:
        """Called by the collision handler after a successful hit
        (any tier: 8x first, 3x secondary). Records the elapsed time
        so the FLYING -> FADING timer can defer the transition.
        """
        self.hit_count += 1
        self.last_hit_time = self.elapsed

    def hits(self, enemy) -> bool:
        """AABB collision test between this disc and an enemy. The
        enemy must expose a `hitbox()` method returning a pygame.Rect.
        This is the same convention used by the existing bullet
        collision loop in scenes/gameplay.py.
        """
        if not self.alive:
            return False
        if self.state is not State.FLYING:
            # No hits while fading -- the disc is a visual ghost.
            return False
        return self.hitbox().colliderect(enemy.hitbox())

    def hitbox(self) -> pygame.Rect:
        """80x80 AABB centered on (x, y). The collision handler
        only sees this rect; the render draws a circle for the
        visual but the AABB is the truth for hit detection.
        """
        return pygame.Rect(
            int(self.x - self.RADIUS),
            int(self.y - self.RADIUS),
            self.RADIUS * 2,
            self.RADIUS * 2,
        )

    # ----- helpers for the renderer (read-only views) -----

    def fade_alpha(self) -> int:
        """Current alpha (0..255) for the renderer. Constant 255 in
        FLYING, linear lerp 255 -> 0 in FADING.
        """
        if self.state is State.FLYING:
            return 255
        if self.FADE_DURATION_S <= 0.0:
            return 0
        t = min(1.0, self.fade_elapsed / self.FADE_DURATION_S)
        return int(255 * (1.0 - t))

    def fade_scale(self) -> float:
        """Current scale (1.0..1.3) for the renderer. Constant 1.0 in
        FLYING, linear lerp 1.0 -> 1.3 in FADING.
        """
        if self.state is State.FLYING:
            return 1.0
        if self.FADE_DURATION_S <= 0.0:
            return 1.3
        t = min(1.0, self.fade_elapsed / self.FADE_DURATION_S)
        return 1.0 + 0.3 * t


__all__ = ["ChargedDisc", "State"]
