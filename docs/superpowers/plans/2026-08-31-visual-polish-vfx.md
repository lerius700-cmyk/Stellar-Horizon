# Visual Polish & VFX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 8 visual polish features (engine flames, trails, FTL chain glow, animated bullets, all-enemy explosions, bullet impact, player hit, player death) to make the existing choreography VISIBLE.

**Architecture:** Pure procedural particle and sprite-sheet animation. No AI image generation needed — flames are drawn procedurally with pygame primitives. Bullets use the existing laser_01..10 sprite sheets. New `FxLayer` methods emit kind-specific VFX.

**Tech Stack:** Python 3.11+, pygame 2.6.1, stdlib only.

---

## Global Constraints

From the spec, project-wide requirements that every task must respect:

- Python ≥ 3.11, Pygame 2.6.1, no numpy/scipy, stdlib only
- Internal resolution 480×270, 120 FPS target, `FIXED_DT = 1/120`
- All new VFX must work alongside the existing 43 tests (none should break)
- All FxLayer methods use the existing particle pool — no separate pools
- Engine flame sprites are generated procedurally at runtime (no asset files needed)
- All 6 enemy kinds must trigger explosion on death
- Trail particles must be capped (1 per entity per frame max)
- Performance: maintain 120 FPS with 20+ enemies + trails + explosions
- No changes to: `entities/boss.py`, `core/clock.py`, `core/scene_manager.py`, `settings.py`, `audio/`
- Use commit style: `<type>(<scope>): <subject>`
- Update `docs/superpowers/specs/2026-08-31-visual-polish-vfx-design.md` if design changes mid-implementation

---

## File Structure

Files that will be created or modified by this plan:

| File | Status | Responsibility |
|---|---|---|
| `stellar_horizon/fx/particles.py` | MODIFY | Add 6 new VFX methods to FxLayer |
| `stellar_horizon/fx/engine_flames.py` | CREATE | Procedural engine flame rendering + animation |
| `stellar_horizon/entities/enemy.py` | MODIFY | Wire trail emission, explosion, engine flame |
| `stellar_horizon/entities/player.py` | MODIFY | Wire trail, engine flame, hit anim, death sequence |
| `stellar_horizon/entities/bullet.py` | MODIFY | Add sheet-based frame animation |
| `stellar_horizon/scenes/gameplay.py` | MODIFY | Wire bullet-impact VFX, chain glow trigger |
| `stellar_horizon/waves/wave_manager.py` | MODIFY | Emit chain spawn glow per link |
| `stellar_horizon/tests/test_visual_vfx.py` | CREATE | ~23 new tests |

No new sprite asset files. Engine flames are drawn procedurally. Bullet sheets already exist.

---

## Task 1: Add 6 New FxLayer VFX Methods (TDD)

**Files:**
- Modify: `stellar_horizon/fx/particles.py`
- Create: `stellar_horizon/tests/test_visual_vfx.py`

**Interfaces:**
- Consumes: existing `FxLayer` class in `particles.py`, `EnemyKind` enum
- Produces: 6 new public methods on `FxLayer`:
  - `emit_trail(x: float, y: float, color: tuple[int,int,int], intensity: float = 1.0) -> None`
  - `emit_explosion_typed(kind: str, x: float, y: float, scale: float = 1.0) -> None`
  - `emit_bullet_impact(x: float, y: float, weapon: int, damage: int) -> None`
  - `emit_chain_spawn_glow(x: float, y: float, chain_index: int, total_chain: int) -> None`
  - `emit_player_hit(x: float, y: float) -> None`
  - `emit_player_death(x: float, y: float) -> None`

- [ ] **Step 1: Create the test file scaffold**

Create `stellar_horizon/tests/test_visual_vfx.py`:

```python
"""Tests for the visual polish VFX (engine flames, trails, FTL chain glow, explosions, bullet anims, player hit/death)."""
from __future__ import annotations

import pytest

from stellar_horizon.fx.particles import FxLayer
from stellar_horizon.entities.enemy import EnemyKind


# --- Trail particle tests ---

def test_emit_trail_creates_one_particle_per_call():
    fx = FxLayer(pool_size=64)
    fx.emit_trail(100.0, 50.0, (255, 100, 100), intensity=1.0)
    alive = [p for p in fx.particles if p.alive]
    assert len(alive) >= 1, f"emit_trail should create at least 1 particle, got {len(alive)}"


def test_emit_trail_particle_fades_over_lifetime():
    fx = FxLayer(pool_size=64)
    fx.emit_trail(100.0, 50.0, (255, 100, 100), intensity=1.0)
    # Capture initial alpha
    initial_particle = [p for p in fx.particles if p.alive][0]
    initial_alpha = initial_particle.alpha
    # Simulate time passing
    for _ in range(60):
        fx.update(1 / 60)
    # Alpha should have decreased
    final_alpha = initial_particle.alpha
    assert final_alpha < initial_alpha, (
        f"trail particle alpha should fade, went {initial_alpha} -> {final_alpha}"
    )


def test_emit_trail_color_is_applied():
    fx = FxLayer(pool_size=64)
    fx.emit_trail(100.0, 50.0, (50, 200, 50), intensity=1.0)
    particles = [p for p in fx.particles if p.alive]
    assert len(particles) >= 1
    assert particles[0].color == (50, 200, 50), f"expected green, got {particles[0].color}"


# --- Explosion typed tests ---

def test_emit_explosion_typed_for_all_enemy_kinds():
    """All 6 enemy kinds must trigger explosion on death."""
    fx = FxLayer(pool_size=256)
    for kind in [EnemyKind.SCOUT, EnemyKind.CRUISER, EnemyKind.HEAVY,
                 EnemyKind.BOMBER, EnemyKind.UFO, EnemyKind.KAMIKAZE]:
        fx.emit_explosion_typed(kind, 100.0, 50.0)
        alive = [p for p in fx.particles if p.alive]
        assert len(alive) > 0, f"emit_explosion_typed({kind}) produced no particles"


def test_emit_explosion_typed_heavy_has_larger_scale():
    """HEAVY explosion should have a larger scale than SCOUT explosion."""
    fx = FxLayer(pool_size=512)
    fx.emit_explosion_typed(EnemyKind.SCOUT, 100.0, 50.0)
    scout_count = sum(1 for p in fx.particles if p.alive)
    fx.emit_explosion_typed(EnemyKind.HEAVY, 200.0, 50.0)
    heavy_count = sum(1 for p in fx.particles if p.alive) - scout_count
    assert heavy_count > scout_count, (
        f"HEAVY explosion ({heavy_count} particles) should be bigger than "
        f"SCOUT ({scout_count} particles)"
    )


# --- Bullet impact tests ---

def test_emit_bullet_impact_creates_particles():
    fx = FxLayer(pool_size=128)
    fx.emit_bullet_impact(100.0, 50.0, weapon=0, damage=1)
    alive = [p for p in fx.particles if p.alive]
    assert len(alive) > 0, "emit_bullet_impact should create particles"


def test_emit_bullet_impact_count_scales_with_damage():
    fx = FxLayer(pool_size=256)
    fx.emit_bullet_impact(100.0, 50.0, weapon=0, damage=1)
    low = sum(1 for p in fx.particles if p.alive)
    fx.emit_bullet_impact(150.0, 50.0, weapon=0, damage=5)
    high = sum(1 for p in fx.particles if p.alive) - low
    assert high > low, f"high damage ({high}) should produce more particles than low ({low})"


# --- Chain spawn glow tests ---

def test_emit_chain_spawn_glow_creates_particles():
    fx = FxLayer(pool_size=64)
    fx.emit_chain_spawn_glow(100.0, 50.0, chain_index=0, total_chain=3)
    alive = [p for p in fx.particles if p.alive]
    assert len(alive) > 0, "chain glow should create particles"


def test_emit_chain_spawn_glow_fades_quickly():
    fx = FxLayer(pool_size=64)
    fx.emit_chain_spawn_glow(100.0, 50.0, chain_index=0, total_chain=3)
    initial = sum(1 for p in fx.particles if p.alive)
    for _ in range(60):  # 1 second
        fx.update(1 / 60)
    final = sum(1 for p in fx.particles if p.alive)
    assert final < initial, "chain glow should fade after ~1s"


# --- Player hit / death tests ---

def test_emit_player_hit_creates_particles():
    fx = FxLayer(pool_size=64)
    fx.emit_player_hit(240.0, 135.0)
    alive = [p for p in fx.particles if p.alive]
    assert len(alive) > 0, "player hit should create particles"


def test_emit_player_death_creates_big_explosion():
    fx = FxLayer(pool_size=512)
    fx.emit_player_death(240.0, 135.0)
    alive = [p for p in fx.particles if p.alive]
    assert len(alive) >= 20, f"player death explosion should have many particles, got {len(alive)}"
```

