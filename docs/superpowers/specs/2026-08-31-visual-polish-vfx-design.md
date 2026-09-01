# Visual Polish & VFX for Choreographed Enemy Movement — Design Spec

**Date:** 2026-08-31
**Status:** Draft (awaiting user review)
**Scope:** Visual polish for the existing 6 enemy types + player + bullets, leveraging the choreographed movement just implemented. **No new enemy types. No gameplay changes. No boss changes.**

---

## 1. Goal

Make the existing choreography VISIBLE through visual polish:
- **Trail particles** behind every moving ship so bezier curves are drawn in the air
- **Animated engine flames** on the 6 enemy types + player, AI-generated sprite sheets
- **FTL chain entry glow** when each link of a chain spawns
- **Animated bullet sprite sheets** (10 player weapons + enemy bullet) — the sheets exist, wire them up
- **Explosion particles on all enemy deaths** — currently some enemies just vanish
- **Bigger bullet-hit impact effect** when bullets connect
- **Player-hit animation** (screen shake + sparks)
- **Player death sequence** before game over

User explicitly said: **"not in contrast and brightness, but in details"** — actual visual elements, not just color tweaks.

**Approach:** Mixto. AI sprite sheets for engine flames (3-4 frames per type). Procedural for everything else (particles, trails, glows, impacts).

---

## 2. Components

### 2.1 Engine flames (AI-generated, animated sprite sheets)
- **6 enemy type sheets** + **1 player sheet** = 7 sheets total
- Each sheet: 4 frames at ~10x8 px (or sized to match ship width)
- Color tinted to ship type (red for bomber, blue for UFO, etc.)
- Frame sequence: small flame → big flame → medium → small (loop)
- **Loaded as AnimatedSprite**, frame advances per game tick
- **Flame size scales with speed** — slow ship = small flame, fast ship = big flame

### 2.2 Trail particles (procedural)
- New particle class `TrailParticle` in `fx/trail.py`
- Emitted by every moving entity (enemies + player + bullets)
- Spawned at the entity's exhaust position (back of ship)
- Spawned only when entity is moving (speed > threshold)
- Properties:
  - Position: trail behind ship
  - Velocity: 0 (fades in place)
  - Lifetime: 0.4s
  - Color: matches ship type (configurable)
  - Size: 2x2 px, shrinks over lifetime
  - Alpha: fades from 200 to 0 over lifetime

### 2.3 FTL chain entry glow (procedural)
- New particle burst `emit_chain_spawn_glow(x, y, chain_index, total_chain)`
- Emitted when each chain link spawns (in `wave_manager.py` `begin()` per link)
- Visual: expanding ring of particles (cyan/white)
- Duration: 0.5s
- Different from generic explosion: it's a portal-like entry effect, not damage

### 2.4 Animated bullet sprite sheets (use existing)
- **10 player weapon sheets** (`laser_01.png` to `laser_10.png`) — exist but unused for animation
- **2 enemy bullet sheets** (`player_bullet_sheet.png`, `enemy_bullet_sheet.png`) — exist
- Wire up the existing sheets in `bullet.py`:
  - Add `frame` + `frame_time` state to `PlayerBullet` and `EnemyBullet`
  - Each bullet animates through its sheet
  - Combine with existing `bullet_vfx.py` procedural effects (alpha pulse, halo) for full effect
- The `laser_01` etc. sheets: load as 4-frame strips, animate at 8 FPS

### 2.5 Explosion on all enemy deaths (procedural)
- **Current state:** UFO and KAMIKAZE explode (via FxLayer). Other enemies (SCOUT, CRUISER, HEAVY, BOMBER) just vanish.
- **Fix:** ALL enemy deaths call `FxLayer.emit_explosion(x, y, scale=...)`
- Scale by enemy type:
  - SCOUT: 0.5x (small pop)
  - CRUISER: 0.8x
  - HEAVY: 1.5x (big explosion)
  - BOMBER: 1.0x
  - UFO: 0.8x
  - KAMIKAZE: 1.0x
