"""WEAPON_IMPACT_PARAMS: per-weapon impact burst config.

2026-09-08 v1.5: each weapon has a unique "impact feel" -- when a bullet
hits an enemy, the burst is colored, sized, and shaped differently
per weapon. The collision handler in gameplay.py looks up the
weapon's config and forwards it to FxLayer.emit_impact().

Design constraints (from v1.5 spec):
- count: 6..14 particles per impact (low for "tactical" weapons,
  high for "explosive" ones)
- spread_deg: cone half-angle. 0 = straight forward, 90 = full
  hemisphere. Player bullets always travel in +X, so the burst
  naturally points in the bullet's direction.
- speed_px_s: initial particle speed. Higher = more "punchy".
- particle_kind: which engine particle to use (P_SPARK, P_FIRE,
  P_GLOW, P_DUST, P_FLASH).
- color: RGB triple, mixed with the engine's per-particle fade-to-white.
- lifetime_s: max particle life (engine clamps to its own max).

The existing FxLayer.emit_impact() (12 sparks + 4 shrapnel + 1 flash)
is the default for the legacy "tactical" palette. The charged
weapons 0-3 get distinct configs so the impact reads as "this is
a fire bullet" vs "this is a heart".
"""
from __future__ import annotations

from dataclasses import dataclass

from stellar_horizon._systems.systems.particle_engine import (
    P_SPARK, P_FIRE, P_GLOW, P_DUST, P_FLASH, P_SHRAPNEL,
)


@dataclass(frozen=True)
class WeaponImpactParams:
    """Per-weapon config for the impact burst.
    Frozen so the table is read-only and tests can hash it.
    """
    particle_kind: int
    color: tuple[int, int, int]
    count: int
    spread_deg: float
    speed_px_s: float
    lifetime_s: float = 0.30
    # If True, add 1 P_FLASH on top of the spark burst (for weapons
    # that should "punch" on impact, e.g., Megaman charged bolt).
    add_flash: bool = True


# 2026-09-08 v1.5 final: 5 entries, one per weapon. The "basic 5"
# (yellow/red/blue/green/purple) were removed; only the charged
# weapons + rainbow streak remain.
WEAPON_IMPACT_PARAMS: tuple[WeaponImpactParams, ...] = (
    # 0 orange fire (continuous beam) -- fire particles, very wide
    WeaponImpactParams(P_FIRE, (255, 140, 40), 12, 40.0, 130.0),
    # 1 white piercing (Megaman charged) -- white sparks + bright flash
    WeaponImpactParams(P_SPARK, (255, 255, 255), 14, 20.0, 200.0,
                       add_flash=True),
    # 2 magenta heart (boomerang) -- pink glow + hearts
    WeaponImpactParams(P_GLOW, (255, 100, 180), 12, 30.0, 110.0),
    # 3 cyan ice (piercing stream) -- cyan ice shards, medium
    WeaponImpactParams(P_SPARK, (140, 220, 255), 10, 25.0, 140.0),
    # 4 rainbow streak -- mixed color sparks
    WeaponImpactParams(P_SPARK, (255, 200, 255), 10, 20.0, 160.0),
)


def get_params(weapon: int) -> WeaponImpactParams:
    """Return the impact params for the given weapon id (0..4).
    Falls back to the default (weapon 0 = orange fire) for
    out-of-range weapons. This is a safety net -- the caller should
    pass a valid weapon id.
    """
    if 0 <= weapon < len(WEAPON_IMPACT_PARAMS):
        return WEAPON_IMPACT_PARAMS[weapon]
    return WEAPON_IMPACT_PARAMS[0]


__all__ = [
    "WeaponImpactParams",
    "WEAPON_IMPACT_PARAMS",
    "get_params",
    # Re-export particle kinds for callers that want to inspect the
    # underlying enum.
    "P_SPARK", "P_FIRE", "P_GLOW", "P_DUST", "P_FLASH", "P_SHRAPNEL",
]
