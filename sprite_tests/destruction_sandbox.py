"""Destruction sandbox: capture the death-fall animation for visual review.

For each enemy kind, spawn one ship, take_damage, capture every
1/12s for 1.1s (12 frames). Arrange the 6 kinds × 12 frames in
a 3-column × 12-row grid (one column per kind pair, one row per
time). Save as a single PNG.

Usage:
    python sprite_tests/destruction_sandbox.py [<output_path>]
    python sprite_tests/destruction_sandbox.py --gravity 500 --drag 1.8
    python sprite_tests/destruction_sandbox.py --sweep

Without --sweep, captures one PNG with the current (gravity, drag)
values from enemy.py. With --sweep, captures 9 PNGs over a 3x3
parameter grid and saves them under sprite_tests/captures/.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from stellar_horizon.audio.midi_player import MidiPlayer
from stellar_horizon.entities.enemy import Enemy
from stellar_horizon.scenes.gameplay import GameplayScene


# 6 enemy kinds in display order
KINDS = ("scout", "cruiser", "heavy", "bomber", "ufo", "kamikaze")

FRAMES = 6  # 0.0, 0.1, 0.2, 0.3, 0.4, 0.5 seconds (covers most of the fall)
CELL_W = 80
CELL_H = 50


def _patch_enemy_physics(gravity: float, drag_linear: float) -> tuple[float, float]:
    """Override the module-level constants in enemy.py for one capture.
    Returns the originals so the caller can restore them in a finally.
    """
    import stellar_horizon.entities.enemy as enemy_mod
    orig_g = enemy_mod._ENEMY_DYING_GRAVITY_PX_S2
    orig_dl = enemy_mod._ENEMY_DYING_DRAG_LINEAR
    enemy_mod._ENEMY_DYING_GRAVITY_PX_S2 = gravity
    enemy_mod._ENEMY_DYING_DRAG_LINEAR = drag_linear
    return orig_g, orig_dl


def _restore_enemy_physics(orig_g: float, orig_dl: float) -> None:
    import stellar_horizon.entities.enemy as enemy_mod
    enemy_mod._ENEMY_DYING_GRAVITY_PX_S2 = orig_g
    enemy_mod._ENEMY_DYING_DRAG_LINEAR = orig_dl


class _MockPlayer:
    x = 50.0
    y = 135.0


def capture_one(gravity: float, drag_linear: float, out_path: Path) -> None:
    """Capture one contact-sheet PNG for the current physics params."""
    orig = _patch_enemy_physics(gravity, drag_linear)
    try:
        pygame.init()
        try:
            wave_json = Path("stellar_horizon/waves/waves_act1.json")
            assets_dir = Path("stellar_horizon/assets")
            s = GameplayScene(MidiPlayer(), wave_json, assets_dir)
            s.on_enter()

            # Each kind has its own dedicated scene (one enemy per kind,
            # captured at 6 timestamps). The 6 cells are arranged in a
            # 6-column x 6-row grid.
            for col, kind in enumerate(KINDS):
                for row in range(FRAMES):
                    # Fresh scene per cell to avoid state pollution
                    s2 = GameplayScene(MidiPlayer(), wave_json, assets_dir)
                    s2.on_enter()

                    e = Enemy()
                    e.kind = kind
                    e.on_spawn()
                    e.x = 100.0
                    e.y = 50.0
                    e.vx, e.vy = 0.0, 0.0
                    e.alive = True
                    e.hp = e.max_hp
                    e.path_done = True
                    e.sprite_name = f"enemy_{kind}_v1"
                    # Warm up so the IDLE sprite is on a real frame
                    for _ in range(3):
                        e.update(1 / 120, player=_MockPlayer())
                    e.take_damage(1)
                    # Tick to the desired timestamp
                    t = row * 0.1  # 0.0, 0.1, ..., 0.5
                    while e.dying_elapsed < t and e.alive:
                        e.update(1 / 120, player=_MockPlayer())

                    # Render the cell
                    cell = pygame.Surface((CELL_W, CELL_H), pygame.SRCALPHA)
                    cell.fill((20, 20, 30, 255))  # dark background
                    if e.alive:
                        s2._draw_enemy_sprite(
                            cell, e,
                            ox=CELL_W // 2 - e.x,
                            oy=CELL_H // 2 - e.y,
                        )
                    # Blit the cell onto the big grid surface
                    if col == 0 and row == 0:
                        grid = pygame.Surface(
                            (CELL_W * len(KINDS), CELL_H * FRAMES),
                            pygame.SRCALPHA,
                        )
                        grid.fill((20, 20, 30, 255))
                    grid.blit(cell, (col * CELL_W, row * CELL_H))

            out_path.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(grid, str(out_path))
            print(f"saved {out_path}  ({gravity:.0f} g, {drag_linear:.1f} drag)")
        finally:
            pygame.quit()
    finally:
        _restore_enemy_physics(*orig)


def run_sweep(out_dir: Path) -> None:
    """Capture 9 contact-sheets over a 3x3 parameter grid."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for gravity in (400.0, 500.0, 600.0):
        for drag in (0.5, 1.5, 3.0):
            out = out_dir / f"destruction_grav{int(gravity)}_drag{drag:.1f}.png"
            capture_one(gravity, drag, out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "output", nargs="?",
        default="D:/AI/stellar-horizon/sprite_tests/captures/destruction_default.png",
    )
    parser.add_argument("--gravity", type=float, default=None)
    parser.add_argument("--drag", type=float, default=None)
    parser.add_argument(
        "--sweep", action="store_true",
        help="Run a 3x3 sweep over (gravity, drag) and save to captures/",
    )
    args = parser.parse_args()

    if args.sweep:
        run_sweep(Path("D:/AI/stellar-horizon/sprite_tests/captures"))
    else:
        # Use the current module-level values if not overridden
        import stellar_horizon.entities.enemy as enemy_mod
        g = args.gravity if args.gravity is not None else enemy_mod._ENEMY_DYING_GRAVITY_PX_S2
        d = args.drag if args.drag is not None else enemy_mod._ENEMY_DYING_DRAG_LINEAR
        capture_one(g, d, Path(args.output))


if __name__ == "__main__":
    main()
