"""ChargedDisc procedural renderer.

v1.7: 3 visual stages:
  1) CHARGING (preview at the muzzle, drawn by the gameplay scene):
     small disc that grows from 8px to 40px over the 1.0s charge
     time, with 3 concentric rotating rings starting at 85% charge
     and a sin-based alpha pulse at 100%.

  2) FLYING (in-flight disc):
     - White filled circle (RADIUS=40)
     - White outline ring
     - 3 concentric rotating rings during the first 0.3s (the
       "spin residual" after release)
     - Trail: 1-2 P_SPARK particles per frame at (x - 4, y)

  3) FADING (post-impact, no more hits possible):
     - alpha lerps 255 -> 0 over FADE_DURATION_S
     - scale lerps 1.0 -> 1.3 (the "burst" before disappearance)
     - rotation ring spin continues at 1.0x speed (looks like the
       disc is bursting outward)

All rendering uses pygame.draw primitives. No sprites, no AI-gen.
The renderer is purely stateless -- it reads the disc's state
fields and computes the visuals on the fly.
"""
from __future__ import annotations

import math

import pygame

from stellar_horizon.entities.charged_disc import ChargedDisc, State


# ----- Charge preview (drawn at the muzzle while SPACE is held) -----

# Preview size: lerp from 8px to 40px over the 1.0s charge time.
PREVIEW_MIN_RADIUS = 8.0
PREVIEW_MAX_RADIUS = 40.0
# When do the rotating rings kick in (fraction of full charge).
RINGS_APPEAR_FRAC = 0.85
# When does the body alpha start pulsing (fraction of full charge).
PULSE_APPEAR_FRAC = 0.85


def _ease_out_cubic(t: float) -> float:
    """Cubic ease-out: fast at the start, gentle at the end. Gives
    the disc growth a more natural 'snap into place' feel than a
    pure linear lerp.
    """
    p = 1.0 - t
    return 1.0 - p * p * p