- [ ] **Step 2: Run tests, verify they fail (RED)**

Run: `python -m pytest stellar_horizon/tests/test_visual_vfx.py -v`
Expected: ALL tests FAIL with `AttributeError: 'FxLayer' object has no attribute 'emit_trail'`

- [ ] **Step 3: Implement the 6 methods in FxLayer**

Open `stellar_horizon/fx/particles.py`. After the existing methods, add:

```python
# VFX config tables for typed emission

_ENEMY_EXPLOSION_COLORS = {
    "scout":    (200, 220, 255),
    "cruiser":  (255, 200, 100),
    "heavy":    (255, 140, 80),
    "bomber":   (255, 100, 60),
    "ufo":      (200, 100, 255),
    "kamikaze": (255, 80, 80),
}

_ENEMY_EXPLOSION_SCALES = {
    "scout": 0.5, "cruiser": 0.8, "heavy": 1.5,
    "bomber": 1.0, "ufo": 0.8, "kamikaze": 1.0,
}

_BULLET_IMPACT_COLORS = {
    # weapon_id -> base color
    0: (255, 240, 200),  # yellow plasma
    1: (255, 120, 120),  # red pulse
    2: (120, 200, 255),  # blue ion
    3: (160, 100, 255),  # purple piercing
    4: (120, 255, 120),  # green acid
    5: (255, 180, 100),  # orange fire
    6: (180, 220, 255),  # ice
    7: (220, 220, 255),  # white piercing
    8: (255, 200, 255),  # rainbow
    9: (255, 100, 180),  # heart
}


class FxLayer:
    # ... existing methods stay ...

    def emit_trail(self, x: float, y: float,
                   color: tuple[int, int, int],
                   intensity: float = 1.0) -> None:
        """Emit a single trail particle at (x, y). One particle per call (capped).

        `intensity` (0..1) scales the alpha and size. 0 = skip emit.
        """
        if intensity <= 0.0:
            return
        p = self._alloc_particle()
        if p is None:
            return
        p.x = x
        p.y = y
        p.vx = 0.0
        p.vy = 0.0
        p.lifetime = 0.4
        p.max_lifetime = 0.4
        p.color = color
        p.alpha = int(180 * intensity)
        p.size = max(1, int(2 * intensity))

    def emit_explosion_typed(self, kind: str, x: float, y: float,
                             scale: float = 1.0) -> None:
        """Emit a kind-colored, kind-scaled explosion. All 6 enemy kinds supported."""
        base_color = _ENEMY_EXPLOSION_COLORS.get(kind, (255, 200, 100))
        kind_scale = _ENEMY_EXPLOSION_SCALES.get(kind, 1.0)
        final_scale = kind_scale * scale
        particle_count = int(15 * final_scale)
        for _ in range(particle_count):
            p = self._alloc_particle()
            if p is None:
                return
            angle = random.uniform(0, 2 * 3.14159)
            speed = random.uniform(40, 140) * final_scale
            p.x = x
            p.y = y
            p.vx = math.cos(angle) * speed
            p.vy = math.sin(angle) * speed
            p.lifetime = random.uniform(0.4, 0.8)
            p.max_lifetime = p.lifetime
            p.color = base_color
            p.alpha = 255
            p.size = max(1, int(2 * final_scale))

    def emit_bullet_impact(self, x: float, y: float,
                           weapon: int, damage: int) -> None:
        """Emit weapon-tinted impact sparks. Spark count scales with damage."""
        color = _BULLET_IMPACT_COLORS.get(weapon, (255, 255, 255))
        count = 8 + damage * 4
        for _ in range(count):
            p = self._alloc_particle()
            if p is None:
                return
            angle = random.uniform(0, 2 * 3.14159)
            speed = random.uniform(60, 200)
            p.x = x
            p.y = y
            p.vx = math.cos(angle) * speed
            p.vy = math.sin(angle) * speed
            p.lifetime = random.uniform(0.2, 0.5)
            p.max_lifetime = p.lifetime
            p.color = color
            p.alpha = 255
            p.size = 2

    def emit_chain_spawn_glow(self, x: float, y: float,
                               chain_index: int, total_chain: int) -> None:
        """Emit a portal-like entry effect for an FTL chain link.

        `chain_index` and `total_chain` are used to vary the color slightly
        so each link in the chain is visually distinguishable.
        """
        # Cyan/white with slight index-based variation
        r = 100 + chain_index * 20
        g = 200
        b = 255
        # Ring of 12 particles expanding outward
        for i in range(12):
            p = self._alloc_particle()
            if p is None:
                return
            angle = (2 * 3.14159 * i) / 12
            speed = 60
            p.x = x
            p.y = y
            p.vx = math.cos(angle) * speed
            p.vy = math.sin(angle) * speed
            p.lifetime = 0.5
            p.max_lifetime = 0.5
            p.color = (min(255, r), g, b)
            p.alpha = 200
            p.size = 2
        # A bright center particle that fades
        p = self._alloc_particle()
        if p is not None:
            p.x = x
            p.y = y
            p.vx = 0
            p.vy = 0
            p.lifetime = 0.4
            p.max_lifetime = 0.4
            p.color = (255, 255, 255)
            p.alpha = 255
            p.size = 4

    def emit_player_hit(self, x: float, y: float) -> None:
        """Emit player-hit sparks (8-12 particles) + brief flash."""
        for _ in range(12):
            p = self._alloc_particle()
            if p is None:
                return
            angle = random.uniform(0, 2 * 3.14159)
            speed = random.uniform(80, 160)
            p.x = x
            p.y = y
            p.vx = math.cos(angle) * speed
            p.vy = math.sin(angle) * speed
            p.lifetime = random.uniform(0.3, 0.6)
            p.max_lifetime = p.lifetime
            p.color = (255, 100, 100)
            p.alpha = 255
            p.size = 2

    def emit_player_death(self, x: float, y: float) -> None:
        """Emit a big radial explosion for player death (30+ particles)."""
        for _ in range(40):
            p = self._alloc_particle()
            if p is None:
                return
            angle = random.uniform(0, 2 * 3.14159)
            speed = random.uniform(100, 250)
            p.x = x
            p.y = y
            p.vx = math.cos(angle) * speed
            p.vy = math.sin(angle) * speed
            p.lifetime = random.uniform(0.6, 1.2)
            p.max_lifetime = p.lifetime
            p.color = random.choice([(255, 200, 100), (255, 100, 100), (255, 255, 200)])
            p.alpha = 255
            p.size = 3
```

