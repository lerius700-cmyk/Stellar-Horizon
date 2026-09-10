"""ChargedBullet — a release-fired piercing projectile with FSM.

This is the canonical "Megaman bolt" or "StarFox disc" entity. It is
NOT a normal bullet: it has its own state machine, its own pool, and
its own collision protocol. The clean separation from the normal
bullet pool is intentional — see DESIGN.md section 6 for why.

FSM:
  FLYING  -> moving +X, counting hits, can still hit
  FADING  -> stopped, alpha lerp 255→0, scale 1.0→1.3, no more hits
  dead    -> alive=False, removed from update loops

Transitions:
  spawn                  -> FLYING (always, no fade on entry)
  elapsed >= settle_s    -> FADING (miss timeout; no hits at all)
  hit_count >= MAX_HITS
    AND elapsed - last_hit >= settle_s -> FADING (cap reached)
  fade_elapsed >= FADE_S  -> dead
  x > world_w + margin   -> dead (no fade; off-screen is off-screen)

Pool pattern:
  The game pre-allocates 2-4 instances. On spawn, the dispatch code
  finds the first non-alive slot and calls `spawn()`. If all slots
  are alive, the second spawn is a silent no-op. Don't queue — that
  breaks the player's mental model of "this is a powerful shot, not
  a machine gun".

Usage outline (see examples/full_demo.py for a runnable example):

    pool = [ChargedBullet() for _ in range(2)]

    # In the dispatch branch, on release at full charge:
    for slot in pool:
        if not slot.alive:
            slot.spawn(x=muzzle_x, y=muzzle_y, vx=speed, now=scene_time)
            break

    # Each frame:
    for b in pool:
        if b.alive:
            b.update(dt)
            # collision check:
            for enemy in enemies:
                if b.hits(enemy):
                    b.register_hit()
                    apply_damage(enemy, b.damage_for_hit(b.hit_count))
"""
from __future__ import annotations

from enum import Enum, auto

import pygame


class State(Enum):
    FLYING = auto()
    FADING = auto()


