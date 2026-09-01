"""Tests for the visual polish VFX (engine flames, trails, FTL chain glow, explosions, bullet anims, player hit/death)."""
from __future__ import annotations

import pytest

from stellar_horizon.fx.particles import FxLayer
from stellar_horizon.entities.enemy import EnemyKind


# --- Trail particle tests ---

def test_emit_trail_creates_one_particle_per_call():
    fx = FxLayer(pool_size=64)
    fx.emit_trail(100.0, 50.0, (255, 100, 100), intensity=1.0)
    active = [p for p in fx.particles if p.active]
    assert len(active) >= 1, f"emit_trail should create at least 1 particle, got {len(active)}"


def test_emit_trail_particle_fades_over_lifetime():
    fx = FxLayer(pool_size=64)
    fx.emit_trail(100.0, 50.0, (255, 100, 100), intensity=1.0)
    initial_particle = [p for p in fx.particles if p.active][0]
    initial_life = initial_particle.life
    for _ in range(60):
        fx.update(1 / 60)
    final_life = initial_particle.life
    assert final_life < initial_life, (
        f"trail particle life should decay, went {initial_life} -> {final_life}"
    )


def test_emit_trail_color_is_applied():
    fx = FxLayer(pool_size=64)
    fx.emit_trail(100.0, 50.0, (50, 200, 50), intensity=1.0)
    particles = [p for p in fx.particles if p.active]
    assert len(particles) >= 1
    assert particles[0].color == (50, 200, 50), f"expected green, got {particles[0].color}"


def test_emit_trail_zero_intensity_emits_nothing():
    fx = FxLayer(pool_size=64)
    fx.emit_trail(100.0, 50.0, (255, 100, 100), intensity=0.0)
    assert len(fx.particles) == 0, "intensity=0 should emit no particles"


# --- Explosion typed tests ---

def test_emit_explosion_typed_for_all_enemy_kinds():
    """All 6 enemy kinds must trigger explosion on death."""
    fx = FxLayer(pool_size=256)
    for kind in [EnemyKind.SCOUT, EnemyKind.CRUISER, EnemyKind.HEAVY,
                 EnemyKind.BOMBER, EnemyKind.UFO, EnemyKind.KAMIKAZE]:
        fx.emit_explosion_typed(kind, 100.0, 50.0)
        active = [p for p in fx.particles if p.active]
        assert len(active) > 0, f"emit_explosion_typed({kind}) produced no particles"
        # Reset for next iteration
        for p in fx.particles:
            p.active = False


def test_emit_explosion_typed_heavy_has_larger_scale():
    """HEAVY explosion should have a larger scale than SCOUT explosion."""
    fx = FxLayer(pool_size=512)
    fx.emit_explosion_typed(EnemyKind.SCOUT, 100.0, 50.0)
    scout_count = len(fx.particles)
    fx.emit_explosion_typed(EnemyKind.HEAVY, 200.0, 50.0)
    heavy_count = len(fx.particles) - scout_count
    assert heavy_count > scout_count, (
        f"HEAVY explosion ({heavy_count} particles) should be bigger than "
        f"SCOUT ({scout_count} particles)"
    )


# --- Bullet impact tests ---

def test_emit_bullet_impact_creates_particles():
    fx = FxLayer(pool_size=128)
    fx.emit_bullet_impact(100.0, 50.0, weapon=0, damage=1)
    active = [p for p in fx.particles if p.active]
    assert len(active) > 0, "emit_bullet_impact should create particles"


def test_emit_bullet_impact_count_scales_with_damage():
    fx = FxLayer(pool_size=256)
    fx.emit_bullet_impact(100.0, 50.0, weapon=0, damage=1)
    low = len(fx.particles)
    fx.emit_bullet_impact(150.0, 50.0, weapon=0, damage=5)
    high = len(fx.particles) - low
    assert high > low, f"high damage ({high}) should produce more particles than low ({low})"


# --- Chain spawn glow tests ---