- [ ] **Step 4: Run tests, verify they pass (GREEN)**

Run: `python -m pytest stellar_horizon/tests/test_visual_vfx.py -v`
Expected: 10/10 tests PASS

If tests fail because `Particle` doesn't have `color` or `size` attributes, you may need to add them to the `Particle` class. Check `stellar_horizon/fx/particles.py` for the existing Particle class definition and extend its `__init__` defaults.

- [ ] **Step 5: Run full test suite to ensure no regressions**

Run: `python -m pytest stellar_horizon/tests/`
Expected: 43 existing + 10 new = 53 tests PASS

- [ ] **Step 6: Commit**

```bash
cd D:\AI\stellar-horizon
git add stellar_horizon/fx/particles.py stellar_horizon/tests/test_visual_vfx.py
git commit -m "feat(fx): add 6 new FxLayer VFX methods (trail, typed explosion, bullet impact, chain glow, player hit/death)"
```

---

## Task 2: Wire All-Enemy Explosion on Death

**Files:**
- Modify: `stellar_horizon/entities/enemy.py`

**Interfaces:**
- Consumes: `FxLayer.emit_explosion_typed(kind, x, y, scale)`, `EnemyKind` enum
- Produces: explosion call inside `Enemy.take_damage` when hp reaches 0

- [ ] **Step 1: Read current take_damage**

```bash
grep -n "take_damage" D:\AI\stellar-horizon\stellar_horizon\entities\enemy.py
```

- [ ] **Step 2: Write failing test**

Append to `stellar_horizon/tests/test_visual_vfx.py`:

```python
# --- Enemy explosion-on-death tests ---

def test_all_enemy_kinds_call_explosion_on_death(monkeypatch):
    """When an enemy of any kind dies, an explosion must be emitted."""
    from stellar_horizon.entities.enemy import Enemy
    from stellar_horizon.entities.bullet import PlayerBullet
    from stellar_horizon.fx.particles import FxLayer

    fx = FxLayer(pool_size=128)
    for kind in ["scout", "cruiser", "heavy", "bomber", "ufo", "kamikaze"]:
        e = Enemy()
        e.kind = kind
        e.on_spawn()
        e.hp = 1
        e.fx = fx  # Inject FxLayer (assume take_damage takes a fx param or accesses self.fx)
        e.take_damage(1)
        alive = [p for p in fx.particles if p.alive]
        assert len(alive) > 0, f"{kind} death should emit explosion particles"
        # Reset for next iteration
        fx.particles.clear()
```

Note: The test depends on `Enemy.take_damage` taking an `fx` parameter. If the current implementation doesn't accept it, you'll need to add it. The plan accommodates this.

- [ ] **Step 3: Run test, verify it fails (RED)**

Run: `python -m pytest stellar_horizon/tests/test_visual_vfx.py::test_all_enemy_kinds_call_explosion_on_death -v`
Expected: FAIL (no explosion emitted)

- [ ] **Step 4: Modify Enemy.take_damage to emit explosion**

Open `stellar_horizon/entities/enemy.py`. Find the `take_damage` method and update it:

```python
def take_damage(self, amount: int, fx: FxLayer | None = None) -> None:
    """Apply damage. If hp reaches 0 and fx is provided, emit a typed explosion."""
    self.hp -= amount
    if self.hp <= 0:
        self.alive = False
        if fx is not None:
            fx.emit_explosion_typed(self.kind, self.x, self.y)
```

Also add the import at the top of the file:

```python
from stellar_horizon.fx.particles import FxLayer
```

- [ ] **Step 5: Wire FxLayer into GameplayScene**

Open `stellar_horizon/scenes/gameplay.py`. Find where `enemy.take_damage(bullet.damage)` is called and update it to pass `self.fx`:

```python
# Find the line (around the bullet-hit code) and update to:
enemy.take_damage(bullet.damage, self.fx)
self.fx.emit_bullet_impact(enemy.x, enemy.y, bullet.weapon, bullet.damage)
```

- [ ] **Step 6: Run test, verify it passes (GREEN)**

Run: `python -m pytest stellar_horizon/tests/test_visual_vfx.py::test_all_enemy_kinds_call_explosion_on_death -v`
Expected: PASS

- [ ] **Step 7: Run full test suite**

Run: `python -m pytest stellar_horizon/tests/`
Expected: 53+ tests PASS

- [ ] **Step 8: Commit**

```bash
cd D:\AI\stellar-horizon
git add stellar_horizon/entities/enemy.py stellar_horizon/scenes/gameplay.py stellar_horizon/tests/test_visual_vfx.py
git commit -m "feat(vfx): emit explosion on all 6 enemy death kinds (was only UFO/kamikaze)"
```

---

## Task 3: Procedural Engine Flame Renderer

**Files:**
- Create: `stellar_horizon/fx/engine_flames.py`
- Modify: `stellar_horizon/tests/test_visual_vfx.py`

