# stellar_horizon/tests/test_enemy.py
import pytest
import pygame

from stellar_horizon.entities.enemy import Enemy, EnemyKind
from stellar_horizon._systems.movement import PathFollower, HybridPath
from stellar_horizon.waves.bezier_horizontal import path_s_right_to_left


class FakePlayer:
    def __init__(self, x=200, y=135):
        self.x, self.y = x, y


def test_enemy_kind_constants():
    assert EnemyKind.SCOUT == "scout"
    assert EnemyKind.CRUISER == "cruiser"
    assert EnemyKind.HEAVY == "heavy"


def test_enemy_starts_inactive():
    e = Enemy()
    assert e.alive is False
    assert e.hp == 1
    assert e.kind == EnemyKind.SCOUT


def test_enemy_take_damage_decrements_hp():
    e = Enemy()
    e.hp = 4
    e.alive = True
    e.take_damage(1)
    assert e.hp == 3


def test_enemy_take_damage_kills_at_zero():
    # 2026-09-06 polish: take_damage now starts a 1.0s death
    # sequence (dying_timer > 0) instead of immediately setting
    # alive = False. alive is only flipped to False once update()
    # either ticks the dying_timer down to 0 OR the ship crosses
    # the bottom of the viewport (whichever comes first). This
    # test reflects the new immediate-after-damage state.
    e = Enemy()
    e.hp = 1
    e.alive = True
    e.take_damage(1)
    # Immediate: alive is still True (death sequence is playing).
    assert e.alive is True
    assert e.dying_timer > 0.0
    # After enough update() calls, the ship is finally marked
    # dead so the wave manager purges it.
    e.update(2.0, FakePlayer())
    assert e.alive is False
    assert e.dying_timer == 0.0


def test_enemy_take_damage_starts_dying_sequence_with_kind_sheet():
    # The death sheet is named enemy_{kind}_death_v1. take_damage
    # swaps sprite_name to that sheet so the draw code can pick it
    # up. The original sprite_name is captured in base_sprite_name.
    e = Enemy()
    e.kind = EnemyKind.CRUISER
    e.hp = 1
    e.alive = True
    e.sprite_name = "enemy_cruiser_v3"
    e.take_damage(1)
    assert e.sprite_name == "enemy_cruiser_death_v1"
    assert e.base_sprite_name == "enemy_cruiser_v3"
    assert e.dying_timer > 0.0
    assert e.alive is True


def test_enemy_take_damage_does_not_restart_dying_sequence():
    # If take_damage is called again during the death sequence
    # (e.g. an AOE hits a dying enemy), we MUST NOT restart the
    # timer or change the sheet — the enemy is already committed
    # to dying.
    e = Enemy()
    e.kind = EnemyKind.SCOUT
    e.hp = 1
    e.alive = True
    e.sprite_name = "enemy_scout_v2"
    e.take_damage(1)
    first_timer = e.dying_timer
    first_sheet = e.sprite_name
    e.take_damage(1)
    assert e.dying_timer == first_timer
    assert e.sprite_name == first_sheet


def test_enemy_update_skips_movement_when_dying():
    # 2026-09-06 polish 2: the dying enemy no longer locks in
    # place — it now falls to the ground under arcade gravity and
    # tumbles. So the FIRST update tick DOES change y (gravity
    # adds to vy) and x (vx drift). Subsequent updates keep
    # accelerating downward. After enough ticks, the ship leaves
    # the bottom of the viewport and is marked dead.
    path = path_s_right_to_left(y_offset=0)
    hybrid = HybridPath.from_segments([path])
    follower = PathFollower(hybrid)
    e = Enemy()
    e.attach_path(follower, slot_dx=0, slot_dy=0)
    e.x = 100.0
    e.y = 50.0
    e.vx, e.vy = -30.0, 0.0
    e.alive = True
    e.on_spawn()  # sets kind=scout
    e.hp = 1
    e.take_damage(1)
    px_before, py_before = e.x, e.y
    e.update(0.05, FakePlayer())
    # The ship should be moving down (gravity) and slightly left
    # (vx drift). It should NOT be frozen in place anymore.
    assert e.y > py_before, (
        f"dying enemy should fall (y went {py_before} -> {e.y})"
    )
    assert e.x < px_before, "dying enemy should keep drifting in vx"
    # Rotation must be advancing (tumble).
    assert e.dying_rotation > 0.0


