"""Capture the death-fall animation: a row of enemies at different
points in their fall, so the user can see the gravity + tumble.

Usage: python capture_falling.py [output_path]
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
from stellar_horizon.settings import INTERNAL_W, INTERNAL_H
from stellar_horizon.entities.enemy import Enemy, EnemyKind


def _make_dying(kind: str, x: float, y: float,
                elapsed_s: float, sprite_name: str, player) -> Enemy:
    """Create an enemy, kill it, and tick the simulation forward
    by `elapsed_s` so the death-fall has progressed.
    """
    e = Enemy()
    e.kind = kind
    e.on_spawn()
    e.x = x
    e.y = y
    e.vx, e.vy = -30.0, 0.0
    e.alive = True
    e.hp = e.max_hp
    e.path_done = True
    e.sprite_name = sprite_name
    for _ in range(3):
        e.update(1 / 120, player=player)
    e.hp = 1
    e.take_damage(1)
    # Tick the simulation `elapsed_s` of death-fall time.
    ticks = int(elapsed_s * 120)
    for _ in range(ticks):
        e.update(1 / 120, player=player)
    return e


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "D:/AI/stellar-horizon/sprite_tests/capture_falling.png"
    )
    pygame.init()
    try:
        wave_json = Path("stellar_horizon/waves/waves_act1.json")
        assets_dir = Path("stellar_horizon/assets")
        s = GameplayScene(MidiPlayer(), wave_json, assets_dir)
        s.on_enter()

        class _MockPlayer:
            x = 50.0
            y = 135.0
        mock_player = _MockPlayer()

        # One row of dying enemies at different fall stages.
        # Start all at the same height (y=40), then let them fall
        # for 0.0, 0.15, 0.30, 0.45, 0.60 seconds. The earliest is
        # at the spawn height (just died); the latest is near the
        # ground.
        kinds = ("scout", "cruiser", "heavy", "bomber", "ufo", "kamikaze")
        sprite_map = {k: f"enemy_{k}_v1" for k in kinds}
        enemies = []
        x0 = 50
        for i, kind in enumerate(kinds):
            elapsed = 0.10 + i * 0.15
            e = _make_dying(kind, x0 + i * 70, 40, elapsed, sprite_map[kind], mock_player)
            enemies.append(e)
        if s.wave_manager is not None:
            s.wave_manager.spawned_enemies = enemies  # type: ignore[attr-defined]

        surface = pygame.Surface((INTERNAL_W, INTERNAL_H))
        s.draw(surface)

        font = pygame.font.SysFont("Arial", 11, bold=True)
        label = font.render("DEATH-FALL (gravity + tumble, ships drop to ground)", True, (255, 255, 255))
        shadow = font.render("DEATH-FALL (gravity + tumble, ships drop to ground)", True, (0, 0, 0))
        surface.blit(shadow, (6, 4))
        surface.blit(label, (5, 3))

        out.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(surface, str(out))
        print(f"saved {out}")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