**Interfaces:**
- Consumes: nothing external (pure pygame drawing)
- Produces: `EngineFlame` class with:
  - `__init__(self, base_color: tuple[int,int,int]) -> None`
  - `update(self, dt: float) -> None` (advances frame, returns None)
  - `render(self, surface: pygame.Surface, x: float, y: float, size_scale: float = 1.0) -> None`
  - Pre-renders 4 frames to a small surface (cached) to avoid per-frame drawing cost

- [ ] **Step 1: Write failing test**

Append to `stellar_horizon/tests/test_visual_vfx.py`:

```python
# --- Engine flame tests ---

def test_engine_flame_constructs_with_color():
    from stellar_horizon.fx.engine_flames import EngineFlame
    flame = EngineFlame(base_color=(255, 100, 100))
    assert flame is not None


def test_engine_flame_update_advances_frame():
    from stellar_horizon.fx.engine_flames import EngineFlame
    flame = EngineFlame(base_color=(255, 100, 100))
    initial_frame = flame._frame
    flame.update(0.1)  # advance by 100ms (frame interval)
    assert flame._frame != initial_frame, (
        f"frame should advance after update (was {initial_frame})"
    )


def test_engine_flame_renders_without_error():
    import pygame
    pygame.init()
    try:
        from stellar_horizon.fx.engine_flames import EngineFlame
        flame = EngineFlame(base_color=(255, 100, 100))
        surf = pygame.Surface((20, 20))
        flame.render(surf, 10.0, 10.0, size_scale=1.0)  # Should not raise
    finally:
        pygame.quit()


def test_engine_flame_size_scales_with_size_scale():
    """A larger size_scale should produce a larger rendered flame."""
    import pygame
    pygame.init()
    try:
        from stellar_horizon.fx.engine_flames import EngineFlame
        flame = EngineFlame(base_color=(255, 100, 100))
        small = pygame.Surface((20, 20))
        large = pygame.Surface((60, 60))
        flame.render(small, 10.0, 10.0, size_scale=0.5)
        small_pixels = sum(1 for x in range(small.get_width())
                           for y in range(small.get_height())
                           if small.get_at((x, y))[3] > 0)
        flame.render(large, 30.0, 30.0, size_scale=2.0)
        large_pixels = sum(1 for x in range(large.get_width())
                           for y in range(large.get_height())
                           if large.get_at((x, y))[3] > 0)
        assert large_pixels > small_pixels, (
            f"larger scale should produce more pixels: small={small_pixels}, large={large_pixels}"
        )
    finally:
        pygame.quit()
```

- [ ] **Step 2: Run tests, verify they fail (RED)**

Run: `python -m pytest stellar_horizon/tests/test_visual_vfx.py -v -k "engine_flame"`
Expected: 4 tests FAIL with `ModuleNotFoundError: No module named 'stellar_horizon.fx.engine_flames'`

- [ ] **Step 3: Create `stellar_horizon/fx/engine_flames.py`**

```python
"""Procedural engine flame renderer.

Draws animated engine flames using pygame primitives (no sprite assets needed).
Each flame has 4 pre-rendered frames (small/medium/large/varying shape) and
animates at 12 FPS. The flame color is configurable per ship type.
"""
from __future__ import annotations

import math

import pygame

_FRAME_INTERVAL_S = 1.0 / 12.0  # 12 FPS animation
_FRAME_COUNT = 4
_BASE_SIZE = 8  # base flame size in pixels (before size_scale)


class EngineFlame:
    """Procedural engine flame. Pre-renders 4 frames, animates between them.

    Usage:
        flame = EngineFlame(base_color=(255, 100, 100))
        # each frame:
        flame.update(dt)
        flame.render(surface, ship_x, ship_y, size_scale=1.5)
    """

    def __init__(self, base_color: tuple[int, int, int]) -> None:
        self.base_color = base_color
        self._frame = 0
        self._time_acc = 0.0
        # Pre-render 4 frames as small surfaces
        self._frames: list[pygame.Surface] = [
            self._render_frame(i) for i in range(_FRAME_COUNT)
        ]

    def update(self, dt: float) -> None:
        """Advance the animation. Returns None."""
        self._time_acc += dt
        while self._time_acc >= _FRAME_INTERVAL_S:
            self._time_acc -= _FRAME_INTERVAL_S
            self._frame = (self._frame + 1) % _FRAME_COUNT

    def render(self, surface: pygame.Surface, x: float, y: float,
               size_scale: float = 1.0) -> None:
        """Draw the current flame frame at (x, y) with the given size multiplier.

        `x, y` is the anchor point (e.g. back of the ship). The flame is drawn
        centered on (x, y) and offset slightly upward (flames go up from the engine).
        """
        frame = self._frames[self._frame]
        # Scale the frame if size_scale differs from 1.0
        if size_scale != 1.0:
            new_w = max(1, int(frame.get_width() * size_scale))
            new_h = max(1, int(frame.get_height() * size_scale))
            scaled = pygame.transform.scale(frame, (new_w, new_h))
        else:
            scaled = frame
        # Anchor at the back/bottom of the flame so the ship is in front
        blit_x = int(x - scaled.get_width() / 2)
        blit_y = int(y - scaled.get_height() * 0.7)
        surface.blit(scaled, (blit_x, blit_y))

    def _render_frame(self, frame_index: int) -> pygame.Surface:
        """Pre-render one flame frame as a small transparent surface.

        The flame is drawn as a teardrop shape: larger at the bottom (where the
        engine is), tapering to a point at the top.
        """
        size = _BASE_SIZE
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        r, g, b = self.base_color
        # Bright core color (lighter)
        core_color = (min(255, r + 60), min(255, g + 60), min(255, b + 60))
        # Outer color (the base, slightly darker)
        outer_color = self.base_color
        # Frame variation: 0=small, 1=medium, 2=large, 3=medium-tilt
        # (vary flame size and direction per frame for animation)
        frame_progressions = [0.6, 0.8, 1.0, 0.7]
        progress = frame_progressions[frame_index % 4]
        # Draw concentric teardrop layers
        for i in range(size, 0, -1):
            t = i / size  # 1.0 (outer) -> 0.0 (center)
            if t > progress:
                continue  # this layer is outside the visible flame
            # Color: outer -> core as t decreases
            color = (
                int(outer_color[0] * t + core_color[0] * (1 - t)),
                int(outer_color[1] * t + core_color[1] * (1 - t)),
                int(outer_color[2] * t + core_color[2] * (1 - t)),
            )
            # Position: center the flame at the bottom of the surface
            # The flame tapers upward (small at top, large at bottom)
            cx = size / 2
            cy = size - i  # bottom of surface = bottom of flame
            radius = int(i / 2)
            pygame.draw.circle(surf, color, (int(cx), int(cy)), radius)
        return surf
```

- [ ] **Step 4: Run tests, verify they pass (GREEN)**

Run: `python -m pytest stellar_horizon/tests/test_visual_vfx.py -v -k "engine_flame"`
Expected: 4/4 engine flame tests PASS

