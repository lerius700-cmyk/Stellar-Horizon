"""Contact sheet for the 4 long sheets (laser_06..laser_09 _long_sheet.png).

Each long sheet is 900x50 = 6 frames of 150x50 in a row. The postprocess
right-aligned them so the head (where the bullet energy concentrates)
sits on the right edge of each frame.

This contact sheet stacks the 4 sheets vertically with a label per row
so the user can review them and decide what to do (keep, repurpose,
delete, etc.).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

# Mapping weapon -> long sheet file (matches gameplay.py _load_sprites).
LONG_SHEETS = [
    ("weapon 0 ORANGE FIRE (continuous beam)",  "laser_07_long_sheet.png"),
    ("weapon 1 WHITE PIERCING (Megaman bolt)",  "laser_08_long_sheet.png"),
    ("weapon 2 MAGENTA HEART (boomerang)",      "laser_09_long_sheet.png"),
    ("weapon 3 CYAN ICE (piercing stream)",     "laser_06_long_sheet.png"),
]


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "D:/AI/stellar-horizon/sprite_tests/captures/long_sheets_contact_v15.png"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    pygame.init()
    try:
        # Load all 4 sheets.
        loaded = []
        for label, fname in LONG_SHEETS:
            path = Path("stellar_horizon/assets/sprites/bullets") / fname
            surf = pygame.image.load(str(path))
            # The sheet is 900x50; scale each frame 2x for visibility.
            scaled = pygame.transform.scale(surf, (900 * 2, 50 * 2))
            loaded.append((label, fname, surf, scaled))

        # Build the contact sheet.
        cell_w = 900 * 2
        cell_h = 50 * 2 + 30  # frame + label space
        composite = pygame.Surface(
            (cell_w, cell_h * len(loaded) + 30),
            pygame.SRCALPHA,
        )
        composite.fill((20, 24, 36, 255))

        # Title.
        font = pygame.font.SysFont("monospace", 16)
        title = font.render(
            "LONG SHEETS (laser_NN_long_sheet.png) — 6 frames x 150x50 each",
            True, (220, 220, 240),
        )
        composite.blit(title, (10, 6))

        for i, (label, fname, _raw, scaled) in enumerate(loaded):
            y = 30 + i * cell_h
            # Frame separator.
            pygame.draw.line(
                composite, (60, 60, 80, 255),
                (0, y), (cell_w, y), 1,
            )
            # Label.
            text = font.render(
                f"{label}  <-  {fname}  (orig 900x50, shown 2x)",
                True, (180, 220, 255),
            )
            composite.blit(text, (10, y + 4))
            # The scaled sheet (2x).
            composite.blit(scaled, (0, y + 24))

        pygame.image.save(composite, str(out))
        print(f"wrote {out} ({composite.get_size()})")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
