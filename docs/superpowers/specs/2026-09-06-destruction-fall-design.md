# Destruction Fall — Design Spec

**Date:** 2026-09-06
**Status:** Approved (user signed off Approach A — ship sprite falling + smoke trail)
**Author:** Lerius (with Mavis)

## Problem

The current destruction animation (added 2026-09-06 polish pass) makes
the ship appear to fly off in random directions at high speed instead
of falling naturally downward. Root cause: `take_damage()` preserves
the enemy's previous movement velocity (`vx`, `vy`) into the death
state and only dampens it by 35%. A kamikaze charging at the player
at vx=180 px/s keeps drifting at 63 px/s while the explosion sprite
rotates at 240°/s, producing a chaotic "shot in any direction" read.

## Goal

When an enemy is killed, the ship must:
- Stop all previous movement instantly (vx = vy = 0 at the moment of death)
- Fall under constant gravity, with air drag slowing both linear and angular velocity
- Tumble realistically: rotation rate decays with drag, not uniform
- Render as the actual ship (rotated), not the explosion sprite
- Leave a smoke trail during the fall
- Be purgable when it exits the viewport bottom

## Approach (chosen)

**Approach A — Ship sprite falling + smoke trail**
1. Rewrite `Enemy` dying physics: zero momentum on death, then gravity + exponential linear/angular drag.
2. Split the visible sprite: death sheet for the first 0.15s (explosion burst), then the ship's IDLE sheet (the actual ship, rotated by `dying_rotation`).
3. Add a new `P_SMOKE` particle kind emitted during the fall.
4. Build a destruction sandbox tool that produces a contact-sheet PNG per (gravity, drag) parameter pair so we can iterate visually.

## Components

### 1. `stellar_horizon/entities/enemy.py`

**New module-level constants:**
```python
_ENEMY_DYING_GRAVITY_PX_S2 = 500.0          # gravity acceleration
_ENEMY_DYING_DRAG_LINEAR = 1.8              # 1/s exponential drag on vx
_ENEMY_DYING_DRAG_ANGULAR = 0.6             # 1/s exponential drag on omega
_ENEMY_DYING_OMEGA_RANGE = (-180.0, 180.0)  # deg/s random initial spin
_ENEMY_DYING_DEATH_SHEET_S = 0.15           # burst duration before showing ship
```

**`__slots__` additions:** `dying_omega: float`, `dying_elapsed: float`, `_smoke_throttle: int`

**`__init__` additions:** `dying_omega = 0.0`, `dying_elapsed = 0.0`, `_smoke_throttle = 0`

**`take_damage()` change** (when HP→0):
```python
self.vx = 0.0
self.vy = 0.0
self.dying_omega = random.uniform(*_ENEMY_DYING_OMEGA_RANGE)
self.dying_elapsed = 0.0
self.dying_timer = 1.0  # (was 0.6, kept at 1.0 for death sheet + safety)
self.sprite_name = f"enemy_{self.kind}_death_v1"
```

**`update()` change** (in the `dying_timer > 0` block):
```python
self.dying_elapsed += dt
self.vy += _ENEMY_DYING_GRAVITY_PX_S2 * dt
self.vx *= math.exp(-_ENEMY_DYING_DRAG_LINEAR * dt)
self.dying_omega *= math.exp(-_ENEMY_DYING_DRAG_ANGULAR * dt)
self.dying_rotation += self.dying_omega * dt
self.y += self.vy * dt
self.x += self.vx * dt
# ... existing purge condition (y > 295 or timer <= 0)
# Smoke emission (throttled 1 every 2 frames)
if self.fx is not None:
    self._smoke_throttle = (self._smoke_throttle + 1) % 2
    if self._smoke_throttle == 0:
        self.fx.emit_smoke(self.x, self.y)
```

**New method `current_dying_sheet() -> str`:**
```python
def current_dying_sheet(self) -> str:
    if self.dying_elapsed < _ENEMY_DYING_DEATH_SHEET_S:
        return f"enemy_{self.kind}_death_v1"
    return self.base_sprite_name or f"enemy_{self.kind}_v1"
```

### 2. `stellar_horizon/scenes/gameplay.py`

**`_draw_enemy_sprite` change** (priority section):
```python
if getattr(e, "dying_timer", 0.0) > 0.0:
    sheet_name = e.current_dying_sheet()
    anim = self._animated.get(sheet_name)
    if anim is not None:
        sil_key = ("enemy", sheet_name)
# ... rest unchanged, still uses _blit_centered_rotated
```

### 3. `stellar_horizon/fx/particle_engine.py`

**New particle kind:** `P_SMOKE = 19` (next after P_WAKE=18)