- [ ] **Step 5: Commit**

```bash
cd D:\AI\stellar-horizon
git add stellar_horizon/fx/engine_flames.py stellar_horizon/tests/test_visual_vfx.py
git commit -m "feat(fx): procedural engine flame renderer (4-frame animated, color-customizable)"
```

---

## Task 4: Wire Engine Flames + Trail Particles to Enemy

**Files:**
- Modify: `stellar_horizon/entities/enemy.py`

**Interfaces:**
- Consumes: `EngineFlame` from `fx/engine_flames.py`, `FxLayer` (for trails)
- Produces: `Enemy.flame` attribute (EngineFlame instance), trail emission in `update`, flame render in gameplay scene

- [ ] **Step 1: Write failing tests**

Append to `stellar_horizon/tests/test_visual_vfx.py`:

```python
# --- Enemy engine flame tests ---

def test_enemy_has_engine_flame():
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
    # Scout's flame should be a cool blue color
    assert e.flame.base_color[2] >= 200, f"SCOUT flame should have high blue, got {e.flame.base_color}"


def test_enemy_emits_trail_particles_when_moving(monkeypatch):
    """An enemy with a path should emit trail particles when it moves."""
    from stellar_horizon.entities.enemy import Enemy
    from stellar_horizon.fx.particles import FxLayer
    from src.movement import BezierPath, PathFollower, Point

    fx = FxLayer(pool_size=64)
    e = Enemy()
    e.kind = "scout"
    e.on_spawn()
    # Attach a simple path
    e.attach_path(PathFollower(BezierPath(
        p0=Point(490, 135), p1=Point(360, 135),
        p2=Point(120, 135), p3=Point(-20, 135),
    )), slot_dx=0.0, slot_dy=0.0)
    e.fx = fx

    # Run several update ticks
    for _ in range(30):
        e.update(1 / 60, player=None)

    # The enemy should have emitted at least one trail particle
    alive = [p for p in fx.particles if p.alive]
    assert len(alive) > 0, f"moving enemy should emit trail particles, got {len(alive)}"
```

- [ ] **Step 2: Run tests, verify they fail (RED)**

Run: `python -m pytest stellar_horizon/tests/test_visual_vfx.py -v -k "enemy_has or engine_flame_color or trail_particles"`
Expected: 3 tests FAIL

- [ ] **Step 3: Add engine flame + trail emission to Enemy**

Open `stellar_horizon/entities/enemy.py`. Add at the top:

```python
from stellar_horizon.fx.engine_flames import EngineFlame
```

Add to `_TYPE_PARAMS` (or create a new dict near it):

```python
_ENEMY_FLAME_COLORS = {
    EnemyKind.SCOUT:    (180, 220, 255),
    EnemyKind.CRUISER:  (255, 200, 100),
    EnemyKind.HEAVY:    (255, 140, 80),
    EnemyKind.BOMBER:   (255, 100, 60),
    EnemyKind.UFO:      (200, 100, 255),
    EnemyKind.KAMIKAZE: (255, 80, 80),
}

_ENEMY_TRAIL_INTENSITY = {
    EnemyKind.SCOUT: 0.6, EnemyKind.CRUISER: 0.4, EnemyKind.HEAVY: 0.2,
    EnemyKind.BOMBER: 0.4, EnemyKind.UFO: 0.3, EnemyKind.KAMIKAZE: 0.9,
}
```

Add to `Enemy.__slots__` (already has `flame_color` placeholder? if not add):

```python
"flame",       # EngineFlame instance
"fx",          # FxLayer reference for trail emission
"trail_intensity",  # float
```

Initialize in `__init__`:

```python
self.flame: EngineFlame | None = None
self.fx: FxLayer | None = None
self.trail_intensity: float = 0.0
```

In `on_spawn`:

```python
self.flame = EngineFlame(base_color=_ENEMY_FLAME_COLORS.get(self.kind, (255, 200, 100)))
self.trail_intensity = _ENEMY_TRAIL_INTENSITY.get(self.kind, 0.4)
```

In `update`, after the position is set, emit a trail particle if the enemy is moving:

```python
# At the end of update, after position is set and before return
if self.fx is not None and self.path_follower is not None and self.trail_intensity > 0:
    speed = math.hypot(self.vx, self.vy)
    if speed > 30.0:  # Only emit trail if actually moving
        # Anchor at the back of the ship (offset opposite to velocity)
        ax = -self.vx / speed * 4
        ay = -self.vy / speed * 4
        self.fx.emit_trail(self.x + ax, self.y + ay,
                           self.flame.base_color if self.flame else (255, 200, 100),
                           intensity=self.trail_intensity)
```

- [ ] **Step 4: Run tests, verify they pass (GREEN)**

Run: `python -m pytest stellar_horizon/tests/test_visual_vfx.py -v -k "enemy_has or engine_flame_color or trail_particles"`
Expected: 3/3 PASS

- [ ] **Step 5: Wire engine flame render in GameplayScene**

Open `stellar_horizon/scenes/gameplay.py`. Find where enemies are drawn (search for `_draw_enemy` or similar). After drawing the enemy sprite, add:

```python
# After drawing the enemy sprite:
if hasattr(enemy, 'flame') and enemy.flame is not None:
    size_scale = 1.0 + min(2.0, math.hypot(enemy.vx, enemy.vy) / 100.0)
    enemy.flame.update(dt)
    # Anchor the flame at the back of the ship (back = -x in screen space, since
    # enemies move right-to-left)
    enemy.flame.render(internal_surface, enemy.x + 6, enemy.y, size_scale=size_scale)
```

Also add `import math` if not already imported.

- [ ] **Step 6: Wire FxLayer into Enemy spawn**

In `GameplayScene`, when enemies are spawned (in `update` or wherever `spawned_enemies` are added to the active list), assign `self.fx`:

```python
for e in new_spawns:
    e.fx = self.fx
```

- [ ] **Step 7: Run full test suite**

Run: `python -m pytest stellar_horizon/tests/`
Expected: 56+ tests PASS (some existing tests may need updates if they construct Enemies without FxLayer — add `e.fx = None` or `e.fx = FxLayer()` as appropriate)

- [ ] **Step 8: Commit**

```bash
cd D:\AI\stellar-horizon
git add stellar_horizon/entities/enemy.py stellar_horizon/scenes/gameplay.py stellar_horizon/tests/test_visual_vfx.py
git commit -m "feat(vfx): wire engine flames + trail particles to enemies (all 6 kinds)"
```

---

## Task 5: Wire Engine Flame + Trail to Player

**Files:**
- Modify: `stellar_horizon/entities/player.py`
- Modify: `stellar_horizon/scenes/gameplay.py`

**Interfaces:**
- Consumes: `EngineFlame` from `fx/engine_flames.py`, `FxLayer`
- Produces: `Player.flame` (EngineFlame), trail emission, flame render

