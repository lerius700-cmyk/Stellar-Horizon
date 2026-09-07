# stellar_horizon/tests/test_player.py
import pygame
import pytest

from stellar_horizon.entities.player import Player
from stellar_horizon.settings import INTERNAL_W, INTERNAL_H


@pytest.fixture
def screen_rect():
    return pygame.Rect(0, 0, INTERNAL_W, INTERNAL_H)


@pytest.fixture
def no_keys():
    return {k: False for k in (
        pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d,
        pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT,
        pygame.K_SPACE,
    )}


def test_player_starts_at_left_center(screen_rect):
    p = Player(screen_rect)
    assert p.x == 40.0
    assert p.y == screen_rect.centery


def test_player_has_3_lives(screen_rect):
    p = Player(screen_rect)
    assert p.lives == 3
    assert p.alive is True


def test_player_move_right(screen_rect, no_keys):
    p = Player(screen_rect)
    keys = {**no_keys, pygame.K_d: True}
    p.update(0.1, keys, [])
    assert p.x > 40.0
    assert p.vy == 0.0


def test_player_move_up_with_w(screen_rect, no_keys):
    p = Player(screen_rect)
    keys = {**no_keys, pygame.K_w: True}
    p.update(0.1, keys, [])
    assert p.y < screen_rect.centery


def test_player_move_with_arrows(screen_rect, no_keys):
    p = Player(screen_rect)
    keys = {**no_keys, pygame.K_LEFT: True}
    p.update(0.1, keys, [])
    assert p.x < 40.0


def test_player_bounds_x(screen_rect, no_keys):
    p = Player(screen_rect)
    keys = {**no_keys, pygame.K_d: True}
    for _ in range(600):
        p.update(1 / 120, keys, [])
    assert p.x <= 472


def test_player_bounds_y(screen_rect, no_keys):
    p = Player(screen_rect)
    keys = {**no_keys, pygame.K_w: True}
    for _ in range(600):
        p.update(1 / 120, keys, [])
    assert p.y >= 16


def test_player_take_hit_decrements_lives(screen_rect):
    p = Player(screen_rect)
    p.take_hit()
    assert p.lives == 2


def test_player_take_hit_sets_iframes(screen_rect):
    p = Player(screen_rect)
    p.take_hit()
    assert p.invulnerable_frames > 0


def test_player_take_hit_kills_when_no_lives(screen_rect):
    p = Player(screen_rect)
    p.take_hit()
    p.invulnerable_frames = 0  # reset iframes between hits (in real gameplay 3 hits can't happen within 30f)
    p.take_hit()
    p.invulnerable_frames = 0
    p.take_hit()
    assert p.lives == 0
    assert p.alive is False


def test_player_iframes_prevent_double_hit(screen_rect):
    p = Player(screen_rect)
    p.take_hit()
    p.take_hit()
    assert p.lives == 2


def test_player_shoot_cooldown_decreases(screen_rect, no_keys):
    p = Player(screen_rect)
    p.shoot_cooldown = 0.5
    p.update(0.1, no_keys, [])
    assert p.shoot_cooldown == pytest.approx(0.4)


# ------------------------------------------------------------------
# Power-up ring tests (Checkpoint 2/3)
# ------------------------------------------------------------------

def test_player_starts_with_max_lives_three(screen_rect):
    p = Player(screen_rect)
    assert p.max_lives == 3


def test_player_starts_with_no_gold_stacks(screen_rect):
    p = Player(screen_rect)
    assert p.gold_stacks == 0
    assert p.gold_rings_collected == 0


def test_player_take_hit_with_amount_two_decrements_by_two(screen_rect):
    p = Player(screen_rect)
    p.take_hit(amount=2)
    assert p.lives == 1


def test_player_heal_restores_lives(screen_rect):
    p = Player(screen_rect)
    p.lives = 1
    healed = p.heal(2)
    assert healed == 2
    assert p.lives == 3


def test_player_heal_caps_at_max_lives(screen_rect):
    p = Player(screen_rect)
    p.lives = 2
    healed = p.heal(5)
    assert healed == 1
    assert p.lives == 3


def test_player_heal_zero_if_dead(screen_rect):
    p = Player(screen_rect)
    p.alive = False
    assert p.heal(5) == 0


def test_player_collect_gold_ring_three_bumps_max_lives(screen_rect):
    p = Player(screen_rect)
    assert p.max_lives == 3
    # First gold ring — no stack yet.
    assert p.collect_gold_ring() is False
    assert p.max_lives == 3
    # Second — no stack yet.
    assert p.collect_gold_ring() is False
    # Third — stack 1, +3 max lives.
    assert p.collect_gold_ring() is True
    assert p.gold_stacks == 1
    assert p.max_lives == 6


