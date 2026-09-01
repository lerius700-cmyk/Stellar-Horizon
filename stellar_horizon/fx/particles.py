"""Particle FX layer wrapping Void-Hunter's ParticleEngine."""
from __future__ import annotations

import math
import random

import pygame

from stellar_horizon._systems.systems.particle_engine import (
    P_DUST, P_FIRE, P_FLASH, P_GLOW, P_SHOCKWAVE, P_SHRAPNEL,
    P_SMOKE, P_SPARK, ParticleEngine,
)
from stellar_horizon.settings import PARTICLE_POOL

# Per-enemy-kind explosion tuning (color, scale, spark count, life).
_ENEMY_EXPLOSION_COLORS = {
    "scout":    (200, 220, 255),
    "cruiser":  (255, 200, 100),
    "heavy":    (255, 140, 80),
    "bomber":   (255, 100, 60),
    "ufo":      (200, 100, 255),
    "kamikaze": (255, 80, 80),
}

_ENEMY_EXPLOSION_SCALES = {
    "scout": 0.5, "cruiser": 0.8, "heavy": 1.5,
    "bomber": 1.0, "ufo": 0.8, "kamikaze": 1.0,
}

# Per-weapon bullet impact colors (matches laser sheet colors).
_BULLET_IMPACT_COLORS = {
    0: (255, 240, 200),  # yellow plasma
    1: (255, 120, 120),  # red pulse
    2: (120, 200, 255),  # blue ion
    3: (160, 100, 255),  # purple piercing
    4: (120, 255, 120),  # green acid
    5: (255, 180, 100),  # orange fire
    6: (180, 220, 255),  # ice
    7: (220, 220, 255),  # white piercing
    8: (255, 200, 255),  # rainbow
    9: (255, 100, 180),  # heart
}