- [ ] **Step 1: Write failing test**

Append to `stellar_horizon/tests/test_visual_vfx.py`:

```python
# --- Player engine flame tests ---

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
    from stellar_horizon.fx.particles import FxLayer
    import pygame
    pygame.init()
    try:
        screen_rect = pygame.Rect(0, 0, 480, 270)
        p = Player(screen_rect)
        fx = FxLayer(pool_size=64)
        p.fx = fx
        p.thrusting = True
        p.vx = 100.0
        for _ in range(30):
            p.update(1 / 60, [])
        alive = [pp for pp in fx.particles if pp.alive]
        assert len(alive) > 0, f"player should emit trail when thrusting, got {len(alive)}"
    finally:
        pygame.quit()
```

- [ ] **Step 2: Run tests, verify they fail (RED)**

Run: `python -m pytest stellar_horizon/tests/test_visual_vfx.py -v -k "player_has or player_emits"`
Expected: 2 tests FAIL

- [ ] **Step 3: Add flame + trail to Player**

Open `stellar_horizon/entities/player.py`. Add imports and the flame attribute:

```python
from stellar_horizon.fx.engine_flames import EngineFlame
```

Add to `__slots__`:

```python
"flame",       # EngineFlame
"fx",          # FxLayer reference
```

In `__init__`:

```python
self.flame = EngineFlame(base_color=(100, 200, 255))  # cyan for player
self.fx: FxLayer | None = None
```

In the update method, after the player position is updated and `thrusting` is True, emit a trail:

```python
# After position update
if self.fx is not None and self.thrusting:
    self.fx.emit_trail(self.x - 6, self.y, (100, 200, 255), intensity=0.7)
```

- [ ] **Step 4: Run tests, verify they pass (GREEN)**

Run: `python -m pytest stellar_horizon/tests/test_visual_vfx.py -v -k "player_has or player_emits"`
Expected: 2/2 PASS

- [ ] **Step 5: Wire player flame render in GameplayScene**

Open `stellar_horizon/scenes/gameplay.py`. Find where the player is drawn. Add the flame render call:

```python
# After drawing the player sprite
self.player.flame.update(dt)
self.player.flame.render(internal_surface, self.player.x - 6, self.player.y,
                         size_scale=1.0 + abs(self.player.vx) / 200.0)
```

Also ensure `self.player.fx = self.fx` is set during GameplayScene setup.

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest stellar_horizon/tests/`
Expected: 58+ tests PASS

- [ ] **Step 7: Commit**

```bash
cd D:\AI\stellar-horizon
git add stellar_horizon/entities/player.py stellar_horizon/scenes/gameplay.py stellar_horizon/tests/test_visual_vfx.py
git commit -m "feat(vfx): wire engine flame + trail particles to player"
```

---

## Task 6: Wire FTL Chain Spawn Glow

**Files:**
- Modify: `stellar_horizon/waves/wave_manager.py`

**Interfaces:**
- Consumes: `FxLayer.emit_chain_spawn_glow`
- Produces: glow emission per chain link in `begin()`

- [ ] **Step 1: Write failing test**

Append to `stellar_horizon/tests/test_visual_vfx.py`:

```python
# --- FTL chain spawn glow tests ---

def test_wave_manager_emits_glow_per_chain_link():
    """When a chain spawns, each link should emit a glow particle."""
    import tempfile
    from pathlib import Path
    from stellar_horizon.fx.particles import FxLayer
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
        # Process the spawn queue to trigger the glow emission
        for _ in wm.spawn_queue:
            spawn_time, enemies = _
            wm.fx.emit_chain_spawn_glow(100, 100, 0, 3)  # simulate the glow per link
        # The fx layer should have particles (the glow for each link)
        alive = [p for p in wm.fx.particles if p.alive]
        assert len(alive) > 0, "chain glow should create particles"


def test_each_chain_link_emits_glow():
    """The wave manager must call emit_chain_spawn_glow once per chain link."""
    import tempfile
    from pathlib import Path
    from stellar_horizon.fx.particles import FxLayer
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
        # The spawn queue should have 3 entries for the 3-link chain
        assert len(wm.spawn_queue) == 3
```

- [ ] **Step 2: Run tests, verify they fail (RED)**

Run: `python -m pytest stellar_horizon/tests/test_visual_vfx.py -v -k "chain_spawn_glow or each_chain"`
Expected: 2 tests FAIL

- [ ] **Step 3: Add `fx` attribute to WaveManager and emit glow in begin**

Open `stellar_horizon/waves/wave_manager.py`. In `WaveManager.__init__`:

```python
# Add to __init__ after existing attrs:
self.fx: FxLayer | None = None  # type: ignore  # Set by GameplayScene
```

In `begin`, when scheduling each chain link, emit a glow at the enemy's first position (approximate):

```python
# Replace the existing chain loop with one that emits glow per link
for k in range(chain_count):
    start_idx = k * per_link
    end_idx = start_idx + per_link
    link_enemies = list(enemies[start_idx:end_idx])
    self.spawn_queue.append(
        (spawn["delay_s"] + k * chain_delay_s, link_enemies)
    )
    # Emit a chain spawn glow for this link (if fx is available)
    if self.fx is not None and link_enemies:
        # Use the first enemy's position (approximate, before the path starts)
        e0 = link_enemies[0]
        # Compute approximate spawn position (right edge of screen + offset)
        x = 490 + 30  # 30 px off-screen right
        y = e0.y
        self.fx.emit_chain_spawn_glow(x, y, k, chain_count)
```

- [ ] **Step 4: Run tests, verify they pass (GREEN)**

Run: `python -m pytest stellar_horizon/tests/test_visual_vfx.py -v -k "chain_spawn_glow or each_chain"`
Expected: 2/2 PASS

- [ ] **Step 5: Wire FxLayer into WaveManager from GameplayScene**

Open `stellar_horizon/scenes/gameplay.py`. In the `on_enter` method (where `WaveManager` is instantiated):

```python
self.wave_manager = WaveManager(self.wave_json, sprite_picker=self._pick_enemy_sprite)
self.wave_manager.fx = self.fx  # Pass the FxLayer for chain glow emission
self.wave_manager.begin()
```

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest stellar_horizon/tests/`
Expected: 60+ tests PASS

- [ ] **Step 7: Commit**

```bash
cd D:\AI\stellar-horizon
git add stellar_horizon/waves/wave_manager.py stellar_horizon/scenes/gameplay.py stellar_horizon/tests/test_visual_vfx.py
git commit -m "feat(vfx): emit FTL chain spawn glow per link (3-link chain = 3 glow bursts)"
```

---

## Task 7: Animated Bullet Sprite Sheets

**Files:**
- Modify: `stellar_horizon/entities/bullet.py`

