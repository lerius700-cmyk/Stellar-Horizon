"""Regression tests for the per-enemy light trail (comet tail) effect.

2026-09-06 feature: enemy ships leave a visible light trail as they
move. Implemented as a position buffer (deque) that the draw code
renders as alpha-faded afterimages.

These tests assert:
- The trail buffer exists on every enemy kind
- The trail grows as the enemy moves
- The trail is capped at the configured max length
- The trail contains actual position history (not just current)
"""
from __future__ import annotations

from collections import deque
import pytest


# Trail config: must match what gameplay.py draw code expects.
EXPECTED_MAX_TRAIL_LEN = 15


def _make_enemy(kind: str):
    """Construct an enemy and force-set the minimum state needed
    to call update() without a path follower. KAMIKAZE needs a player
    target to home toward; provide a mock for those cases."""
    from stellar_horizon.entities.enemy import Enemy
    e = Enemy()
    e.kind = kind
    e.on_spawn()
    e.x, e.y = 200.0, 135.0
    e.vx, e.vy = -50.0, 0.0  # moving left
    e.alive = True
    e.hp = e.max_hp
    return e


class _MockPlayer:
    """Minimal stand-in for Player so KAMIKAZE's homing logic can run."""
    x = 0.0
    y = 0.0


def _player_for(kind: str):
    """Return a player-like object if the kind needs one, else None."""
    if kind == "kamikaze":
        return _MockPlayer()
    return None


@pytest.mark.parametrize("kind", [
    "scout", "cruiser", "heavy", "bomber", "ufo", "kamikaze",
])
def test_enemy_has_trail_buffer(kind: str) -> None:
    """Every enemy kind must have a trail buffer initialized in
    on_spawn(). The draw code reads e._trail unconditionally."""
    e = _make_enemy(kind)
    assert hasattr(e, "_trail"), f"{kind} enemy missing _trail attribute"
    assert isinstance(e._trail, deque), (
        f"{kind}._trail should be a deque, got {type(e._trail)}"
    )


@pytest.mark.parametrize("kind", [
    "scout", "cruiser", "heavy", "bomber", "ufo", "kamikaze",
])
def test_trail_grows_as_enemy_moves(kind: str) -> None:
    """Calling update() multiple times should grow the trail buffer."""
    e = _make_enemy(kind)
    initial_len = len(e._trail)
    for _ in range(5):
        e.update(1 / 120, player=_player_for(kind))
    assert len(e._trail) > initial_len, (
        f"{kind} trail should grow with movement, "
        f"went {initial_len} -> {len(e._trail)}"
    )


def test_trail_caps_at_max_length() -> None:
    """The trail is a maxlen deque — it should never exceed the cap."""
    e = _make_enemy("scout")
    for _ in range(50):  # way more than the cap
        e.update(1 / 120, player=None)
    assert len(e._trail) <= EXPECTED_MAX_TRAIL_LEN, (
        f"trail exceeded maxlen: {len(e._trail)} > {EXPECTED_MAX_TRAIL_LEN}"
    )


def test_trail_contains_position_history() -> None:
    """The trail must contain positions DISTINCT from the current
    one (so the draw code can render afterimages at past positions)."""
    e = _make_enemy("scout")
    # Force the post-path movement code (moves -30 px/s) so the enemy
    # actually translates. Without this, enemies without a path_follower
    # sit still and the trail stays at the same position.
    e.path_done = True
    for _ in range(10):
        e.update(1 / 120, player=None)
    current = (e.x, e.y)
    # At least one trail entry should be DIFFERENT from current
    # (since the ship is moving, past positions are at different x).
    distinct = [(tx, ty) for (tx, ty) in e._trail if (tx, ty) != current]
    assert len(distinct) >= 1, (
        "trail should contain at least one past position distinct from current"
    )
    # Trail should include positions strictly to the right of current
    # (since ship is moving left, past = right of current).
    past_right = [tx for (tx, ty) in e._trail if tx > current[0]]
    assert len(past_right) >= 1, (
        "trail should contain past positions (right of current) "
        f"for a ship moving left; current x={current[0]}, trail={list(e._trail)}"
    )
