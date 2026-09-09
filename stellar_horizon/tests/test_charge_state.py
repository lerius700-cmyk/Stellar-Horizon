"""Tests for v1.5 charge mechanic state on Player.

These tests cover the data-side of the charge system (state transitions
in Player.update), not the visual side (that's in test_ship_charge_aura).
"""
from __future__ import annotations

import pygame
import pytest

from stellar_horizon.entities.player import Player


@pytest.fixture
def player() -> Player:
    screen = pygame.Rect(0, 0, 480, 270)
    p = Player(screen)
    p.fx = None  # no FxLayer in unit tests
    return p


def _press(p: Player) -> None:
    p.on_fire_pressed()
    p.firing = True


def _release(p: Player) -> None:
    p.on_fire_released()
    p.firing = False


def test_tap_only_weapon_does_not_accumulate_charge(player: Player) -> None:
    # 2026-09-08 v1.5 final: tap-only weapon is 4 (rainbow streak).
    # Holding the key must NOT change charge_time (it's always 0).
    player.set_weapon(4)
    _press(player)
    for _ in range(10):
        player.update(0.1, {}, [], now=0.0)
    assert player.charge_time == 0.0
    assert player.charge_complete is False


def test_charge_accumulates_while_held_for_weapon_1(player: Player) -> None:
    # 2026-09-08 v1.5 final: weapon 1 (white piercing) has
    # CHARGE_TIME_S=1.2s. Holding the key should accumulate
    # charge_time, and once we cross 1.2s, charge_complete is True.
    player.set_weapon(1)
    _press(player)
    for _ in range(6):  # 6 * 0.1 = 0.6s
        player.update(0.1, {}, [], now=0.0)
    assert 0.5 <= player.charge_time <= 0.7
    assert player.charge_complete is False
    # Keep going to cross the 1.2s threshold.
    for _ in range(8):  # 8 * 0.1 = 0.8s more, total 1.4s
        player.update(0.1, {}, [], now=0.0)
    assert player.charge_time >= 1.2
    assert player.charge_complete is True


def test_release_resets_charge(player: Player) -> None:
    # 2026-09-08 v1.5 final: on KEYUP, charge_time resets to 0.
    player.set_weapon(1)
    _press(player)
    for _ in range(15):  # 1.5s of hold
        player.update(0.1, {}, [], now=0.0)
    assert player.charge_complete is True
    # Now release: charge resets.
    _release(player)
    player.update(0.0, {}, [], now=0.0)  # the KEYUP frame consumes the flag
    # After the release frame, charge_time should be 0 again.
    assert player.charge_time == 0.0
    assert player.charge_complete is False


def test_weapon_0_continuous_charge_is_immediately_complete(player: Player) -> None:
    # 2026-09-08 v1.5 final: weapon 0 (orange fire) has CHARGE_TIME_S=0.0
    # meaning "continuous, no threshold". charge_complete should be
    # True on the first frame of holding.
    player.set_weapon(0)
    _press(player)
    player.update(0.016, {}, [], now=0.0)  # 1 frame
    assert player.charge_complete is True


def test_weapon_3_piercing_timer_increments(player: Player) -> None:
    # 2026-09-08 v1.5 final: weapon 3 (cyan ice) has
    # PIERCING_SPAWN_INTERVAL_S=1.5. The internal spawn timer should
    # increment each frame while held, and reset when the player
    # releases.
    player.set_weapon(3)
    _press(player)
    for _ in range(10):  # 1.0s
        player.update(0.1, {}, [], now=0.0)
    assert 0.9 <= player._piercing_spawn_timer <= 1.1
    # Release: timer resets.
    _release(player)
    player.update(0.0, {}, [], now=0.0)
    assert player._piercing_spawn_timer == 0.0


def test_switching_weapon_cancels_charge(player: Player) -> None:
    # 2026-09-08 v1.5 final: set_weapon() cancels any in-progress charge.
    player.set_weapon(1)
    _press(player)
    for _ in range(8):  # 0.8s
        player.update(0.1, {}, [], now=0.0)
    assert player.charge_time > 0.0
    # Switch to weapon 4 (tap-only) — charge should reset.
    player.set_weapon(4)
    assert player.charge_time == 0.0
    assert player.charge_complete is False


def test_charge_time_s_table_covers_all_5_weapons() -> None:
    # 2026-09-08 v1.5 final: CHARGE_TIME_S must have one entry per
    # of the 5 weapons. Weapons 0/3 use 0.0 (continuous), 1=1.2,
    # 2=1.5, 4 is None (tap-only).
    assert len(Player.CHARGE_TIME_S) == 5
    assert Player.CHARGE_TIME_S[0] == 0.0
    assert Player.CHARGE_TIME_S[3] == 0.0
    assert Player.CHARGE_TIME_S[1] == 1.2
    assert Player.CHARGE_TIME_S[2] == 1.5
    assert Player.CHARGE_TIME_S[4] is None