def test_emit_chain_spawn_glow_creates_particles():
    fx = FxLayer(pool_size=64)
    fx.emit_chain_spawn_glow(100.0, 50.0, chain_index=0, total_chain=3)
    active = [p for p in fx.particles if p.active]
    assert len(active) > 0, "chain glow should create particles"


def test_emit_chain_spawn_glow_fades_quickly():
    fx = FxLayer(pool_size=64)
    fx.emit_chain_spawn_glow(100.0, 50.0, chain_index=0, total_chain=3)
    initial = len(fx.particles)
    for _ in range(60):  # 1 second
        fx.update(1 / 60)
    final = len(fx.particles)
    assert final < initial, "chain glow should fade after ~1s"


# --- Player hit / death tests ---

def test_emit_player_hit_creates_particles():
    fx = FxLayer(pool_size=64)
    fx.emit_player_hit(240.0, 135.0)
    active = [p for p in fx.particles if p.active]
    assert len(active) > 0, "player hit should create particles"


def test_emit_player_death_creates_big_explosion():
    fx = FxLayer(pool_size=512)
    fx.emit_player_death(240.0, 135.0)
    active = [p for p in fx.particles if p.active]
    assert len(active) >= 20, f"player death explosion should have many particles, got {len(active)}"


# --- Enemy explosion-on-death tests ---

def test_all_enemy_kinds_call_explosion_on_death():
    """When an enemy of any kind dies, an explosion must be emitted."""
    from stellar_horizon.entities.enemy import Enemy
    for kind in ["scout", "cruiser", "heavy", "bomber", "ufo", "kamikaze"]:
        fx = FxLayer(pool_size=256)
        e = Enemy()
        e.kind = kind
        e.on_spawn()
        e.hp = 1
        e.fx = fx
        e.take_damage(1)
        alive = [p for p in fx.particles if p.active]
        assert len(alive) > 0, f"{kind} death should emit explosion particles"


# --- Engine flame tests ---

def test_engine_flame_constructs_with_color():
    from stellar_horizon.fx.engine_flames import EngineFlame
    flame = EngineFlame(base_color=(255, 100, 100))
    assert flame is not None
    assert flame.base_color == (255, 100, 100)


def test_engine_flame_update_advances_frame():
    from stellar_horizon.fx.engine_flames import EngineFlame
    flame = EngineFlame(base_color=(255, 100, 100))
    initial_frame = flame._frame
    # Update enough to advance one frame (1/12 s = 0.0833s)
    flame.update(0.1)
    assert flame._frame != initial_frame, (
        f"frame should advance after update (was {initial_frame}, now {flame._frame})"
    )


def test_engine_flame_renders_without_error():
    import pygame
    pygame.init()
    try:
        from stellar_horizon.fx.engine_flames import EngineFlame
        flame = EngineFlame(base_color=(255, 100, 100))
        surf = pygame.Surface((20, 20))
        flame.render(surf, 10.0, 10.0, size_scale=1.0)
    finally:
        pygame.quit()


def test_engine_flame_size_scales_with_size_scale():
    """A larger size_scale should produce more visible pixels."""
    import pygame
    pygame.init()
    try:
        from stellar_horizon.fx.engine_flames import EngineFlame
        flame = EngineFlame(base_color=(255, 100, 100))
        small = pygame.Surface((20, 20), pygame.SRCALPHA)
        large = pygame.Surface((60, 60), pygame.SRCALPHA)
        flame.render(small, 10.0, 10.0, size_scale=0.5)
        flame.render(large, 30.0, 30.0, size_scale=2.0)
        small_pixels = sum(1 for x in range(small.get_width())
                           for y in range(small.get_height())
                           if small.get_at((x, y))[3] > 0)
        large_pixels = sum(1 for x in range(large.get_width())
                           for y in range(large.get_height())
                           if large.get_at((x, y))[3] > 0)
        assert large_pixels > small_pixels, (
            f"larger scale should produce more pixels: small={small_pixels}, large={large_pixels}"
        )
    finally:
        pygame.quit()


