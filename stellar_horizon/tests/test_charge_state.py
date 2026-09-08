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
    # 2026-09-08 v1.5: tap-only weapons (0, 1, 2, 3, 4, 9) have
    # CHARGE_TIME_S == None. Holding the key must NOT change
    # charge_time (it's always 0).
    player.set_weapon(0)
    _press(player)
    for _ in range(10):
        player.update(0.1, {}, [], now=0.0)
    assert player.charge_time == 0.0
    assert player.charge_complete is False


def test_charge_accumulates_while_held_for_weapon_6(player: Player) -> None:
    # 2026-09-08 v1.5: weapon 6 (white piercing) has CHARGE_TIME_S=1.2s.
    # Holding the key should accumulate charge_time, and once we cross
    # 1.2s, charge_complete should be True.
    player.set_weapon(6)
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
    # 2026-09-08 v1.5: on KEYUP, charge_time resets to 0.
    player.set_weapon(6)
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


def test_weapon_5_continuous_charge_is_immediately_complete(player: Player) -> None:
    # 2026-09-08 v1.5: weapon 5 (orange fire) has CHARGE_TIME_S=0.0
    # meaning "continuous, no threshold". charge_complete should be
    # True on the first frame of holding.
    player.set_weapon(5)
    _press(player)
    player.update(0.016, {}, [], now=0.0)  # 1 frame
    assert player.charge_complete is True


def test_weapon_8_piercing_timer_increments(player: Player) -> None:
    # 2026-09-08 v1.5: weapon 8 (cyan ice) has
    # PIERCING_SPAWN_INTERVAL_S=1.5. The internal spawn timer should
    # increment each frame while held, and reset when the player
    # releases.
    player.set_weapon(8)
    _press(player)
    for _ in range(10):  # 1.0s
        player.update(0.1, {}, [], now=0.0)
    assert 0.9 <= player._piercing_spawn_timer <= 1.1
    # Release: timer resets.
    _release(player)
    player.update(0.0, {}, [], now=0.0)
    assert player._piercing_spawn_timer == 0.0


def test_switching_weapon_cancels_charge(player: Player) -> None:
    # 2026-09-08 v1.5: set_weapon() cancels any in-progress charge.
    player.set_weapon(6)
    _press(player)
    for _ in range(8):  # 0.8s
        player.update(0.1, {}, [], now=0.0)
    assert player.charge_time > 0.0
    # Switch to weapon 0 — charge should reset.
    player.set_weapon(0)
    assert player.charge_time == 0.0
    assert player.charge_complete is False


def test_charge_time_s_table_covers_all_10_weapons() -> None:
    # 2026-09-08 v1.5: CHARGE_TIME_S must have one entry per weapon.
    assert len(Player.CHARGE_TIME_S) == 10
    # Per-weapon sanity: weapons 5/8 use 0.0 (continuous), 6=1.2, 7=1.5,
    # the rest are None.
    assert Player.CHARGE_TIME_S[5] == 0.0
    assert Player.CHARGE_TIME_S[8] == 0.0
    assert Player.CHARGE_TIME_S[6] == 1.2
    assert Player.CHARGE_TIME_S[7] == 1.5
    for w in (0, 1, 2, 3, 4, 9):
        assert Player.CHARGE_TIME_S[w] is None
