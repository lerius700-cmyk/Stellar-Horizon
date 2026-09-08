"""Tests for fx/beam_renderer — procedural beam body drawing.

The beam renderer draws the beam as a polygon (outer body + inner
core) with sinusoidal ondulations. These tests verify:
- No-op when beam is not alive
- Pixels are drawn when the beam IS alive
- The body width grows from start to end (no-op for visual diff,
  but the polygon must close properly)
- Ondulations change the pixels over time (so the beam wiggles)
"""
from __future__ import annotations

import pygame
import pytest

from stellar_horizon.entities.beam import Beam
from stellar_horizon.fx.beam_renderer import draw


@pytest.fixture
def beam() -> Beam:
    b = Beam()
    b.spawn(start_x=100.0, start_y=135.0,
            end_x=300.0, end_y=135.0,
            spawn_time=0.0)
    return b


@pytest.fixture
def target_surf() -> pygame.Surface:
    return pygame.Surface((480, 270), pygame.SRCALPHA)


def test_no_op_when_beam_inactive(target_surf: pygame.Surface) -> None:
    # An inactive beam should produce no pixel changes.
    beam = Beam()  # never spawned
    before = pygame.image.tostring(target_surf, "RGBA")
    draw(target_surf, beam, now=0.0)
    after = pygame.image.tostring(target_surf, "RGBA")
    assert before == after


def test_pixels_drawn_when_beam_active(
    target_surf: pygame.Surface, beam: Beam
) -> None:
    before = pygame.image.tostring(target_surf, "RGBA")
    draw(target_surf, beam, now=0.0)
    after = pygame.image.tostring(target_surf, "RGBA")
    assert before != after, "expected pixels for active beam"


def test_beam_ondulates_over_time(
    target_surf: pygame.Surface, beam: Beam
) -> None:
    # 2026-09-08 v1.5: the body has sinusoidal ondulations that
    # change with time. Two consecutive draws with different `now`
    # should produce different pixels (the body wiggles).
    target_a = pygame.Surface((480, 270), pygame.SRCALPHA)
    target_b = pygame.Surface((480, 270), pygame.SRCALPHA)
    draw(target_a, beam, now=0.0)
    draw(target_b, beam, now=0.5)  # half a period later
    a = pygame.image.tostring(target_a, "RGBA")
    b = pygame.image.tostring(target_b, "RGBA")
    assert a != b, "ondulation should change pixels across time"


def test_beam_with_zero_length_segment_does_not_crash(
    target_surf: pygame.Surface
) -> None:
    # Edge case: start == end. Renderer should bail out gracefully.
    beam = Beam()
    beam.spawn(start_x=100.0, start_y=135.0,
               end_x=100.0, end_y=135.0, spawn_time=0.0)
    draw(target_surf, beam, now=0.0)  # should not raise