**`FxLayer.emit_smoke(x, y)`:**
- Spawn one P_SMOKE particle at (x, y)
- Properties: `vx = random.uniform(-3, 3)`, `vy = -8` (rises), `lifetime = 0.6s`
- Render: gray `(180, 180, 180)`, alpha 200→0 linear fade, scale 1.0→2.5

**`update_particles()`:** Add the P_SMOKE branch:
- `vy += 5 * dt` (slow upward drift decelerates)
- `x += vx * dt`, `y += vy * dt`
- `alpha = int(200 * (1 - age))`
- `radius = 1.0 + 1.5 * age`

### 4. `sprite_tests/destruction_sandbox.py` (new tool)

**`capture_destruction(gravity, drag_linear, out_path)`:**
- Headless pygame (`SDL_VIDEODRIVER=dummy`)
- For each of 6 kinds: spawn at (60 + i*70, 50), warm up 3 ticks, `take_damage(1)`
- Capture every 1/30s for 1.2s (36 frames)
- Compose 6 columns (kinds) × 36 rows (frames) into a single PNG
- Save to `sprite_tests/captures/destruction_grav{g}_drag{d}.png`

**`run_sweep()`:**
- Calls `capture_destruction` with 9 combinations:
  - gravity ∈ {400, 500, 600}
  - drag_linear ∈ {0.5, 1.5, 3.0}
- Produces 9 PNGs for visual A/B comparison

## Data flow

```
[bullet hits enemy]
    v
take_damage(1):
  vx=vy=0
  dying_omega = random
  dying_elapsed=0, dying_timer=1.0
  sprite_name = death_v1
  fx.emit_explosion_typed  (the burst)
    v
[each frame during dying_timer>0]
  update():
    dying_elapsed += dt
    vy += GRAVITY*dt
    vx *= exp(-DRAG_L*dt)
    omega *= exp(-DRAG_A*dt)
    dying_rotation += omega*dt
    y += vy*dt; x += vx*dt
    if (y>295 or timer<=0): alive=False
    fx.emit_smoke (throttled)
    v
  draw() -> _draw_enemy_sprite:
    sheet = current_dying_sheet()
      [first 0.15s: death_v1, after: base_sprite]
    blit silhouette + sprite rotated by dying_rotation
    v
[wave_manager.update() next tick]
  purges alive=False enemies
```

## Error handling

| Case | Handling |
|---|---|
| vx/vy very high at death | Forced to 0 in take_damage |
| Random omega out of range | `random.uniform` always in range; tests verify range |
| Drag on live enemy | Block guarded by `dying_timer > 0` |
| Large dt (frame skip) | Drag math works for any dt; gravity may skip a frame |
| `current_dying_sheet()` when dying_timer=0 | Returns base_sprite_name (may be "") |
| Death off-screen (y>270) | Purged quickly via y>295 or timer=0 safety net |
| P_SMOKE without fx | Guarded by `if self.fx is not None` |
| fx.emit_smoke missing | AttributeError on first emission (fails loud) |
| Boss dying | NOT affected — boss has its own phase state |
| Sandbox frame capture fails | Log + continue; mosaic may be partial |

## Testing

**Unit tests in `tests/test_enemy.py` (8 new):**
- `test_dying_zeroes_momentum`
- `test_dying_applies_gravity_monotonically`
- `test_dying_drag_slows_horizontal`
- `test_dying_omega_decays_with_drag`
- `test_dying_random_omega_within_range`
- `test_dying_death_sheet_first_then_idle`
- `test_dying_offscreen_ends`
- `test_dying_timer_ends`

**Integration test in `tests/test_destruction_render.py` (1 new):**
- `test_destruction_render_produces_visible_ship_after_burst` — headless render, asserts pixels at expected position include a non-background ship cluster.

**Visual sandbox (not automated):**
- `destruction_sandbox.py` produces 9 contact-sheets
- Agent reviews the PNGs, picks the best (gravity, drag) pair, hardcodes those values in code

## Success criteria

- 8 + 1 = 9 new tests pass
- 9 contact-sheet PNGs produced
- Visual review confirms: ship falls almost vertically, tumbles with decaying rotation, smoke trail visible, exits viewport bottom
- 390 existing tests + 9 new = 399 tests passing total

## Skills used

- `superpowers:brainstorming` (this spec)
- `superpowers:writing-plans` (next: convert spec to task list)
- `superpowers:test-driven-development` (write tests before code)
- `superpowers:verification-before-completion` (run contact-sandbox before claiming done)
- `superpowers:requesting-code-review` (final review before merge)

## Out of scope

- Ground collision with mountain geometry (viewport bottom = "ground")
- Bounce on impact
- Performance benchmarks for many simultaneous deaths
- Boss-specific death animation (separate state machine)
