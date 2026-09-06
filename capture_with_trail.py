"""Capture a frame WITH the enemy moving (so the trail is visible).

Used to verify the comet-tail light trail effect. Constructs an
enemy, moves it for a few frames to populate the trail, then renders
one frame and saves as PNG.
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


class _MockPlayer:
    x = 0.0
    y = 0.0


def main(output_path: str) -> int:
    wave_json = ROOT / "stellar_horizon" / "waves" / "waves_act1.json"
    pygame.init()
    pygame.mixer.init()
    g = Game(wave_json=wave_json)

    from stellar_horizon.scenes.gameplay import GameplayScene
    g.scenes.current = GameplayScene(
        g.midi_player, g.wave_json, g.assets_dir,
    )
    g.scenes.current.on_enter()
    sc = g.scenes.current

    # Set up player in view.
    sc.player.x = 240.0
    sc.player.y = 135.0
    sc.player.vx = 165.0

    # Spawn 2 enemies in view, with trails populated by movement.
    if sc.wave_manager and sc.wave_manager.spawned_enemies:
        # Enemy 1: scout, moving left fast (right to left)
        e1 = sc.wave_manager.spawned_enemies[0]
        e1.kind = "scout"
        e1.on_spawn()  # re-init to reset vx, flame, etc.
        e1.x, e1.y = 200.0, 60.0
        e1.vx, e1.vy = -180.0, 0.0
        e1.alive = True
        e1.path_done = True  # force translation in update()
        # Manually populate the trail to simulate 10 frames of movement.
        from collections import deque
        e1._trail = deque(maxlen=15)
        for i in range(10):
            e1._trail.append((e1.x + i * 1.5, e1.y))  # past positions to the right

        # Enemy 2: kamikaze, moving down
        e2 = sc.wave_manager.spawned_enemies[1] if len(sc.wave_manager.spawned_enemies) > 1 else None
        if e2 is not None:
            e2.kind = "kamikaze"
            e2.on_spawn()
            e2.x, e2.y = 350.0, 180.0
            e2.vx, e2.vy = 0.0, 200.0
            e2.alive = True
            e2._trail = deque(maxlen=15)
            for i in range(10):
                e2._trail.append((e2.x, e2.y - i * 1.5))  # past positions above

    # Render one frame.
    g.scenes.update(1 / 120, [])
    g.scenes.draw(g.internal)
    pygame.image.save(g.internal, output_path)
    print(f"Saved frame: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "frame_trail.png"))
