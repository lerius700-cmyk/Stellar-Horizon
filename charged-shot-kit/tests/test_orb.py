"""Tests for the muzzle orb renderer.

The orb is a visual layer; the tests verify:
  1. No-op when not charging.
  2. No-op for unknown weapons.
  3. Draws at growth=0 (just the outer ring).
  4. Draws the body layer at growth >= BODY_ACTIVATION_FRAC.
  5. Draws the core layer at growth >= CORE_ACTIVATION_FRAC.
  6. Pulse modulates alpha near full charge.

We don't verify pixel values (fragile) — we verify the surface has
been modified vs. a blank baseline.
"""
import os

import pygame
import pytest

from charged_shot_kit.orb import (
    BODY_ACTIVATION_FRAC,
    CORE_ACTIVATION_FRAC,
    PULSE_ACTIVATION_FRAC,
    RAMP_TIME_S,
    draw as draw_charge_orb,
)


@pytest.fixture
def surface():
    return pygame.Surface((200, 200), pygame.SRCALPHA)


def _has_nonzero_alpha(surf: pygame.Surface) -> bool:
    """True if any pixel in the surface has a non-zero alpha."""
    w, h = surf.get_size()
    for y in range(h):
        for x in range(w):
            if surf.get_at((x, y))[3] > 0:
                return True
    return False


def test_orb_noop_when_not_charging(surface):
    draw_charge_orb(surface, 100, 100, weapon=1,
                    charge_time=0.0, charging=False, now=0.0)
    assert _has_nonzero_alpha(surface) is False


def test_orb_noop_for_unknown_weapon(surface):
    draw_charge_orb(surface, 100, 100, weapon=999,
                    charge_time=1.0, charging=True, now=0.0)
    assert _has_nonzero_alpha(surface) is False


def test_orb_draws_at_growth_zero(surface):
    """At growth=0, only the outer ring (3px radius) is visible. The
    body and core are below their activation fractions.
    """
    draw_charge_orb(surface, 100, 100, weapon=1,
                    charge_time=0.0, charging=True, now=0.0)
    assert _has_nonzero_alpha(surface) is True


def test_orb_body_appears_at_25_percent(surface):
    surface_before = pygame.Surface((200, 200), pygame.SRCALPHA)
    # Pick a charge_time just past 25% of the ramp.
    ramp = RAMP_TIME_S[1]
    charge_time = ramp * (BODY_ACTIVATION_FRAC + 0.05)
    draw_charge_orb(surface, 100, 100, weapon=1,
                    charge_time=charge_time, charging=True, now=0.0)
    # The body layer is bigger than the ring at 25% (because the ring
    # has already grown). Sanity check: orb occupies more pixels than
    # the ring-only baseline.
    draw_charge_orb(surface_before, 100, 100, weapon=1,
                    charge_time=0.0, charging=True, now=0.0)
    pixels_with_body = sum(
        1 for y in range(200) for x in range(200)
        if surface.get_at((x, y))[3] > 0
    )
    pixels_ring_only = sum(
        1 for y in range(200) for x in range(200)
        if surface_before.get_at((x, y))[3] > 0
    )
    assert pixels_with_body > pixels_ring_only


def test_orb_core_appears_at_50_percent(surface):
    """At 50% growth, the white hot core is visible. We can't easily
    verify it's WHITE without checking colors, but we can verify the
    orb is larger (more filled).
    """
    ramp = RAMP_TIME_S[1]
    charge_time_25 = ramp * (BODY_ACTIVATION_FRAC + 0.05)
    charge_time_50 = ramp * (CORE_ACTIVATION_FRAC + 0.05)
    surface_25 = pygame.Surface((200, 200), pygame.SRCALPHA)
    surface_50 = pygame.Surface((200, 200), pygame.SRCALPHA)
    draw_charge_orb(surface_25, 100, 100, weapon=1,
                    charge_time=charge_time_25, charging=True, now=0.0)
    draw_charge_orb(surface_50, 100, 100, weapon=1,
                    charge_time=charge_time_50, charging=True, now=0.0)
    pixels_25 = sum(
        1 for y in range(200) for x in range(200)
        if surface_25.get_at((x, y))[3] > 0
    )
    pixels_50 = sum(
        1 for y in range(200) for x in range(200)
        if surface_50.get_at((x, y))[3] > 0
    )
    assert pixels_50 > pixels_25


def test_orb_pulses_at_full_charge(surface):
    """At growth >= PULSE_ACTIVATION_FRAC, the alpha is modulated by
    sin(now * 2*pi*8Hz). The pulse function is:

        pulse = 1.0 - PULSE_DEPTH + PULSE_DEPTH * (0.5 + 0.5 * sin(now * 2*pi*8))

    sin(2*pi*8*t) has period 1/8. Peak (sin=+1) at t=1/32; trough
    (sin=-1) at t=3/32. At peak, pulse = 1.0 (full alpha). At trough,
    pulse = 1.0 - 2*PULSE_DEPTH = 0.64 (64% alpha).
    """
    ramp = RAMP_TIME_S[1]
    charge_time = ramp * (PULSE_ACTIVATION_FRAC + 0.1)
    # Peak of the pulse (sin=+1, pulse=1.0).
    surface_peak = pygame.Surface((200, 200), pygame.SRCALPHA)
    now_peak = 1.0 / 32
    # Trough of the pulse (sin=-1, pulse=0.64).
    surface_trough = pygame.Surface((200, 200), pygame.SRCALPHA)
    now_trough = 3.0 / 32
    draw_charge_orb(surface_peak, 100, 100, weapon=1,
                    charge_time=charge_time, charging=True, now=now_peak)
    draw_charge_orb(surface_trough, 100, 100, weapon=1,
                    charge_time=charge_time, charging=True, now=now_trough)
    # Peak alpha sum should be strictly higher than trough.
    peak_sum = sum(
        surface_peak.get_at((x, y))[3]
        for y in range(200) for x in range(200)
    )
    trough_sum = sum(
        surface_trough.get_at((x, y))[3]
        for y in range(200) for x in range(200)
    )
    assert peak_sum > trough_sum
