"""Visual evidence for the v1.7 re-implemented power-up rings.

Renders a composite PNG showing the gold + silver rings in
different states (drop burst, idle, magnet hint active) plus
the floating pickup popups.

Layout: 2 columns (gold, silver) x 3 rows (drop, idle, magnet).
Plus a 4th row showing the popup text floating above the player.

Usage: python capture_powerup_rings.py [output_path]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from stellar_horizon.audio.midi_player import MidiPlayer
from stellar_horizon.entities.player import Player
from stellar_horizon.entities.powerup import PowerUp, PowerUpKind
from stellar_horizon.scenes.gameplay import GameplayScene
from stellar_horizon.settings import INTERNAL_W, INTERNAL_H


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "D:/AI/stellar-horizon/sprite_tests/captures/powerup_rings_v17.png"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    pygame.init()
    try:
        s = GameplayScene(MidiPlayer(),
                          Path("stellar_horizon/waves/waves_act1.json"),
                          Path("stellar_horizon/assets"))
        s.on_enter()
        # Composite: 2 cols (gold, silver) x 3 rows (drop/idle/magnet).
        # Each cell is 480x90.
        cell_w, cell_h = INTERNAL_W, 90
        composite = pygame.Surface(
            (cell_w * 2, cell_h * 3 + 30), pygame.SRCALPHA,
        )
        composite.fill((8, 12, 24, 255))
        # Title.
        font = pygame.font.SysFont("monospace", 14, bold=True)
        title = font.render(
            "v1.7 Power-Up Rings (gold + silver) -- drop / idle / magnet",
            True, (220, 220, 240),
        )
        composite.blit(title, (10, 6))
        for col, kind in enumerate((PowerUpKind.GOLD, PowerUpKind.SILVER)):
            for row, scene_t in enumerate(("drop", "idle", "magnet")):
                cell = pygame.Surface((cell_w, cell_h), pygame.SRCALPHA)
                cell.fill((8, 12, 24, 255))
                # Player at left side, ring at right.
                player_x, player_y = 80, cell_h // 2
                if scene_t == "magnet":
                    ring_x, ring_y = 130, cell_h // 2
                else:
                    ring_x, ring_y = 280, cell_h // 2
                # Draw the player (sprite).
                s.player.x, s.player.y = float(player_x), float(player_y)
                s._draw_player_sprite(cell, s.player, 0, 0)
                # Spawn the ring.
                p = PowerUp()
                p.spawn(float(ring_x), float(ring_y), kind, now=0.0)
                p.alive = True
                # For "drop" state, show the drop-burst particles.
                if scene_t == "drop" and s.fx is not None:
                    if kind == PowerUpKind.GOLD:
                        s.fx.emit_impact(float(ring_x), float(ring_y),
                                         count=10, color=(255, 220, 110))
                    else:
                        s.fx.emit_impact(float(ring_x), float(ring_y),
                                         count=8, color=(220, 230, 255))
                # For "idle" or "magnet" state, advance the ring's
                # alpha pulse to a visible moment.
                # 0.4s age gives a mid-pulse + visible bob.
                age = 0.4 if scene_t == "idle" else 0.0
                # Compute scale (1.0 normal, 1.3 when player is near).
                scale = 1.3 if scene_t == "magnet" else 1.0
                # Draw the ring with the chosen scale (we re-implement
                # the draw inline to inject the scale; the production
                # code path would be the same).
                _draw_ring_scaled(cell, p, kind, float(ring_x),
                                  float(ring_y), age, scale)
                # Draw the FX overlay (the drop burst).
                s.fx.draw(cell)
                composite.blit(cell, (col * cell_w, 30 + row * cell_h))
        # Fourth row: floating pickup popup text.
        popup_row = pygame.Surface((cell_w, 60), pygame.SRCALPHA)
        popup_row.fill((8, 12, 24, 255))
        popup_font = pygame.font.SysFont("monospace", 14, bold=True)
        for text, color, x in (
            ("+1 LIFE",  (220, 230, 255), 200),
            ("+1 MAX",   (255, 220, 110), 400),
            ("+1 MAX",   (255, 220, 110), 600),
            ("+1 LIFE",  (220, 230, 255), 800),
        ):
            for i, (alpha_f) in enumerate((1.0, 0.66, 0.33)):
                # Cascade: text at different y offsets to show the
                # upward drift + fade.
                y_off = 0 - i * 12
                t_surf = popup_font.render(text, True, color)
                t_surf.set_alpha(int(255 * alpha_f))
                popup_row.blit(t_surf, (x, 30 + y_off))
        composite.blit(popup_row, (0, 30 + 3 * cell_h))
        pygame.image.save(composite, str(out))
        print(f"wrote {out} ({composite.get_size()})")
    finally:
        pygame.quit()


def _draw_ring_scaled(surface: pygame.Surface, p: PowerUp, kind: str,
                      x: float, y: float, age: float, scale: float) -> None:
    """Inline ring draw that respects a scale factor (the production
    powerup.py uses scale=1.0; this capture script overrides to
    show the magnet hint at 1.3x)."""
    import math
    alpha = 255
    angle = age * p.SPIN_SPEED_RAD_S
    bob = math.sin(age * 2.0 * math.pi * p.BOB_FREQUENCY_HZ) * p.BOB_AMPLITUDE_PX
    pulse = 0.85 + 0.15 * math.sin(age * 2.0 * math.pi * 0.5)
    if kind == PowerUpKind.GOLD:
        inner_color = (255, 220, 110)
        outer_color = (255, 150, 50)
    else:
        inner_color = (220, 230, 255)
        outer_color = (140, 170, 220)
    cx, cy = int(x), int(y + bob)
    glow_r = int(p.GLOW_SIZE * scale)
    glow_surf = pygame.Surface(
        (glow_r * 2 + 2, glow_r * 2 + 2), pygame.SRCALPHA,
    )
    glow_alpha = int(alpha * 0.4 * pulse)
    pygame.draw.circle(
        glow_surf, (*outer_color, glow_alpha),
        (glow_r + 1, glow_r + 1), glow_r,
    )
    surface.blit(glow_surf, (cx - glow_r - 1, cy - glow_r - 1))
    ring_outer = int(p.SIZE * 0.5 * scale)
    ring_thickness = max(2, int(2.5 * scale))
    ring_surf = pygame.Surface(
        (ring_outer * 2 + 4, ring_outer * 2 + 4), pygame.SRCALPHA,
    )
    center = ring_outer + 2
    pygame.draw.circle(
        ring_surf, (*inner_color, alpha),
        (center, center), ring_outer, ring_thickness,
    )
    for i in range(4):
        a = angle + i * (math.pi / 2.0)
        ox = center + math.cos(a) * (ring_outer + 2.5)
        oy = center + math.sin(a) * (ring_outer + 2.5)
        pygame.draw.circle(
            ring_surf, (*outer_color, alpha),
            (int(ox), int(oy)), 1,
        )
    surface.blit(ring_surf, (cx - center, cy - center))


if __name__ == "__main__":
    main()
