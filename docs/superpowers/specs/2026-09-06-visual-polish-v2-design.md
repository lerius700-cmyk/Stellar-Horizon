# Visual Polish v2 — Design Spec

**Date:** 2026-09-06
**Status:** Approved (user signed off on 3 axis choices: both_flame_trail, two_layer, sprite-sheet + per-weapon particles/trail)
**Author:** Lerius (with Mavis)
**Baseline:** `v1.2.0` tag (commit `9b772de`)

## Problem

After the destruction-fall v2 work, the visual layer has 3 remaining rough edges that the user wants smoothed:

1. **Enemy engine flame + comet-tail keep rendering during the death-fall.** The ship is supposed to be "dead" (motor cortado, no propulsion), but the engine flame and the comet-tail light trail keep drawing because they're gated only by `e.alive` (which stays `True` during the 1.0s `dying_timer` window).

2. **Player trail is too thin.** Today the player only emits a single cyan P_SPARK when `thrusting=True`. The player ship is the main character and should always have a visible aura; the thrust itself should feel impactful.

3. **Bullets are static single-frame sprites.** The per-weapon VFX (alpha pulse, scale pulse, halo) is good, but the bullet body itself is a static image. A 6-frame animated sprite sheet per weapon, plus per-weapon particles and trails, will make every shot feel alive.

The user also asked for visual recommendations. These are captured in the "Out of scope" section below.

## Goal

When a ship is killed, the engine flame and comet-tail disappear immediately. The player always has a faint base trail and a brighter thrust trail. Bullets are 6-frame animated sprites with per-weapon particles and trails.

## Approach

Four coordinated changes, ordered by impact:
- **A.** Enemy death cleanup (small, gated render)
- **B.** Player two-layer trail (medium, new state on Player)
- **C.** Bullet 6-frame sprite-sheet (largest, AI generation + per-frame cycling)
- **D.** Per-weapon bullet particles + trails (medium, extends existing bullet_vfx.py)

## Components

### 1. `stellar_horizon/scenes/gameplay.py` (draw loop, lines 628-642)

**Current code:**

```python
for e in self.wave_manager.spawned_enemies:
    if e.alive:
        self._draw_enemy_trail(surface, e, ox, oy)
        self._draw_enemy_sprite(surface, e, ox, oy)
        if e.flame is not None:
            e.flame.update(self._last_dt)
            speed = math.hypot(e.vx, e.vy)
            size_scale = 0.5 + min(1.0, speed / 150.0)
            e.flame.render(surface, e.x + 6, e.y, size_scale=size_scale)
```

**Change:** gate the trail AND the flame on `e.dying_timer == 0.0`. The sprite (death burst / IDLE falling) keeps rendering because the user wants to see the ship during the fall.

```python
for e in self.wave_manager.spawned_enemies:
    if e.alive:
        # Motor cortado durante la muerte: NO trail, NO llama
        is_dying = getattr(e, "dying_timer", 0.0) > 0.0
        if not is_dying:
            self._draw_enemy_trail(surface, e, ox, oy)
        self._draw_enemy_sprite(surface, e, ox, oy)
        if not is_dying and e.flame is not None:
            e.flame.update(self._last_dt)
            speed = math.hypot(e.vx, e.vy)
            size_scale = 0.5 + min(1.0, speed / 150.0)
            e.flame.render(surface, e.x + 6, e.y, size_scale=size_scale)
```

### 2. `stellar_horizon/entities/player.py` (update method)

**Add slot:** `_trail_thrust_cooldown: float = 0.0`

**Initialize in `__init__`:** `self._trail_thrust_cooldown = 0.0`

**Update logic (replace existing trail block at line 158-160):**

```python
# --- Visual polish: 2-layer trail ---
# Capa 1: aura tenue SIEMPRE (no requiere thrusting)
if self.alive and self.fx is not None:
    self.fx.emit_trail(self.x - 6, self.y, (100, 200, 255), intensity=0.30)
# Capa 2: destello brillante al moverse, throttled a ~30Hz
if self.alive and self.thrusting and self.fx is not None:
    self._trail_thrust_cooldown -= dt
    if self._trail_thrust_cooldown <= 0.0:
        self.fx.emit_trail(self.x - 6, self.y, (200, 230, 255), intensity=1.0)
        self._trail_thrust_cooldown = 1.0 / 30.0
```

### 3. `stellar_horizon/assets/sprites_v2/laser_NN_sheet.png` (5 new sprite sheets)

Generate 5 sprite sheets (one per laser archetype), 6 frames each, 29×7 per frame:
- `laser_01_sheet.png` — yellow plasma (weapon 0)
- `laser_02_sheet.png` — red pulse (weapon 1)
- `laser_03_sheet.png` — blue ion (weapon 2)
- `laser_04_sheet.png` — purple void (weapon 4)
- `laser_05_sheet.png` — orange fireball (weapon 5)