class FxLayer:
    def __init__(self, pool_size: int = PARTICLE_POOL) -> None:
        self.engine = ParticleEngine(pool_size=pool_size)

    def emit_sparks(self, x: float, y: float, count: int = 8,
                    color: tuple = (255, 255, 255),
                    speed: float = 140.0) -> None:
        """Burst of N radial sparks at (x, y)."""
        for _ in range(count):
            angle = random.uniform(0.0, math.tau)
            v = random.uniform(speed * 0.5, speed)
            vx = math.cos(angle) * v
            vy = math.sin(angle) * v
            t = random.uniform(0.3, 0.9)
            r = int(color[0] * t + 255 * (1 - t))
            g = int(color[1] * t + 255 * (1 - t))
            b = int(color[2] * t + 255 * (1 - t))
            self.engine.emit(P_SPARK, x, y, vx, vy, color=(r, g, b),
                             life=random.uniform(0.15, 0.30))

    def emit_impact(self, x: float, y: float, count: int = 12,
                    color: tuple = (255, 240, 100)) -> None:
        """Punchy impact: spark burst + shrapnel + flash."""
        self.emit_sparks(x, y, count=count, color=color, speed=180.0)
        for _ in range(4):
            angle = random.uniform(0.0, math.tau)
            v = random.uniform(60.0, 120.0)
            self.engine.emit(P_SHRAPNEL, x, y, math.cos(angle) * v,
                             math.sin(angle) * v, color=color, life=0.4)
        self.engine.emit(P_FLASH, x, y, 0, 0, color=(255, 255, 255), life=0.08)

    def emit_explosion(self, x: float, y: float, scale: float = 1.0) -> None:
        n_sparks = int(16 * scale)
        n_smoke = int(4 * scale)
        for _ in range(n_sparks):
            self.engine.emit(P_SPARK, x, y, 0, 0)
        for _ in range(n_smoke):
            self.engine.emit(P_SMOKE, x, y, 0, 0)

    # --- Visual polish VFX (choreographed enemy movement) ---

    def emit_trail(self, x: float, y: float,
                   color: tuple[int, int, int],
                   intensity: float = 1.0) -> None:
        """Emit a single trail particle. One particle per call (capped).

        `intensity` (0..1) scales life and radius. 0 = skip emit.
        Used for enemy and player engine trails during movement.
        """
        if intensity <= 0.0:
            return
        self.engine.emit(
            P_SPARK, x, y, 0.0, 0.0,
            color=color,
            life=0.4 * intensity,
            radius=max(1, int(2 * intensity)),
        )

    def emit_explosion_typed(self, kind: str, x: float, y: float,
                             scale: float = 1.0) -> None:
        """Emit a kind-colored, kind-scaled explosion. All 6 enemy kinds supported.

        Composes: P_SHRAPNEL radial burst + P_SPARK glow + P_FIRE accents.
        """
        base_color = _ENEMY_EXPLOSION_COLORS.get(kind, (255, 200, 100))
        kind_scale = _ENEMY_EXPLOSION_SCALES.get(kind, 1.0)
        final_scale = kind_scale * scale
        # Shrapnel radial burst (8 chunks * scale)
        for _ in range(int(8 * final_scale)):
            angle = random.uniform(0.0, math.tau)
            speed = random.uniform(60.0, 160.0) * final_scale
            self.engine.emit(
                P_SHRAPNEL, x, y,
                math.cos(angle) * speed, math.sin(angle) * speed,
                color=base_color,
                life=random.uniform(0.4, 0.7),
                radius=2.0,
            )
        # Sparks for a brighter flash
        for _ in range(int(6 * final_scale)):
            angle = random.uniform(0.0, math.tau)
            speed = random.uniform(100.0, 220.0) * final_scale
            self.engine.emit(
                P_SPARK, x, y,
                math.cos(angle) * speed, math.sin(angle) * speed,
                color=base_color,
                life=random.uniform(0.2, 0.4),
            )
        # Fire accents for heavy/bomber
        if kind in ("heavy", "bomber"):
            for _ in range(int(4 * final_scale)):
                angle = random.uniform(0.0, math.tau)
                speed = random.uniform(40.0, 90.0) * final_scale
                self.engine.emit(
                    P_FIRE, x, y,
                    math.cos(angle) * speed, math.sin(angle) * speed,
                    color=base_color,
                    life=random.uniform(0.5, 0.9),
                )

    def emit_bullet_impact(self, x: float, y: float,
                           weapon: int, damage: int) -> None:
        """Emit weapon-tinted impact sparks. Count scales with damage."""
        color = _BULLET_IMPACT_COLORS.get(weapon, (255, 255, 255))
        count = 8 + damage * 4
        for _ in range(count):
            angle = random.uniform(0.0, math.tau)
            speed = random.uniform(60.0, 200.0)
            self.engine.emit(
                P_SPARK, x, y,
                math.cos(angle) * speed, math.sin(angle) * speed,
                color=color,
                life=random.uniform(0.2, 0.5),
                radius=2.0,
            )
        # One quick flash on impact
        self.engine.emit(
            P_FLASH, x, y, 0.0, 0.0, color=(255, 255, 255), life=0.06,
        )

    def emit_chain_spawn_glow(self, x: float, y: float,
                               chain_index: int, total_chain: int) -> None:
        """Emit a portal-like entry effect for an FTL chain link.

        Composes: P_SHOCKWAVE expanding ring + P_GLOW center halo. Color
        varies slightly with chain_index so each link is distinguishable.
        """
        # Cyan/white with slight index-based variation
        r = min(255, 100 + chain_index * 20)
        g = 200
        b = 255
        # Expanding ring of 12 sparks
        for i in range(12):
            angle = (2 * math.pi * i) / 12
            speed = 60.0
            self.engine.emit(
                P_SHOCKWAVE, x, y,
                math.cos(angle) * speed, math.sin(angle) * speed,
                color=(r, g, b),
                life=0.5,
                radius=2.0,
            )
        # Bright center halo
        self.engine.emit(
            P_GLOW, x, y, 0.0, 0.0,
            color=(r, g, b),
            life=0.4,
            radius=4.0,
        )

    def emit_player_hit(self, x: float, y: float) -> None:
        """Emit player-hit sparks (12 red-tinted particles)."""
        for _ in range(12):
            angle = random.uniform(0.0, math.tau)
            speed = random.uniform(80.0, 160.0)
            self.engine.emit(
                P_SPARK, x, y,
                math.cos(angle) * speed, math.sin(angle) * speed,
                color=(255, 100, 100),
                life=random.uniform(0.3, 0.6),
                radius=2.0,
            )
        # Quick white flash
        self.engine.emit(
            P_FLASH, x, y, 0.0, 0.0, color=(255, 255, 255), life=0.08,
        )

    def emit_player_death(self, x: float, y: float) -> None:
        """Emit a big radial explosion for player death (40+ particles)."""
        for _ in range(40):
            angle = random.uniform(0.0, math.tau)
            speed = random.uniform(100.0, 250.0)
            color = random.choice([
                (255, 200, 100), (255, 100, 100), (255, 255, 200),
            ])
            self.engine.emit(
                P_SPARK, x, y,
                math.cos(angle) * speed, math.sin(angle) * speed,
                color=color,
                life=random.uniform(0.6, 1.2),
                radius=3.0,
            )
        # Slow dust/smoke for the afterimage
        for _ in range(8):
            angle = random.uniform(0.0, math.tau)
            speed = random.uniform(20.0, 60.0)
            self.engine.emit(
                P_DUST, x, y,
                math.cos(angle) * speed, math.sin(angle) * speed,
                color=(120, 120, 140),
                life=random.uniform(1.0, 1.5),
                radius=4.0,
            )
        # Central flash
        self.engine.emit(
            P_FLASH, x, y, 0.0, 0.0, color=(255, 255, 255), life=0.12,
        )

    def update(self, dt: float) -> None:
        self.engine.update(dt)

    def draw(self, surface) -> None:
        self.engine.draw(surface)

    @property
    def particles(self):
        """List of currently-active particles. Read-only view for tests/debug."""
        return [p for p in self.engine.pool if p.active]
