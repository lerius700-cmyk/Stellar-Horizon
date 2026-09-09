"""Bullets: PlayerBullet (moves +X) and EnemyBullet (aims at target)."""
from __future__ import annotations

import math

import pygame


# 2026-09-06 visual polish v2: weapon id -> laser archetype.
# 2026-09-08 v1.5 final: 5 weapons only, mapping to archetypes 4/5/6/7/8.
# The "basic 5" (yellow/red/blue/green/purple void) and their
# archetypes 0..3 were removed. Mapping:
#   0 orange fire      -> archetype 6 (laser_07)
#   1 white piercing   -> archetype 7 (laser_08)
#   2 magenta heart    -> archetype 8 (laser_09)
#   3 cyan ice         -> archetype 5 (laser_06)
#   4 rainbow streak   -> archetype 4 (laser_05) — alias from v1.4
WEAPON_ARCHETYPE: tuple[int, ...] = (
    6,  # 0 orange fire      -> laser_07 (orange flame)
    7,  # 1 white piercing   -> laser_08 (white lightning)
    8,  # 2 magenta heart    -> laser_09 (magenta heart)
    5,  # 3 cyan ice         -> laser_06 (cyan ice)
    4,  # 4 rainbow streak   -> laser_05 (alias)
)


class PlayerBullet:
    SPEED_PX_S = 480.0
    SIZE = (12, 4)
    POOL_SIZE = 32

    # `spawn_time` is the scene time at which this bullet was fired —
    # the code-driven VFX (fx/bullet_vfx.py) reads it to compute
    # alpha/scale/halo phase. `weapon` is which of the 5 weapons
    # fired this bullet so the VFX knows which animation to apply.
    # `frame` and `frame_time` drive sprite-sheet animation (4-frame loop
    # at 8 FPS). Falls back to no sheet animation if the sprite is single-frame.
    # 2026-09-06 visual polish v2: `frame_elapsed`, `frame_index` and
    # `weapon_archetype` drive the 6-frame sheet animation at 12 fps
    # (render code looks up the archetype's laser_NN sheet).
    # 2026-09-08 v1.5: charged-shot flags. Per-shot behavior is now
    # parameterizable without subclassing:
    #   - damage: multiplier on hit (1 = normal, 3 = Megaman bolt).
    #   - piercing: keep going through enemies instead of dying.
    #   - returning: boomerang behavior. After `return_at` seconds,
    #     flip vx to negative so the bullet flies back to the player.
    #   - hit_count: how many enemies the bullet has hit. Used to
    #     cap piercing at a sensible limit (no infinite piercing).
    __slots__ = ("x", "y", "vx", "vy", "alive", "spawn_time", "weapon",
                 "frame", "frame_time",
                 "frame_elapsed",   # seconds since spawn (drives frame_index)
                 "frame_index",     # current sheet frame, 0..5
                 "weapon_archetype",  # index into laser_NN sheet
                 "damage",          # hit damage (default 1)
                 "piercing",        # keep going through enemies
                 "returning",       # boomerang: flip vx after return_at
                 "return_timer",    # seconds since spawn (for boomerang)
                 "return_at",       # seconds before flip (default 0.6)
                 "hit_count")       # how many enemies hit (for pierce cap)

    def __init__(self) -> None:
        self.x = self.y = self.vx = self.vy = 0.0
        self.alive = False
        self.spawn_time: float = 0.0
        self.weapon: int = 0
        self.frame: int = 0
        self.frame_time: float = 0.0
        self.frame_elapsed: float = 0.0
        self.frame_index: int = 0
        self.weapon_archetype: int = 0
        self.damage: int = 1
        self.piercing: bool = False
        self.returning: bool = False
        self.return_timer: float = 0.0
        self.return_at: float = 0.6
        self.hit_count: int = 0

    def spawn(self, x: float, y: float, vx: float, vy: float,
              weapon: int, spawn_time: float,
              damage: int = 1, piercing: bool = False,
              returning: bool = False, return_at: float = 0.6) -> None:
        """Activate this bullet for a new shot. Resets animation state
        so the sprite-sheet frame_index restarts at 0 for every shot.
        `weapon_archetype` is derived from `weapon` via WEAPON_ARCHETYPE.

        2026-09-08 v1.5: optional charged-shot flags:
        - damage: hit damage (default 1; Megaman bolt uses 3).
        - piercing: keep going through enemies (cyan ice charged).
        - returning: boomerang — after `return_at` seconds, flip vx
          to negative so the bullet flies back to the player.
        """
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.alive = True
        self.spawn_time = spawn_time
        self.weapon = weapon
        self.weapon_archetype = (
            WEAPON_ARCHETYPE[weapon] if 0 <= weapon < len(WEAPON_ARCHETYPE) else 0
        )
        self.frame_elapsed = 0.0
        self.frame_index = 0
        self.damage = damage
        self.piercing = piercing
        self.returning = returning
        self.return_at = return_at
        self.return_timer = 0.0
        self.hit_count = 0

    def update(self, dt: float) -> None:
        if not self.alive:
            return
        # 2026-09-08 v1.5: boomerang behavior. If returning, after
        # `return_at` seconds since spawn, flip vx so the bullet flies
        # back toward the player. The flip is one-shot — once
        # reversed, the bullet continues with the new velocity until
        # it leaves the screen.
        if self.returning:
            self.return_timer += dt
            if self.return_timer >= self.return_at and self.vx > 0:
                self.vx = -self.vx
        self.x += self.vx * dt
        self.y += self.vy * dt
        # Animate sprite sheet at 8 FPS (4-frame loop)
        self.frame_time = (self.frame_time or 0.0) + dt
        if self.frame_time >= 1.0 / 8.0:
            self.frame_time = 0.0
            self.frame = (self.frame + 1) % 4
        # 2026-09-06 visual polish v2: cycle through 6-frame sheet
        # at 12 fps.
        self.frame_elapsed += dt
        self.frame_index = int(self.frame_elapsed * 12) % 6
        if self.x > 480 + 12 or self.x < -12:
            self.alive = False

    def hitbox(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - 6), int(self.y - 2), 12, 4)


