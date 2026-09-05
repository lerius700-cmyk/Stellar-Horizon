"""Regression guard: GameplayScene.draw() must work on the FIRST frame
after scene transition (before any update() has been called for the
new scene).

2026-09-04 bug: GameplayScene had no default for `_last_dt`. The
attribute was set in update() but used in draw() to advance engine
flames. On the title→gameplay transition, the scene manager calls
draw() in the same frame it instantiates GameplayScene (before the
first update()). The draw() crashed with:
    AttributeError: 'GameplayScene' object has no attribute '_last_dt'

This test fails the build if the regression returns.
"""
from __future__ import annotations

import os
import pytest


@pytest.fixture(autouse=True)
def _sdl_dummy(monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")


def test_gameplay_scene_draw_works_before_first_update(tmp_path) -> None:
    """Construct GameplayScene, call on_enter (typical scene lifecycle),
    then draw() — without calling update() first. Must not raise.

    This is exactly what the scene manager does on the title→gameplay
    transition frame: instantiate, set as current, call draw() in the
    same frame."""
    import pygame
    pygame.init()
    try:
        from stellar_horizon.audio.midi_player import MidiPlayer
        from stellar_horizon.scenes.gameplay import GameplayScene

        from pathlib import Path
        here = Path(__file__).resolve().parent
        wave_json = here.parent / "waves" / "waves_act1.json"
        assets_dir = here.parent / "assets"

        s = GameplayScene(MidiPlayer(), wave_json, assets_dir)
        s.on_enter()  # set up sprites, wave manager, fx, etc.
        # CRITICAL: do NOT call s.update() before draw(). The first draw
        # must succeed because the scene manager draws on the same
        # frame it instantiates the new scene.
        surface = pygame.Surface((480, 270))
        s.draw(surface)  # MUST NOT RAISE
    finally:
        pygame.quit()