(The other 5 weapons are already covered by 5 archetypes, mapping weapon id → archetype happens elsewhere.)

Use the existing pipeline:
1. `tools/postprocess_v3.py` cleans the AI-generated singles
2. `sprite_tests/generate_sheets.py` expands each single to 6 frames procedurally

**Map weapon id → archetype:**

```python
# In a new helper or directly in the bullet draw
WEAPON_ARCHETYPE = (0, 1, 2, 3, 4, 4, 2, 3, 2, 4)
# weapon 0 (yellow) → archetype 0 (laser_01)
# weapon 1 (red)    → archetype 1 (laser_02)
# weapon 2 (blue)   → archetype 2 (laser_03)
# weapon 3 (acid)   → archetype 3 (laser_04)
# weapon 4 (purple) → archetype 4 (laser_05) [or wherever it fits]
# weapon 5 (orange) → archetype 4 (orange fireball)
# weapon 6 (white)  → archetype 2 (thin/needle)
# weapon 7 (pink)   → archetype 3 (heart)
# weapon 8 (cyan)   → archetype 2 (ice shard)
# weapon 9 (rainbow)→ archetype 4 (rainbow streak)
```

### 4. `stellar_horizon/entities/bullet.py` (animation state)

**Add slots:** `frame_elapsed: float`, `frame_index: int`

**Initialize in `__init__`:** `self.frame_elapsed = 0.0`, `self.frame_index = 0`

**Add in `update`:**

```python
def update(self, dt: float) -> None:
    self.x += self.vx * dt
    self.y += self.vy * dt
    # Frame animation: 12 fps cycling through 6 frames
    self.frame_elapsed += dt
    self.frame_index = int(self.frame_elapsed * 12) % 6
```

**Add `weapon_archetype` slot** (computed from `self.weapon` via the `WEAPON_ARCHETYPE` map at spawn time).

### 5. `stellar_horizon/scenes/gameplay.py` (bullet render)

**Replace the bullet draw loop** to use the new 6-frame sheet:

```python
for b in self.player_bullets:
    if b.alive:
        vfx = compute(b, self._elapsed)
        archetype = b.weapon_archetype
        sheet = self._animated.get(f"laser_{archetype:02d}")
        if sheet is not None and sheet.loaded and len(sheet._frames) > b.frame_index:
            frame = sheet._frames[b.frame_index]
            # ... apply vfx.alpha, vfx.scale, draw halo + frame ...
```

### 6. `stellar_horizon/fx/bullet_vfx.py` (per-weapon particles)

**Add fields to `WeaponVFX` dataclass:**

```python
@dataclass(frozen=True)
class WeaponVFX:
    # ... existing fields ...
    particle_kind: int = 0     # 0 = no particles, otherwise P_* from particle engine
    particle_color: tuple | None = None
    particles_per_frame: float = 0.0  # average particles per frame
    trail_intensity: float = 0.0
```

**Update `WEAPON_VFX_PARAMS` (10 entries):**

| weapon | kind | color | particles/frame | trail |
|---|---|---|---|---|
| 0 yellow plasma | P_SPARK | (255, 240, 100) | 2.0 | 0.6 |
| 1 red pulse | P_SPARK | (255, 100, 100) | 2.5 | 0.7 |
| 2 blue ion | P_SPARK | (120, 200, 255) | 1.0 | 0.0 |
| 3 green acid | P_DUST | (80, 255, 120) | 3.0 | 0.8 |
| 4 purple void | P_GLOW | (180, 80, 255) | 0.5 | 0.3 |
| 5 orange fireball | P_FIRE | (255, 140, 40) | 2.0 | 0.5 |
| 6 white piercing | — | — | 0.0 | 0.0 |
| 7 pink heart | P_SPARK | (255, 150, 200) | 1.5 | 0.4 |
| 8 cyan ice | P_SPARK | (140, 220, 255) | 1.0 | 0.5 |
| 9 rainbow | P_SPARK | (255, 200, 255) | 2.0 | 0.6 |

### 7. `stellar_horizon/fx/particles.py` (new emit method)

**Add to `FxLayer`:**

```python
def emit_bullet_particle(self, x: float, y: float, kind: int,
                          color: tuple[int, int, int] | None = None,
                          intensity: float = 1.0) -> None:
    """Emit a single bullet-trail particle. Caller throttles.
    
    `intensity` 0.0 = skip emit. The kind/color/intensity come from
    the WeaponVFX dataclass for the bullet's weapon.
    """
    if intensity <= 0.0 or kind == 0:
        return
    vx = random.uniform(-25, 25)
    vy = random.uniform(-25, 25)
    self.engine.emit(
        kind, x, y, vx, vy,
        color=color,
        life=0.2 * intensity,
        radius=1,
    )
```