# --- Enemy engine flame + trail tests ---

def test_enemy_has_engine_flame_after_on_spawn():
    from stellar_horizon.entities.enemy import Enemy
    e = Enemy()
    e.kind = "scout"
    e.on_spawn()
    assert e.flame is not None, "Enemy should have an EngineFlame after on_spawn"


def test_enemy_engine_flame_color_matches_kind():
    from stellar_horizon.entities.enemy import Enemy, EnemyKind
    e = Enemy()
    e.kind = EnemyKind.SCOUT
    e.on_spawn()
    # Scout's flame is light blue
    assert e.flame.base_color[2] >= 200, (
        f"SCOUT flame should have high blue, got {e.flame.base_color}"
    )


def test_enemy_emits_trail_particles_when_moving():
    """A moving enemy should emit trail particles via update()."""
    from stellar_horizon.entities.enemy import Enemy
    from src.movement import BezierPath, HybridPath, PathFollower, Point

    fx = FxLayer(pool_size=64)
    e = Enemy()
    e.kind = "scout"
    e.on_spawn()
    e.fx = fx
    # Wrap a BezierPath in HybridPath (the same way wave_manager does)
    bp = BezierPath(
        p0=Point(490, 135), p1=Point(360, 135),
        p2=Point(120, 135), p3=Point(-20, 135),
    )
    path = HybridPath([bp], [max(0.5, bp.length_estimate / 80.0)])
    e.attach_path(PathFollower(path), slot_dx=0.0, slot_dy=0.0)
    # Run several ticks
    for _ in range(30):
        e.update(1 / 60, player=None)
    active = [p for p in fx.particles if p.active]
    assert len(active) > 0, f"moving enemy should emit trail particles, got {len(active)}"


# --- Player engine flame + trail tests ---

def test_player_has_engine_flame():
    from stellar_horizon.entities.player import Player
    import pygame
    pygame.init()
    try:
        screen_rect = pygame.Rect(0, 0, 480, 270)
        p = Player(screen_rect)
        assert p.flame is not None, "Player should have an EngineFlame"
    finally:
        pygame.quit()


def test_player_emits_trail_particles_when_thrusting():
    from stellar_horizon.entities.player import Player
    import pygame
    pygame.init()
    try:
        screen_rect = pygame.Rect(0, 0, 480, 270)
        p = Player(screen_rect)
        fx = FxLayer(pool_size=64)
        p.fx = fx
        # Press RIGHT to make the player actually thrust
        keys = {pygame.K_d: True}
        for _ in range(30):
            p.update(1 / 60, keys, [])
        active = [pp for pp in fx.particles if pp.active]
        assert len(active) > 0, f"player should emit trail when thrusting, got {len(active)}"
    finally:
        pygame.quit()


# --- FTL chain spawn glow tests ---

def test_wave_manager_emits_chain_spawn_glow_per_link():
    """Each link of an FTL chain should emit a glow particle burst."""
    import json
    import tempfile
    from pathlib import Path
    from stellar_horizon.waves.wave_manager import WaveManager
    json_content = """{
        "act": 1, "act_name": "Test", "background": "act1_asteroid_belt",
        "midi_track": "act1.mid", "boss": null,
        "waves": [{
            "id": "w1", "duration_s": 20.0,
            "spawns": [{
                "delay_s": 5.0,
                "formation": "train_chain", "formation_count": 1,
                "enemy_kind": "bomber", "path": "s_right_to_left",
                "chain_count": 3, "chain_delay_s": 0.4
            }]
        }]
    }"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json_content)
        f.flush()
        wm = WaveManager(Path(f.name))
        wm.fx = FxLayer(pool_size=128)
        wm.begin()
        # The chain has 3 links; begin() should have emitted 3 chain glows.
        active = [p for p in wm.fx.particles if p.active]
        assert len(active) > 0, f"chain should emit glow particles per link, got {len(active)}"
