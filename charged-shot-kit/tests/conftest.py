"""Headless pytest config for the charged_shot_kit.

Sets SDL_VIDEEDRIVER=dummy so tests that need a pygame Surface can run
without a display. Mirrors the pattern used in stellar_horizon/tests.
"""
import os

# Set BEFORE importing pygame.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((1, 1))
