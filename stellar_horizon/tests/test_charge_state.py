"""Tests for v1.6 charge mechanic state on Player.

v1.6 control scheme:
  B (tap)         -> tier-1 basic bullet per weapon
  SPACE (hold+rel)-> tier-2 charged behavior per weapon
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


def _tap_press(p: Player) -> None:
    p.on_tap_pressed()
    p.firing = True


def _tap_release(p: Player) -> None:
    p.on_tap_released()
    p.firing = False


def _charge_press(p: Player) -> None:
    p.on_charge_pressed()
    p.charging = True


def _charge_release(p: Player) -> None:
    p.on_charge_released()
    p.charging = False


def test_tap_only_weapon_does_not_accumulate_charge(player: Player) -> None:
    # 2026-09-08 v1.6: tap-only weapon is 4 (rainbow streak).
    # SPACE must NOT change charge_time (it's always 0).
    player.set_weapon(4)
    _charge_press(player)
    for _ in range(10):
        player.update(0.1, {}, [], now=0.0)
    assert player.charge_time == 0.0
    assert player.charge_complete is False


def test_charge_accumulates_while_held_for_weapon_1(player: Player) -> None:
    # 2026-09-08 v1.6: weapon 1 (white piercing) CHARGE_TIME_S=1.2s.
    # Holding SPACE accumulates charge_time, and once we cross
    # 1.2s, charge_complete is True.
    player.set_weapon(1)
    _charge_press(player)
    for _ in range(6):  # 6 * 0.1 = 0.6s
        player.update(0.1, {}, [], now=0.0)
    assert 0.5 <= player.charge_time <= 0.7
    assert player.charge_complete is False
    # Keep going to cross the 1.2s threshold.
    for _ in range(8):  # 8 * 0.1 = 0.8s more, total 1.4s
        player.update(0.1, {}, [], now=0.0)
    assert player.charge_time >= 1.2
    assert player.charge_complete is True


def test_charge_release_resets_charge(player: Player) -> None:
    # 2026-09-08 v1.6: on SPACE KEYUP, charge_time resets to 0.
    player.set_weapon(1)
    _charge_press(player)
    for _ in range(15):  # 1.5s of hold
        player.update(0.1, {}, [], now=0.0)
    assert player.charge_complete is True
    _charge_release(player)
    player.update(0.0, {}, [], now=0.0)  # the KEYUP frame consumes the flag
    assert player.charge_time == 0.0
    assert player.charge_complete is False


def test_weapon_0_continuous_charge_is_immediately_complete(player: Player) -> None:
    # 2026-09-08 v1.6: weapon 0 (orange fire) has CHARGE_TIME_S=0.0
    # meaning "continuous, no threshold". charge_complete should be
    # True on the first frame of holding SPACE.
    player.set_weapon(0)
    _charge_press(player)
    player.update(0.016, {}, [], now=0.0)  # 1 frame
    assert player.charge_complete is True


def test_weapon_3_piercing_timer_increments(player: Player) -> None:
    # 2026-09-08 v1.6: weapon 3 (cyan ice) has
    # PIERCING_SPAWN_INTERVAL_S=1.5. The internal spawn timer should
    # increment each frame while SPACE is held, and reset when the
    # player releases.
    player.set_weapon(3)
    _charge_press(player)
    for _ in range(10):  # 1.0s
        player.update(0.1, {}, [], now=0.0)
    assert 0.9 <= player._piercing_spawn_timer <= 1.1
    _charge_release(player)
    player.update(0.0, {}, [], now=0.0)
    assert player._piercing_spawn_timer == 0.0


def test_switching_weapon_cancels_charge(player: Player) -> None:
    # 2026-09-08 v1.6: set_weapon() cancels any in-progress charge.
    player.set_weapon(1)
    _charge_press(player)
    for _ in range(8):  # 0.8s
        player.update(0.1, {}, [], now=0.0)
    assert player.charge_time > 0.0
    player.set_weapon(4)  # tap-only
    assert player.charge_time == 0.0
    assert player.charge_complete is False


def test_tap_firing_independent_of_charge(player: Player) -> None:
    # 2026-09-08 v1.6: B (tap) and SPACE (charge) are independent.
    # Holding B should not accumulate charge_time; holding SPACE
    # should not trigger basic-shot cooldown.
    player.set_weapon(1)  # white piercing (1.2s charge)
    _tap_press(player)
    for _ in range(5):
        player.update(0.1, {}, [], now=0.0)
    assert player.charge_time == 0.0
    # Now release B, press SPACE.
    _tap_release(player)
    _charge_press(player)
    for _ in range(5):
        player.update(0.1, {}, [], now=0.0)
    assert 0.4 <= player.charge_time <= 0.6
    assert player.charge_complete is False


def test_charge_time_s_table_covers_all_5_weapons() -> None:
    # v1.7: CHARGE_TIME_S[1] was reduced from 1.2 to 1.0 (the
    # ChargedDisc replaces the v1.6 Megaman bolt and has a tighter
    # charge window for snappier feel). Weapons 0/3 still use 0.0
    # (continuous), 2=1.5 unchanged, 4 is None (tap-only).
    assert len(Player.CHARGE_TIME_S) == 5
    assert Player.CHARGE_TIME_S[0] == 0.0
    assert Player.CHARGE_TIME_S[3] == 0.0
    assert Player.CHARGE_TIME_S[1] == 1.0  # v1.7: was 1.2
    assert Player.CHARGE_TIME_S[2] == 1.5
    assert Player.CHARGE_TIME_S[4] is None


def test_charged_shot_fires_on_space_release_for_weapon_1(player: Player) -> None:
    # v1.7: on SPACE KEYUP at full charge, weapon 1 spawns a
    # ChargedDisc in the dedicated disc pool (replaces the v1.6
    # Megaman bolt with damage=3). The disc is NOT a PlayerBullet;
    # it's a separate entity. This test passes an empty
    # charged_disc_pool and verifies the disc spawns there.
    from stellar_horizon.entities.charged_disc import ChargedDisc
    player.set_weapon(1)
    pool = []
    from stellar_horizon.entities.bullet import PlayerBullet
    for _ in range(2):
        pool.append(PlayerBullet())
    disc_pool = [ChargedDisc(), ChargedDisc()]
    _charge_press(player)
    # 1.0s is the new threshold (was 1.2s). Use 1.1s to be safely
    # past it.
    for _ in range(11):  # 11 * 0.1 = 1.1s, > 1.0s threshold
        player.update(0.1, {}, pool, now=0.0, charged_disc_pool=disc_pool)
    assert player.charge_complete is True
    _charge_release(player)
    # The release frame consumes the edge flag and dispatches the
    # charged disc.
    player.update(0.0, {}, pool, now=0.0, charged_disc_pool=disc_pool)
    # The ChargedDisc is in the disc pool, NOT the bullet pool.
    alive_bullets = [b for b in pool if b.alive]
    assert len(alive_bullets) == 0
    alive_discs = [d for d in disc_pool if d.alive]
    assert len(alive_discs) == 1
    # Disc is at the muzzle.
    assert alive_discs[0].x == player.x + player.BULLET_OFFSET_X
    assert alive_discs[0].y == player.y


def test_charged_shot_fires_on_space_release_for_weapon_2(player: Player) -> None:
    # 2026-09-08 v1.6: weapon 2 (magenta heart) fires a boomerang
    # (returning=True, return_at=0.6, damage=2) on release at full
    # charge.
    player.set_weapon(2)
    pool = []
    from stellar_horizon.entities.bullet import PlayerBullet
    for _ in range(2):
        pool.append(PlayerBullet())
    _charge_press(player)
    for _ in range(20):  # 2.0s, above 1.5s threshold
        player.update(0.1, {}, pool, now=0.0)
    assert player.charge_complete is True
    _charge_release(player)
    player.update(0.0, {}, pool, now=0.0)
    alive = [b for b in pool if b.alive]
    assert len(alive) == 1
    assert alive[0].damage == 2
    assert alive[0].returning is True
    assert alive[0].return_at == 0.6
    assert alive[0].weapon == 2


def test_tap_shot_does_not_count_as_charged_release(player: Player) -> None:
    # 2026-09-08 v1.6: B (tap) press/release must NOT trigger the
    # charged-shot dispatch path. Only SPACE release does that.
    player.set_weapon(1)
    pool = []
    from stellar_horizon.entities.bullet import PlayerBullet
    for _ in range(2):
        pool.append(PlayerBullet())
    _tap_press(player)
    # No charge has been accumulated (SPACE not held).
    player.update(0.1, {}, pool, now=0.0)
    _tap_release(player)
    player.update(0.0, {}, pool, now=0.0)
    # The tap should spawn a basic bullet (B-key tier-1, damage=1).
    alive = [b for b in pool if b.alive]
    assert len(alive) == 1
    assert alive[0].damage == 1