- New `emit_explosion_typed(kind, x, y)` in `FxLayer` that picks color/size by kind

### 2.6 Bullet-hit impact (procedural)
- **Current state:** `emit_impact(x, y, count=12)` — small spark
- **New:** `emit_bullet_impact(x, y, weapon, damage)`:
  - Weapon-tinted sparks (color matches the bullet)
  - Bigger debris count (20-30)
  - Brief flash sprite (1 frame, full screen at 30% alpha) for hard hits
  - Different impact per weapon type:
    - Plasma: white spark
    - Acid: green bubbling
    - Ice: pale blue shards
    - Fire: orange flame
    - Heart: pink hearts (existing behavior)
- Emitted in `scenes/gameplay.py` when `bullet.hit(enemy)` is called

### 2.7 Player-hit animation (procedural)
- When player takes damage:
  - Screen shake (use `fx/screen_shake.py` — already exists)
  - Player sprite flashes red/white for 0.3s
  - 8-12 sparks around player position
- Implemented in `Player.take_damage()`

### 2.8 Player death sequence (procedural)
- When player HP reaches 0:
  - Big explosion at player position (3x scale)
  - Player sprite plays a 0.8s "death" animation (8 frames, spiral)
  - 30-40 particles in a radial burst
  - Game waits 1.5s before showing "GAME OVER"
  - Screen shake intensifies
- New `Player.die()` method that triggers the sequence
- `GameplayScene` listens for player.dead to be True and waits before transitioning

---

## 3. Architecture

### 3.1 New files
| File | Purpose |
|---|---|
| `stellar_horizon/fx/engine_flames.py` | Load + animate engine flame sprite sheets |
| `stellar_horizon/fx/trail.py` | `TrailParticle` class + emission logic |
| `tools/generate_engine_flames.py` | AI script to generate 7 flame sheets via image_synthesize |

### 3.2 Modified files
| File | Change |
|---|---|
| `entities/enemy.py` | Add `flame` (AnimatedSprite ref), `flame_color`, emit trail particles in update, explode on death |
| `entities/player.py` | Add `flame` (AnimatedSprite ref), `flame_color`, emit trail particles, hit animation, death sequence |
| `entities/bullet.py` | Add `frame` + `frame_time` to PlayerBullet + EnemyBullet |
| `fx/particles.py` | Add `emit_explosion_typed(kind, x, y)`, `emit_bullet_impact(x, y, weapon)`, `emit_chain_spawn_glow(x, y)` |
| `fx/bullet_vfx.py` | Add sheet-based animation alongside existing code-driven VFX |
| `scenes/gameplay.py` | Wire up trail emission, hit animations, player death, chain spawn glows |
| `waves/wave_manager.py` | Emit chain spawn glow per link in `begin()` |
| `ui/animated_sprite.py` | Add optional `update` for flame sheets |

### 3.3 New AI assets
- `assets/sprites/engine_flame_sheet.png` — generic flame sheet (4 frames)
- `assets/sprites/engine_flame_player_sheet.png` — player-flavored
- `assets/sprites/engine_flame_scout_sheet.png`
- `assets/sprimes/engine_flame_cruiser_sheet.png`
- `assets/sprites/engine_flame_heavy_sheet.png`
- `assets/sprites/engine_flame_bomber_sheet.png`
- `assets/sprites/engine_flame_ufo_sheet.png`
- `assets/sprites/engine_flame_kamikaze_sheet.png`

Total: 7 sheets × 4 frames = 28 sprite frames

---

## 4. Data Flow

### 4.1 Per-frame update sequence (entity with engine flame)
```
1. Entity.update(dt, ...)
2.   PathFollower.update(dt)  -> new position
3.   Entity.x, y = new position
4.   If speed > threshold: FxLayer.emit_trail(x, y, kind, dt)
5.   self.flame.update(dt)  # advance flame frame
6.   Emit scheduled attacks (telegraph, shoot, etc.)
```

