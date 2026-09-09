"""Tests for fx/ship_charge_orb -- the v1.6 3-layer energy sphere.

The orb renders at the player's muzzle, growing as charge_time
increases. It has 3 layers (outer ring + cyan body + white core) with
per-weapon colors and a pulse animation at full charge for the
"ready" feedback.

The conftest pre-inits pygame with SDL_VIDEODRIVER=dummy so we can
build surfaces in unit tests.
"""
from __future__ import annotations

import pygame
import pytest

from stellar_horizon.fx.ship_charge_orb import (
    ORB_RING_COLOR,
    ORB_BODY_COLOR,
    RAMP_TIME_S,
    PULSE_WEAPONS,
    draw,
)


@pytest.fixture
def target_surf() -> pygame.Surface:
    return pygame.Surface((480, 270), pygame.SRCALPHA)


def test_no_orb_when_charge_time_is_zero(target_surf: pygame.Surface) -> None:
    # charge_time <= 0 + not charging -> no-op.
    before = pygame.image.tostring(target_surf, "RGBA")
    draw(target_surf, 240.0, 135.0, weapon=0,
         charge_time=0.0, charging=False, now=0.0)
    after = pygame.image.tostring(target_surf, "RGBA")
    assert before == after, "draw() should be a no-op when not charging"


def test_no_orb_when_charging_but_charge_time_is_zero(target_surf: pygame.Surface) -> None:
    # Edge case: charging=True but charge_time=0 (first frame). The
    # orb is so small it's nearly invisible, but the function should
    # not raise and should produce only minimal pixels.
    draw(target_surf, 240.0, 135.0, weapon=0,
         charge_time=0.0, charging=True, now=0.0)
    # The function is allowed to draw, but the alpha is so low that
    # the visible pixel count is bounded.
    raw = pygame.image.tobytes(target_surf, "RGBA")
    nonzero_alpha_count = sum(
        1 for i in range(3, len(raw), 4) if raw[i] > 5
    )
    # At growth01=0 the ring is at base radius 3 with alpha ~200,
    # the body and core are gated off. So we expect at most a few
    # dozen pixels with any alpha. (Just verify it doesn't crash.)
    assert nonzero_alpha_count < 200


def test_orb_drawn_for_weapon_0_at_full_charge(target_surf: pygame.Surface) -> None:
    # Weapon 0 (orange) at full charge: the orb should paint
    # a clear ring + body + core.
    before = pygame.image.tostring(target_surf, "RGBA")
    draw(target_surf, 240.0, 135.0, weapon=0,
         charge_time=0.5, charging=True, now=0.0)
    after = pygame.image.tostring(target_surf, "RGBA")
    assert before != after, "expected orb pixels for weapon 0 at full charge"


def test_orb_color_per_weapon() -> None:
    # Each charged weapon has a distinct ring color.
    assert ORB_RING_COLOR[0] == (255, 140, 42)    # orange
    assert ORB_RING_COLOR[1] == (255, 255, 255)   # white
    assert ORB_RING_COLOR[2] == (255, 106, 180)   # magenta
    assert ORB_RING_COLOR[3] == (140, 246, 255)   # cyan
    # Weapon 4 (tap-only rainbow) is NOT in the table.
    assert 4 not in ORB_RING_COLOR
    # Body color is always cyan-shifted, so the green channel is
    # high across all weapons. The mix is 55% cyan + 45% ring color,
    # so weapons with low green (e.g. magenta) end up around 168.
    for w in (0, 1, 2, 3):
        r, g, b = ORB_BODY_COLOR[w]
        assert g >= 160, f"weapon {w} body color should be cyan-shifted"


def test_orb_ramp_times_match_charge_thresholds() -> None:
    # Continuous weapons (0, 3) use 0.5s visual ramp.
    # Discrete weapons (1, 2) use the full charge threshold.
    assert RAMP_TIME_S[0] == 0.5
    assert RAMP_TIME_S[3] == 0.5
    assert RAMP_TIME_S[1] == 1.2
    assert RAMP_TIME_S[2] == 1.5


def test_orb_pulses_for_beam_and_discrete_weapons() -> None:
    # Pulse weapons: 0 (beam), 1, 2 (discrete charged).
    # NOT pulse: 3 (continuous piercing -- the stream is the
    # "ready" feedback, no pulse needed).
    assert 0 in PULSE_WEAPONS
    assert 1 in PULSE_WEAPONS
    assert 2 in PULSE_WEAPONS
    assert 3 not in PULSE_WEAPONS


def test_orb_grows_with_charge_time(target_surf: pygame.Surface) -> None:
    # The orb's pixel coverage should grow as charge_time grows.
    # Render at 0.1s vs 0.5s (full charge for weapon 0) and compare.
    small = pygame.Surface((480, 270), pygame.SRCALPHA)
    draw(small, 240.0, 135.0, weapon=0,
         charge_time=0.1, charging=True, now=0.0)
    big = pygame.Surface((480, 270), pygame.SRCALPHA)
    draw(big, 240.0, 135.0, weapon=0,
         charge_time=0.5, charging=True, now=0.0)
    def count_alpha(s: pygame.Surface) -> int:
        raw = pygame.image.tobytes(s, "RGBA")
        return sum(1 for i in range(3, len(raw), 4) if raw[i] > 10)
    small_count = count_alpha(small)
    big_count = count_alpha(big)
    assert big_count > small_count, (
        f"orb at full charge should have more pixels than at 20% "
        f"(got {big_count} vs {small_count})"
    )


def test_orb_pulses_during_hold(target_surf: pygame.Surface) -> None:
    # The pulse alpha varies with `now`. Two snapshots at the same
    # charge_time but different now values should produce different
    # pixel counts (because the alpha is modulated by sin(now*8)).
    target_a = pygame.Surface((480, 270), pygame.SRCALPHA)
    target_b = pygame.Surface((480, 270), pygame.SRCALPHA)
    # Use weapon 1 (white piercing) which pulses, at full charge.
    draw(target_a, 240.0, 135.0, weapon=1,
         charge_time=1.2, charging=True, now=0.0)
    draw(target_b, 240.0, 135.0, weapon=1,
         charge_time=1.2, charging=True, now=1.0)  # half period
    a = pygame.image.tostring(target_a, "RGBA")
    b = pygame.image.tostring(target_b, "RGBA")
    assert a != b, "pulse alpha should differ across `now` values"


def test_orb_unknown_weapon_is_noop(target_surf: pygame.Surface) -> None:
    # Weapon 4 (tap-only rainbow) is not in the table; the orb
    # function should return without drawing.
    before = pygame.image.tostring(target_surf, "RGBA")
    draw(target_surf, 240.0, 135.0, weapon=4,
         charge_time=1.0, charging=True, now=0.0)
    after = pygame.image.tostring(target_surf, "RGBA")
    assert before == after, "tap-only weapon should not show an orb"


def test_orb_release_does_not_draw(target_surf: pygame.Surface) -> None:
    # If the player released SPACE (charging=False) and charge_time
    # is 0 (Player.update resets it on the release frame), the orb
    # should not draw.
    before = pygame.image.tostring(target_surf, "RGBA")
    draw(target_surf, 240.0, 135.0, weapon=0,
         charge_time=0.0, charging=False, now=0.0)
    after = pygame.image.tostring(target_surf, "RGBA")
    assert before == after
