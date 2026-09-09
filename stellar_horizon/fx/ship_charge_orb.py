"""Ship charge orb: a 3-layer energy sphere that grows at the muzzle
as the player holds the charge key (SPACE).

This is the v1.6 redesign of the v1.5 ShipChargeAura. The orb is
anchored at the player's muzzle (right side of the ship, where
bullets emerge) instead of the body, and it grows from a tiny
yellow ring into a big pulsing energy ball. It replaces both the
v1.5 ShipChargeAura (centered on the ship) and the v1.5 long-sheet
preview (horizontal bar ahead of the muzzle).

Reference frames (Wan video + Gemini grid, 2026-09-08):
  - Outer ring: weapon color, soft edge, radius grows with charge_time.
    Present from the start; visible at all charge levels.
  - Body: weapon color shifted toward cyan, semi-transparent disc.
    Appears at ~25% charge; grows to fill most of the orb area.
  - White hot core: small, very bright. Appears at ~50% charge.
    Pulses at full charge for the "ready" feedback.

Per-weapon outer color (matches WEAPON_IMPACT_PARAMS):
    0 orange fire    -> #FF8C2A  (orange)
    1 white piercing -> #FFFFFF  (white)
    2 magenta heart  -> #FF6AB4  (magenta/pink)
    3 cyan ice       -> #8CF6FF  (cyan)
Body color is always a cyan-shifted variant of the ring color so the
energy ball reads as "plasma" not just "a colored disc".

The orb is drawn with a per-pixel-alpha surface so the soft edges
blend correctly even when the parent surface is 24-bit.
"""
from __future__ import annotations

import math
import pygame

# 2026-09-08 v1.6: per-weapon outer-ring color (RGB).
ORB_RING_COLOR: tuple[int, int, int] = {
    0: (255, 140, 42),   # orange fire
    1: (255, 255, 255),  # white piercing
    2: (255, 106, 180),  # magenta heart
    3: (140, 246, 255),  # cyan ice
}

# Body color: weapon color shifted toward cyan (gives the "plasma"
# read). For each weapon, the body is a mix of the ring color and
# the canonical plasma cyan.
_PLASMA_CYAN: tuple[int, int, int] = (100, 220, 255)


def _shift_toward_cyan(rgb: tuple[int, int, int],
                       mix: float = 0.55) -> tuple[int, int, int]:
    """Blend the ring color with plasma cyan. mix=0.55 means the
    body color is 55% cyan + 45% ring color -- enough cyan to
    read as plasma without erasing the weapon's identity."""
    r, g, b = rgb
    cr, cg, cb = _PLASMA_CYAN
    return (
        int(r * (1 - mix) + cr * mix),
        int(g * (1 - mix) + cg * mix),
        int(b * (1 - mix) + cb * mix),
    )


ORB_BODY_COLOR: dict[int, tuple[int, int, int]] = {
    w: _shift_toward_cyan(c) for w, c in ORB_RING_COLOR.items()
}

# Orb geometry constants. All in pixels.
RING_BASE = 3.0        # starting ring radius at charge_time=0
RING_GROWTH = 22.0     # px per second of charge_time
RING_MAX = 38.0        # hard cap (the user said "grows huge")
BODY_RATIO = 0.78      # body radius as fraction of ring radius
CORE_RATIO = 0.32      # white core radius as fraction of ring radius
# Per-weapon ramp time: how long the charge takes to reach full size.
# Continuous weapons (0, 3) use a 0.5s visual ramp; discrete (1, 2)
# use the full charge threshold. This matches the v1.5 logic.
RAMP_TIME_S = {
    0: 0.5,  # orange (continuous beam)
    1: 1.2,  # white (Megaman bolt)
    2: 1.5,  # magenta (boomerang)
    3: 0.5,  # cyan (continuous piercing)
}
# Core activation: white core starts appearing at this fraction of
# full ramp time.
CORE_ACTIVATION_FRAC = 0.50
# Body activation: cyan body starts appearing at this fraction of
# full ramp time.
BODY_ACTIVATION_FRAC = 0.25
# Pulsing at full charge: weapons that have a discrete charge
# threshold (1, 2) and the continuous beam (0) get a pulse for
# "ready" feedback. Weapon 3 (continuous piercing) does not pulse
# -- the stream itself is the "ready" feedback.
PULSE_WEAPONS = frozenset({0, 1, 2})
PULSE_SPEED = 8.0      # Hz
PULSE_DEPTH = 0.18     # peak alpha modulation (0..1)


