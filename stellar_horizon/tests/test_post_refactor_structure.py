"""Post-SF+SM-refactor structural invariants.

These tests codify the contract of the 2026-09-01 cleanup. They exist to
catch regressions where a phantom directory sneaks back in, or where a
needed file gets accidentally deleted.

If any of these tests fail, the project structure has been broken and
the refactor is no longer in effect.
"""
from __future__ import annotations

from pathlib import Path

import pytest


# Project root resolution: this test file is at stellar_horizon/tests/, so
# going up 2 parents lands at the repo root.
ROOT = Path(__file__).resolve().parents[2]


# --- Directories that MUST NOT exist (cleaned 2026-09-01) ---

@pytest.mark.parametrize("forbidden_path", [
    ROOT / "assets",                       # phantom duplicate of stellar_horizon/assets
    ROOT / "src",                          # moved to stellar_horizon/_systems/
    ROOT / "stellar_horizon" / "_vendor",  # dead code (movement, palette, particle_engine, pool)
    ROOT / "tests",                        # unified into stellar_horizon/tests/
    ROOT / "build_fresh",                  # stale build artifact
    ROOT / "dist_fresh",                   # stale build artifact
])
def test_forbidden_directory_does_not_exist(forbidden_path: Path) -> None:
    """The refactor removed these directories; if they come back,
    the project has regressed."""
    assert not forbidden_path.exists(), (
        f"FORBIDDEN directory exists: {forbidden_path}. "
        f"Refactor regression — investigate before re-introducing."
    )


# --- Directories that MUST exist (refactor created/moved these) ---

@pytest.mark.parametrize("required_path", [
    ROOT / "stellar_horizon" / "_systems",
    ROOT / "stellar_horizon" / "_systems" / "movement",
    ROOT / "stellar_horizon" / "_systems" / "audio",
    ROOT / "stellar_horizon" / "_systems" / "systems",
    ROOT / "stellar_horizon" / "assets" / "sprites",
    ROOT / "stellar_horizon" / "assets" / "midi",
    ROOT / "stellar_horizon" / "assets" / "backgrounds",
    ROOT / "stellar_horizon" / "tests",
    ROOT / "stellar_horizon" / "tests" / "conftest.py",
])
def test_required_path_exists(required_path: Path) -> None:
    """Refactor moved/created these paths. Missing = regression."""
    assert required_path.exists(), f"REQUIRED path missing: {required_path}"


# --- File counts as structural assertions ---

def test_systems_movement_has_expected_modules() -> None:
    """The movement submodule has the files that WaveManager + tests
    depend on. If any of these disappear, the game crashes on import."""
    movement = ROOT / "stellar_horizon" / "_systems" / "movement"
    expected = {"__init__.py", "bezier.py", "follower.py", "hybrid.py",
                "orbital_path.py", "parallel_path.py", "spec.py", "waypoint.py"}
    actual = {p.name for p in movement.iterdir() if p.is_file()}
    missing = expected - actual
    assert not missing, f"movement/ missing required files: {missing}"


def test_systems_audio_has_synth() -> None:
    """audio/synth.py is the only file from src/audio/ that the live
    code imports (via sfx.py). Missing = MidiPlayer crashes."""
    synth = ROOT / "stellar_horizon" / "_systems" / "audio" / "synth.py"
    assert synth.exists(), "audio/synth.py is required by sfx.py"


def test_systems_particle_engine_exists() -> None:
    """systems/particle_engine.py is imported by fx/particles.py.
    Missing = FxLayer construction crashes the game."""
    pe = ROOT / "stellar_horizon" / "_systems" / "systems" / "particle_engine.py"
    assert pe.exists(), "systems/particle_engine.py is required by fx/particles.py"


# --- Top-level project files ---

def test_agents_md_exists() -> None:
    """AGENTS.md is the memory layer entry point. Without it, future
    agents have no onboarding context."""
    assert (ROOT / "AGENTS.md").exists(), "AGENTS.md is missing at repo root"


def test_context_md_exists() -> None:
    """CONTEXT.md is the project state diary. Required by SF+SM Lite."""
    assert (ROOT / "CONTEXT.md").exists(), "CONTEXT.md is missing at repo root"


def test_no_log_files_at_root() -> None:
    """The refactor removed build_err.log, build_out.log, game_err.log,
    game_out.log from the root. They were stale build artifacts."""
    log_files = list(ROOT.glob("*.log"))
    assert not log_files, f"Stale log files at root: {[p.name for p in log_files]}"
