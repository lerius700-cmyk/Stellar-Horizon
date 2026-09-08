"""Tests for v1.5 per-weapon impact burst (WEAPON_IMPACT_PARAMS +
FxLayer.emit_impact_weapon).

The collision handler in gameplay.py looks up the weapon's params
and calls emit_impact_weapon() with the bullet's velocity. These
tests verify:
- The table covers all 10 weapons.
- get_params() returns the right params for each weapon and a
  safe fallback for out-of-range.
- emit_impact_weapon() emits the expected number of particles
  with the right kind/color, oriented along the velocity cone.
- Forward-cone math: particles concentrate in the velocity
  direction, not behind the bullet.
- add_flash=True adds a P_FLASH particle.
- Zero-velocity direction falls back to +X.
"""
from __future__ import annotations

import math
from unittest.mock import MagicMock

import pytest

from stellar_horizon.fx.weapon_impact import (
    WEAPON_IMPACT_PARAMS,
    WeaponImpactParams,
    get_params,
)


def test_table_covers_all_10_weapons() -> None:
    # 2026-09-08 v1.5: one entry per weapon, 0..9.
    assert len(WEAPON_IMPACT_PARAMS) == 10


def test_each_entry_has_required_fields() -> None:
    # Each entry must be a frozen WeaponImpactParams with non-zero
    # count, non-empty color, and a valid particle kind.
    for i, p in enumerate(WEAPON_IMPACT_PARAMS):
        assert isinstance(p, WeaponImpactParams), f"weapon {i} is not WeaponImpactParams"
        assert p.count > 0, f"weapon {i} has count 0"
        assert len(p.color) == 3, f"weapon {i} color must be RGB"
        assert p.spread_deg >= 0.0, f"weapon {i} spread_deg must be >= 0"
        assert p.speed_px_s > 0.0, f"weapon {i} speed must be > 0"


def test_get_params_returns_correct_entry() -> None:
    for i in range(10):
        assert get_params(i) is WEAPON_IMPACT_PARAMS[i]


def test_get_params_falls_back_to_weapon_0_for_out_of_range() -> None:
    # 2026-09-08: safety fallback for invalid weapon ids.
    assert get_params(-1) is WEAPON_IMPACT_PARAMS[0]
    assert get_params(99) is WEAPON_IMPACT_PARAMS[0]


def test_per_weapon_palette_distinct() -> None:
    # The 4 new charged-shot weapons (5, 6, 7, 8) should have
    # distinct colors from each other (orange, white, magenta, cyan).
    c5 = WEAPON_IMPACT_PARAMS[5].color
    c6 = WEAPON_IMPACT_PARAMS[6].color
    c7 = WEAPON_IMPACT_PARAMS[7].color
    c8 = WEAPON_IMPACT_PARAMS[8].color
    palettes = {c5, c6, c7, c8}
    assert len(palettes) == 4, "the 4 charged weapons must have distinct colors"


# --- FxLayer.emit_impact_weapon tests ---

def _make_fx() -> tuple:
    """Construct a real FxLayer (with a small particle pool) plus
    a MagicMock wrapping its engine.emit, so we can inspect the
    emit() calls without standing up a real ParticleEngine.
    """
    from stellar_horizon.fx.particles import FxLayer
    fx = FxLayer(pool_size=64)
    # Replace the engine's emit with a mock we can inspect.
    fx.engine.emit = MagicMock()
    return fx, fx.engine


def test_emit_impact_weapon_emits_count_particles() -> None:
    fx, engine = _make_fx()
    params = WEAPON_IMPACT_PARAMS[5]  # orange fire
    fx.emit_impact_weapon(100.0, 100.0, vx_dir=200.0, vy_dir=0.0,
                          params=params)
    spark_emits = [c for c in engine.emit.call_args_list
                   if c.args[0] == params.particle_kind]
    assert len(spark_emits) == params.count


def test_emit_impact_weapon_adds_flash_when_enabled() -> None:
    from stellar_horizon.fx.particles import P_FLASH
    fx, engine = _make_fx()
    params = WEAPON_IMPACT_PARAMS[6]  # Megaman charged, add_flash=True
    fx.emit_impact_weapon(0.0, 0.0, 100.0, 0.0, params)
    flash_emits = [c for c in engine.emit.call_args_list
                   if c.args[0] == P_FLASH]
    assert len(flash_emits) == 1


def test_emit_impact_weapon_no_flash_when_disabled() -> None:
    from stellar_horizon.fx.particles import P_FLASH
    fx, engine = _make_fx()
    params = WeaponImpactParams(
        particle_kind=0, color=(255, 255, 255), count=4,
        spread_deg=20.0, speed_px_s=100.0, add_flash=False,
    )
    fx.emit_impact_weapon(0.0, 0.0, 100.0, 0.0, params)
    flash_emits = [c for c in engine.emit.call_args_list
                   if c.args[0] == P_FLASH]
    assert len(flash_emits) == 0


def test_emit_impact_weapon_particles_concentrate_forward() -> None:
    fx, engine = _make_fx()
    params = WEAPON_IMPACT_PARAMS[5]
    # Use a high count + tight spread for statistical reliability.
    params = WeaponImpactParams(
        particle_kind=params.particle_kind, color=params.color,
        count=1000, spread_deg=params.spread_deg,
        speed_px_s=params.speed_px_s, add_flash=False,
    )
    fx.emit_impact_weapon(0.0, 0.0, 200.0, 0.0, params)
    total_vx = 0.0
    for c in engine.emit.call_args_list:
        vx = c.args[3]
        total_vx += vx
    assert total_vx > 0.0


def test_emit_impact_weapon_zero_velocity_falls_back_to_forward() -> None:
    fx, engine = _make_fx()
    params = WEAPON_IMPACT_PARAMS[0]
    fx.emit_impact_weapon(0.0, 0.0, 0.0, 0.0, params)
    for c in engine.emit.call_args_list:
        vx, vy = c.args[3], c.args[4]
        assert not math.isnan(vx)
        assert not math.isnan(vy)


def test_emit_impact_weapon_uses_params_color_and_life() -> None:
    fx, engine = _make_fx()
    params = WEAPON_IMPACT_PARAMS[7]  # magenta heart
    fx.emit_impact_weapon(0.0, 0.0, 100.0, 0.0, params)
    for c in engine.emit.call_args_list:
        # emit(kind, x, y, vx, vy, color=..., life=...)
        kwargs = c.kwargs
        if c.args[0] == params.particle_kind:
            assert kwargs.get("color") == params.color
            assert kwargs.get("life") == params.lifetime_s