### 8. `stellar_horizon/scenes/gameplay.py` (bullet update: emit particles)

**In the bullet update loop, emit particles throttled:**

```python
for b in self.player_bullets:
    if b.alive:
        vfx = compute(b, self._elapsed)
        if vfx.particles_per_frame > 0.0 and self.fx is not None:
            # Per-frame stochastic emission
            if random.random() < vfx.particles_per_frame / 60.0:
                self.fx.emit_bullet_particle(
                    b.x, b.y,
                    kind=vfx.particle_kind,
                    color=vfx.particle_color,
                    intensity=vfx.trail_intensity,
                )
```

## Data flow

### Camino 1: Enemy es derribado → motor cortado

```
[bullet hits enemy] → e.take_damage(amount)
  ↓
  hp <= 0:
    vx = vy = 0                    (momento cero, ya del destruction-fall v2)
    dying_timer = 1.0
    sprite_name = enemy_{kind}_death_v1
    fx.emit_explosion_typed(...)
  ↓
[next frame] e.update(dt) → bloque dying_timer > 0:
    vy += GRAVITY * dt
    vx *= exp(-DRAG * dt)
    y += vy * dt
    fx.emit_smoke(...)
    if y > 295 or timer <= 0: alive = False
  ↓
[next frame] gameplay.draw() → _draw_enemy_block:
    if e.alive:                     ← True (dying)
        is_dying = (dying_timer > 0) ← True
        if not is_dying: SKIP trail ← ACTIVO (skipea)
        _draw_enemy_sprite(...)
        if not is_dying and e.flame: SKIP flame ← ACTIVO (skipea)
```

### Camino 2: Player se mueve → 2 capas de trail

```
[each frame] player.update(dt):
    self.thrusting = (movement_input != 0)
    if alive and fx is not None:
        fx.emit_trail(self.x - 6, self.y, (100, 200, 255), intensity=0.30)
        if thrusting:
            _trail_thrust_cooldown -= dt
            if _trail_thrust_cooldown <= 0:
                fx.emit_trail(self.x - 6, self.y, (200, 230, 255), intensity=1.0)
                _trail_thrust_cooldown = 1/30
```

### Camino 3: Bala disparada → sprite animado + partículas + trail

```
[Space pressed] player._spawn_bullet():
    b.alive = True
    b.frame_elapsed = 0.0
    b.frame_index = 0
    b.weapon_archetype = WEAPON_ARCHETYPE[b.weapon]
    sfx.play_event("laser_fire")
  ↓
[each frame] b.update(dt):
    x += vx * dt
    y += vy * dt
    frame_elapsed += dt
    frame_index = int(frame_elapsed * 12) % 6
  ↓
[gameplay.update()]:
    for b in player_bullets:
        if b.alive:
            vfx = compute(b, t)
            if vfx.particles_per_frame > 0:
                if random.random() < vfx.particles_per_frame / 60:
                    fx.emit_bullet_particle(b.x, b.y, vfx.particle_kind,
                                             vfx.particle_color, vfx.trail_intensity)
  ↓
[gameplay.draw()] bullet render:
    vfx = compute(b, t)
    archetype = b.weapon_archetype
    sheet = self._animated.get(f"laser_{archetype:02d}")
    if sheet and sheet.loaded:
        frame = sheet._frames[b.frame_index]
        # apply vfx.alpha (per-pixel), vfx.scale (size), halo
        blit_frame(surface, b.x, b.y, frame, vfx)
```

## Error handling

| Case | Handling |
|---|---|
| `b.frame_index` out of range | `int(frame_elapsed * 12) % 6` is always 0..5. Sheet has exactly 6 frames. |
| `vfx.particle_kind = 0` means no particles | Convention: `particle_kind=0` is a no-op in `emit_bullet_particle`. Tests cover. |
| `vfx.particle_color is None` with particles > 0 | Engine uses default color of the P_ kind. Test: assert every weapon with particles has a color. |
| `b.weapon_archetype` out of range | `f"laser_{archetype:02d}"` produces "laser_99" if bad. `self._animated.get(name)` returns None. Guard: `if sheet is not None and sheet.loaded:`. |
| Bullet exits screen | `b.alive = False` set by wave_manager cleanup. |
| `_trail_thrust_cooldown` drift | Reset to 1/30 on every emit. Bounded. |
| `e.flame is None` | Guard already in place. New check: also `dying_timer == 0.0`. |
| Floating-point comparison `dying_timer == 0.0` | Use property `is_dying` returning `dying_timer > 0.0` for safety. |
| Bullet sprite sheet not loaded | `_load_sprites()` already warns. Draw has guard. |
| `fx is None` | Guards `if self.fx is not None:` everywhere. |
| Boss dying state | Boss uses `phase`, not `dying_timer`. New code only checks `dying_timer > 0` on enemies. Safe. |
| AI generation of laser sprites fails | Script captures exception, doesn't commit. Bullets fallback to current single-frame. |
| Performance (too many particles) | Engine uses pool, cost is O(1). Throttled emission caps particles/frame at ~2-3. ~50-100 particles/frame total — well within budget. |

