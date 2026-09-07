# stellar_horizon/tests/test_bullet.py
import math
import pytest
import pygame

from stellar_horizon.entities.bullet import PlayerBullet, EnemyBullet


def test_player_bullet_starts_dead():
    b = PlayerBullet()
    assert b.alive is False


def test_player_bullet_moves_right():
    b = PlayerBullet()
    b.x, b.y = 100.0, 135.0
    b.vx, b.vy = 480.0, 0.0
    b.alive = True
    b.update(0.1)
    assert b.x == pytest.approx(148.0)
    assert b.y == 135.0


def test_player_bullet_despawns_off_screen():
    b = PlayerBullet()
    b.x, b.y = 470.0, 135.0
    b.vx, b.vy = 480.0, 0.0
    b.alive = True
    b.update(0.1)
    assert b.alive is False


def test_player_bullet_hitbox_12x4():
    b = PlayerBullet()
    b.x, b.y = 100.0, 135.0
    b.alive = True
    hb = b.hitbox()
    assert hb.width == 12
    assert hb.height == 4


def test_player_bullet_has_spawn_time_and_weapon_slots():
    """The code-driven bullet VFX (fx/bullet_vfx.py) reads the
    `spawn_time` and `weapon` attributes to compute the alpha/scale/
    halo phase per bullet. Verify they exist and default to safe
    values so legacy callers (and headless tests) don't crash."""
    b = PlayerBullet()
    assert hasattr(b, "spawn_time")
    assert hasattr(b, "weapon")
    assert b.spawn_time == 0.0
    assert b.weapon == 0


def test_enemy_bullet_spawn_aims_at_target():
    b = EnemyBullet()
    b.spawn(400, 100, 100, 100)
    assert b.vx < 0
    assert b.vy == pytest.approx(0.0, abs=0.01)
    assert b.alive is True


def test_enemy_bullet_moves_in_direction():
    b = EnemyBullet()
    b.spawn(400, 100, 100, 100)
    b.update(0.1)
    assert b.x < 400
    assert abs(b.y - 100) < 1.0


def test_enemy_bullet_despawns_off_screen():
    b = EnemyBullet()
    b.spawn(0, 100, 480, 100)
    b.update(10.0)
    assert b.alive is False


# --- visual polish v2: bullet animation state (frame_index, weapon_archetype) ---


def test_bullet_frame_index_advances_at_12fps():
    # 2026-09-06 visual polish v2: bullets cycle through 6 frames
    # at 12 fps. After 0.3 seconds of update, frame_index should
    # be int(0.3 * 12) % 6 = 3.
    from stellar_horizon.entities.bullet import PlayerBullet
    b = PlayerBullet()
    b.x = 0.0
    b.y = 0.0
    b.vx = 100.0
    b.vy = 0.0
    b.alive = True
    for _ in range(6):
        b.update(0.05)
    assert b.frame_index == 3, (
        f"frame_index should be 3 after 0.3s, got {b.frame_index}"
    )


def test_bullet_frame_index_wraps_after_6():
    # 2026-09-06 visual polish v2: after 0.5s of update, frame_index
    # should wrap: int(0.5 * 12) % 6 = 6 % 6 = 0.
    from stellar_horizon.entities.bullet import PlayerBullet
    b = PlayerBullet()
    b.x = 0.0
    b.y = 0.0
    b.vx = 100.0
    b.vy = 0.0
    b.alive = True
    b.update(0.5)
    assert b.frame_index == 0, (
        f"frame_index should wrap to 0 after 0.5s, got {b.frame_index}"
    )


def test_bullet_weapon_archetype_maps_correctly():
    # 2026-09-06 visual polish v2: each weapon id maps to a laser
    # archetype (0..4). Verify the WEAPON_ARCHETYPE table covers
    # all 10 weapons and values are in range.
    from stellar_horizon.entities.bullet import WEAPON_ARCHETYPE
    assert len(WEAPON_ARCHETYPE) == 10, (
        f"WEAPON_ARCHETYPE should have 10 entries, got {len(WEAPON_ARCHETYPE)}"
    )
    for i, archetype in enumerate(WEAPON_ARCHETYPE):
        assert 0 <= archetype <= 4, (
            f"weapon {i} archetype {archetype} out of range 0..4"
        )
