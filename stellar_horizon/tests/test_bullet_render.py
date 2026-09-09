# stellar_horizon/tests/test_bullet_render.py
"""Integration tests for the 6-frame animated bullet render
(visual polish v2).
"""
from __future__ import annotations
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from pathlib import Path
from stellar_horizon.audio.midi_player import MidiPlayer
from stellar_horizon.scenes.gameplay import GameplayScene
from stellar_horizon.entities.bullet import PlayerBullet


def test_bullet_renders_with_animation_frame_changes():
    # 2026-09-06 visual polish v2: the bullet sprite is now a
    # 6-frame animated sheet. After 0.15s of update, frame_index
    # should be 1, and the sheet loaded from gameplay should have
    # 6 frames available.
    # 2026-09-08 v1.5 final: weapon 4 (rainbow streak) maps to
    # laser_05.
    pygame.init()
    try:
        s = GameplayScene(
            MidiPlayer(),
            Path("stellar_horizon/waves/waves_act1.json"),
            Path("stellar_horizon/assets"),
        )
        s._load_sprites()
        b = PlayerBullet()
        b.spawn(100, 100, 100, 0, weapon=4, spawn_time=0.0)
        b.alive = True
        # Advance 0.15s
        for _ in range(15):
            b.update(0.01)
        assert b.frame_index >= 1, (
            f"frame_index should advance past 0 after 0.15s, got {b.frame_index}"
        )
        # Verify the sheet has 6 frames
        sheet = s._animated.get("laser_05")
        assert sheet is not None and sheet.loaded, (
            "laser_05 sheet should be loaded"
        )
        assert len(sheet._frames) == 6, (
            f"laser_05 sheet should have 6 frames, got {len(sheet._frames)}"
        )
    finally:
        pygame.quit()


def test_weapon4_emits_sparks_in_pool():
    # 2026-09-08 v1.5 final: weapon 4 (rainbow streak) emits
    # P_SPARK particles. After many update() calls, the FxLayer's
    # particle pool should have P_SPARK particles.
    pygame.init()
    try:
        s = GameplayScene(
            MidiPlayer(),
            Path("stellar_horizon/waves/waves_act1.json"),
            Path("stellar_horizon/assets"),
        )
        s._load_sprites()
        # on_enter() creates the player + wires the wave manager +
        # background + MIDI. We call it so s.player exists for the
        # fx-injection step below.
        s.on_enter()
        # Put the test bullet into a pool slot so the scene's update
        # loop iterates over it. Without this, the scene never sees
        # the bullet and no particles are emitted.
        s.player_bullets[0].spawn(100, 100, 100, 0,
                                   weapon=4, spawn_time=0.0)
        # Tick the scene many times. The scene's update() runs the
        # bullet update loop on its pool, which is now where our
        # weapon-4 bullet lives.
        for _ in range(100):
            s.update(1/60, [])
        # P_SPARK = 0 in the engine
        spark_particles = [
            p for p in s.fx.particles
            if getattr(p, "kind", None) == 0
        ]
        assert len(spark_particles) > 0, (
            f"expected at least 1 P_SPARK particle after 100 ticks, "
            f"got {len(spark_particles)}"
        )
    finally:
        pygame.quit()
