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
    # 2026-09-06 polish 2 + destruction-fall v2: the dying enemy
    # no longer locks in place — it now falls to the ground under
    # arcade gravity and tumbles. After destruction-fall v2, the
    # vx/vy are ZEROED in take_damage() (no carry-over from the
    # pre-death movement), so the FIRST update tick changes y
    # (gravity adds to vy) but x stays put (vx = 0). Rotation
    # still advances via the random initial omega. After enough
    # ticks, the ship leaves the bottom of the viewport and is
    # marked dead.
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
    # After take_damage, vx/vy are zeroed — no carry-over.
    assert e.vx == 0.0, f"vx should be 0 after death, got {e.vx}"
    assert e.vy == 0.0, f"vy should be 0 after death, got {e.vy}"
    px_before, py_before = e.x, e.y
    e.update(0.05, FakePlayer())
    # The ship should be moving down (gravity). It should NOT be
    # frozen in place anymore.
    assert e.y > py_before, (
        f"dying enemy should fall (y went {py_before} -> {e.y})"
    )
    # x is unchanged because vx was zeroed by take_damage.
    assert e.x == px_before, (
        f"dying enemy should not drift in x (vx=0); x went {px_before} -> {e.x}"
    )
    # Rotation must be advancing (tumble via random omega).
    assert e.dying_rotation != 0.0, (
        f"dying enemy should rotate via random omega; got {e.dying_rotation}"
    )


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


def test_dying_zeroes_momentum():
    # 2026-09-06 destruction-fall: take_damage must zero vx/vy
    # so the ship stops moving forward/backward instantly and
    # gravity takes over. Previously, the previous frame's
    # movement velocity was preserved, making the ship appear
    # to fly off at full speed in its pre-death direction.
    e = Enemy()
    e.kind = "scout"
    e.on_spawn()
    e.vx, e.vy = 180.0, -90.0
    e.hp = 1
    e.take_damage(1)
    assert e.vx == 0.0, f"vx should be 0 after take_damage, got {e.vx}"
    assert e.vy == 0.0, f"vy should be 0 after take_damage, got {e.vy}"


def test_dying_applies_gravity_monotonically():
    # Gravity should pull the ship straight down. y must grow
    # monotonically over a sequence of update() calls and vy
    # must become positive (downward in screen coords).
    e = Enemy()
    e.kind = "scout"
    e.on_spawn()
    e.hp = 1
    e.x = 200.0
    e.y = 50.0
    e.take_damage(1)
    y_prev = e.y
    vy_samples = []
    for _ in range(20):
        e.update(0.05, FakePlayer())
        assert e.y > y_prev, f"y went {y_prev} -> {e.y} (must grow)"
        vy_samples.append(e.vy)
        y_prev = e.y
    # vy must be positive (downward in screen coords) and growing
    assert vy_samples[0] > 0.0, f"vy should be positive (downward), got {vy_samples[0]}"
    assert vy_samples[-1] > vy_samples[0], (
        f"vy should grow under gravity: start {vy_samples[0]} end {vy_samples[-1]}"
    )


def test_dying_drag_slows_horizontal_velocity():
    # Linear drag should decay vx exponentially. Since vx is
    # zeroed on death in the new physics, force a vx via
    # take_damage + manual override. The integration uses
    # math.exp(-DRAG_LINEAR * dt) so vx should drop by a
    # predictable factor.
    e = Enemy()
    e.kind = "scout"
    e.on_spawn()
    e.hp = 1
    e.take_damage(1)
    e.vx = 100.0  # force-set after take_damage
    vx_initial = e.vx
    e.update(0.5, FakePlayer())
    # After 0.5s with DRAG_LINEAR=1.8, the multiplier is
    # exp(-1.8 * 0.5) = exp(-0.9) ≈ 0.406. So vx should be
    # about 40% of initial. Allow a 20% margin to avoid
    # brittleness.
    expected = vx_initial * 0.4066
    assert e.vx < vx_initial * 0.6, (
        f"vx should decay significantly under drag: "
        f"start {vx_initial} end {e.vx} (expected ~{expected:.1f})"
    )
    assert e.vx > 0, "vx should keep its sign under drag"


