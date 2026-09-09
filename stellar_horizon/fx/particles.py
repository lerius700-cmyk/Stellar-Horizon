"""Particle FX layer wrapping Void-Hunter's ParticleEngine.

v1.7: extended with three new visual primitives used by the
ChargedDisc (white piercing weapon 1):
  - Shockwave: expanding ring, used for the first-hit splash
    (see fx/shockwave.py for the dataclass).
  - Screen shake: amplitude+duration kick, additive on top of the
    existing ScreenShake trauma system. Used for "hard" impacts
    that need a definite jolt (the ChargedDisc's first hit).
  - Flash: brief bright disc at a point. Used for the ChargedDisc
    first hit's "impact white" feedback.

All three are managed by the FxLayer (lifetime ticking, reaping
dead ones). The shake exposes shake_offset() so the gameplay
scene can apply the offset on top of the existing ScreenShake.
"""
from __future__ import annotations

import math
import random

import pygame

from stellar_horizon._systems.systems.particle_engine import (
    P_DUST, P_FIRE, P_FLASH, P_GLOW, P_SHOCKWAVE, P_SHRAPNEL,
    P_SMOKE, P_SPARK, ParticleEngine,
)
from stellar_horizon.fx.shockwave import Shockwave
from stellar_horizon.settings import PARTICLE_POOL