def draw_charging_preview(surface: pygame.Surface, x: float, y: float,
                          charge_time: float, full_charge_time: float,
                          now: float) -> None:
    """Render the disc preview at the muzzle while the player holds
    SPACE. `charge_time` is seconds held; `full_charge_time` is the
    per-weapon threshold (1.0s for weapon 1). `now` is the scene
    clock for ring rotation phase.

    No-op when charge_time <= 0.0.
    """
    if charge_time <= 0.0 or full_charge_time <= 0.0:
        return
    frac = max(0.0, min(1.0, charge_time / full_charge_time))
    radius = PREVIEW_MIN_RADIUS + (PREVIEW_MAX_RADIUS - PREVIEW_MIN_RADIUS) * _ease_out_cubic(frac)
    # Body alpha. Pulses on the high end of the charge (>=85%) so the
    # player gets a "ready" cue, matching the ShipChargeOrb pattern.
    base_alpha = 220
    pulse_alpha = base_alpha
    if frac >= PULSE_APPEAR_FRAC:
        # sin(t * 10) over [-1, 1] -> [0.5, 0.8] alpha envelope
        # (per spec: alpha 0.5-0.8)
        env = 0.5 + 0.3 * (0.5 + 0.5 * math.sin(now * 10.0))
        pulse_alpha = int(255 * env)
    # 1) Body (filled white disc)
    size = int(radius * 2 + 6)
    orb = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2
    pygame.draw.circle(
        orb, (255, 255, 255, pulse_alpha), (cx, cy), int(radius),
    )
    # 2) Outline ring
    pygame.draw.circle(
        orb, (255, 255, 255, 255), (cx, cy), int(radius), 2,
    )
    # 3) Rotating concentric rings (kick in at 85% charge)
    if frac >= RINGS_APPEAR_FRAC:
        # Outer ring rotates at 90 deg/s
        _draw_rotating_ring(orb, cx, cy, radius * 0.6,
                            1, (255, 255, 255), now * 90.0)
        # Middle ring rotates at 180 deg/s, lighter blue tint
        _draw_rotating_ring(orb, cx, cy, radius * 0.4,
                            1, (200, 240, 255), now * 180.0)
        # Inner ring rotates at 360 deg/s (the fastest, the "core")
        _draw_rotating_ring(orb, cx, cy, radius * 0.2,
                            1, (255, 255, 255), now * 360.0)
    surface.blit(orb, (int(x - size // 2), int(y - size // 2)))


def _draw_rotating_ring(surface: pygame.Surface, cx: int, cy: int,
                        radius: float, width: int,
                        color: tuple[int, int, int],
                        angle_deg: float) -> None:
    """Draw a 3-quarter-arc ring at (cx, cy) with `radius`, rotated
    by `angle_deg` (clockwise). Implemented as 3 line segments that
    form a 3/4 circle -- the missing 1/4 is the visual "rotation
    gap" that makes the spin read clearly.
    """
    a_rad = math.radians(angle_deg)
    # Three quarter-arc spans, each 90 degrees (pi/2 rad).
    # Start at the rotation angle, span 3 * pi/2 total.
    n_arcs = 3
    arc_span = math.pi / 2
    samples_per_arc = 8
    prev_x = cx + math.cos(a_rad) * radius
    prev_y = cy + math.sin(a_rad) * radius
    for i in range(n_arcs):
        for s in range(1, samples_per_arc + 1):
            t_a = a_rad + (i * arc_span) + (s / samples_per_arc) * arc_span
            nx = cx + math.cos(t_a) * radius
            ny = cy + math.sin(t_a) * radius
            pygame.draw.line(
                surface, color,
                (int(prev_x), int(prev_y)), (int(nx), int(ny)),
                width,
            )
            prev_x, prev_y = nx, ny


# ----- In-flight and fading disc -----

# How long after spawn the residual rings keep spinning.
RESIDUAL_SPIN_S = 0.3


def draw(surface: pygame.Surface, disc: ChargedDisc, now: float) -> None:
    """Render the disc's body on `surface`. `now` is the scene clock
    for ring rotation phase. The renderer is a pure function of the
    disc's state -- no internal state, no allocations beyond the
    per-frame alpha surface.
    """
    if not disc.alive:
        return
    # Alpha + scale per state
    alpha = disc.fade_alpha()
    if alpha <= 0:
        return
    scale = disc.fade_scale()
    radius = int(ChargedDisc.RADIUS * scale)
    if radius <= 0:
        return
    # Per-pixel-alpha surface (recreated each frame; the disc is
    # small enough that the cost is negligible). Sized to the
    # largest possible extent so the rotating rings + outline
    # never get clipped.
    size = int(radius * 2 + 12)
    orb = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2
    # 1) Body: filled white disc
    pygame.draw.circle(
        orb, (255, 255, 255, alpha), (cx, cy), radius,
    )
    # 2) Outline ring (no alpha on the outline so it stays crisp
    #    even when the body is fading).
    pygame.draw.circle(
        orb, (255, 255, 255, alpha), (cx, cy), radius, 2,
    )
    # 3) Rotating rings (residual spin during FLYING's first 0.3s
    #    and continuously during FADING -- the "burst" effect).
    show_rings = (
        (disc.state is State.FLYING and disc.elapsed <= RESIDUAL_SPIN_S)
        or disc.state is State.FADING
    )
    if show_rings:
        # The phase is offset by elapsed so each frame ticks forward
        # (matches the live preview's behavior, no jump on spawn).
        phase = now * 1.0
        _draw_rotating_ring(orb, cx, cy, radius * 0.6,
                            1, (255, 255, 255, alpha),
                            phase * 90.0)
        _draw_rotating_ring(orb, cx, cy, radius * 0.4,
                            1, (200, 240, 255, alpha),
                            phase * 180.0)
        _draw_rotating_ring(orb, cx, cy, radius * 0.2,
                            1, (255, 255, 255, alpha),
                            phase * 360.0)
    surface.blit(orb, (int(disc.x - size // 2), int(disc.y - size // 2)))


def emit_trail(fx, disc: ChargedDisc) -> None:
    """Spawn 1-2 white trail particles at (disc.x - 4, disc.y) for
    the in-flight disc. Called once per frame from the gameplay
    scene. No-op during FADING (the disc is a visual ghost, no
    trail -- the rings already imply the burst).
    """
    if not disc.alive:
        return
    if disc.state is not State.FLYING:
        return
    if fx is None:
        return
    # Use the existing emit_trail helper on FxLayer (a single
    # P_SPARK per call, throttled by intensity).
    fx.emit_trail(disc.x - 4, disc.y, (255, 255, 255), intensity=0.5)
    fx.emit_trail(disc.x - 6, disc.y + 2, (200, 230, 255), intensity=0.3)


__all__ = ["draw", "draw_charging_preview", "emit_trail",
           "PREVIEW_MIN_RADIUS", "PREVIEW_MAX_RADIUS"]
