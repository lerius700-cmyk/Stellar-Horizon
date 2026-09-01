"""Post-SF+SM-refactor import invariants.

The refactor moved src/ -> stellar_horizon/_systems/ and rewrote 196
import statements. These tests assert that:

1. No `from src.X` or `import src.X` remains in the codebase.
2. The active modules ARE importable from their new home.
3. Critical game subsystems (FxLayer, Player, Enemy, WaveManager, GameplayScene)
   still construct without import errors.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
PATTERN_FROM_SRC = re.compile(r"^(\s*)from\s+src\.", re.MULTILINE)
PATTERN_IMPORT_SRC = re.compile(r"^(\s*)import\s+src\.", re.MULTILINE)


# --- No legacy src/ imports should remain ---

@pytest.mark.parametrize("scan_dir", [
    ROOT / "stellar_horizon" / "_systems",
    ROOT / "stellar_horizon" / "audio",
    ROOT / "stellar_horizon" / "core",
    ROOT / "stellar_horizon" / "entities",
    ROOT / "stellar_horizon" / "fx",
    ROOT / "stellar_horizon" / "scenes",
    ROOT / "stellar_horizon" / "ui",
    ROOT / "stellar_horizon" / "waves",
    ROOT / "stellar_horizon" / "tests",
    ROOT / "main.py",
    ROOT / "smoke.py",
])
def test_no_from_src_imports_remain(scan_dir: Path) -> None:
    """`from src.X` is forbidden post-refactor. src/ no longer exists."""
    if scan_dir.is_file():
        files = [scan_dir]
    else:
        files = [p for p in scan_dir.rglob("*.py") if "__pycache__" not in p.parts]
    offenders = []
    for f in files:
        # utf-8-sig auto-strips the BOM if present. PowerShell's Out-File
        # adds a BOM that would defeat the ^ anchor in our regex.
        text = f.read_text(encoding="utf-8-sig")
        if PATTERN_FROM_SRC.search(text) or PATTERN_IMPORT_SRC.search(text):
            offenders.append(str(f.relative_to(ROOT)))
    assert not offenders, (
        f"Legacy src/ imports found (refactor regression): {offenders}"
    )


# --- The active modules must import from their new home ---

def test_movement_module_importable_from_new_home() -> None:
    """BezierPath, HybridPath, PathFollower are the symbols that the
    waves + entities modules depend on. If they don't import, the
    game crashes on wave JSON load."""
    from stellar_horizon._systems.movement import (  # noqa: F401
        BezierPath, FlightFormation, HybridPath, PathFollower, Point,
        WaypointPath,
    )


def test_audio_synth_module_importable() -> None:
    """audio.synth.AudioEngine is imported by stellar_horizon/audio/sfx.py.
    Without it, sfx.play_event crashes."""
    from stellar_horizon._systems.audio.synth import AudioEngine  # noqa: F401


def test_particle_engine_module_importable() -> None:
    """systems.particle_engine provides the particle pool + kinds
    that FxLayer wraps. Without it, every scene's on_enter crashes."""
    from stellar_horizon._systems.systems.particle_engine import (  # noqa: F401
        ParticleEngine, P_SPARK, P_FIRE, P_GLOW, P_DUST, P_FLASH,
    )


# --- Critical game subsystems construct without errors ---

def test_fx_layer_constructs() -> None:
    """FxLayer is created by every scene. If it doesn't construct,
    no scene can run."""
    import pygame
    pygame.init()
    try:
        from stellar_horizon.fx.particles import FxLayer
        fx = FxLayer()
        assert fx is not None
    finally:
        pygame.quit()


def test_player_constructs() -> None:
    """Player is the playable ship. Constructing it exercises the
    Player.__init__ + EngineFlame init path."""
    import pygame
    pygame.init()
    try:
        from stellar_horizon.entities.player import Player
        from stellar_horizon.settings import INTERNAL_W, INTERNAL_H
        p = Player(pygame.Rect(0, 0, INTERNAL_W, INTERNAL_H))
        assert p.lives == Player.MAX_LIVES
        assert p.flame is not None  # visual polish
    finally:
        pygame.quit()


def test_enemy_constructs_and_emits_explosion() -> None:
    """Enemy construction + take_damage must not raise. The visual polish
    refactor added fx.explosion on death; if the import broke, this fails."""
    import pygame
    pygame.init()
    try:
        from stellar_horizon.entities.enemy import Enemy
        from stellar_horizon.fx.particles import FxLayer
        for kind in ("scout", "cruiser", "heavy", "bomber", "ufo", "kamikaze"):
            e = Enemy()
            e.kind = kind
            e.on_spawn()
            e.hp = 1
            e.fx = FxLayer()
            e.take_damage(1)  # should not raise
    finally:
        pygame.quit()


def test_gameplay_scene_on_enter_does_not_crash() -> None:
    """GameplayScene.on_enter() is where EVERYTHING wires up: sprites,
    wave manager, audio, FX, HUD, thrusters. If any import broke, this fails.
    CWD-independent via Path(__file__)."""
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    import pygame
    pygame.init()
    try:
        from stellar_horizon.audio.midi_player import MidiPlayer
        from stellar_horizon.scenes.gameplay import GameplayScene
        from stellar_horizon.settings import INTERNAL_W, INTERNAL_H
        from pathlib import Path
        # Use __file__-relative paths (post-path-fix contract).
        here = Path(__file__).resolve().parent
        wave_json = here.parent / "waves" / "waves_act1.json"
        assets_dir = here.parent / "assets"
        s = GameplayScene(MidiPlayer(), wave_json, assets_dir)
        s.on_enter()  # MUST NOT RAISE
        assert s.player is not None
        assert s.wave_manager is not None
        assert s.fx is not None
    finally:
        pygame.quit()
