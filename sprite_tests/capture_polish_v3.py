"""Visual evidence for the 2026-09-06 polish pass 2.

Renders a composite screenshot showing:
  - Row 1: 6 enemy kinds in their IDLE/v1 sheets (10% shrink check)
  - Row 2: same kinds in TELEGRAPHING (attack sheet) + 1 in DYING
  - Player ship in IDLE
  - Boss at center (10% shrink + entry)

Usage: python capture_polish_v3.py [output_path]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from stellar_horizon.audio.midi_player import MidiPlayer
from stellar_horizon.scenes.gameplay import GameplayScene
from stellar_horizon.settings import INTERNAL_W, INTERNAL_H
from stellar_horizon.entities.enemy import Enemy, EnemyKind


def _make_enemy(kind: str, x: float, y: float, sprite_name: str) -> Enemy:
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
    return e


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "D:/AI/stellar-horizon/sprite_tests/capture_polish_v3.png"
    )
    pygame.init()
    try:
        wave_json = Path("stellar_horizon/waves/waves_act1.json")
        assets_dir = Path("stellar_horizon/assets")
        s = GameplayScene(MidiPlayer(), wave_json, assets_dir)
        s.on_enter()

        class _MockPlayer:
            x = 100.0
            y = 135.0

        mock_player = _MockPlayer()

        # Six enemy kinds, IDLE state, baseline row.
        kinds = ("scout", "cruiser", "heavy", "bomber", "ufo", "kamikaze")
        sprite_map = {
            "scout":    "enemy_scout_v1",
            "cruiser":  "enemy_cruiser_v1",
            "heavy":    "enemy_heavy_v1",
            "bomber":   "enemy_bomber_v1",
            "ufo":      "enemy_ufo_v1",
            "kamikaze": "enemy_kamikaze_v1",
        }
        row1_enemies = []
        for i, kind in enumerate(kinds):
            e = _make_enemy(kind, 80 + i * 65, 35, sprite_map[kind])
            for _ in range(3):
                e.update(1 / 120, player=mock_player)
            row1_enemies.append(e)

        # Six enemy kinds, TELEGRAPHING. The draw code should pick
        # enemy_{kind}_attack_v1 here.
        row2_enemies = []
        for i, kind in enumerate(kinds):
            e = _make_enemy(kind, 80 + i * 65, 90, sprite_map[kind])
            e.telegraphing = True
            e.telegraph_frames = 30
            for _ in range(3):
                e.update(1 / 120, player=mock_player)
            row2_enemies.append(e)

        # One DYING enemy on its own row (separate so it doesn't
        # overlap the telegraph row's ships).
        dying_enemies = []
        for i, kind in enumerate(kinds):
            e = _make_enemy(kind, 80 + i * 65, 145, sprite_map[kind])
            e.hp = 1
            e.take_damage(1)
            for _ in range(3):
                e.update(1 / 120, player=mock_player)
            dying_enemies.append(e)

        # Player at the bottom row, IDLE.
        s.player.x = 200.0
        s.player.y = 220.0

        all_enemies = row1_enemies + row2_enemies + dying_enemies
        if s.wave_manager is not None:
            s.wave_manager.spawned_enemies = all_enemies  # type: ignore[attr-defined]

        # Draw labels via a small surface for the screenshot.
        surface = pygame.Surface((INTERNAL_W, INTERNAL_H))
        s.draw(surface)

        # Overlay labels so the user can match the visual to the
        # intent. Y positions match the row centers above.
        font = pygame.font.SysFont("Arial", 11, bold=True)
        for txt, (x, y) in (
            ("IDLE       (10% shrink — 29x29)",     (10,  18)),
            ("TELEGRAPH  (attack sheet)",           (10,  73)),
            ("DYING      (death sheet, 0.6s)",      (10, 128)),
            ("PLAYER     (idle)",                   (10, 205)),
        ):
            label = font.render(txt, True, (255, 255, 255))
            shadow = font.render(txt, True, (0, 0, 0))
            surface.blit(shadow, (x + 1, y + 1))
            surface.blit(label, (x, y))

        out.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(surface, str(out))
        print(f"saved {out}")
        print(f"surface size: {INTERNAL_W}x{INTERNAL_H}")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