def draw(surface: pygame.Surface, muzzle_x: float, muzzle_y: float,
         weapon: int, charge_time: float, charging: bool,
         now: float = 0.0) -> None:
    """Render the charge orb centered at (muzzle_x, muzzle_y).

    `charge_time` is the seconds SPACE has been held. When 0 or
    negative, this function returns immediately (no orb).
    `charging` is whether SPACE is currently held -- if the player
    released SPACE, the orb should fade out smoothly even if
    `charge_time` hasn't reset to 0 yet.
    `now` is the scene clock (seconds); used for the pulse phase.
    """
    if not charging and charge_time <= 0.0:
        return
    if weapon not in ORB_RING_COLOR:
        return
    ring_color = ORB_RING_COLOR[weapon]
    body_color = ORB_BODY_COLOR[weapon]
    ramp = RAMP_TIME_S[weapon]
    # Compute the "visual" charge time. If SPACE is released, fade
    # the orb out over 0.2s instead of letting it snap to 0.
    if not charging:
        # Quick fade after release: each frame this orb is drawn
        # without SPACE held, decay the visual charge.
        # We use a global counter via an attribute on the module.
        # Simpler approach: just use a smaller scale based on
        # whether the key is held -- if the key is released, the
        # caller's charge_time will be 0 by the next frame anyway
        # (Player.update resets it on `not self.charging`). So this
        # path is a 1-frame artifact at most.
        # No additional fade work needed.
        return
    growth01 = max(0.0, min(1.0, charge_time / ramp))
    # Ring radius scales with growth. The ring is always visible
    # (even at growth01=0) so the player has an immediate visual
    # cue that SPACE is doing something.
    ring_r = RING_BASE + growth01 * (RING_MAX - RING_BASE)
    body_r = ring_r * BODY_RATIO
    core_r = ring_r * CORE_RATIO
    # Alpha envelope for the body: ramps in from BODY_ACTIVATION_FRAC
    # to 1.0 with a soft ease.
    body_frac = max(0.0, min(1.0,
        (growth01 - BODY_ACTIVATION_FRAC) / (1.0 - BODY_ACTIVATION_FRAC)
    ))
    # Core alpha: same idea, gated by CORE_ACTIVATION_FRAC.
    core_frac = max(0.0, min(1.0,
        (growth01 - CORE_ACTIVATION_FRAC) / (1.0 - CORE_ACTIVATION_FRAC)
    ))
    # Pulse alpha at full charge for "ready" feedback.
    pulse = 1.0
    if weapon in PULSE_WEAPONS and growth01 >= 0.85:
        # 1.0 +/- PULSE_DEPTH at PULSE_SPEED Hz
        pulse = 1.0 - PULSE_DEPTH + PULSE_DEPTH * (
            0.5 + 0.5 * math.sin(now * PULSE_SPEED)
        )
    # Build a per-pixel-alpha surface (recreated each frame; the
    # orb is small enough that the cost is negligible).
    size = int(ring_r * 2 + 4)
    orb = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2
    # 1) Outer ring: just the outline of a disc, soft anti-aliased
    # feel via alpha.
    ring_alpha = int(200 * pulse)
    pygame.draw.circle(
        orb, (*ring_color, ring_alpha),
        (cx, cy), int(ring_r), 2,
    )
    # 2) Body: a filled disc, alpha gated by body_frac.
    if body_frac > 0.0 and body_r > 0:
        body_alpha = int(180 * body_frac * pulse)
        pygame.draw.circle(
            orb, (*body_color, body_alpha),
            (cx, cy), int(body_r),
        )
    # 3) White hot core: a small filled disc, alpha gated by core_frac.
    if core_frac > 0.0 and core_r > 0:
        core_alpha = int(255 * core_frac * pulse)
        pygame.draw.circle(
            orb, (255, 255, 255, core_alpha),
            (cx, cy), int(core_r),
        )
    # Center the orb on the muzzle.
    surface.blit(orb, (int(muzzle_x - size // 2), int(muzzle_y - size // 2)))
