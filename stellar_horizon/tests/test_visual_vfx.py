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
