"""DEPRECATED 2026-09-08 v1.6: replaced by fx/ship_charge_orb.py.

This module is kept on disk as historical reference and so existing
test_ship_charge_aura.py can still run, but the gameplay scene no
longer imports it. The new ShipChargeOrb anchors the visual at the
muzzle (right side of the ship) instead of the body, and grows from
a tiny yellow ring into a big pulsing 3-layer energy sphere.

The v1.5 design (centered on the ship body) didn't read as "this is
what's about to fly out of the cannon" -- it read as "the ship is
glowing". The v1.6 redesign follows the user's reference video (Wan
+ Gemini, 2026-09-08) which shows the orb growing at the muzzle.

If you want this module deleted, please ask the user explicitly
(memory rule 2026-09-07: NEVER delete user files without per-instance
ask). To remove, use the trash tool and confirm first.

-- original docstring below --

Ship charge aura: Megaman-style visual on the player while fire is held.

This module is render-only — it has no game state, just a single
`draw(surface, player, weapon, charge_time)` call that the gameplay
scene invokes each frame after the player is drawn (so the aura sits
ON TOP of the ship sprite).

Per-weapon color table (matches the laser sheet palette):
    0 orange fire    -> #FF8C00
    1 white piercing -> #FFFFFF
    2 magenta heart  -> #FF44AA
    3 cyan ice       -> #88FFFF

All other weapons: aura is not drawn (returns immediately).

Visual:
    Outer ring: weapon color at 30% alpha, radius 8 + charge_time * 12
                (caps at 32).
    Inner disc: weapon color at 50% alpha, radius 4 + charge_time * 4
                (caps at 16).
    At full charge (weapons 1, 2, 3): pulse alpha with sin(t * 8)
                for a "ready" feedback (weapons with a discrete
                charge threshold).
    For weapon 0 (continuous beam): once charge_time > 0, the aura
                stays at full size (no pulse — the beam itself is the
                "ready" feedback).

The aura is drawn with a per-pixel-alpha surface so the alpha
blends correctly even when the parent surface is 24-bit.
"""
from __future__ import annotations

import math
import pygame

# 2026-09-08 v1.5: per-weapon aura color (RGB).
CHARGE_AURA_COLOR: tuple[int, int, int] = {
    0: (255, 140, 0),    # orange (flamethrower)
    1: (255, 255, 255),  # white (lightning)
    2: (255, 68, 170),   # magenta (heart)
    3: (136, 255, 255),  # cyan (ice)
}

# Aura geometry constants.
RADIUS_OUTER_BASE = 8
RADIUS_OUTER_GROWTH = 12   # px per second of charge_time
RADIUS_OUTER_MAX = 32
RADIUS_INNER_BASE = 4
RADIUS_INNER_GROWTH = 4
RADIUS_INNER_MAX = 16
ALPHA_OUTER = 76           # 30% of 255
ALPHA_INNER = 128          # 50% of 255
PULSE_SPEED = 8.0          # Hz for the full-charge pulse
# Weapons that have a DISCRETE charge threshold (1.2s / 1.5s) and
# therefore benefit from a "ready" pulse at full charge. Weapon 0
# is excluded because the beam itself signals "ready".
DISCRETE_CHARGE_WEAPONS = frozenset({1, 2, 3})


def draw(surface: pygame.Surface, x: float, y: float, weapon: int,
         charge_time: float, now: float = 0.0) -> None:
    """Render the charge aura on `surface` centered at (x, y).

    `charge_time` is the seconds the fire key has been held. When 0
    or negative, this function returns immediately (no aura).
    `now` is the scene clock (seconds); used for the pulse phase.
    """
    if charge_time <= 0.0:
        return
    color = CHARGE_AURA_COLOR.get(weapon)
    if color is None:
        # Tap-only weapon — no aura.
        return
    # Compute outer + inner radii. Cap so the aura doesn't grow
    # unbounded for weapons with very long holds.
    outer_r = min(RADIUS_OUTER_MAX,
                  RADIUS_OUTER_BASE + charge_time * RADIUS_OUTER_GROWTH)
    inner_r = min(RADIUS_INNER_MAX,
                  RADIUS_INNER_BASE + charge_time * RADIUS_INNER_GROWTH)
    outer_alpha = ALPHA_OUTER
    inner_alpha = ALPHA_INNER
    # Pulse alpha at full charge for discrete-charge weapons.
    if weapon in DISCRETE_CHARGE_WEAPONS and charge_time >= 0.3:
        # 0.6..1.0 multiplier
        pulse = 0.8 + 0.2 * (0.5 + 0.5 * math.sin(now * PULSE_SPEED))
        outer_alpha = int(outer_alpha * pulse)
        inner_alpha = int(inner_alpha * pulse)
    # Build a per-pixel-alpha surface (one frame, recycled by the
    # caller isn't worth it for a small 64x64 sprite — we recreate
    # each frame for simplicity).
    size = int(outer_r * 2 + 4)
    aura_surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2
    # Outer ring (just the outline of the disc).
    pygame.draw.circle(aura_surf, (*color, outer_alpha),
                       (cx, cy), int(outer_r), 2)
    # Inner disc.
    if inner_r > 0:
        pygame.draw.circle(aura_surf, (*color, inner_alpha),
                           (cx, cy), int(inner_r))
    # Center the aura surface on (x, y).
    surface.blit(aura_surf, (int(x - size // 2), int(y - size // 2)))