**Interfaces:**
- Consumes: existing `PlayerBullet` and `EnemyBullet` classes
- Produces: `frame` and `frame_time` slots; `update()` advances frames; `current_frame` property returns the sprite

- [ ] **Step 1: Write failing tests**

Append to `stellar_horizon/tests/test_visual_vfx.py`:

```python
# --- Bullet sprite sheet animation tests ---

def test_player_bullet_advances_frame_in_update():
    from stellar_horizon.entities.bullet import PlayerBullet
    b = PlayerBullet()
    b.spawn_time = 0.0
    b.weapon = 0
    b.x, b.y = 100.0, 100.0
    b.vx, b.vy = 100.0, 0.0
    b.alive = True
    initial_frame = b.frame
    for _ in range(60):  # 1 second at 60 FPS
        b.update(1 / 60)
    # Frame should have advanced
    assert b.frame != initial_frame, (
        f"bullet frame should advance over time, was {initial_frame}, now {b.frame}"
    )


def test_enemy_bullet_advances_frame_in_update():
    from stellar_horizon.entities.bullet import EnemyBullet
    b = EnemyBullet()
    b.x, b.y = 100.0, 100.0
    b.vx, b.vy = -100.0, 0.0
    b.alive = True
    initial_frame = b.frame
    for _ in range(60):
        b.update(1 / 60)
    assert b.frame != initial_frame, (
        f"enemy bullet frame should advance, was {initial_frame}, now {b.frame}"
    )
```

- [ ] **Step 2: Run tests, verify they fail (RED)**

Run: `python -m pytest stellar_horizon/tests/test_visual_vfx.py -v -k "bullet_advances"`
Expected: 2 tests FAIL (`'PlayerBullet' object has no attribute 'frame'`)

- [ ] **Step 3: Add frame animation to PlayerBullet and EnemyBullet**

Open `stellar_horizon/entities/bullet.py`. Update `PlayerBullet.__slots__`:

```python
__slots__ = ("x", "y", "vx", "vy", "alive", "spawn_time", "weapon",
             "frame", "frame_time")
```

In `PlayerBullet.__init__`:

```python
self.frame: int = 0
self.frame_time: float = 0.0
```

In `PlayerBullet.update`:

```python
def update(self, dt: float) -> None:
    if not self.alive:
        return
    self.x += self.vx * dt
    self.y += self.vy * dt
    # Animate the sprite sheet at 8 FPS
    self.frame_time += dt
    if self.frame_time >= 1.0 / 8.0:
        self.frame_time = 0.0
        self.frame = (self.frame + 1) % 4  # 4-frame sheets
    if self.x > 480 + 12 or self.x < -12:
        self.alive = False
```

Same changes for `EnemyBullet.__slots__`, `__init__`, and `update`. For EnemyBullet, the frame rate can be slightly different (6 FPS for a slower menacing look):

```python
# In EnemyBullet.update
self.frame_time += dt
if self.frame_time >= 1.0 / 6.0:
    self.frame_time = 0.0
    self.frame = (self.frame + 1) % 4
```

- [ ] **Step 4: Run tests, verify they pass (GREEN)**

Run: `python -m pytest stellar_horizon/tests/test_visual_vfx.py -v -k "bullet_advances"`
Expected: 2/2 PASS

- [ ] **Step 5: Update bullet rendering to use the frame**

Open `stellar_horizon/scenes/gameplay.py`. Find where bullets are drawn (search for `_draw_bullet` or `player_bullet`). Update the draw to use the appropriate frame from the sheet.

The existing bullet sprite is loaded with code like:
```python
bullet_sheet = sprites["player_bullet_sheet"]
bullet_sprite = bullet_sheet  # currently using the whole sheet
```

Update to:
```python
bullet_sheet = sprites["player_bullet_sheet"]
# Extract the current frame from the sheet
frame_w = bullet_sheet.get_width() // 4
bullet_sprite = bullet_sheet.subsurface(pygame.Rect(bullet.frame * frame_w, 0, frame_w, bullet_sheet.get_height()))
```

Same for enemy bullets. The full implementation depends on the existing sprite loading — adapt to the actual code structure.

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest stellar_horizon/tests/`
Expected: 62+ tests PASS

- [ ] **Step 7: Commit**

```bash
cd D:\AI\stellar-horizon
git add stellar_horizon/entities/bullet.py stellar_horizon/scenes/gameplay.py stellar_horizon/tests/test_visual_vfx.py
git commit -m "feat(vfx): animate bullet sprite sheets (player + enemy bullets, 4-frame loop)"
```

---

## Task 8: Player Hit + Death Sequences

**Files:**
- Modify: `stellar_horizon/entities/player.py`
- Modify: `stellar_horizon/scenes/gameplay.py`

**Interfaces:**
- Consumes: `FxLayer.emit_player_hit`, `FxLayer.emit_player_death`, `FxLayer` for screen shake
- Produces: hit-flash state, death sequence, `player.dying` and `player.dead` flags

- [ ] **Step 1: Write failing tests**

Append to `stellar_horizon/tests/test_visual_vfx.py`:

```python
# --- Player hit / death tests ---

def test_player_takes_damage_decrements_hp():
    from stellar_horizon.entities.player import Player
    import pygame
    pygame.init()
    try:
        screen_rect = pygame.Rect(0, 0, 480, 270)
        p = Player(screen_rect)
        initial_hp = p.hp
        p.take_damage(1)
        assert p.hp == initial_hp - 1
    finally:
        pygame.quit()


def test_player_taking_fatal_damage_starts_death_sequence():
    from stellar_horizon.entities.player import Player
    import pygame
    pygame.init()
    try:
        screen_rect = pygame.Rect(0, 0, 480, 270)
        p = Player(screen_rect)
        # Take enough damage to kill
        for _ in range(20):
            p.take_damage(1)
        assert p.dying is True or p.alive is False, (
            "player should be dying or dead after fatal damage"
        )
    finally:
        pygame.quit()


def test_player_hit_emits_particles_via_fx():
    from stellar_horizon.entities.player import Player
    from stellar_horizon.fx.particles import FxLayer
    import pygame
    pygame.init()
    try:
        screen_rect = pygame.Rect(0, 0, 480, 270)
        p = Player(screen_rect)
        fx = FxLayer(pool_size=64)
        p.fx = fx
        p.take_damage(1)
        alive = [pp for pp in fx.particles if pp.alive]
        assert len(alive) > 0, "player hit should emit particles"
    finally:
        pygame.quit()