class ChargedBullet:
    """One active release-charged projectile. Pre-allocate a small
    pool of these (2-4) and recycle them.

    Tunables (class-level — override on a subclass if your game needs
    different numbers; the defaults match the Stellar Horizon v1.7
    ChargedDisc):

      SPEED_PX_S         1100.0
      RADIUS             40    (hitbox is 80x80)
      MAX_HITS           4
      FADE_DURATION_S    0.4
      LAST_HIT_SETTLE_S  0.4
      OFFSCREEN_MARGIN   60

    Damage model:
      damage_for_hit(n) returns `FIRST_HIT_MULT` on the first call
      (hit_count=1) and `SECONDARY_HIT_MULT` on every subsequent call.
      Override these on a subclass for a different damage curve.
    """

    # --- Tunables (override on a subclass per game). ---
    SPEED_PX_S: float = 1100.0
    RADIUS: int = 40
    MAX_HITS: int = 4
    FADE_DURATION_S: float = 0.4
    LAST_HIT_SETTLE_S: float = 0.4
    OFFSCREEN_MARGIN: int = 60
    FIRST_HIT_MULT: int = 8
    SECONDARY_HIT_MULT: int = 3

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
        self.fade_elapsed: float = 0.0
        # Elapsed at the moment of the most recent hit. -1 = no hits
        # yet. Used to defer the FLYING -> FADING transition by
        # LAST_HIT_SETTLE_S after the last meaningful hit.
        self.last_hit_time: float = -1.0
        # Scene time (seconds) when this bullet was spawned. Useful
        # for VFX that need a global timestamp.
        self.spawn_time: float = 0.0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def spawn(self, x: float, y: float, vx: float | None = None,
              vy: float = 0.0, now: float = 0.0) -> None:
        """Activate this bullet at (x, y). vx defaults to the class
        speed; pass a custom vx for a slower / faster release shot.
        Always spawns flying (no fade on entry).
        """
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx) if vx is not None else self.SPEED_PX_S
        self.vy = float(vy)
        self.alive = True
        self.state = State.FLYING
        self.hit_count = 0
        self.elapsed = 0.0
        self.fade_elapsed = 0.0
        self.last_hit_time = -1.0
        self.spawn_time = float(now)

    def update(self, dt: float, world_width: int) -> None:
        """Per-frame tick. Pass the world's width in pixels so the
        off-screen check knows where "gone" is. The off-screen
        transition is instantaneous (no fade) — once the bullet
        leaves, it's gone.

        Three sub-cases:

          FLYING: move along velocity, check off-screen, decide if we
                  should start fading.
          FADING: tick fade_elapsed, kill at FADE_DURATION_S.
          dead:   no-op (alive = False).
        """
        if not self.alive:
            return
        self.elapsed += dt
        if self.state is State.FLYING:
            self.x += self.vx * dt
            self.y += self.vy * dt
            # Off-screen kill: instantaneous, no fade. The render will
            # skip it, so no transition is needed.
            if self.x > world_width + self.OFFSCREEN_MARGIN:
                self.alive = False
                return
            # Decide FLYING -> FADING. Two sub-cases:
            #   1) Miss: no hits yet AND elapsed >= settle.
            #   2) Cap: MAX_HITS reached AND settle since last hit.
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
        """Internal: transition FLYING -> FADING. Freezes position by
        zeroing velocity so the fade animation has a fixed anchor.
        """
        self.state = State.FADING
        self.fade_elapsed = 0.0
        self.vx = 0.0
        self.vy = 0.0

    # ------------------------------------------------------------------
    # Collision protocol. The collision handler in your game calls
    # these. The convention matches normal bullets: a `hits()` test
    # that returns bool, plus a `hitbox()` Rect getter.
    # ------------------------------------------------------------------

    def hits(self, target) -> bool:
        """True iff this bullet is in FLYING state AND its hitbox
        overlaps the target's hitbox. Targets must expose a
        `hitbox()` method returning a pygame.Rect (the same convention
        used by normal bullets and enemies in most pygame games).
        No hits while fading — the bullet is a visual ghost.
        """
        if not self.alive:
            return False
        if self.state is not State.FLYING:
            return False
        return self.hitbox().colliderect(target.hitbox())

    def hitbox(self) -> pygame.Rect:
        """Axis-aligned bounding box. The render may draw a circle
        for the visual, but the AABB is the truth for hit detection.
        """
        return pygame.Rect(
            int(self.x - self.RADIUS),
            int(self.y - self.RADIUS),
            self.RADIUS * 2,
            self.RADIUS * 2,
        )

    def register_hit(self) -> None:
        """Called by the collision handler after a successful hit.
        Bumps `hit_count` and records the elapsed time so the
        FLYING -> FADING timer can defer the transition by
        LAST_HIT_SETTLE_S.
        """
        self.hit_count += 1
        self.last_hit_time = self.elapsed

    def damage_for_hit(self, hit_index: int | None = None) -> int:
        """Damage multiplier for the next hit. `hit_index=1` (the
        first hit) returns FIRST_HIT_MULT; anything else returns
        SECONDARY_HIT_MULT. If `hit_index` is None, uses
        `self.hit_count + 1` (i.e. the damage the NEXT hit will
        deal, called BEFORE register_hit). Override on a subclass
        for a different damage curve.
        """
        if hit_index is None:
            hit_index = self.hit_count + 1
        if hit_index == 1:
            return self.FIRST_HIT_MULT
        return self.SECONDARY_HIT_MULT

    # ------------------------------------------------------------------
    # Render helpers. The kit doesn't draw the bullet (that's a
    # visual choice — sprite, particle, or shape) but provides the
    # values a renderer needs: current alpha, current scale.
    # ------------------------------------------------------------------

    def fade_alpha(self) -> int:
        """Current alpha (0..255). 255 in FLYING, linear lerp 255->0
        in FADING. Pass this to your renderer's surface.set_alpha()
        or to a per-pixel alpha blit.
        """
        if self.state is State.FLYING:
            return 255
        if self.FADE_DURATION_S <= 0.0:
            return 0
        t = min(1.0, self.fade_elapsed / self.FADE_DURATION_S)
        return int(255 * (1.0 - t))

    def fade_scale(self) -> float:
        """Current scale (1.0..1.3). 1.0 in FLYING, linear lerp
        1.0->1.3 in FADING. The "burst" before disappearance.
        """
        if self.state is State.FLYING:
            return 1.0
        if self.FADE_DURATION_S <= 0.0:
            return 1.3
        t = min(1.0, self.fade_elapsed / self.FADE_DURATION_S)
        return 1.0 + 0.3 * t


__all__ = ["ChargedBullet", "State"]
