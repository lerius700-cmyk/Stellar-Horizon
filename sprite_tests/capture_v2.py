"""Quick visual evidence: launch the GameplayScene headless, render a
few frames onto a pygame Surface, save a screenshot showing the new
AI sprites in their game context.

Usage: python capture_v2.py [output_path]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Force SDL to use the dummy video driver (no real window).
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from stellar_horizon.audio.midi_player import MidiPlayer
from stellar_horizon.scenes.gameplay import GameplayScene


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "D:/AI/stellar-horizon/sprite_tests/capture_v2.png"
    )
    pygame.init()
    try:
        wave_json = Path("stellar_horizon/waves/waves_act1.json")
        assets_dir = Path("stellar_horizon/assets")
        s = GameplayScene(MidiPlayer(), wave_json, assets_dir)
        s.on_enter()
        # Force-spawn a few different enemy kinds so the screenshot
        # shows the visual variety.
        from stellar_horizon.entities.enemy import Enemy
        from stellar_horizon.settings import INTERNAL_W, INTERNAL_H

        # Mock player for kamikaze homing.
        class _MockPlayer:
            x = 100.0
            y = 135.0

        mock_player = _MockPlayer()
        enemies = []
        for i, kind in enumerate(("scout", "cruiser", "heavy",
                                  "bomber", "ufo", "kamikaze")):
            e = Enemy()
            e.kind = kind
            e.on_spawn()
            e.x = 60 + i * 70
            e.y = 80 + (i % 2) * 50
            e.vx, e.vy = -30.0, 0.0
            e.alive = True
            e.hp = e.max_hp
            e.path_done = True
            # Populate the trail (kamikaze needs a player for homing).
            for _ in range(5):
                e.update(1 / 120, player=mock_player)
            enemies.append(e)
        # Inject into the wave_manager (where draw looks for them).
        if s.wave_manager is not None:
            s.wave_manager.spawned_enemies = enemies  # type: ignore[attr-defined]

        # Render a frame
        surface = pygame.Surface((INTERNAL_W, INTERNAL_H))
        s.draw(surface)
        out.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(surface, str(out))
        print(f"saved {out}")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
