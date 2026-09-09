"""Visual evidence for v1.6 charge orb (fx/ship_charge_orb.py).

Renders a composite screenshot showing the 4 charged weapons (0/1/2/3)
with the procedural orb at the muzzle at 4 charge levels (0% / 25% /
50% / 100%). Layout: 4 columns x 4 rows.

This is the v1.6 redesign of the v1.5 ShipChargeAura + long-sheet
preview. The orb anchors at the muzzle (not the body), grows from
a tiny yellow ring into a big pulsing 3-layer energy sphere, and uses
the weapon's color for the outer ring + cyan-shifted body + white core.

Usage: python capture_charge_orb_v16.py [output_path]
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


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "D:/AI/stellar-horizon/sprite_tests/captures/charge_orb_v16.png"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    pygame.init()
    try:
        s = GameplayScene(MidiPlayer(),
                          Path("stellar_horizon/waves/waves_act1.json"),
                          Path("stellar_horizon/assets"))
        s.on_enter()
        # Layout: 4 columns (weapons 0/1/2/3) x 4 rows (charge levels).
        cell_w, cell_h = INTERNAL_W, INTERNAL_H // 4
        composite = pygame.Surface(
            (cell_w * 4, cell_h * 4 + 30), pygame.SRCALPHA,
        )
        composite.fill((8, 12, 24, 255))
        # Title.
        font = pygame.font.SysFont("monospace", 16)
        title = font.render(
            "v1.6 CHARGE ORB at muzzle -- 4 weapons x 4 charge levels "
            "(0% / 25% / 50% / 100%)",
            True, (220, 220, 240),
        )
        composite.blit(title, (10, 6))
        # Per-weapon info.
        weapons = (0, 1, 2, 3)
        # Per-weapon full-charge time (matches the render-time formula).
        full_charge = {0: 0.5, 1: 1.2, 2: 1.5, 3: 0.5}
        for col, weapon in enumerate(weapons):
            for row, frac in enumerate((0.0, 0.25, 0.50, 1.0)):
                cell = pygame.Surface((cell_w, cell_h), pygame.SRCALPHA)
                cell.fill((8, 12, 24, 255))
                s.player.set_weapon(weapon)
                # Player centered in the cell, leaving room for the orb
                # to extend to the right.
                s.player.x = 200
                s.player.y = cell_h // 2
                s.player.charging = frac > 0.0
                s.player.charge_time = full_charge[weapon] * frac
                s.player.charge_complete = frac >= 1.0
                # Manually draw the player + engine flame + orb.
                s._draw_player_sprite(cell, s.player, 0, 0)
                if s.player.flame is not None:
                    s.player.flame.update(1 / 60)
                    s.player.flame.render(
                        cell, s.player.x - 6, s.player.y, size_scale=1.0,
                    )
                from stellar_horizon.fx.ship_charge_orb import draw as draw_charge_orb
                draw_charge_orb(
                    cell,
                    s.player.x + s.player.BULLET_OFFSET_X,
                    s.player.y,
                    s.player.weapon,
                    s.player.charge_time,
                    s.player.charging,
                    now=0.0,
                )
                composite.blit(cell, (col * cell_w, 30 + row * cell_h))
        pygame.image.save(composite, str(out))
        print(f"wrote {out} ({composite.get_size()})")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
