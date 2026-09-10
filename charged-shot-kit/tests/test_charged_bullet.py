"""Tests for ChargedBullet FSM, pool pattern, and collision protocol."""
import pygame
import pytest

from charged_shot_kit import ChargedBullet, ChargedBulletState as State


# A minimal target with a hitbox(). Mirrors the convention used by
# enemies and other bullets in pygame shmups.
class _Target:
    def __init__(self, x, y, w=20, h=20):
        self.x = x
        self.y = y
        self.alive = True
        self._w = w
        self._h = h

    def hitbox(self):
        return pygame.Rect(int(self.x - self._w / 2), int(self.y - self._h / 2),
                           self._w, self._h)


# ---------------------------------------------------------------------------
# Spawn / lifecycle
# ---------------------------------------------------------------------------

def test_spawn_makes_bullet_alive():
    b = ChargedBullet()
    assert b.alive is False
    b.spawn(x=100, y=100, now=0.0)
    assert b.alive is True
    assert b.state is State.FLYING
    assert b.hit_count == 0


def test_dead_bullet_does_not_move():
    b = ChargedBullet()
    # Not spawned — update should be a no-op.
    b.update(dt=1 / 60, world_width=480)
    assert b.alive is False


def test_flying_bullet_moves_in_x():
    """A flying bullet moves at SPEED_PX_S in +X. The frame budget is
    under LAST_HIT_SETTLE_S (0.4s) so the bullet doesn't transition
    to FADING before we measure. 20 frames * 1/60s = 0.333s.
    """
    b = ChargedBullet()
    b.spawn(x=100, y=100, now=0.0)
    for _ in range(20):
        b.update(dt=1 / 60, world_width=2000)
    # SPEED_PX_S = 1100. After 0.333s, x = 100 + 1100 * 0.333 = 466.67.
    assert b.x == pytest.approx(100 + 1100.0 * 20 / 60, rel=1e-3)


def test_off_screen_kills_instantly():
    """No fade when off-screen — the bullet is just gone. This is
    different from the miss/cap case which DOES fade.
    """
    b = ChargedBullet()
    b.spawn(x=100, y=100, now=0.0)
    # Push past the world width + margin.
    while b.alive:
        b.update(dt=1 / 60, world_width=480)
        if b.x > 10000:
            break
    assert b.alive is False
    # And the state is NOT FADING (it was killed, not faded).
    assert b.state is State.FLYING


# ---------------------------------------------------------------------------
# FSM transitions: miss -> FADING; cap -> FADING; FADING -> dead
# ---------------------------------------------------------------------------

def test_miss_after_settle_transitions_to_fading():
    """No hits at all and elapsed >= LAST_HIT_SETTLE_S -> FADING.
    The world_width is large enough that the bullet doesn't go
    off-screen before the settle timer fires.
    """
    b = ChargedBullet()
    b.spawn(x=100, y=100, now=0.0)
    # Run for slightly past LAST_HIT_SETTLE_S (0.4s).
    for _ in range(30):  # 30/60 = 0.5s
        b.update(dt=1 / 60, world_width=2000)
    assert b.state is State.FADING


def test_cap_reached_transitions_to_fading():
    """MAX_HITS reached and settle since last hit -> FADING."""
    b = ChargedBullet()
    b.spawn(x=100, y=100, now=0.0)
    # Register MAX_HITS hits. Use a world_width large enough to
    # avoid the off-screen kill before the settle timer.
    for _ in range(b.MAX_HITS):
        b.register_hit()
    for _ in range(30):
        b.update(dt=1 / 60, world_width=2000)
    assert b.state is State.FADING


def test_fading_kills_at_fade_duration():
    b = ChargedBullet()
    b.spawn(x=100, y=100, now=0.0)
    # Force into FADING (world_width=2000 keeps the bullet on-screen
    # long enough for the miss-settle to fire, not the off-screen kill).
    for _ in range(30):
        b.update(dt=1 / 60, world_width=2000)
    assert b.state is State.FADING
    # Run past FADE_DURATION_S.
    for _ in range(30):
        b.update(dt=1 / 60, world_width=2000)
    assert b.alive is False