class EnemyBullet:
    SPEED_PX_S = 220.0
    SIZE = (8, 8)
    POOL_SIZE = 64

    # 2026-09-06 visual polish v2: frame_elapsed / frame_index added
    # for consistency with PlayerBullet (enemy bullets use their own
    # sheet, no weapon_archetype mapping).
    __slots__ = ("x", "y", "vx", "vy", "alive", "damage",
                 "speed_mult", "_bomb", "_bomb_fuse",
                 "frame", "frame_time",
                 "frame_elapsed", "frame_index")

    def __init__(self) -> None:
        self.x = self.y = self.vx = self.vy = 0.0
        self.damage = 1
        self.alive = False
        self.speed_mult: float = 1.0
        self.frame: int = 0
        self.frame_time: float = 0.0
        self.frame_elapsed: float = 0.0
        self.frame_index: int = 0
        self._bomb: bool = False
        self._bomb_fuse: float = 0.0

    def spawn(self, x: float, y: float, target_x: float, target_y: float) -> None:
        dx, dy = target_x - x, target_y - y
        d = math.hypot(dx, dy) or 1.0
        self.vx = dx / d * self.SPEED_PX_S
        self.vy = dy / d * self.SPEED_PX_S
        self.x, self.y, self.alive = x, y, True
        # Reset per-shot flags.
        self.speed_mult = 1.0
        self._bomb = False
        self._bomb_fuse = 0.0

    def update(self, dt: float) -> None:
        if not self.alive:
            return
        if self._bomb:
            # Gravity bomb: constant horizontal velocity, accelerating
            # downward. Fuse timer kills the bullet if it doesn't hit
            # anything (so they don't accumulate forever).
            self._bomb_fuse += dt
            self.x += self.vx * self.speed_mult * dt
            self.y += self.vy * self.speed_mult * dt
            self.vy += 360.0 * dt  # gravity (px/s^2)
            if self._bomb_fuse > 4.0:
                self.alive = False
        else:
            self.x += self.vx * dt
            self.y += self.vy * dt
        if not (-16 <= self.x <= 496 and -16 <= self.y <= 286):
            self.alive = False
        # Animate sprite sheet at 6 FPS (4-frame loop, slower than player bullets)
        self.frame_time += dt
        if self.frame_time >= 1.0 / 6.0:
            self.frame_time = 0.0
            self.frame = (self.frame + 1) % 4

    def hitbox(self) -> pygame.Rect:
        if self._bomb:
            return pygame.Rect(int(self.x - 5), int(self.y - 5), 10, 10)
        return pygame.Rect(int(self.x - 4), int(self.y - 4), 8, 8)