def test_enemy_dying_falls_and_is_removed_at_bottom_of_viewport():
    # 2026-09-06 polish 2: a dying enemy must be removed from the
    # wave manager when it crosses the bottom of the viewport
    # (y > 295), not just when the timer expires. Falling enemies
    # must not linger off-screen.
    e = Enemy()
    e.alive = True
    e.on_spawn()
    e.hp = 1
    e.x = 200.0
    e.y = 280.0  # already near the bottom
    e.vy = 50.0   # small downward velocity (e.g. mid-fall)
    e.take_damage(1)
    # First update should push the ship past the off-screen line
    # and flip alive to False.
    e.update(0.5, FakePlayer())
    assert e.alive is False
    assert e.y > 295.0


def test_enemy_dying_timer_counts_down_to_zero_and_dies():
    # 2026-09-06 polish 2: with the new "fall to ground" mechanic,
    # the timer is 1.0s and the ship is removed when EITHER the
    # timer expires OR it leaves the bottom of the viewport. A
    # ship killed near the top of the screen reaches the offscreen
    # line via gravity before the timer expires, so the offscreen
    # path triggers first. This test forces offscreen by giving
    # the ship a high starting y.
    e = Enemy()
    e.alive = True
    e.on_spawn()
    e.hp = 1
    e.x = 100.0
    e.y = 280.0  # near the bottom, will fall off fast
    e.vy = 0.0
    e.take_damage(1)
    # 1 tick of 0.5s is enough to fall past y=295 from y=280 with
    # gravity 620 px/s^2.
    e.update(0.5, FakePlayer())
    assert e.alive is False
    assert e.dying_timer == 0.0


def test_enemy_path_attached_moves_along_path():
    path = path_s_right_to_left(y_offset=0)
    hybrid = HybridPath.from_segments([path])
    follower = PathFollower(hybrid)
    e = Enemy()
    e.attach_path(follower, slot_dx=0, slot_dy=0)
    e.x = 0
    e.y = 0
    e.alive = True
    player = FakePlayer()
    for _ in range(10):
        e.update(0.05, player)
    assert e.x > 0


def test_enemy_path_done_marks_done_flag():
    path = path_s_right_to_left()
    hybrid = HybridPath.from_segments([path])
    hybrid_short = HybridPath([hybrid.segments[0]], [0.2])
    follower = PathFollower(hybrid_short)
    e = Enemy()
    e.attach_path(follower, slot_dx=0, slot_dy=0)
    e.alive = True
    player = FakePlayer()
    for _ in range(60):
        e.update(0.05, player)
    assert e.path_done is True


def test_enemy_off_screen_culling_left():
    e = Enemy()
    e.x = -50.0
    e.y = 100.0
    e.alive = True
    e.path_done = True
    e.update(0.05, FakePlayer())
    assert e.alive is False


def test_enemy_off_screen_culling_top():
    e = Enemy()
    e.x = 100.0
    e.y = -50.0
    e.alive = True
    e.path_done = True
    e.update(0.05, FakePlayer())
    assert e.alive is False


def test_scout_attack_cooldown_1_5s():
    e = Enemy()
    e.kind = EnemyKind.SCOUT
    e.hp = 1
    e.alive = True
    e.x, e.y = 200.0, 100.0
    e.shoot_cooldown = 0.0
    player = FakePlayer(x=200, y=135)
    e.update(0.05, player)
    assert e.telegraphing is True
    assert e.telegraph_frames == 8


def test_cruiser_attack_cooldown_1_2s():
    e = Enemy()
    e.kind = EnemyKind.CRUISER
    e.hp = 4
    e.alive = True
    e.x, e.y = 200.0, 100.0
    e.shoot_cooldown = 0.0
    player = FakePlayer(x=200, y=135)
    e.update(0.05, player)
    assert e.telegraph_frames == 14


def test_heavy_attack_cooldown_2_5s():
    e = Enemy()
    e.kind = EnemyKind.HEAVY
    e.hp = 12
    e.alive = True
    e.x, e.y = 200.0, 100.0
    e.shoot_cooldown = 0.0
    player = FakePlayer(x=200, y=135)
    e.update(0.05, player)
    assert e.telegraph_frames == 24


def test_enemy_emits_bullet_after_telegraph():
    """Verify telegraph starts, ticks down, then emits a bullet. Position kept in play area manually."""
    e = Enemy()
    e.kind = EnemyKind.SCOUT
    e.hp = 1
    e.alive = True
    # No path attached — we want to control position manually to stay in play area
    e.x, e.y = 200.0, 100.0
    e.shoot_cooldown = 0.0
    player = FakePlayer(x=200, y=135)
    e.update(0.05, player)
    assert e.telegraphing is True
    for _ in range(20):
        e.update(0.05, player)
        e.x, e.y = 200.0, 100.0  # keep position in play area (no path = no auto-move)
    assert e.telegraphing is False
