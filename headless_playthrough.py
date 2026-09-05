"""Headless end-to-end playthrough.

Runs the full Stellar Horizon game loop without opening a visible
window. Simulates player input via pygame.event.post() and reports
any exception that would have crashed the .exe.

The user can't accidentally close this (no window = nothing to close).
Captures all exceptions, not just stderr.
"""
from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path

# Force headless mode BEFORE importing pygame.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from stellar_horizon.core.game import Game  # noqa: E402
from stellar_horizon.settings import FPS_TARGET  # noqa: E402


def make_key_event(key: int, unicode: str = " ") -> pygame.event.Event:
    return pygame.event.Event(
        pygame.KEYDOWN,
        {"key": key, "mod": 0, "unicode": unicode, "scancode": 0, "window": None},
    )


def main(duration_s: float = 200.0) -> int:
    """Run the game headless for `duration_s` seconds, simulating
    a player who shoots constantly and moves in a cycle.
    Returns 0 on success, 1 on crash, 2 on setup failure."""
    print(f"=== Headless playthrough for {duration_s}s (full Act 1 + boss) ===")

    wave_json = ROOT / "stellar_horizon" / "waves" / "waves_act1.json"
    if not wave_json.exists():
        print(f"FATAL: wave JSON not found: {wave_json}")
        return 2

    pygame.init()
    pygame.mixer.init()
    try:
        g = Game(wave_json=wave_json)
    except Exception as e:
        print(f"FATAL: Game() construction crashed: {type(e).__name__}: {e}")
        traceback.print_exc()
        return 1

    # Skip the title menu and force the gameplay scene.
    from stellar_horizon.scenes.gameplay import GameplayScene
    g.scenes.current = GameplayScene(
        g.midi_player, g.wave_json, g.assets_dir,
    )
    g.scenes.current.on_enter()
    print("Gameplay scene started. Running main loop headless...")

    start = time.perf_counter()
    tick = 0
    last_move = 0.0
    move_idx = 0
    moves = ["w", "a", "s", "d"]
    key_map = {"w": pygame.K_w, "a": pygame.K_a, "s": pygame.K_s, "d": pygame.K_d}

    while (time.perf_counter() - start) < duration_s:
        try:
            now = time.perf_counter()
            # Inject SPACE (shoot) every frame.
            pygame.event.post(make_key_event(pygame.K_SPACE, " "))
            # Inject movement every ~1.2s.
            if (now - last_move) > 1.2:
                d = moves[move_idx % 4]
                pygame.event.post(make_key_event(key_map[d], d))
                move_idx += 1
                last_move = now

            # Drive one frame. _tick_frame uses pygame.event.get() internally
            # so our posted events will be processed.
            g._tick_frame()
            tick += 1

            # Periodic log.
            if tick % (30 * FPS_TARGET) == 0:
                elapsed = int(time.perf_counter() - start)
                sc = g.scenes.current
                player_alive = getattr(sc, "player", None) and sc.player.alive
                boss_alive = bool(getattr(sc, "boss", None) and sc.boss and sc.boss.alive)
                wave_idx = g.scenes.current.wave_manager.current_wave_index if hasattr(g.scenes.current, "wave_manager") and g.scenes.current.wave_manager else "?"
                print(f"[{elapsed}s] tick={tick} wave={wave_idx} player_alive={player_alive} boss_alive={boss_alive}")
        except Exception as e:
            elapsed = int(time.perf_counter() - start)
            print(f"CRASH at {elapsed}s tick {tick}: {type(e).__name__}: {e}")
            traceback.print_exc()
            return 1

    elapsed = int(time.perf_counter() - start)
    print(f"=== Fin tras {elapsed}s (tick={tick}) ===")
    print("Sin crashes. Engine solido para duracion completa del nivel.")
    return 0


if __name__ == "__main__":
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 200.0
    raise SystemExit(main(duration))