# v1.7: cap on the FxLayer's screen shake so two simultaneous
# hard impacts don't compound into an unreadable mess.
SHAKE_AMPLITUDE_CAP: float = 6.0
# Default life of a fresh shockwave (seconds). Caller can override.
DEFAULT_SHOCKWAVE_LIFE_S: float = 0.35
# Default max radius of a fresh shockwave (px). Caller can override.
DEFAULT_SHOCKWAVE_MAX_RADIUS: float = 50.0
# Default life of a fresh flash (seconds).
DEFAULT_FLASH_LIFE_S: float = 0.3
# Default radius of a fresh flash (px).
DEFAULT_FLASH_RADIUS: float = 30

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
        # v1.7: shockwave list -- bounded by simultaneous-shockwave
        # count (typically <5 in normal play, never pruned explicitly
        # because the list is short-lived and filtered each update).
        self.shockwaves: list[Shockwave] = []
        # v1.7: FxLayer's own screen shake (amplitude + duration
        # model, additive on top of the existing ScreenShake trauma
        # in the gameplay scene). Decays linearly: amplitude * (life
        # / max_life) -> 0. The gameplay scene's draw() combines
        # both offsets for the final blit offset.
        self.shake_amplitude: float = 0.0
        self.shake_life: float = 0.0
        self.shake_max_life: float = 0.0
        # v1.7: flash list -- brief bright disc overlays at a point.
        # Only the most recent flash is rendered (the list is a
        # stack; old ones are reaped on update).
        self._flashes: list[tuple[float, float, float,
                                 tuple[int, int, int],
                                 float, float]] = []
        # Fields: (x, y, radius, color, life, max_life)

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

    def emit_impact_weapon(self, x: float, y: float,
                           vx_dir: float, vy_dir: float,
                           params) -> None:
        """2026-09-08 v1.5: per-weapon impact burst.

        Spawns `params.count` particles in a forward cone oriented
        along (vx_dir, vy_dir) with half-angle `params.spread_deg`.
        Optionally adds a bright P_FLASH on top.

        The cone math: each particle picks a base direction
        (vx_dir, vy_dir) (normalized), then a random angle within
        ±spread_deg is added via rotation. The magnitude is
        `params.speed_px_s` plus a small per-particle jitter so
        the burst looks organic.

        Used by the collision handler in gameplay.py for every
        bullet/enemy hit, replacing the previous hardcoded yellow
        emit_impact with a per-weapon palette.
        """
        # Normalize the direction. If the bullet is stationary
        # (vx_dir == vy_dir == 0), fall back to a +X direction.
        mag = math.hypot(vx_dir, vy_dir)
        if mag < 1e-3:
            dir_x, dir_y = 1.0, 0.0
        else:
            dir_x, dir_y = vx_dir / mag, vy_dir / mag
        spread_rad = math.radians(params.spread_deg)
        for _ in range(params.count):
            # Random angle within +/- spread_rad.
            angle_offset = random.uniform(-spread_rad, spread_rad)
            # Rotate the base direction by angle_offset.
            cos_o = math.cos(angle_offset)
            sin_o = math.sin(angle_offset)
            base_x = dir_x * cos_o - dir_y * sin_o
            base_y = dir_x * sin_o + dir_y * cos_o
            # Per-particle speed jitter (0.7..1.2 of base speed).
            speed = params.speed_px_s * random.uniform(0.7, 1.2)
            vx = base_x * speed
            vy = base_y * speed
            self.engine.emit(
                params.particle_kind, x, y, vx, vy,
                color=params.color,
                life=params.lifetime_s,
            )
        # Optional bright flash on top (P_FLASH at the impact point).
        if params.add_flash:
            self.engine.emit(
                P_FLASH, x, y, 0, 0,
                color=(255, 255, 255), life=0.08,
            )

    def emit_explosion(self, x: float, y: float, scale: float = 1.0) -> None:
        n_sparks = int(16 * scale)
        n_smoke = int(4 * scale)
        for _ in range(n_sparks):
            self.engine.emit(P_SPARK, x, y, 0, 0)
        for _ in range(n_smoke):
            self.engine.emit(P_SMOKE, x, y, 0, 0)

    def emit_smoke(self, x: float, y: float) -> None:
        """Emit a single smoke particle for the destruction-fall
        smoke trail. Slow upward drift, small random horizontal
        velocity, gray color, 0.6s lifetime.

        The engine's P_SMOKE config handles the visual evolution
        (expands, fades, rises via accel). We just need to set
        the initial conditions and override the color.
        """
        self.engine.emit(
            P_SMOKE,
            x, y,
            random.uniform(-3.0, 3.0),   # vx: small horizontal drift
            random.uniform(-12.0, -4.0), # vy: slight upward initial kick
            color=(180, 180, 180),       # gray, not engine default (120, 120, 140)
            life=0.6,
        )

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

    def emit_bullet_particle(self, x: float, y: float, kind: int,
                              color: tuple[int, int, int] | None = None,
                              intensity: float = 1.0,
                              particles_per_frame: float = 0.0) -> None:
        """Emit a single bullet-trail particle. Caller throttles.

        2026-09-06 visual polish v2: every player bullet emits
        per-weapon particles (P_SPARK for most weapons, P_DUST
        for green acid, P_GLOW for purple void, P_FIRE for
        orange fireball). The engine kind/color/intensity come
        from the WeaponVFX dataclass for the bullet's weapon.

        `particles_per_frame <= 0.0` or `intensity <= 0.0` = skip emit
        (no-op). Pass the per-frame rate from the weapon's
        WeaponVFX so the no-op marker works without coupling
        `intensity` to the emission rate.
        """
        if intensity <= 0.0 or particles_per_frame <= 0.0:
            return
        vx = random.uniform(-25, 25)
        vy = random.uniform(-25, 25)
        self.engine.emit(
            kind, x, y, vx, vy,
            color=color,
            life=0.2 * intensity,
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
        # v1.7: tick shockwaves and reap dead ones. list() copy
        # because we mutate the list during iteration.
        for sw in self.shockwaves:
            sw.update(dt)
        self.shockwaves = [sw for sw in self.shockwaves if sw.alive]
        # v1.7: tick FxLayer screen shake. Linear decay: amplitude
        # scales with remaining life. shake_amplitude is held at
        # its initial value (the "peak" amplitude) so callers can
        # read the cap; only shake_life ticks down.
        if self.shake_life > 0.0:
            self.shake_life = max(0.0, self.shake_life - dt)
            if self.shake_life <= 0.0:
                self.shake_amplitude = 0.0
                self.shake_max_life = 0.0
        # v1.7: tick flashes. Reap dead.
        if self._flashes:
            new_flashes = []
            for fl in self._flashes:
                _x, _y, _r, _c, life, _max_life = fl
                life -= dt
                if life > 0.0:
                    new_flashes.append(
                        (_x, _y, _r, _c, life, _max_life)
                    )
            self._flashes = new_flashes

    def draw(self, surface) -> None:
        self.engine.draw(surface)
        # v1.7: shockwaves drawn on top of the particle layer.
        # Each is a hollow circle (stroke 2) whose alpha lerps
        # from 255 to 0 over its lifetime.
        for sw in self.shockwaves:
            if not sw.alive:
                continue
            alpha = sw.alpha_255()
            if alpha <= 0:
                continue
            # SRCALPHA temp surface so we can stroke with alpha.
            r = max(1, int(sw.radius))
            size = r * 2 + 4
            tmp = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(
                tmp, (*sw.color, alpha),
                (size // 2, size // 2), r, sw.width,
            )
            surface.blit(tmp, (int(sw.x - size // 2),
                               int(sw.y - size // 2)))
        # v1.7: flash overlays. Each is a filled translucent disc
        # at the impact point. Drawn after shockwaves so the bright
        # center "punch" reads on top of the expanding ring.
        for fl in self._flashes:
            x, y, radius, color, life, max_life = fl
            if max_life <= 0.0:
                continue
            progress = 1.0 - (life / max_life)
            alpha = int(255 * (1.0 - progress))
            if alpha <= 0:
                continue
            r = max(1, int(radius * (1.0 + 0.3 * progress)))
            size = r * 2 + 4
            tmp = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(
                tmp, (*color, alpha),
                (size // 2, size // 2), r,
            )
            surface.blit(tmp, (int(x - size // 2),
                               int(y - size // 2)))

    def shake_offset(self) -> tuple[float, float]:
        """Return the FxLayer's current shake offset (px). Random
        in (-amp, +amp) for x, 0 for y (vertical shake on a
        horizontal shmup reads as "off" -- the playfield is taller
        than it is wide and a vertical jitter fights the player's
        position). Returns (0, 0) when no shake is active.
        """
        if self.shake_life <= 0.0 or self.shake_max_life <= 0.0:
            return (0.0, 0.0)
        # Amplitude scales with remaining life (linear decay).
        progress = self.shake_life / self.shake_max_life
        amp = self.shake_amplitude * progress
        # Random within (-amp, +amp). random.uniform returns a
        # float in [a, b].
        return (random.uniform(-amp, amp), 0.0)

    # ----- v1.7: new FX primitives for the ChargedDisc -----

    def emit_shockwave(self, x: float, y: float,
                       radius: float = DEFAULT_SHOCKWAVE_MAX_RADIUS,
                       color: tuple[int, int, int] = (255, 255, 255),
                       life: float = DEFAULT_SHOCKWAVE_LIFE_S) -> None:
        """Spawn an expanding ring at (x, y). The ring starts at
        radius 0 and grows to `radius` over `life` seconds while
        fading from full alpha to 0.
        """
        self.shockwaves.append(
            Shockwave(
                x=x, y=y,
                radius=0.0, max_radius=float(radius),
                life=float(life), max_life=float(life),
                color=color, width=2,
            )
        )

    def add_screen_shake(self, amplitude: float,
                         duration: float) -> None:
        """Kick the FxLayer's screen shake. `amplitude` is the peak
        offset in px (capped at SHAKE_AMPLITUDE_CAP=6.0). `duration`
        is the total decay time in seconds. New kicks are
        max-merged with the current state: the new kick only
        raises the amplitude / life if it's stronger than the
        in-flight one, so a 1px kick doesn't reset a 5px shake
        that's still decaying.
        """
        if duration <= 0.0 or amplitude <= 0.0:
            return
        amp = min(float(amplitude), SHAKE_AMPLITUDE_CAP)
        dur = float(duration)
        if self.shake_life <= 0.0 or amp > self.shake_amplitude:
            # Fresh shake (or stronger than the current one).
            self.shake_amplitude = amp
            self.shake_max_life = dur
            self.shake_life = dur
        # else: keep the existing shake. A weaker kick mid-decay
        # doesn't reset the clock; the spec's anti-pattern note
        # "Screen shake acumula 2 eventos simultaneos" wants the
        # cap to win, not the latest input.

    def add_flash(self, x: float, y: float,
                  radius: float = DEFAULT_FLASH_RADIUS,
                  color: tuple[int, int, int] = (255, 255, 255),
                  duration: float = DEFAULT_FLASH_LIFE_S) -> None:
        """Spawn a brief bright disc at (x, y). Used for the
        ChargedDisc first-hit "punch". Multiple flashes stack
        (each one renders), so a flurry of hits produces a
        short-lived strobe -- which is the intended read.
        """
        if duration <= 0.0:
            return
        self._flashes.append(
            (float(x), float(y), float(radius), color,
             float(duration), float(duration))
        )

    @property
    def particles(self):
        """List of currently-active particles. Read-only view for tests/debug."""
        return [p for p in self.engine.pool if p.active]