## Testing

### Unit tests (11 new)

**Enemy death cleanup (2 tests in `test_enemy.py`):**
- `test_enemy_no_trail_or_flame_state_during_dying` — verify `is_dying` property works
- `test_enemy_during_dying_skips_trail_emission` — assert trail deque doesn't grow

**Player two-layer trail (3 tests in `test_player.py`):**
- `test_player_base_trail_emits_every_frame_when_alive`
- `test_player_thrust_trail_emits_at_30hz`
- `test_player_two_layers_independent_counts`

**Bullet animation (3 tests in `test_bullet.py`):**
- `test_bullet_frame_index_advances_at_12fps`
- `test_bullet_frame_index_wraps_after_6`
- `test_bullet_weapon_archetype_maps_correctly`

**Per-weapon particles (3 tests in `test_bullet_vfx.py`):**
- `test_weapon_vfx_dataclass_new_fields_default_correctly`
- `test_bullet_particles_per_frame_throttled_to_60hz_baseline`
- `test_weapon_particle_kind_0_means_no_particles`

### Integration tests (2 new in `test_bullet_render.py`)

- `test_bullet_renders_with_animation_frame_changes`
- `test_weapon0_emits_chispas_amarillas_in_pool`

### Visual sandbox (1 new tool, not a test)

- `sprite_tests/bullet_sandbox.py` — produces 64 contact-sheets
  - 4 representative weapons (plasma, ion, fireball, rainbow) × 4 particles/frame × 4 trail intensity
  - Saves to `sprite_tests/captures/bullet_vfx_*.png`
  - User reviews visually to confirm VFX feel

### What is NOT tested

- Exact pixel color of frame N (depends on AI generation)
- Performance benchmarks (out of scope; engine uses pool)
- Cross-weapon visual consistency (user decision via sandbox)

## Success criteria

- 11 new unit tests pass
- 2 new integration tests pass
- 64 sandbox PNGs produced
- Visual review confirms: engine flame + trail cut on enemy death, player 2-layer trail visible, bullets animated, per-weapon particles + trails visible
- 400 + 13 = 413 tests passing total
- No regression in existing 400 tests

## Skills used

- `superpowers:brainstorming` (this spec)
- `superpowers:writing-plans` (next: convert spec to task list)
- `superpowers:test-driven-development` (write tests before code)
- `superpowers:verification-before-completion` (run sandbox before claiming done)
- `superpowers:requesting-code-review` (final review before merge)

## Out of scope (recommendations for future)

The user asked for visual recommendations. These are NOT in this spec but documented here as a future-work list:

1. **Boss death-fall v2** — boss doesn't use the new physics. Could add a similar realistic tumble for boss death.
2. **Player ship sprite variety** — currently 5 variants but the gameplay only uses variant 1. Could randomize per life/respawn.
3. **Explosion VFX variety per kind** — all enemies share the same `emit_explosion_typed` pattern. Could differentiate by kind (scout: small puff, heavy: shockwave + fire ring, etc.).
4. **Boss telegraph visual** — boss telegraph line is a flat line. Could be a pulsating beam with particles.
5. **Power-up sparkles** — silver/gold rings are static. Could rotate + sparkle.
6. **Screen shake feedback per weapon** — yellow plasma: light, fireball: heavy. Currently all weapons shake the same.
7. **Hit-stop / freeze frame** — when the player is hit, briefly freeze the game (~0.1s) for impact feel. 16-bit shmups often do this.
8. **Muzzle flash** — when the player fires, briefly flash the ship's front. We have `laser_fire` SFX but no visual muzzle.
9. **Cockpit HUD elements** — score popup animations, multiplier counters.
10. **Camera shake on big explosions** — boss death, heavy/bomber death.

## Skeleton path resolution

All asset paths via `Path(__file__).resolve().parent` (never CWD-relative).
All tests use `$env:PYTHONPATH = $PWD; .\.venv\Scripts\python.exe -m pytest`.
Type hints on all new methods. `__slots__` discipline preserved.