def test_dying_omega_decays_with_drag():
    # Angular drag should decay omega exponentially. The sign
    # of omega is preserved (rotation direction doesn't
    # reverse), only its magnitude decreases.
    e = Enemy()
    e.kind = "scout"
    e.on_spawn()
    e.hp = 1
    e.take_damage(1)
    e.dying_omega = 300.0  # force-set after take_damage
    omega_initial = e.dying_omega
    e.update(2.0, FakePlayer())
    # After 2s with DRAG_ANGULAR=0.6, multiplier is
    # exp(-0.6 * 2) = exp(-1.2) ≈ 0.301. So omega should be
    # about 30% of initial.
    expected = omega_initial * 0.3012
    assert abs(e.dying_omega) < abs(omega_initial) * 0.5, (
        f"|omega| should decay under angular drag: "
        f"start {omega_initial} end {e.dying_omega} (expected ~{expected:.1f})"
    )
    assert e.dying_omega > 0, "omega should keep its sign under drag"


def test_dying_random_omega_within_range():
    # The initial omega after take_damage is sampled uniformly
    # from [-180, +180] deg/s. Over 50 samples we should see
    # both positive and negative values, all in range.
    omegas = []
    for _ in range(50):
        e = Enemy()
        e.kind = "scout"
        e.on_spawn()
        e.hp = 1
        e.take_damage(1)
        omegas.append(e.dying_omega)
    # All in range
    for omega in omegas:
        assert -180.0 <= omega <= 180.0, (
            f"omega {omega} out of range [-180, 180]"
        )
    # Both signs present (random is working)
    positives = sum(1 for o in omegas if o > 0)
    negatives = sum(1 for o in omegas if o < 0)
    assert positives > 5, f"only {positives} positive omegas in 50 samples"
    assert negatives > 5, f"only {negatives} negative omegas in 50 samples"


def test_dying_death_sheet_first_then_idle():
    # During the first 0.15s of the death sequence the death
    # sheet (the explosion) is shown. After that, the ship's
    # IDLE/base sheet (its original sprite) takes over so the
    # player can see the ship itself tumbling, not a static
    # explosion sprite being rotated.
    e = Enemy()
    e.kind = "scout"
    e.on_spawn()
    e.hp = 1
    e.sprite_name = "enemy_scout_v3"
    e.take_damage(1)
    # t=0: death sheet
    assert e.current_dying_sheet() == "enemy_scout_death_v1", (
        f"at t=0 expected death sheet, got {e.current_dying_sheet()}"
    )
    # t=0.10s: still in burst window
    e.update(0.10, FakePlayer())
    assert e.current_dying_sheet() == "enemy_scout_death_v1", (
        f"at t=0.10 expected death sheet, got {e.current_dying_sheet()}"
    )
    # t=0.20s: burst done, base sheet takes over
    e.update(0.10, FakePlayer())
    assert e.current_dying_sheet() == "enemy_scout_v3", (
        f"at t=0.20 expected base sheet 'enemy_scout_v3', "
        f"got {e.current_dying_sheet()}"
    )


def test_dying_emits_smoke_when_fx_set():
    # A dying enemy with an injected FxLayer reference should
    # emit P_SMOKE particles during update(). We use a tiny
    # fake FxLayer that counts calls.
    class _FakeFx:
        def __init__(self):
            self.smokes = []
        def emit_smoke(self, x, y):
            self.smokes.append((x, y))
        # take_damage() also calls emit_explosion_typed; provide a
        # no-op so the test can focus on smoke emission.
        def emit_explosion_typed(self, kind, x, y):
            pass

    e = Enemy()
    e.kind = "scout"
    e.on_spawn()
    e.hp = 1
    e.x = 100.0
    e.y = 50.0
    e.fx = _FakeFx()
    e.take_damage(1)
    for _ in range(10):
        e.update(0.05, FakePlayer())
    # 10 ticks of 0.05s with throttle 1-in-2 means 5 smoke emits
    # (the throttle increments every tick and emits on even
    # ticks; 10 ticks / 2 = 5 emits).
    assert len(e.fx.smokes) >= 3, (
        f"expected >= 3 smoke emits in 10 ticks, got {len(e.fx.smokes)}"
    )
    # The smoke positions should be near the ship's position
    # (within a few pixels — gravity moves the ship down).
    for sx, sy in e.fx.smokes:
        assert abs(sx - e.x) < 50
        assert sy >= 30  # never above the spawn point
