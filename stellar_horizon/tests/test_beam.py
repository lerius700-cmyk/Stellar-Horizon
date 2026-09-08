"""Tests for v1.5 Beam entity (weapon 5 = orange fire "lanzallamas").

The Beam is a single entity (not pool-managed) that:
- Connects a start point (muzzle) to an end point (impact or range).
- Damages enemies within HIT_RADIUS_PX of the line segment.
- Has per-enemy hit cooldowns to avoid instant-killing a row.
- Emits dispersion particles on each hit.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from stellar_horizon.entities.beam import Beam


def test_beam_defaults_to_inactive() -> None:
    beam = Beam()
    assert beam.alive is False


def test_beam_spawn_activates_with_endpoints() -> None:
    beam = Beam()
    beam.spawn(start_x=100.0, start_y=135.0,
               end_x=200.0, end_y=135.0,
               spawn_time=1.0)
    assert beam.alive is True
    assert beam.start_x == 100.0
    assert beam.start_y == 135.0
    assert beam.end_x == 200.0
    assert beam.end_y == 135.0


def test_beam_despawn_deactivates() -> None:
    beam = Beam()
    beam.spawn(0.0, 0.0, 100.0, 0.0, 0.0)
    assert beam.alive is True
    beam.despawn()
    assert beam.alive is False


def test_beam_damages_enemy_within_radius() -> None:
    beam = Beam()
    beam.spawn(start_x=100.0, start_y=135.0,
               end_x=200.0, end_y=135.0, spawn_time=0.0)
    # Enemy directly on the line.
    enemy = MagicMock()
    enemy.alive = True
    enemy.x, enemy.y = 150.0, 135.0
    fx = MagicMock()
    beam.damage_enemies_in_strip([enemy], fx)
    enemy.take_damage.assert_called_once_with(beam.DAMAGE_PER_TICK)
    fx.emit_impact.assert_called_once()
    assert id(enemy) in beam._hit_cooldown


def test_beam_skips_enemy_outside_radius() -> None:
    beam = Beam()
    beam.spawn(start_x=100.0, start_y=135.0,
               end_x=200.0, end_y=135.0, spawn_time=0.0)
    # Enemy far above the line.
    enemy = MagicMock()
    enemy.alive = True
    enemy.x, enemy.y = 150.0, 50.0  # 85 px above, way past HIT_RADIUS_PX
    fx = MagicMock()
    beam.damage_enemies_in_strip([enemy], fx)
    enemy.take_damage.assert_not_called()
    fx.emit_impact.assert_not_called()


def test_beam_hit_cooldown_prevents_double_damage() -> None:
    # 2026-09-08 v1.5: per-enemy cooldown. Two consecutive
    # damage_enemies_in_strip() calls should hit the same enemy
    # only once until the cooldown expires.
    beam = Beam()
    beam.spawn(0.0, 0.0, 100.0, 0.0, 0.0)
    enemy = MagicMock()
    enemy.alive = True
    enemy.x, enemy.y = 50.0, 0.0
    fx = MagicMock()
    beam.damage_enemies_in_strip([enemy], fx)
    beam.damage_enemies_in_strip([enemy], fx)  # should be no-op
    assert enemy.take_damage.call_count == 1


def test_beam_skips_dead_enemies() -> None:
    beam = Beam()
    beam.spawn(0.0, 0.0, 100.0, 0.0, 0.0)
    enemy = MagicMock()
    enemy.alive = False
    enemy.x, enemy.y = 50.0, 0.0
    fx = MagicMock()
    beam.damage_enemies_in_strip([enemy], fx)
    enemy.take_damage.assert_not_called()


def test_beam_advance_tick_fires_at_interval() -> None:
    beam = Beam()
    beam.spawn(0.0, 0.0, 100.0, 0.0, 0.0)
    # Initially no tick is due.
    assert beam.advance_tick(0.01) is False
    # After accumulating past TICK_INTERVAL_S, a tick fires.
    fired = beam.advance_tick(beam.TICK_INTERVAL_S)
    assert fired is True
    # Right after a tick, no more are due.
    assert beam.advance_tick(0.0) is False


def test_beam_inactive_no_damage() -> None:
    beam = Beam()
    # Beam was never spawned.
    enemy = MagicMock()
    enemy.alive = True
    fx = MagicMock()
    beam.damage_enemies_in_strip([enemy], fx)
    enemy.take_damage.assert_not_called()


def test_beam_update_start_moves_muzzle() -> None:
    beam = Beam()
    beam.spawn(100.0, 135.0, 200.0, 135.0, 0.0)
    beam.update_start(150.0, 140.0)
    assert beam.start_x == 150.0
    assert beam.start_y == 140.0
    # End stays the same — update_start only moves the muzzle.
    assert beam.end_x == 200.0


def test_beam_point_in_strip_handles_zero_length_segment() -> None:
    # Edge case: start == end. No enemy should match.
    beam = Beam()
    beam.spawn(100.0, 100.0, 100.0, 100.0, 0.0)
    # _point_in_strip should return False because seg_len_sq == 0.
    assert beam._point_in_strip(100.0, 100.0, 100.0) is False
    assert beam._point_in_strip(50.0, 50.0, 100.0) is False


def test_beam_hit_radius_at_endpoints() -> None:
    # A point AT the start should be in the strip (within radius).
    # A point at the end should be in the strip (within radius).
    # A point WAY past the end should be OUT (t clamps to 1.0, so
    # the projection is the end point, and the distance is > radius).
    beam = Beam()
    beam.spawn(0.0, 0.0, 100.0, 0.0, 0.0)
    radius = beam.HIT_RADIUS_PX
    # At start
    assert beam._point_in_strip(0.0, 0.0, radius) is True
    # At end
    assert beam._point_in_strip(100.0, 0.0, radius) is True
    # Just past the end (5 px past) — clamped to endpoint at (100, 0),
    # distance is 5, within radius 10.
    assert beam._point_in_strip(105.0, 0.0, radius) is True
    # Way past the end (50 px past) — clamped to endpoint, distance
    # is 50, way outside radius 10.
    assert beam._point_in_strip(150.0, 0.0, radius) is False
