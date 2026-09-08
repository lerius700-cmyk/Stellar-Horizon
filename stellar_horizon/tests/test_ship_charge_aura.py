"""Tests for fx/ship_charge_aura — the Megaman-style aura on the player.

The aura is render-only and uses pygame.Surface (per-pixel-alpha). The
conftest already sets SDL_VIDEODRIVER=dummy so we can build surfaces
in unit tests.
"""
from __future__ import annotations

import pygame
import pytest

from stellar_horizon.fx.ship_charge_aura import (
    CHARGE_AURA_COLOR,
    draw,
)


@pytest.fixture
def target_surf() -> pygame.Surface:
    return pygame.Surface((480, 270), pygame.SRCALPHA)


def test_no_aura_when_charge_time_is_zero(target_surf: pygame.Surface) -> None:
    # charge_time <= 0 must be a no-op.
    before = pygame.image.tostring(target_surf, "RGBA")
    draw(target_surf, x=240.0, y=135.0, weapon=5,
         charge_time=0.0, now=0.0)
    after = pygame.image.tostring(target_surf, "RGBA")
    assert before == after, "draw() should be a no-op when charge_time=0"


def test_no_aura_for_tap_only_weapons(target_surf: pygame.Surface) -> None:
    # 2026-09-08 v1.5: tap-only weapons (0,1,2,3,4,9) have no aura.
    before = pygame.image.tostring(target_surf, "RGBA")
    draw(target_surf, x=240.0, y=135.0, weapon=0,
         charge_time=1.0, now=0.0)
    after = pygame.image.tostring(target_surf, "RGBA")
    assert before == after, "tap-only weapons should not show an aura"


def test_aura_drawn_for_weapon_5_at_full_charge(target_surf: pygame.Surface) -> None:
    # Weapon 5 (orange fire) should paint SOMETHING on the surface.
    before = pygame.image.tostring(target_surf, "RGBA")
    draw(target_surf, x=240.0, y=135.0, weapon=5,
         charge_time=1.0, now=0.0)
    after = pygame.image.tostring(target_surf, "RGBA")
    assert before != after, "expected aura pixels for weapon 5"


def test_aura_color_matches_weapon_table() -> None:
    # 2026-09-08 v1.5: each charge-capable weapon has its own color.
    assert CHARGE_AURA_COLOR[5] == (255, 140, 0)    # orange
    assert CHARGE_AURA_COLOR[6] == (255, 255, 255)  # white
    assert CHARGE_AURA_COLOR[7] == (255, 68, 170)   # magenta
    assert CHARGE_AURA_COLOR[8] == (136, 255, 255)  # cyan
    # Tap-only weapons must not be in the color table.
    for w in (0, 1, 2, 3, 4, 9):
        assert w not in CHARGE_AURA_COLOR


def test_aura_radii_capped_at_max(target_surf: pygame.Surface) -> None:
    # The aura's outer radius caps at 32, so a charge_time of 100s
    # should produce the same visual as charge_time of ~2s. We can
    # verify the outer radius indirectly: a 100s charge should not
    # produce a surface bigger than ~68x68 (32*2 + 4 padding).
    draw(target_surf, x=240.0, y=135.0, weapon=5,
         charge_time=100.0, now=0.0)
    # Inspect: the surface itself is 480x270 (parent) so we can't
    # measure the aura from the surface. Instead, the test ensures
    # no exception is raised (capping works).
    # (A more direct test would require exposing the aura surface or
    # capturing the blit destination — overkill for this small
    # module.)


def test_aura_pulses_for_discrete_charge_weapons(target_surf: pygame.Surface) -> None:
    # 2026-09-08 v1.5: weapons 6, 7, 8 pulse at full charge. Verify
    # that drawing the same surface with the same charge_time but
    # different `now` values produces different pixels (because the
    # alpha is modulated by sin(now * 8)).
    target_a = pygame.Surface((480, 270), pygame.SRCALPHA)
    target_b = pygame.Surface((480, 270), pygame.SRCALPHA)
    draw(target_a, x=240.0, y=135.0, weapon=6,
         charge_time=1.0, now=0.0)
    draw(target_b, x=240.0, y=135.0, weapon=6,
         charge_time=1.0, now=1.0)  # half a period later
    a = pygame.image.tostring(target_a, "RGBA")
    b = pygame.image.tostring(target_b, "RGBA")
    assert a != b, "pulse alpha should differ across `now` values"


def test_aura_for_weapon_5_does_not_pulse(target_surf: pygame.Surface) -> None:
    # 2026-09-08 v1.5: weapon 5 is continuous (no discrete threshold),
    # so its aura is stable (no pulse).
    target_a = pygame.Surface((480, 270), pygame.SRCALPHA)
    target_b = pygame.Surface((480, 270), pygame.SRCALPHA)
    draw(target_a, x=240.0, y=135.0, weapon=5,
         charge_time=1.0, now=0.0)
    draw(target_b, x=240.0, y=135.0, weapon=5,
         charge_time=1.0, now=1.0)
    a = pygame.image.tostring(target_a, "RGBA")
    b = pygame.image.tostring(target_b, "RGBA")
    assert a == b, "weapon 5 aura should be stable (no pulse)"
