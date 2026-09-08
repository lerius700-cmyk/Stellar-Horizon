"""Visual evidence for the 2026-09-08 v1.5 charge preview.

Renders a composite screenshot showing the 4 charged weapons (5/6/7/8)
with the long sheet preview at full alpha. Layout:
  - 4 columns, one per charged weapon
  - 2 rows: top = charge_time at 0.0 (no preview),
            bottom = charge_time at full threshold (full alpha)
  - All on a 480x270 surface
  - Each cell has the player ship + the long preview

Usage: python capture_charge_preview.py [output_path]
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
        "D:/AI/stellar-horizon/sprite_tests/captures/charge_preview_v15.png"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    pygame.init()
    try:
        wave_json = Path("stellar_horizon/waves/waves_act1.json")
        assets_dir = Path("stellar_horizon/assets")
        s = GameplayScene(MidiPlayer(), wave_json, assets_dir)
        s.on_enter()

        # Composite surface: 2 rows x 4 cols, each cell = 480x135.
        cell_w, cell_h = INTERNAL_W, INTERNAL_H // 2
        composite = pygame.Surface((cell_w * 4, cell_h * 2),
                                   pygame.SRCALPHA)
        # Per-weapon info.
        weapons = (5, 6, 7, 8)
        # Per-weapon full-charge time (matches the render-time formula).
        full_charge = {5: 0.5, 6: 1.2, 7: 1.5, 8: 0.5}

        for col, weapon in enumerate(weapons):
            # ---- Top row: charge_time=0 (no preview) ---------------
            cell = pygame.Surface((cell_w, cell_h), pygame.SRCALPHA)
            # Clear to dark blue (no enemies, no background).
            cell.fill((8, 12, 24, 255))
            # Position the player at the left third.
            s.player.set_weapon(weapon)
            s.player.x = 200
            s.player.y = cell_h // 2
            s.player.charge_time = 0.0
            # Manually draw the player + aura + long preview.
            # We invoke the same draw path as the scene to keep the
            # capture in sync with the real render.
            _draw_player_block(s, cell, ox=0, oy=0)
            composite.blit(cell, (col * cell_w, 0))
            # ---- Bottom row: full charge ----------------------------
            cell = pygame.Surface((cell_w, cell_h), pygame.SRCALPHA)
            cell.fill((8, 12, 24, 255))
            s.player.set_weapon(weapon)
            s.player.x = 200
            s.player.y = cell_h // 2
            s.player.charge_time = full_charge[weapon]
            _draw_player_block(s, cell, ox=0, oy=0)
            composite.blit(cell, (col * cell_w, cell_h))

        pygame.image.save(composite, str(out))
        print(f"wrote {out} ({composite.get_size()})")
    finally:
        pygame.quit()


def _draw_player_block(s: GameplayScene, surface: pygame.Surface,
                        ox: int, oy: int) -> None:
    """Render just the player (sprite + flame + charge aura + long
    preview). Inlines the relevant slice of GameplayScene.draw() so
    the capture works without running the full update tick.
    """
    if not s.player.alive:
        return
    # Player sprite.
    s._draw_player_sprite(surface, s.player, ox, oy)
    # Engine flame.
    if s.player.flame is not None:
        s.player.flame.update(1 / 60)
        s.player.flame.render(
            surface, s.player.x - 6, s.player.y, size_scale=1.0
        )
    # Charge aura.
    from stellar_horizon.fx.ship_charge_aura import draw as draw_charge_aura
    draw_charge_aura(
        surface, s.player.x, s.player.y,
        s.player.weapon, s.player.charge_time, now=0.0,
    )
    # Long preview (the new code we're capturing).
    long_anim = s._laser_long_sprites.get(s.player.weapon)
    if long_anim is not None and s.player.charge_time > 0.0:
        from stellar_horizon.entities.player import Player
        weapon = s.player.weapon
        threshold = Player.CHARGE_TIME_S[weapon]
        ramp = 0.5 if (threshold is None or threshold <= 0.0) else threshold
        alpha01 = max(0.0, min(1.0, s.player.charge_time / ramp))
        if alpha01 > 0.02:
            frame = long_anim.get_current_surface()  # 150x50
            scaled = pygame.transform.scale(frame, (30, 10))
            scaled.set_alpha(int(alpha01 * 255))
            muzzle_x = int(s.player.x + s.player.BULLET_OFFSET_X)
            surface.blit(scaled, (muzzle_x, int(s.player.y - 5)))


if __name__ == "__main__":
    main()
