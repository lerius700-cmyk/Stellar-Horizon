"""Headless end-to-end playthrough — v2 with REAL input.

v1 was bogus: it posted events to the pygame queue but Player.update
reads the key state via pygame.key.get_pressed(), not the event queue.
The player never actually moved or shot, died immediately, and the
test sat on the game over screen for 200s. 23,283 meaningless ticks.

v2 monkey-patches:
1. pygame.key.get_pressed() to return a fake state (SPACE + cyclic WASD)
2. Player.take_hit() to be a no-op (so the player survives and the
   waves actually progress)

This makes the level ACTUALLY exercise: waves spawn, enemies fire,
boss spawns, boss attacks, boss takes damage.
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


# ---------------------------------------------------------------------------
# Patches
# ---------------------------------------------------------------------------

class FakeKeys:
    """Acts like pygame's ScancodeWrapper: keys[K_SPACE] returns True/False."""
    def __init__(self) -> None:
        self._state: dict[int, bool] = {}

    def set(self, key: int, pressed: bool) -> None:
        self._state[key] = pressed

    def __getitem__(self, key: int) -> bool:
        return self._state.get(key, False)

    def __setitem__(self, key: int, value: bool) -> None:
        self._state[key] = value


_FAKE_KEYS = FakeKeys()
_cycle = ["w", "a", "s", "d"]
_cycle_idx = [0]
_last_move = [0.0]


def fake_get_pressed() -> FakeKeys:
    """Return a FakeKeys whose state changes over time to simulate
    SPACE held + WASD cycling every 1.2s. Called by the game each frame
    to read movement/shooting state."""
    now = time.perf_counter()
    # Always hold SPACE (shoot).
    _FAKE_KEYS[pygame.K_SPACE] = True
    # Move direction changes every 1.2s.
    if (now - _last_move[0]) > 1.2:
        d = _cycle[_cycle_idx[0] % 4]
        keymap = {"w": pygame.K_w, "a": pygame.K_a, "s": pygame.K_s, "d": pygame.K_d}
        for k in (pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d):
            _FAKE_KEYS[k] = False
        _FAKE_KEYS[keymap[d]] = True
        _cycle_idx[0] += 1
        _last_move[0] = now
    return _FAKE_KEYS


def install_patches() -> None:
    """Patch pygame.key.get_pressed + Player.take_hit BEFORE Game()
    is constructed."""
    # Patch pygame's key state reader.
    pygame.key.get_pressed = fake_get_pressed  # type: ignore[assignment]

    # Patch Player.take_hit to be a no-op so the player survives and
    # the level plays out. This is the test-only "invincibility" mode.
    from stellar_horizon.entities.player import Player

    def _invincible_take_hit(self, amount: int = 1) -> None:  # type: ignore[no-redef]
        return  # no-op for headless test

    Player.take_hit = _invincible_take_hit  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Main driver
# ---------------------------------------------------------------------------

def main(duration_s: float = 200.0) -> int:
    print(f"=== Headless playthrough v2 for {duration_s}s ===")
    print("Patches applied: SPACE always held, WASD cycling, player invincible")
    print("Goal: ACTUALLY exercise waves + boss (not just sit on game over)")

    wave_json = ROOT / "stellar_horizon" / "waves" / "waves_act1.json"
    if not wave_json.exists():
        print(f"FATAL: wave JSON not found: {wave_json}")
        return 2

    install_patches()

    pygame.init()
    pygame.mixer.init()
    try:
        g = Game(wave_json=wave_json)
    except Exception as e:
        print(f"FATAL: Game() construction crashed: {type(e).__name__}: {e}")
        traceback.print_exc()
        return 1

    # Skip the title menu; force the gameplay scene.
    from stellar_horizon.scenes.gameplay import GameplayScene
    g.scenes.current = GameplayScene(
        g.midi_player, g.wave_json, g.assets_dir,
    )
    g.scenes.current.on_enter()
    print("Gameplay scene started. Running main loop headless...")

    start = time.perf_counter()
    tick = 0
    boss_spawned_at: float | None = None
    boss_killed = False
    waves_seen: set[int] = set()

    while (time.perf_counter() - start) < duration_s:
        try:
            g._tick_frame()
            tick += 1
            sc = g.scenes.current

            # Log progress every 15s.
            if tick % (15 * FPS_TARGET) == 0:
                elapsed = int(time.perf_counter() - start)
                wm = getattr(sc, "wave_manager", None)
                wave_idx = wm.current_wave_index if wm else "?"
                if isinstance(wave_idx, int):
                    waves_seen.add(wave_idx)
                boss_alive = bool(getattr(sc, "boss", None) and sc.boss and sc.boss.alive)
                boss_hp = sc.boss.hp if (getattr(sc, "boss", None) and sc.boss) else None
                if boss_alive and boss_spawned_at is None:
                    boss_spawned_at = time.perf_counter() - start
                print(f"[{elapsed}s] tick={tick} wave={wave_idx} waves_seen={sorted(waves_seen)} "
                      f"boss_alive={boss_alive} boss_hp={boss_hp} player_alive={getattr(sc, 'player', None) and sc.player.alive}")

            # Check if boss was killed (transitioned away from gameplay or boss is dead).
            boss = getattr(sc, "boss", None)
            if boss is not None and not boss.alive and boss_spawned_at is not None and not boss_killed:
                boss_killed = True
                print(f"BOSS KILLED at {int(time.perf_counter() - start)}s!")
        except Exception as e:
            elapsed = int(time.perf_counter() - start)
            print(f"CRASH at {elapsed}s tick {tick}: {type(e).__name__}: {e}")
            traceback.print_exc()
            return 1

    elapsed = int(time.perf_counter() - start)
    print(f"=== Fin tras {elapsed}s (tick={tick}) ===")
    print(f"Waves actually exercised: {sorted(waves_seen)}")
    print(f"Boss spawned: {boss_spawned_at is not None} (at t={boss_spawned_at}s)")
    print(f"Boss killed: {boss_killed}")
    if not waves_seen:
        print("FAIL: no waves were actually played (engine sat on game over)")
        return 1
    if boss_spawned_at is None:
        print("FAIL: boss never spawned (level didn't progress through waves)")
        return 1
    print("PASS: engine actually exercised waves + boss")
    return 0


if __name__ == "__main__":
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 200.0
    raise SystemExit(main(duration))