# ---------------------------------------------------------------------------
# Collision protocol
# ---------------------------------------------------------------------------

def test_hits_returns_true_when_overlap():
    b = ChargedBullet()
    b.spawn(x=100, y=100, now=0.0)
    # Target 20px to the right; within the 80x80 hitbox.
    target = _Target(120, 100)
    assert b.hits(target) is True


def test_hits_returns_false_when_no_overlap():
    b = ChargedBullet()
    b.spawn(x=100, y=100, now=0.0)
    # Target 500px to the right; well outside the 80x80 hitbox.
    target = _Target(600, 100)
    assert b.hits(target) is False


def test_hits_returns_false_while_fading():
    b = ChargedBullet()
    b.spawn(x=100, y=100, now=0.0)
    target = _Target(100, 100)
    assert b.hits(target) is True
    # Force into FADING (world_width=2000 keeps the bullet alive so
    # we can observe the FADING -> dead transition cleanly).
    for _ in range(30):
        b.update(dt=1 / 60, world_width=2000)
    # Now hits() should return False even though the hitbox is the same.
    assert b.hits(target) is False


def test_register_hit_increments_count():
    b = ChargedBullet()
    b.spawn(x=100, y=100, now=0.0)
    b.register_hit()
    b.register_hit()
    assert b.hit_count == 2
    assert b.last_hit_time == pytest.approx(b.elapsed, rel=1e-6)


# ---------------------------------------------------------------------------
# Damage model
# ---------------------------------------------------------------------------

def test_damage_first_hit_uses_first_mult():
    b = ChargedBullet()
    b.spawn(x=100, y=100, now=0.0)
    # hit_count=0 -> the NEXT hit is hit_index=1 -> FIRST_HIT_MULT.
    assert b.damage_for_hit() == b.FIRST_HIT_MULT
    # After one hit, the next is hit_index=2 -> SECONDARY_HIT_MULT.
    b.register_hit()
    assert b.damage_for_hit() == b.SECONDARY_HIT_MULT


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------

def test_fade_alpha_constant_in_flying():
    b = ChargedBullet()
    b.spawn(x=100, y=100, now=0.0)
    assert b.fade_alpha() == 255


def test_fade_alpha_decreases_in_fading():
    b = ChargedBullet()
    b.spawn(x=100, y=100, now=0.0)
    # World_width=2000 keeps the bullet alive long enough to observe
    # the fade. Run 0.5s: 0.4s of flight (settle) + 0.1s of fade.
    for _ in range(30):
        b.update(dt=1 / 60, world_width=2000)
    assert b.state is State.FADING
    # fade_elapsed is ~0.1s; FADE_DURATION_S = 0.4; alpha = 255*(1 - 0.25) = 191.
    alpha = b.fade_alpha()
    assert 150 <= alpha <= 230, f"expected ~191, got {alpha}"


# ---------------------------------------------------------------------------
# Pool pattern
# ---------------------------------------------------------------------------

def test_pool_spawn_silently_fails_when_full():
    """If all 2 pool slots are alive, the second spawn should be a
    silent no-op. The dispatch code is responsible for finding the
    first non-alive slot; this test verifies the `alive = True` is
    the gate.
    """
    pool = [ChargedBullet() for _ in range(2)]
    pool[0].spawn(x=10, y=10, now=0.0)
    pool[1].spawn(x=20, y=20, now=0.0)
    # Both alive; a "second spawn" would need to find a free slot,
    # which doesn't exist. The dispatch loop should skip silently.
    free = [b for b in pool if not b.alive]
    assert free == []
    # The original two are unaffected.
    assert pool[0].x == 10.0
    assert pool[1].x == 20.0
