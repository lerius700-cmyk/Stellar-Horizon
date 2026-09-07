"""Capture the boss at the very start of its entry (480, 60) to verify
the entry-start clipping is fixed.
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from pathlib import Path

from stellar_horizon.audio.midi_player import MidiPlayer
from stellar_horizon.scenes.gameplay import GameplayScene
from stellar_horizon.entities.boss import Boss
from stellar_horizon.settings import INTERNAL_W, INTERNAL_H


def main() -> None:
    out = Path("D:/AI/stellar-horizon/sprite_tests/capture_boss_entry.png")
    pygame.init()
    try:
        wave_json = Path("stellar_horizon/waves/waves_act1.json")
        assets_dir = Path("stellar_horizon/assets")
        s = GameplayScene(MidiPlayer(), wave_json, assets_dir)
        s.on_enter()

        b = Boss()
        b.phase = "phase_1"
        # Exact path start: (480, 60). Boss is 72x72, so half_w=36,
        # so the boss center at 480 means its right edge is at 516
        # (36px off-screen). The viewport clip in _draw_boss_sprite
        # is what prevents the silhouette from drawing a black bar
        # at the right edge.
        b.x, b.y = 480, 60
        b.action = "idle_patrol"
        s.boss = b
        s.boss_active = True

        surface = pygame.Surface((INTERNAL_W, INTERNAL_H))
        s.draw(surface)
        out.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(surface, str(out))
        print(f"saved {out}  boss at ({b.x:.0f}, {b.y:.0f})")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
