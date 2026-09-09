"""Visual evidence for v1.7 ChargedDisc (entities/charged_disc.py +
fx/charged_disc_renderer.py + fx/shockwave.py).

Renders a composite screenshot showing the full lifecycle of the
new white piercing charged shot. Layout: 4 columns x 4 rows.
  - Row 1: charging preview at 0% / 50% / 85% / 100% of the
    1.0s charge time (the disc grows at the muzzle, with rings
    appearing at 85% and the alpha pulse at 100%).
  - Row 2: in-flight disc at t=0.0 / 0.1 / 0.2 / 0.3 seconds
    after release (the disc moves +X, trails white particles,
    and the residual rings spin during the first 0.3s).
  - Row 3: fading disc at 0% / 33% / 66% / 100% of FADE_DURATION_S
    (alpha lerps 255 -> 0, scale lerps 1.0 -> 1.3).
  - Row 4: hit feedback -- panel 1 = disc cruising before the
    hit. Panel 2 = first hit moment (shockwave expanding + flash
    + 8x splash + screen shake). Panel 3 = secondary hit (3x,
    splash only). Panel 4 = post-fade dead state.

Each cell is INTERNAL_W x INTERNAL_H // 4. Final composite is
4*INTERNAL_W wide x (4 * INTERNAL_H // 4 + 30 title) tall.

Usage: python capture_charged_disc.py [output_path]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from stellar_horizon.audio.midi_player import MidiPlayer
from stellar_horizon.entities.charged_disc import ChargedDisc, State
from stellar_horizon.fx import charged_disc_renderer
from stellar_horizon.scenes.gameplay import GameplayScene
from stellar_horizon.settings import INTERNAL_W, INTERNAL_H


def _render_cell(s: GameplayScene) -> pygame.Surface:
    """Render one frame of the gameplay scene into a full 480x270
    surface, then scale it down to (cell_w, cell_h) for the
    composite. Scaling preserves the layout (player + disc + VFX)
    but fits it into a smaller cell.
    """
    full = pygame.Surface((INTERNAL_W, INTERNAL_H), pygame.SRCALPHA)
    full.fill((8, 12, 24, 255))
    s.draw(full)
    cell_w, cell_h = INTERNAL_W, INTERNAL_H // 4
    return pygame.transform.scale(full, (cell_w, cell_h))


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "D:/AI/stellar-horizon/sprite_tests/captures/charged_disc_v17.png"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    pygame.init()
    s = GameplayScene(
        MidiPlayer(),
        Path("stellar_horizon/waves/waves_act1.json"),
        Path("stellar_horizon/assets"),
    )
    s.on_enter()
    s.player.set_weapon(1)  # white piercing
    cell_w, cell_h = INTERNAL_W, INTERNAL_H // 4
    composite = pygame.Surface(
        (cell_w * 4, cell_h * 4 + 30), pygame.SRCALPHA,
    )
    composite.fill((4, 6, 14, 255))
    # Title.
    font = pygame.font.SysFont("monospace", 14)
    title = font.render(
        "v1.7 CHARGED DISC (weapon 1, white piercing) | "
        "R1: charge 0/50/85/100%  R2: flying 0.0/0.1/0.2/0.3s  "
        "R3: fading 0/33/66/100%  R4: hit cruising/first/secondary/dead",
        True, (220, 220, 240),
    )
    composite.blit(title, (10, 6))
    full_charge = 1.0  # v1.7: weapon 1 = 1.0s (was 1.2s)

    def _blit_cell(col: int, row: int, cell: pygame.Surface) -> None:
        composite.blit(cell, (col * cell_w, 30 + row * cell_h))

    # ----- Row 1: charging preview -----
    for col, frac in enumerate((0.0, 0.50, 0.85, 1.00)):
        s.player.x = 120
        s.player.y = INTERNAL_H // 2
        s.player.alive = True
        s.player.charging = frac > 0.0
        s.player.charge_time = full_charge * frac
        s.player.charge_complete = frac >= 1.0
        for d in s.charged_discs:
            d.alive = False
        _blit_cell(col, 0, _render_cell(s))

    # ----- Row 2: in-flight disc at progressive t -----
    # Each panel shows the disc at a different x position (and
    # therefore a different "elapsed" since spawn, for the
    # residual spin visualization). The disc was spawned at
    # x=60; we just place it at the desired x and stamp elapsed
    # so the rings behave correctly.
    flight_xs = (60, 160, 260, 360)
    for col, fx_x in enumerate(flight_xs):
        s.player.alive = False
        for d in s.charged_discs:
            d.alive = False
        d = s.charged_discs[0]
        d.spawn(fx_x, INTERNAL_H // 2, 0.0)
        d.elapsed = (fx_x - 60) / ChargedDisc.SPEED_PX_S
        # Emit some trail particles for visual richness.
        for _ in range(3):
            charged_disc_renderer.emit_trail(s.fx, d)
        _blit_cell(col, 1, _render_cell(s))
        d.alive = False
        # Clear emitted trail so it doesn't carry over.
        s.fx.engine.pool  # access for the .active_count
        s.fx = type(s.fx)()  # fresh FxLayer for the next panel
        s.player.alive = True

    # ----- Row 3: fading disc at progressive FADE_DURATION_S -----
    fade_fracs = (0.0, 0.33, 0.66, 1.00)
    for col, frac in enumerate(fade_fracs):
        s.player.alive = False
        for d in s.charged_discs:
            d.alive = False
        d = s.charged_discs[0]
        d.spawn(240, INTERNAL_H // 2, 0.0)
        d.state = State.FADING
        d.fade_elapsed = ChargedDisc.FADE_DURATION_S * frac
        d.vx = 0.0  # freeze position so the fade is the only motion
        _blit_cell(col, 2, _render_cell(s))
        d.alive = False
        s.player.alive = True

    # ----- Row 4: hit feedback -----
    from stellar_horizon.fx.weapon_impact import get_params
    # Panel 1: disc cruising (no hit yet)
    s.player.alive = False
    for d in s.charged_discs:
        d.alive = False
    d = s.charged_discs[0]
    d.spawn(200, INTERNAL_H // 2, 0.0)
    _blit_cell(0, 3, _render_cell(s))
    d.alive = False
    # Panel 2: first-hit feedback (8x, shockwave + flash + shake)
    d.spawn(220, INTERNAL_H // 2, 0.0)
    d.register_hit()
    s.fx.emit_shockwave(d.x, d.y, radius=45,
                        color=(255, 255, 255), life=0.18)
    s.fx.add_flash(d.x, d.y, radius=35,
                   color=(255, 255, 255), duration=0.15)
    s.fx.emit_impact_weapon(d.x, d.y, 1.0, 0.0, get_params(1))
    s.fx.add_screen_shake(3.0, 0.15)
    _blit_cell(1, 3, _render_cell(s))
    # Clear FxLayer state
    s.fx.shockwaves.clear()
    s.fx._flashes.clear()
    s.fx.shake_amplitude = 0.0
    s.fx.shake_life = 0.0
    s.fx.shake_max_life = 0.0
    d.alive = False
    # Panel 3: secondary hit (3x, splash only -- no shockwave/flash)
    d.spawn(260, INTERNAL_H // 2, 0.0)
    d.register_hit()  # hit_count = 1
    d.register_hit()  # hit_count = 2 (treated as secondary in the
    # scene's handler: hit_count != 0, hit_count <= MAX_HITS)
    s.fx.emit_impact_weapon(d.x, d.y, 1.0, 0.0, get_params(1))
    _blit_cell(2, 3, _render_cell(s))
    d.alive = False
    # Panel 4: post-fade dead (no disc, no FX)
    _blit_cell(3, 3, _render_cell(s))
    s.player.alive = True

    # Save.
    pygame.image.save(composite, str(out))
    print(f"Saved: {out}")
    print(f"Size: {composite.get_size()}")


if __name__ == "__main__":
    main()