### 4.2 Draw sequence (entity with engine flame)
```
1. Scenelf._draw_enemy(enemy, surface)
2.   rotated = compute_banking(enemy.vx, enemy.vy)
3.   surface.blit(rotated_sprite, (x - w/2, y - h/2))
4.   flame_pos = compute_flame_position(enemy.x, enemy.y, enemy.vx)
5.   surface.blit(enemy.flame.current_frame(), flame_pos)
```

### 4.3 Enemy death sequence
```
1. enemy.take_damage(dmg) -> enemy.hp -= dmg
2. If hp <= 0:
3.   FxLayer.emit_explosion_typed(enemy.kind, enemy.x, enemy.y)
4.   enemy.alive = False
```

---

## 5. Configuration

### 5.1 FxLayer new methods
| Method | Signature | Purpose |
|---|---|---|
| `emit_trail` | `(x, y, kind, intensity=1.0)` | Trail particle burst behind ship |
| `emit_explosion_typed` | `(kind, x, y, scale=1.0)` | Kind-specific explosion (color + size) |
| `emit_bullet_impact` | `(x, y, weapon)` | Weapon-tinted impact spark |
| `emit_chain_spawn_glow` | `(x, y, chain_index, total_chain)` | FTL chain entry effect |
| `emit_player_hit` | `(x, y)` | Player-hit sparks + flash |
| `emit_player_death` | `(x, y)` | Big radial explosion |

### 5.2 Per-enemy-kind config (new dict in `entities/enemy.py`)
```python
_ENEMY_VFX_CONFIG = {
    EnemyKind.SCOUT:    {"flame_color": (180, 220, 255), "trail_intensity": 0.6, "explosion_scale": 0.5},
    EnemyKind.CRUISER:  {"flame_color": (255, 200, 100), "trail_intensity": 0.4, "explosion_scale": 0.8},
    EnemyKind.HEAVY:    {"flame_color": (255, 140, 80),  "trail_intensity": 0.2, "explosion_scale": 1.5},
    EnemyKind.BOMBER:   {"flame_color": (255, 100, 60),  "trail_intensity": 0.4, "explosion_scale": 1.0},
    EnemyKind.UFO:      {"flame_color": (200, 100, 255), "trail_intensity": 0.3, "explosion_scale": 0.8},
    EnemyKind.KAMIKAZE: {"flame_color": (255, 80, 80),   "trail_intensity": 0.9, "explosion_scale": 1.0},
}
```

---

## 6. Edge Cases

