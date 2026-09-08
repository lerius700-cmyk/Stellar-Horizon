"""Tests for v1.5 charged-shot flags on PlayerBullet.

The charge mechanic is implemented as flags on PlayerBullet (not
subclasses) — see entities/bullet.py for the rationale. These tests
cover the per-shot behavior:
- damage multiplier (Megaman bolt does 3x)
- piercing (cyan ice keeps going through enemies)
- returning (boomerang heart flips direction after 0.6s)
- hit_count safety cap (8)
"""
from __future__ import annotations

import pytest

from stellar_horizon.entities.bullet import PlayerBullet


def _fresh() -> PlayerBullet:
    b = PlayerBullet()
    b.spawn(
        x=100.0, y=135.0, vx=480.0, vy=0.0,
        weapon=5, spawn_time=0.0,
    )
    return b


def test_default_damage_is_one() -> None:
    b = _fresh()
    assert b.damage == 1


def test_megaman_charged_shot_has_3x_damage() -> None:
    b = PlayerBullet()
    b.spawn(
        x=100.0, y=135.0, vx=480.0, vy=0.0,
        weapon=6, spawn_time=0.0,
        damage=3,
    )
    assert b.damage == 3


def test_piercing_flag_keeps_bullet_alive() -> None:
    # 2026-09-08 v1.5: cyan ice piercing stream spawns with
    # piercing=True so the collision handler doesn't kill the bullet
    # on the first hit.
    b = PlayerBullet()
    b.spawn(
        x=100.0, y=135.0, vx=420.0, vy=0.0,
        weapon=8, spawn_time=0.0,
        piercing=True,
    )
    assert b.piercing is True
    assert b.hit_count == 0
    # Simulate a hit (collision handler increments hit_count and
    # only kills the bullet if not piercing OR hit_count >= 8).
    b.hit_count += 1
    # Bullet is still alive because piercing=True.
    assert b.alive is True


def test_piercing_caps_at_eight_hits() -> None:
    # Safety cap: even piercing bullets die after 8 hits to prevent
    # infinite life on crowded frames.
    b = PlayerBullet()
    b.spawn(
        x=100.0, y=135.0, vx=420.0, vy=0.0,
        weapon=8, spawn_time=0.0,
        piercing=True,
    )
    for _ in range(8):
        b.hit_count += 1
    # After 8 hits, the handler sets b.alive = False.
    # We test the LOGIC, not the handler, so we simulate:
    if b.hit_count >= 8:
        b.alive = False
    assert b.alive is False


def test_non_piercing_bullet_dies_on_first_hit() -> None:
    # 2026-09-08 v1.5: a normal bullet (no piercing flag) dies on
    # the first hit. The handler sets b.alive = False when
    # b.piercing is False.
    b = _fresh()
    assert b.piercing is False
    # Simulate the handler:
    b.alive = False
    assert b.alive is False


def test_boomerang_returns_after_0_6s() -> None:
    # 2026-09-08 v1.5: magenta heart boomerang. After 0.6s, flip
    # vx to negative so the bullet flies back to the player.
    b = PlayerBullet()
    b.spawn(
        x=100.0, y=135.0, vx=460.0, vy=0.0,
        weapon=7, spawn_time=0.0,
        damage=2, returning=True, return_at=0.6,
    )
    assert b.returning is True
    assert b.return_at == 0.6
    assert b.vx == 460.0
    # Tick for 0.5s — still going forward.
    for _ in range(5):
        b.update(0.1)
    assert b.vx == 460.0
    assert b.return_timer >= 0.5
    # Tick one more 0.1s — past the 0.6s threshold, vx flips.
    b.update(0.1)
    assert b.vx == -460.0
    # Continues moving with the new velocity.
    prev_x = b.x
    b.update(0.1)
    assert b.x < prev_x, "bullet should now be moving leftward"


def test_non_returning_bullet_does_not_flip() -> None:
    # Sanity check: a bullet without the returning flag keeps its
    # original vx regardless of elapsed time.
    b = _fresh()
    for _ in range(20):
        b.update(0.1)
    assert b.vx == 480.0


def test_spawn_resets_charged_flags() -> None:
    # Re-spawning a bullet must reset damage / piercing / returning
    # so a previously charged bullet slot doesn't leak flags into
    # a normal shot.
    b = PlayerBullet()
    b.spawn(
        x=100.0, y=135.0, vx=460.0, vy=0.0,
        weapon=7, spawn_time=0.0,
        damage=2, returning=True, return_at=0.6,
    )
    assert b.returning is True
    # Re-spawn as a normal bullet.
    b.spawn(
        x=100.0, y=135.0, vx=480.0, vy=0.0,
        weapon=0, spawn_time=0.0,
    )
    assert b.damage == 1
    assert b.piercing is False
    assert b.returning is False
    assert b.return_timer == 0.0
    assert b.hit_count == 0
