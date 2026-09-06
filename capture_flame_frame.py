"""Capture a single rendered frame of the gameplay scene.

Used to compare engine flame size before/after the size tuning fix.
Renders one frame to the internal surface and saves it as PNG.

Usage:
    python capture_flame_frame.py path/to/output.png
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

from stellar_horizon.core.game import Game  # noqa: E402


def main(output_path: str) -> int:
    wave_json = ROOT / "stellar_horizon" / "waves" / "waves_act1.json"
    pygame.init()
    pygame.mixer.init()
    g = Game(wave_json=wave_json)

    # Force the gameplay scene.
    from stellar_horizon.scenes.gameplay import GameplayScene
    g.scenes.current = GameplayScene(
        g.midi_player, g.wave_json, g.assets_dir,
    )
    g.scenes.current.on_enter()

    # Position the player center-screen for a clear flame shot.
    sc = g.scenes.current
    sc.player.x = 240.0
    sc.player.y = 135.0
    sc.player.vx = 165.0  # max player speed -> maximum flame size_scale

    # Spawn one enemy in view for comparison.
    if sc.wave_manager and sc.wave_manager.spawned_enemies:
        e = sc.wave_manager.spawned_enemies[0]
        e.x = 100.0
        e.y = 80.0
        e.vx = -200.0  # fast moving
        e.alive = True

    # Render one frame.
    g.scenes.update(1 / 120, [])
    g.scenes.draw(g.internal)
    pygame.image.save(g.internal, output_path)
    print(f"Saved frame: {output_path} ({g.internal.get_size()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "frame.png"))
