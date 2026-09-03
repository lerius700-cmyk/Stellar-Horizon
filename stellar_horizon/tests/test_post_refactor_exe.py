"""Post-SF+SM-refactor executable + PyInstaller spec verification.

Two test groups:

1. **Runtime**: main.py + the built .exe boot without immediate crash.
2. **Build system**: the PyInstaller spec bundles every directory
   the runtime loads data from. Regression guard for the 2026-09-02
   FileNotFoundError on SPACE press (waves_act1.json was not bundled).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "StellarHorizon.spec"
MAIN_PY = ROOT / "main.py"
EXE = ROOT / "dist" / "StellarHorizon.exe"


# --- Build system: PyInstaller spec regression guards ---

# Directories the .exe must bundle. Add to this list when introducing
# new runtime-loaded data.
REQUIRED_DATA_DIRS = (
    "stellar_horizon/assets",
    "stellar_horizon/waves",
    "stellar_horizon/settings.py",
)


def test_spec_file_exists() -> None:
    assert SPEC.exists(), f"PyInstaller spec missing: {SPEC}"


@pytest.mark.parametrize("required_dir", list(REQUIRED_DATA_DIRS))
def test_spec_bundles_required_directory(required_dir: str) -> None:
    """Each runtime-loaded directory must appear in spec datas=.
    Regression guard for the 2026-09-02 FileNotFoundError on SPACE."""
    text = SPEC.read_text(encoding="utf-8-sig")
    pattern = re.compile(rf"['\"]" + re.escape(required_dir) + r"['\"]")
    assert pattern.search(text), (
        f"StellarHorizon.spec is missing '{required_dir}' in datas=. "
        f"Add ('{required_dir}', '{required_dir}') to the datas list."
    )


def test_spec_assets_directory_exists_on_disk() -> None:
    for d in REQUIRED_DATA_DIRS:
        if d.endswith(".py"):
            assert (ROOT / d).is_file(), f"Source missing: {d}"
        else:
            assert (ROOT / d).is_dir(), f"Source missing: {d}"


def test_wave_json_exists_for_bundling() -> None:
    """The specific file that broke the 2026-09-02 release."""
    p = ROOT / "stellar_horizon" / "waves" / "waves_act1.json"
    assert p.is_file(), f"{p} is required by the runtime; spec must bundle stellar_horizon/waves/"


# --- Runtime: main.py validation ---

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
    main loop, and exits cleanly."""
    env = os.environ.copy()
    env.setdefault("SDL_VIDEODRIVER", "dummy")
    env.setdefault("SDL_AUDIODRIVER", "dummy")
    result = subprocess.run(
        [sys.executable, str(MAIN_PY), "--duration", "3"],
        capture_output=True, text=True, timeout=15, env=env,
    )
    assert "Traceback" not in result.stderr, (
        f"main.py --duration 3 raised an exception:\n{result.stderr}"
    )


# --- Runtime: built .exe verification ---

@pytest.mark.skipif(not EXE.exists(), reason="dist/StellarHorizon.exe not built")
def test_built_exe_starts_and_stays_alive() -> None:
    """Boot the .exe. If it imports OK and the scene wires up, the
    process stays alive. If something crashes (path bug, import error,
    display init), the process exits within ~1s."""
    env = {**os.environ, "SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"}
    proc = subprocess.Popen(
        [str(EXE)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
    )
    try:
        time.sleep(2.0)
        poll = proc.poll()
        if poll is not None:
            stdout, stderr = proc.communicate()
            raise AssertionError(
                f".exe exited prematurely with code {poll}\n"
                f"STDOUT: {stdout.decode('utf-8', errors='replace')}\n"
                f"STDERR: {stderr.decode('utf-8', errors='replace')}"
            )
    finally:
        if proc.poll() is None:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True, timeout=5,
            )
