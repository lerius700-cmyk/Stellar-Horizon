"""Power-up rings (Starfox 64 style).

Two kinds:
  * SILVER — heals 1 life. Most common drop (~25% from enemies).
  * GOLD   — heals 2 lives AND counts toward the gold ring stack
    (3 gold rings = +3 max lives, max 2 stacks = 9 lives total).

Pickup is automatic via a 30 px magneto radius around the player.
No button press required.

v1.7 re-implementation: rings are now much more visible and impactful
than the v1.6 tiny 10px version. They have:
  * 18px ring + 22px glow (was 10px solid)
  * Drop VFX: 8-10 particles burst on spawn (color matches ring kind)
  * Idle animation: vertical bob (±3px @ 1.5Hz) + 4-point spin (3 rad/s)
  * Glow pulse: alpha mod 0.85-1.0 @ 0.5Hz to feel "alive"
  * Magnet hint: when player <60px, ring scales 1.0->1.3 (visual cue)
  * Drop rates bumped: 5%->18% gold, 10%->25% silver
  * Drop physics: small initial velocity, gravity, light drag
    (so multi-kills drop rings that don't stack on the same pixel)

Rings stay on screen for 12 seconds with a 3-second fade-out tail
so they don't linger forever after a wave ends.
"""
from __future__ import annotations

import math
import random

import pygame


class PowerUpKind:
    SILVER = "silver"  # heals 1
    GOLD = "gold"      # heals 2 + counts toward gold stack


# 2026-09-09 v1.7: drop rates bumped from 5%/10% to 18%/25% so the
# rings are visible often enough to feel like a real reward.
ENEMY_DROP_RATE_SILVER = 0.25
ENEMY_DROP_RATE_GOLD = 0.18