- **Performance:** 20+ ships emitting trails + chain glows + explosions. Cap trail particles per entity per frame (1 per entity max, regardless of speed).
- **Missing flame sheet:** If an AI generation fails, fall back to no flame (don't crash). Log a warning.
- **Pool exhaustion:** FxLayer already uses a pool. If full, drop oldest.
- **Player death during chain:** Chain links keep spawning even after player death (consistent with current behavior — the wave plays out).
- **Boss:** Out of scope. Boss keeps its existing VFX.

---

## 7. Testing Strategy

New file `tests/test_visual_vfx.py` with:

1. **Engine flame tests (~5 tests)**
   - `test_engine_flame_sheet_loads_4_frames`
   - `test_engine_flame_advances_frame_per_tick`
   - `test_engine_flame_resets_at_end_of_sheet`
   - `test_engine_flame_size_scales_with_speed`
   - `test_missing_flame_sheet_does_not_crash`

2. **Trail particle tests (~4 tests)**
   - `test_trail_emitted_when_entity_moves`
   - `test_trail_not_emitted_when_entity_still`
   - `test_trail_particle_fades_over_lifetime`
   - `test_trail_color_matches_enemy_kind`

3. **FTL chain glow tests (~3 tests)**
   - `test_chain_spawn_emits_glow_per_link`
   - `test_chain_glow_fades_after_0_5s`
   - `test_chain_glow_color_cyan`

4. **Explosion tests (~3 tests)**
   - `test_all_enemy_kinds_explode_on_death`
   - `test_explosion_scale_matches_kind`
   - `test_explosion_uses_kind_color`

5. **Bullet impact tests (~3 tests)**
   - `test_bullet_impact_emits_weapon_tinted_sparks`
   - `test_bullet_impact_count_scales_with_damage`
   - `test_no_impact_when_bullet_misses`

6. **Player tests (~3 tests)**
   - `test_player_hit_emits_sparks_and_screen_shake`
   - `test_player_takes_damage_decrements_hp`
   - `test_player_death_triggers_sequence`

7. **Bullet animation tests (~2 tests)**
   - `test_player_bullet_animates_through_sheet`
   - `test_enemy_bullet_animates_through_sheet`

**Total: ~23 new tests.**

---

## 8. Implementation Order (TDD)

1. **New particle methods in FxLayer** (TDD) — `emit_trail`, `emit_explosion_typed`, `emit_bullet_impact`, `emit_chain_spawn_glow`, `emit_player_hit`, `emit_player_death` (test first, implement)
2. **Wire all-enemy explosion** in `enemy.py` `take_damage` (test all 6 kinds)
3. **Wire trail emission** in `entities/enemy.py` and `entities/player.py` update (test movement triggers)
4. **Generate engine flame sheets** via `tools/generate_engine_flames.py` (one-time AI generation)
5. **Load + animate engine flames** in `fx/engine_flames.py` (TDD)
6. **Wire engine flames to entities** in `enemy.py` and `player.py` (test rendering)
7. **Wire FTL chain entry glow** in `wave_manager.py` `begin()` (test chain expansion emits glow)
8. **Wire bullet sheet animations** in `entities/bullet.py` (test frame advance)
9. **Wire bullet-impact VFX** in `scenes/gameplay.py` (test on hit)
10. **Player hit animation** in `entities/player.py` (test HP + VFX)
11. **Player death sequence** in `entities/player.py` + `scenes/gameplay.py` (test death state)
12. **Visual smoke test** — launch game, verify all VFX visible

---

## 9. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| 20+ trails + explosions tank FPS | Cap trail particles per frame per entity; use object pools |
| AI generation fails for some flame sheets | Fall back to no flame with log warning; not crash |
| Existing 43 tests break | Update carefully; one commit per concern; run full suite between each |
| Bullet sheet animation conflicts with existing VFX | Combine via alpha-blend: sheet frame on top, VFX halo behind |
| Engine flame positioned wrong (covers ship) | Test by visual inspection; flame anchor at exhaust point of sprite |

---

## 10. Out of Scope (Explicit)

- ❌ New enemy types
- ❌ Boss VFX changes
- ❌ Regenerating all enemy sprites (only flames)
- ❌ New audio/SFX
- ❌ Shader effects (the game is 16-bit pixel art, no shaders)
- ❌ Player weapon-specific bullet VFX (existing VFX stays; only sheet animation added)

---

## 11. Acceptance Criteria

The implementation is done when:
- ✅ All 23 new tests pass
- ✅ All 43 existing tests still pass
- ✅ Game launches, runs at 120 FPS with 20+ enemies + trails + explosions
- ✅ All 6 enemy types have visible engine flames
- ✅ All 6 enemy types have explosion on death (not just vanish)
- ✅ Player ship has engine flame + trail
- ✅ Bullets animate through sprite sheets
- ✅ FTL chain entries have visible glow
- ✅ Bullet hits have weapon-tinted impact sparks
- ✅ Player hit triggers screen shake + sparks
- ✅ Player death plays animation before game over
- ✅ `smoke.py` 11/11 gates pass