def test_player_collect_six_gold_rings_caps_at_nine(screen_rect):
    p = Player(screen_rect)
    for _ in range(6):
        p.collect_gold_ring()
    assert p.gold_stacks == 2
    assert p.max_lives == 9
    # 7th ring — no further cap bump.
    assert p.collect_gold_ring() is False
    assert p.max_lives == 9


def test_player_collect_silver_ring_heals_one(screen_rect):
    p = Player(screen_rect)
    p.lives = 1
    p.collect_silver_ring()
    assert p.lives == 2
    # Silver ring does not increment gold stack.
    assert p.gold_stacks == 0
    assert p.max_lives == 3


def test_player_take_hit_zero_amount_does_nothing(screen_rect):
    p = Player(screen_rect)
    p.take_hit(amount=0)
    assert p.lives == 3
    assert p.alive is True


# ------------------------------------------------------------------
# 2026-09-06 visual polish v2: 2-layer player trail
# (Capa 1 base aura + Capa 2 thrust destello at 30Hz)
# ------------------------------------------------------------------

def test_player_base_trail_emits_every_frame_when_alive():
    # 2026-09-06 visual polish v2: the player has a base trail
    # (intensity 0.30) emitted EVERY frame the player is alive,
    # regardless of whether it's thrusting. This gives the player
    # a constant faint aura so it always reads as 'main character'.
    import pygame
    pygame.init()
    try:
        p = Player(pygame.Rect(0, 0, 480, 270))
        class _FakeFx:
            def __init__(self):
                self.calls = []
            def emit_trail(self, x, y, color, intensity):
                self.calls.append((x, y, color, intensity))
        p.fx = _FakeFx()
        for _ in range(10):
            p.update(1/60, _KeysIdle(), [], 0.0)
        base_calls = [c for c in p.fx.calls if c[3] == 0.30]
        assert len(base_calls) == 10, (
            f"expected 10 base trail emits, got {len(base_calls)}"
        )
    finally:
        pygame.quit()


def test_player_thrust_trail_emits_at_30hz():
    # 2026-09-06 visual polish v2: when thrusting, a brighter
    # trail (intensity 1.0) emits at 30Hz (~once every 2 frames at
    # 60fps). 60 calls of update(1/60) = 1 second = ~30 emits.
    import pygame
    pygame.init()
    try:
        p = Player(pygame.Rect(0, 0, 480, 270))
        class _FakeFx:
            def __init__(self):
                self.calls = []
            def emit_trail(self, x, y, color, intensity):
                self.calls.append((x, y, color, intensity))
        p.fx = _FakeFx()
        for _ in range(60):
            p.update(1/60, _KeysThrusting(), [], 0.0)
        thrust_calls = [c for c in p.fx.calls if c[3] == 1.0]
        # 30Hz * 1s = 30 emits. Allow 25-35 for floating-point drift.
        assert 25 <= len(thrust_calls) <= 35, (
            f"expected ~30 thrust trail emits in 60 frames, "
            f"got {len(thrust_calls)}"
        )
    finally:
        pygame.quit()


def test_player_two_layers_independent_counts():
    # 2026-09-06 visual polish v2: the two layers are independent.
    # With thrusting=True, both layers fire each frame. With
    # thrusting=False, only the base layer fires.
    import pygame
    pygame.init()
    try:
        p = Player(pygame.Rect(0, 0, 480, 270))
        class _FakeFx:
            def __init__(self):
                self.calls = []
            def emit_trail(self, x, y, color, intensity):
                self.calls.append((x, y, color, intensity))
        p.fx = _FakeFx()
        for _ in range(10):
            p.update(1/60, _KeysIdle(), [], 0.0)
        idle_base = len([c for c in p.fx.calls if c[3] == 0.30])
        idle_thrust = len([c for c in p.fx.calls if c[3] == 1.0])
        assert idle_base == 10, f"idle base should be 10, got {idle_base}"
        assert idle_thrust == 0, f"idle thrust should be 0, got {idle_thrust}"
    finally:
        pygame.quit()


# Helper classes — only add if they don't already exist in the file
class _KeysIdle:
    """A keys-like object that returns False for movement keys."""
    def __getitem__(self, key):
        return False

class _KeysThrusting:
    """A keys-like object that returns True for K_d (thrusting right)."""
    def __getitem__(self, key):
        import pygame
        return key == pygame.K_d
