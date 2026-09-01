"""Post-SF+SM-refactor executable verification.

These tests boot the actual game (or the built .exe if present) and
verify it runs without immediate crash. This catches:

- Path resolution bugs (would FileNotFoundError on first frame)
- Import errors not caught by pytest (mixer init, display init)
- Display/window creation failures
- Audio init failures
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MAIN_PY = ROOT / "main.py"
EXE = ROOT / "dist" / "StellarHorizon.exe"


# --- main.py validation ---

def test_main_py_check_exits_zero() -> None:
    """`python main.py --check` validates imports + settings. Exit 0
    means the package can be loaded without errors."""
    env = os.environ.copy()
    env.setdefault("SDL_VIDEODRIVER", "dummy")
    env.setdefault("SDL_AUDIODRIVER", "dummy")
    result = subprocess.run(
        [sys.executable, str(MAIN_PY), "--check"],
        capture_output=True, text=True, timeout=30, env=env,
    )
    assert result.returncode == 0, (
        f"main.py --check exited {result.returncode}\n"
        f"STDOUT: {result.stdout}\n"
        f"STDERR: {result.stderr}"
    )
    assert "STELLAR HORIZON check OK" in result.stdout, (
        f"Expected success message. Got: {result.stdout}"
    )


def test_main_py_runs_full_loop_for_3_seconds() -> None:
    """`python main.py --duration 3` actually boots the game, runs the
    main loop, and exits cleanly. Catches errors that only show up at
    runtime (e.g., display init, mixer init, scene on_enter side effects)."""
    env = os.environ.copy()
    env.setdefault("SDL_VIDEODRIVER", "dummy")
    env.setdefault("SDL_AUDIODRIVER", "dummy")
    result = subprocess.run(
        [sys.executable, str(MAIN_PY), "--duration", "3"],
        capture_output=True, text=True, timeout=15, env=env,
    )
    # Auto-exit returns 0 on success; what matters is no exception traceback.
    assert "Traceback" not in result.stderr, (
        f"main.py --duration 3 raised an exception:\n{result.stderr}"
    )


# --- Built .exe verification (only if .exe exists) ---

@pytest.mark.skipif(not EXE.exists(), reason="dist/StellarHorizon.exe not built")
def test_built_exe_starts_and_stays_alive() -> None:
    """Boot the .exe. If it imports OK and the scene wires up, the
    process stays alive. If something crashes (path bug, import error,
    display init), the process exits within ~1s.

    We wait 2s, then check the process is still running. If it is,
    the .exe is healthy. We then force-kill it via taskkill."""
    env = {**os.environ, "SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"}
    proc = subprocess.Popen(
        [str(EXE)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
    )
    try:
        time.sleep(2.0)
        # If the process died, the .exe is broken.
        poll = proc.poll()
        if poll is not None:
            stdout, stderr = proc.communicate()
            raise AssertionError(
                f".exe exited prematurely with code {poll}\n"
                f"STDOUT: {stdout.decode('utf-8', errors='replace')}\n"
                f"STDERR: {stderr.decode('utf-8', errors='replace')}"
            )
    finally:
        # Force-kill via taskkill (more reliable on Windows than proc.kill).
        if proc.poll() is None:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True, timeout=5,
            )