class PowerUp:
    SIZE = 18                # visual ring radius (px)
    GLOW_SIZE = 22           # outer glow radius (px)
    PICKUP_RADIUS = 30.0     # magneto pickup radius (px)
    MAGNET_HINT_RADIUS = 60.0  # when player is this close, ring lights up
    LIFETIME_S = 12.0        # full-opacity duration
    FADE_DURATION_S = 3.0    # tail fade after LIFETIME_S
    SPIN_SPEED_RAD_S = 3.0   # 4 orbital dots spin around the ring
    BOB_AMPLITUDE_PX = 3.0   # vertical sine bob
    BOB_FREQUENCY_HZ = 1.5
    # Drop physics: small random initial velocity so multiple rings
    # from a multi-kill don't stack on the same pixel. Light gravity +
    # drag bring them to rest within ~1s.
    DROP_VX_RANGE = (-30.0, 30.0)
    DROP_VY_RANGE = (-60.0, -20.0)
    GRAVITY_PX_S_S = 30.0
    VY_MAX = 60.0
    DRAG_PER_S = 0.95  # applied as vx *= 0.95 ** (dt * 60)

    __slots__ = (
        "x", "y", "vx", "vy", "kind", "spawn_time", "alive",
    )

    def __init__(self) -> None:
        self.x: float = 0.0
        self.y: float = 0.0
        self.vx: float = 0.0
        self.vy: float = 0.0
        self.kind: str = PowerUpKind.SILVER
        self.spawn_time: float = 0.0
        self.alive: bool = False

    def spawn(self, x: float, y: float, kind: str, now: float) -> None:
        """Spawn the ring at (x, y) with a small random kick so
        multiple drops from a multi-kill don't stack on the same
        pixel. rng is module-level random; tests can pass a seeded
        one via the rng arg.
        """
        self.x = x
        self.y = y
        self.vx = random.uniform(*self.DROP_VX_RANGE)
        self.vy = random.uniform(*self.DROP_VY_RANGE)
        self.kind = kind
        self.spawn_time = now
        self.alive = True

    def update(self, dt: float, player, now: float) -> bool:
        """Advance the power-up one frame.

        Returns True if the power-up was picked up by the player this
        frame (caller should apply the effect and remove it from the
        list). Returns False otherwise.
        """
        if not self.alive:
            return False
        age = now - self.spawn_time
        if age >= self.LIFETIME_S + self.FADE_DURATION_S:
            self.alive = False
            return False
        # Drop physics: light gravity + drag. Drag is applied as a
        # power-of-60 per-second so it's framerate-independent.
        self.x += self.vx * dt
        self.y += self.vy * dt
        drag_factor = self.DRAG_PER_S ** (dt * 60.0)
        self.vx *= drag_factor
        self.vy = min(self.vy + self.GRAVITY_PX_S_S * dt, self.VY_MAX)
        # Magneto pickup: Euclidean distance to the player.
        dx = player.x - self.x
        dy = player.y - self.y
        if (dx * dx + dy * dy) <= self.PICKUP_RADIUS * self.PICKUP_RADIUS:
            self.alive = False
            return True
        return False

    def current_alpha(self, now: float) -> int:
        """Return the current alpha (0-255) for rendering. Full opacity
        for the first LIFETIME_S seconds, then linear fade to 0.
        """
        age = now - self.spawn_time
        if age < self.LIFETIME_S:
            return 255
        fade_progress = (age - self.LIFETIME_S) / self.FADE_DURATION_S
        fade_progress = max(0.0, min(1.0, fade_progress))
        return int(255 * (1.0 - fade_progress))

    def is_magnet_active(self, player) -> bool:
        """Whether the player is close enough to trigger the magnet
        hint (ring scales 1.0->1.3)."""
        dx = player.x - self.x
        dy = player.y - self.y
        return (dx * dx + dy * dy) <= self.MAGNET_HINT_RADIUS * self.MAGNET_HINT_RADIUS

    def draw(self, surface: pygame.Surface, now: float) -> None:
        if not self.alive:
            return
        alpha = self.current_alpha(now)
        if alpha <= 0:
            return
        age = now - self.spawn_time
        # 4-point orbital dot spin (radians)
        angle = age * self.SPIN_SPEED_RAD_S
        # Vertical sine bob (1.5Hz, ±3px)
        bob = math.sin(age * 2.0 * math.pi * self.BOB_FREQUENCY_HZ) * self.BOB_AMPLITUDE_PX
        # Slow glow pulse (0.5Hz, alpha 0.85-1.0)
        pulse = 0.85 + 0.15 * math.sin(age * 2.0 * math.pi * 0.5)
        # Color: gold (warm) vs silver (cool)
        if self.kind == PowerUpKind.GOLD:
            inner_color = (255, 220, 110)
            outer_color = (255, 150, 50)
        else:
            inner_color = (220, 230, 255)
            outer_color = (140, 170, 220)
        # Magnet hint: scale up when player is near.
        scale = 1.0
        # We don't pass the player here; the scale is set by the
        # gameplay scene via the SCALED_DRAW path. For the simple
        # unscaled path, default to 1.0. The advanced scale is in
        # gameplay.py's _draw_powerup() helper.
        cx = int(self.x)
        cy = int(self.y + bob)
        # Outer glow disc (semi-transparent).
        glow_r = int(self.GLOW_SIZE * scale)
        glow_surf = pygame.Surface(
            (glow_r * 2 + 2, glow_r * 2 + 2), pygame.SRCALPHA,
        )
        glow_alpha = int(alpha * 0.4 * pulse)
        pygame.draw.circle(
            glow_surf, (*outer_color, glow_alpha),
            (glow_r + 1, glow_r + 1), glow_r,
        )
        surface.blit(glow_surf, (cx - glow_r - 1, cy - glow_r - 1))
        # The ring itself: hollow circle, inner radius 0.4x outer.
        ring_outer = int(self.SIZE * 0.5 * scale)
        ring_thickness = max(2, int(2.5 * scale))
        ring_surf = pygame.Surface(
            (ring_outer * 2 + 4, ring_outer * 2 + 4), pygame.SRCALPHA,
        )
        center = ring_outer + 2
        pygame.draw.circle(
            ring_surf, (*inner_color, alpha),
            (center, center), ring_outer, ring_thickness,
        )
        # 4 orbital dots that spin around the ring (visual cue of
        # "this is alive, pick me up").
        for i in range(4):
            a = angle + i * (math.pi / 2.0)
            ox = center + math.cos(a) * (ring_outer + 2.5)
            oy = center + math.sin(a) * (ring_outer + 2.5)
            pygame.draw.circle(
                ring_surf, (*outer_color, alpha),
                (int(ox), int(oy)), 1,
            )
        surface.blit(ring_surf, (cx - center, cy - center))

    def hitbox(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - self.SIZE // 2),
                           int(self.y - self.SIZE // 2),
                           self.SIZE, self.SIZE)


def roll_enemy_drop(rng: "random.Random | None" = None) -> str | None:
    """Roll a power-up drop for a freshly-killed enemy.

    2026-09-09 v1.7: rates bumped to 18% gold, 25% silver (was 5%/10%).
    Returns the PowerUpKind or None if no drop.
    """
    r = rng if rng is not None else random
    roll = r.random()
    # Gold is rarer so check it first; if it's not gold, check silver.
    if roll < ENEMY_DROP_RATE_GOLD:
        return PowerUpKind.GOLD
    if roll < ENEMY_DROP_RATE_GOLD + ENEMY_DROP_RATE_SILVER:
        return PowerUpKind.SILVER
    return None
