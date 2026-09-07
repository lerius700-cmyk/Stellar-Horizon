"""Bullet VFX sandbox: capture the per-weapon bullet VFX for visual review.

For each of 4 representative weapons (plasma, ion, fireball, rainbow),
render the 6-frame bullet sheet at full opacity. The output is
a 4-row x 6-col grid PNG showing all frames for all 4 weapons.

Usage:
    python sprite_tests/bullet_sandbox.py [<output_path>]

Output: sprite_tests/captures/bullet_vfx_default.png
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from stellar_horizon.audio.midi_player import MidiPlayer
from stellar_horizon.entities.bullet import PlayerBullet, WEAPON_ARCHETYPE
from stellar_horizon.scenes.gameplay import GameplayScene


# 4 representative weapons covering different VFX styles
WEAPONS_TO_TEST = (0, 2, 5, 9)  # yellow plasma, blue ion, orange fireball, rainbow
CELL_W = 30
CELL_H = 30


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "D:/AI/stellar-horizon/sprite_tests/captures/bullet_vfx_default.png"
    )
    pygame.init()
    try:
        wave_json = Path("stellar_horizon/waves/waves_act1.json")
        assets_dir = Path("stellar_horizon/assets")
        s = GameplayScene(MidiPlayer(), wave_json, assets_dir)
        s.on_enter()

        # Render a 4-row x 6-col grid
        grid = pygame.Surface(
            (CELL_W * 6, CELL_H * len(WEAPONS_TO_TEST)),
            pygame.SRCALPHA,
        )
        grid.fill((20, 20, 30, 255))

        for row, weapon in enumerate(WEAPONS_TO_TEST):
            archetype = WEAPON_ARCHETYPE[weapon]
            sheet_name = f"laser_{archetype + 1:02d}"
            sheet = s._animated.get(sheet_name)
            if sheet is None or not sheet.loaded:
                continue
            for col in range(6):
                if col >= len(sheet._frames):
                    continue
                frame = sheet._frames[col]
                cell = pygame.Surface((CELL_W, CELL_H), pygame.SRCALPHA)
                fx_w, fx_h = frame.get_size()
                cell.blit(
                    frame,
                    ((CELL_W - fx_w) // 2, (CELL_H - fx_h) // 2),
                )
                grid.blit(cell, (col * CELL_W, row * CELL_H))

        out.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(grid, str(out))
        print(f"saved {out}")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