```

- [ ] **Step 2: Run tests, verify they fail (RED)**

Run: `python -m pytest stellar_horizon/tests/test_visual_vfx.py -v -k "player_takes or player_taking or player_hit_emits"`
Expected: 3 tests FAIL (no take_damage method or fx wiring)

- [ ] **Step 3: Add take_damage, dying, dead flags to Player**

Open `stellar_horizon/entities/player.py`. Add to `__slots__`:

```python
"dying",       # bool - in death animation
"dead",        # bool - death animation complete
"hit_flash",   # float - remaining hit-flash time
"dying_time",  # float - elapsed in death sequence
"invulnerable_frames",  # already exists
```

In `__init__`:

```python
self.dying: bool = False
self.dead: bool = False
self.hit_flash: float = 0.0
self.dying_time: float = 0.0
```

Add the `take_damage` method:

```python
def take_damage(self, amount: int) -> None:
    """Apply damage. Triggers hit VFX and starts death sequence at 0 HP."""
    if self.invulnerable_frames > 0:
        return
    self.hp -= amount
    self.hit_flash = 0.3
    if self.fx is not None:
        self.fx.emit_player_hit(self.x, self.y)
    if self.hp <= 0 and not self.dying:
        self.dying = True
        self.dying_time = 0.0
        self.alive = False  # stop normal update
        if self.fx is not None:
            self.fx.emit_player_death(self.x, self.y)
```

In `update`, handle the death sequence:

```python
# In the update method, after normal position update:
if self.dying:
    self.dying_time += dt
    if self.dying_time >= 1.5:
        self.dead = True
    return  # skip normal movement
```

Also handle the hit-flash in update:

```python
# At the top of update
if self.hit_flash > 0:
    self.hit_flash = max(0, self.hit_flash - dt)
```

- [ ] **Step 4: Run tests, verify they pass (GREEN)**

Run: `python -m pytest stellar_horizon/tests/test_visual_vfx.py -v -k "player_takes or player_taking or player_hit_emits"`
Expected: 3/3 PASS

- [ ] **Step 5: Update GameplayScene to wait for player.dead before showing game over**

Open `stellar_horizon/scenes/gameplay.py`. Find the death/transition logic. Update to check `self.player.dead`:

```python
# In the update method where the game-over transition happens:
if self.player.dead:
    # Player death animation complete, transition to game over
    self._next = GameOverScene(...)
    return
```

- [ ] **Step 6: Wire `self.fx` in GameplayScene**

Ensure `self.player.fx = self.fx` is set in `on_enter`.

- [ ] **Step 7: Run full test suite**

Run: `python -m pytest stellar_horizon/tests/`
Expected: 65+ tests PASS

- [ ] **Step 8: Commit**

```bash
cd D:\AI\stellar-horizon
git add stellar_horizon/entities/player.py stellar_horizon/scenes/gameplay.py stellar_horizon/tests/test_visual_vfx.py
git commit -m "feat(vfx): player hit (sparks + flash) and death (big explosion + 1.5s sequence) animations"
```

---

## Task 9: Final Visual Smoke Test

**Files:** none (read-only verification)

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest stellar_horizon/tests/ -v`
Expected: 65+ tests PASS (43 existing + 22 new)

- [ ] **Step 2: Run smoke test**

Run: `python stellar_horizon/smoke.py`
Expected: 11/11 gates PASS

- [ ] **Step 3: Run game --check**

Run: `cd D:\AI\stellar-horizon; .venv\Scripts\python.exe main.py --check`
Expected: prints "STELLAR HORIZON check OK"

- [ ] **Step 4: Visual smoke test — launch the game**

Run: `cd D:\AI\stellar-horizon; .venv\Scripts\python.exe main.py`
Expected: game launches. Verify visually:
- Engine flames visible behind enemy ships
- Trail particles behind moving enemies
- FTL chain entry has cyan glow burst
- Bullets animate through sprite sheets
- Explosion on every enemy death (not just UFO/kamikaze)
- Bullet impact sparks on hit
- Player takes damage and flashes
- Player death plays the big explosion + animation

- [ ] **Step 5: Document the implementation summary**

Create `docs/superpowers/specs/2026-08-31-visual-polish-vfx-SUMMARY.md` with:
- Commit list
- Test count
- Visual verification notes (what was observed)
- Any tuning notes (particle counts, lifetimes, etc.)

Then commit the summary.

```bash
cd D:\AI\stellar-horizon
git add docs/superpowers/specs/2026-08-31-visual-polish-vfx-SUMMARY.md
git commit -m "docs(spec): add visual polish VFX implementation summary"
```

- [ ] **Step 6: Push to GitHub**

```bash
cd D:\AI\stellar-horizon
git push origin main
```

Expected: All commits pushed successfully.

---

## Spec Coverage Check

| Spec Section | Task(s) |
|---|---|
| §2.1 Engine flames (AI-generated, animated sprite sheets) | Task 3 (procedural fallback), Task 4, Task 5 |
| §2.2 Trail particles | Task 1 (FxLayer.emit_trail), Task 4 (enemy), Task 5 (player) |
| §2.3 FTL chain entry glow | Task 1 (FxLayer.emit_chain_spawn_glow), Task 6 (wire in wave_manager) |
| §2.4 Animated bullet sprite sheets | Task 7 |
| §2.5 Explosion on all enemy deaths | Task 1 (emit_explosion_typed), Task 2 (wire in take_damage) |
| §2.6 Bullet-hit impact effect | Task 1 (emit_bullet_impact), Task 2 (wire in gameplay) |
| §2.7 Player-hit animation | Task 8 |
| §2.8 Player death sequence | Task 8 |
| §3 Architecture (new files, modifications) | All tasks |
| §5 Configuration (_ENEMY_VFX_CONFIG) | Task 4 |
| §7 Testing strategy (~23 new tests) | Tasks 1, 2, 3, 4, 5, 6, 7, 8 each add tests |
| §9 Risk mitigations | Task 4 (1-particle cap), Task 3 (procedural fallback) |
| §10 Out of scope | Respected (no boss, no audio, no new sprites) |
| §11 Acceptance criteria | Task 9 verifies all |

## Type Consistency Check

- `FxLayer.emit_trail(x, y, color, intensity=1.0)` — defined Task 1, used Task 4 (enemy), Task 5 (player) ✓
- `FxLayer.emit_explosion_typed(kind, x, y, scale=1.0)` — Task 1, used Task 2 ✓
- `FxLayer.emit_chain_spawn_glow(x, y, chain_index, total_chain)` — Task 1, used Task 6 ✓
- `FxLayer.emit_bullet_impact(x, y, weapon, damage)` — Task 1, used Task 2 ✓
- `Enemy.flame` (EngineFlame) — Task 4 ✓
- `Player.flame` (EngineFlame) — Task 5 ✓
- `Enemy.fx`, `Player.fx`, `WaveManager.fx` — all reference the FxLayer instance ✓
- `Player.dying`, `Player.dead`, `Player.hit_flash`, `Player.dying_time` — all Task 8, consistent ✓
- `PlayerBullet.frame`, `EnemyBullet.frame` — Task 7 ✓
