"""Smoke test: verify pygame can create a window and run a frame loop in this test session.

This is a regression test for the bug where the .exe closes before the user can see
the title. We want to confirm pygame can create a window, run frames, and respond to
events without crashing.
"""
from __future__ import annotations

import os
import time

import pytest


def test_pygame_can_create_window_and_run_frames():
    """Minimal smoke test: pygame init, create window, run 30 frames, quit cleanly."""
    import pygame

    # Set SDL_VIDEODRIVER to dummy if we are in a headless session so this
    # test doesn't try to create a real window. This is a smoke test for
    # the GAME INITIALIZATION path, not the rendering path.
    if "CI" in os.environ or "GITHUB_ACTIONS" in os.environ:
        os.environ["SDL_VIDEODRIVER"] = "dummy"

    pygame.init()
    try:
        # Try to create a small window. If we are in a session that cannot
        # create windows (e.g. a service session), this might fail or
        # produce a window with no handle.
        screen = pygame.display.set_mode((320, 180))
        assert screen is not None, "pygame.display.set_mode returned None"

        # Run 30 frames of the event loop. The window should not close
        # unless we explicitly send a QUIT.
        for _ in range(30):
            events = pygame.event.get()
            for ev in events:
                if ev.type == pygame.QUIT:
                    pytest.fail("Window received QUIT event without us asking for it")
            time.sleep(1 / 60)
    finally:
        pygame.quit()
