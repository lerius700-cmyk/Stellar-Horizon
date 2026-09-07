"""Capture the boss state in-game to see the 'cut off' issue."""
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
    out = Path("D:/AI/stellar-horizon/sprite_tests/capture_boss.png")
    pygame.init()
    try:
        wave_json = Path("stellar_horizon/waves/waves_act1.json")
        assets_dir = Path("stellar_horizon/assets")
        s = GameplayScene(MidiPlayer(), wave_json, assets_dir)
        s.on_enter()

        b = Boss()
        b.phase = "phase_1"
        # Mid-entry: well inside the viewport so we can see the
        # full 72x72 boss body without entry clipping.
        b.x, b.y = 380, 100
        b.action = "idle_patrol"
        s.boss = b
        s.boss_active = True

        # Also spawn a few enemies for context, including action variants.
        from stellar_horizon.entities.enemy import Enemy

        class _MockPlayer:
            x = 240.0
            y = 200.0

        mock_player = _MockPlayer()
        enemies = []
        # Row 1: regular enemies at top
        for i, kind in enumerate(("scout", "cruiser", "kamikaze")):
            e = Enemy()
            e.kind = kind
            e.on_spawn()
            e.x = 60 + i * 70
            e.y = 30
            e.vx, e.vy = -30.0, 0.0
            e.alive = True
            e.hp = e.max_hp
            e.path_done = True
            e.sprite_name = f"enemy_{kind}_v1"
            for _ in range(5):
                e.update(1 / 120, player=mock_player)
            enemies.append(e)
        # Row 2: ATTACK poses
        for i, kind in enumerate(("scout", "cruiser", "kamikaze")):
            e = Enemy()
            e.kind = kind
            e.on_spawn()
            e.x = 60 + i * 70
            e.y = 90
            e.vx, e.vy = -30.0, 0.0
            e.alive = True
            e.hp = e.max_hp
            e.path_done = True
            e.sprite_name = f"enemy_{kind}_attack_v1"
            for _ in range(5):
                e.update(1 / 120, player=mock_player)
            enemies.append(e)
        # Row 3: DEATH poses
        for i, kind in enumerate(("scout", "cruiser", "kamikaze")):
            e = Enemy()
            e.kind = kind
            e.on_spawn()
            e.x = 60 + i * 70
            e.y = 150
            e.vx, e.vy = -30.0, 0.0
            e.alive = True
            e.hp = e.max_hp
            e.path_done = True
            e.sprite_name = f"enemy_{kind}_death_v1"
            for _ in range(5):
                e.update(1 / 120, player=mock_player)
            enemies.append(e)
        s.wave_manager.spawned_enemies = enemies

        surface = pygame.Surface((INTERNAL_W, INTERNAL_H))
        s.draw(surface)
        out.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(surface, str(out))
        print(f"saved {out}  boss at ({b.x:.0f}, {b.y:.0f})")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
