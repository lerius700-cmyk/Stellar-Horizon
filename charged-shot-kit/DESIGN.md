# DESIGN — Implementing a "Megaman-style charged shot" in any shoot-em-up

> A self-contained reference for porting the Stellar Horizon v1.7 charge
> mechanic to a new shmup. The code lives in `charged_shot_kit/`; the
> playable demo lives in `examples/full_demo.py`. Both are stdlib + pygame
> only (no numpy, no external assets).

## 0. TL;DR

A charged shot is **two state machines in series**:

1. A **charging state machine** on the *player* (6 attributes, 4 update
   branches) that answers "did the player hold the key long enough, and
   if so what should happen *this frame*?"
2. A **fired-entity state machine** on the *bullet/disc* (2-3 states,
   ~100 lines) that answers "I was just spawned, how do I behave, when
   do I die?"

Everything else (visual orb, audio, per-weapon tables) is a thin layer on
top of these two. The visual + audio are the only parts that have to
match your game's art direction; the state machines are engine-agnostic.

The kit ships:

| File | Role | Lines |
|---|---|---|
| `charged_shot_kit/state.py` | `ChargedShotState` (the 6 attrs) | ~120 |
| `charged_shot_kit/orb.py` | `ShipChargeOrb.draw()` (3-layer muzzle FX) | ~140 |
| `charged_shot_kit/charged_bullet.py` | `ChargedBullet` (FSM FLYING→FADING) | ~160 |
| `charged_shot_kit/__init__.py` | re-exports | ~10 |
| `examples/full_demo.py` | runnable pygame demo (1 weapon, 3 archetypes) | ~250 |
| `tests/test_state.py` | edges, accumulation, reset, snapshot | ~80 |
| `tests/test_orb.py` | draw at 0/25/50/85/100% + pulse | ~40 |
| `tests/test_charged_bullet.py` | spawn, fly, hit count, fade, off-screen | ~80 |

Total: ~900 lines, including docstrings and tests. Drop-in.

## 1. The mental model

When the player **holds** a fire key, three things are simultaneously true:

- The key is currently down (a *held* boolean — cheap to poll every frame).
- The key transitioned from up to down at some exact frame (a *press edge*
  — true for one frame only).
- The key transitioned from down to up at some exact frame (a *release
  edge* — true for one frame only).

The press edge is what starts the charge. The release edge is what fires
the charged shot. The held boolean is what accumulates charge time.

**Most shmup tutorials get this wrong.** They use only the held boolean,
which forces one of two design choices:

- Fire *while held* (continuous beam): fine, but you can't have a
  "release for big damage" shot.
- Fire *on the press* (tap fire): fine, but you can't have a hold-to-charge.

You need both. The press edge and release edge are the unlock.

## 2. The six attributes on the player

These belong on whatever object owns the firing (the player ship, the
weapon, an input component — pick what fits your architecture). They are
all the state you need; everything else is derived.

| attribute | type | meaning |
|---|---|---|
| `charging` | `bool` | is the charge key currently held? Set every frame from `keys[KEY]`. |
| `charge_pressed_this_frame` | `bool` | edge: True on the single frame the key went down. Cleared next frame. |
| `charge_released_this_frame` | `bool` | edge: True on the single frame the key went up. Cleared next frame. |
| `charge_time` | `float` | seconds the key has been held this press (0 when not held). |
| `charge_complete` | `bool` | `charge_time >= CHARGE_TIME_S[current_weapon]`. Cheap flag for "ready to release". |
| `last_charge_complete` | `bool` | snapshot of `charge_complete` taken BEFORE the `not charging` branch resets it. **Critical.** |

Why the snapshot? On the release frame, `charging` is already False
(because the player let go). The accumulator branch resets `charge_time`
and `charge_complete` to zero *before* your dispatch code can ask "did
they reach the threshold?". Without the snapshot, you can't fire a
charged shot on release — you'll only get "fire while held" or
"fire on press" again.

The kit's `ChargedShotState` class handles this for you. The order in
`update()` is non-negotiable:

```python
def update(self, dt, held, threshold):
    # 1. SNAPSHOT before any reset
    self.last_charge_complete = self.charge_complete
    # 2. Clear the edges (they live for one frame only)
    self.charge_pressed_this_frame = False
    self.charge_released_this_frame = False
    # 3. Accumulate or reset
    if held:
        self.charging = True
        if threshold is not None:
            self.charge_time += dt
            if threshold <= 0.0:
                self.charge_complete = True        # continuous weapons
            else:
                self.charge_complete = self.charge_time >= threshold
    else:
        self.charging = False
        self.charge_time = 0.0
        self.charge_complete = False
```

## 3. The four dispatch branches in your update loop

In order, every frame:

### Branch A — Tap fire (B key / mouse / etc.)

Your existing tap-fire logic, unchanged. Spawns the cheap bullet at the
weapon's cooldown rate.

### Branch B — Charge accumulation

The state machine above. Always runs. Doesn't fire anything by itself;
it just maintains `charge_time`, `charge_complete`, and the two edges.

### Branch C — Continuous-charge behavior (per weapon, while held)

For weapons that do something *while you hold* (beam, piercing stream):

```python
if state.charging and weapon.is_continuous_charge:
    if state.elapsed_since_last_spawn >= weapon.spawn_interval_s:
        spawn_projectile(weapon, muzzle_x, muzzle_y)
        state.elapsed_since_last_spawn = 0.0
```

Weapon 3 in Stellar Horizon is a piercing stream: every 1.5s of holding
SPACE, one piercing crystal spawns. The accumulator's `_extra_spawn_timer`
field handles the interval.

### Branch D — Release-fired behavior (per weapon, on release edge)

This is the actual "Megaman bolt" or "boomerang" path. The condition is
deliberately strict:

```python
if state.charge_released_this_frame and weapon.charges_on_release:
    threshold = weapon.charge_time_s
    # Use the snapshot, NOT the live charge_complete.
    if threshold is not None and threshold > 0.0 and state.last_charge_complete:
        spawn_charged_projectile(weapon, muzzle_x, muzzle_y, now)
        state.cooldown = 0.4   # short cooldown so the charged shot doesn't stack
```

The `>0.0` check excludes the "continuous" weapons (they have
`threshold=0.0` because charge_time doesn't gate them — they fire while
held, see Branch C).

## 4. The per-weapon table

This is the design lever. Each weapon in your game is one row:

| weapon | `charge_time_s` | behavior on hold | behavior on release |
|---|---|---|---|
| `weapon_basic` | `None` | (tap-fire only) | (no-op) |
| `weapon_beam` | `0.0` | continuous beam | end beam |
| `weapon_megaman` | `1.0` | (nothing) | spawn 1 big piercing disc |
| `weapon_boomerang` | `1.5` | (nothing) | spawn returning bullet |
| `weapon_pierce_stream` | `0.0` | spawn piercing every 1.5s | end stream |
| `weapon_rapid` | `None` | (tap-fire only) | (no-op) |

Three semantic categories:

- `None` = "this weapon has no charge behavior". SPACE is a no-op.
- `0.0` = "continuous while held". The charge time doesn't gate anything;
  the held boolean *is* the trigger.
- `>0.0` = "release-after-full-charge". Must hold to threshold, then
  release fires. This is the Megaman pattern.

A clean implementation is a frozen dataclass per weapon with a `kind`
enum (`NONE | CONTINUOUS | RELEASE`) and the threshold + spawn interval
fields. The kit doesn't ship a `Weapon` class because that depends on
your game's data model — copy the pattern, fill in your own fields.

## 5. The muzzle orb (visual feedback)

The player needs a *visible* cue that "I'm charging". The cheapest cue
that reads as "energy building up" is a 3-layer concentric circle at the
muzzle that grows with `charge_time`:

1. **Outer ring** — outline of a disc, weapon color. Always visible from
   `growth=0%` so the player has immediate feedback.
2. **Body** — filled disc, weapon color shifted toward a "plasma cyan"
   blend (~55% cyan + 45% weapon color). Appears at `growth >= 25%`.
3. **White hot core** — small filled disc, white. Appears at `growth >= 50%`.

Geometry (all in pixels):

```
ring_radius  = 3.0  + growth01 * (38.0 - 3.0)    # linear, 3 → 38
body_radius  = ring_radius * 0.78
core_radius  = ring_radius * 0.32
```

`growth01` is `min(1.0, charge_time / ramp_time_for_this_weapon)`. Each
weapon has its own `ramp_time_s` (the visual ramp, not the gameplay
threshold). Continuous weapons use a 0.5s ramp; discrete weapons use
their full charge time.

**Pulse at full charge**: when `growth01 >= 0.85` and the weapon is in
the `PULSE` set (continuous beam + all release-charge weapons), modulate
the alpha by `1.0 +/- 0.18 * sin(now * 8.0)`. The 8Hz pulse is the
"ready" feedback.

The orb is drawn each frame with `pygame.draw.circle` on a per-pixel
alpha surface (recreate the surface per frame — orb is small, the cost
is negligible). See `charged_shot_kit/orb.py:97-178` for the full
implementation.

## 6. The fired entity (the bullet, disc, or whatever)

A charged shot is usually **not** a normal bullet. It's typically larger,
slower, with multi-hit / fade / shockwave behavior. The cleanest pattern
is a dedicated entity class with its own FSM and its own pool:

```python
class ChargedBullet:
    # FSM states
    FLYING:  moving +X, counting hits, can still hit
    FADING:  stopped, alpha lerp 255→0, scale 1.0→1.3, no more hits

    def __init__(self):           # pre-allocated pool slot
        self.alive = False
        self.state = State.FLYING
        self.hit_count = 0
        # ... etc.

    def spawn(self, x, y, now):  # activate
        ...

    def update(self, dt):         # tick state machine
        ...

    def register_hit(self):       # called by collision handler
        ...

    def hits(self, target) -> bool:
        ...

    def hitbox(self) -> pygame.Rect:
        ...
```

Three transitions:

- `spawn` → `FLYING` (always, no fade on entry).
- `FLYING` → `FADING` when **either** `elapsed >= last_hit_settle_s` (miss
  timeout) **or** `hit_count >= MAX_HITS` (cap reached). The settle
  timer is what makes a piercing-through-4-enemies shot feel right:
  after the 4th hit, wait 0.4s of "no more hits" before fading.
- `FADING` → dead when `fade_elapsed >= FADE_DURATION_S` (0.4s default).
- Off-screen (`x > world_width + margin`) → dead instantly, no fade.

The pool size is small (2-4). The spawn logic in the dispatch branch
finds the first non-alive slot; if all are alive, the second spawn is a
silent no-op. **Don't queue** — that breaks the player's mental model of
"this is a powerful shot, not a machine gun".

## 7. Audio (the cheap version)

Three voices cover 90% of what you need:

1. **Hum** — loop a low triangle sweep while charging (200Hz → 800Hz
   over 1s, low volume 0.3).
2. **Release** — one-shot down-sweep on release (1200Hz → 200Hz over
   0.25s, medium volume 0.7).
3. **Hit** — noise burst on first impact, smaller noise pop on
   secondary impacts.

The kit's `examples/full_demo.py` does the hum and release with
`pygame.sndarray` + `numpy`-style array math, but you can do it cheaper
with `sine_wave = lambda f, t: sin(2*pi*f*t)` if you don't have numpy.

If you want to skip audio entirely, the visual orb is enough — the pulse
at full charge is the player's cue. Audio is a polish layer.

## 8. What to NOT do (pitfalls)

1. **Don't fire on the press edge.** That's tap-fire, not charge-fire.
2. **Don't check `charging` to decide if a release shot fires.** By the
   release frame, `charging` is already False. Use `last_charge_complete`
   (the snapshot).
3. **Don't queue pooled entities.** If the pool is full, the spawn is a
   silent no-op. The player has to wait; that's the cost of a powerful
   shot.
4. **Don't make `charge_time` persist across presses.** Reset to 0 every
   frame the key is up. Otherwise a quick tap-then-hold accumulates
   the tap's time.
5. **Don't tie the visual orb to the same threshold as the gameplay
   threshold.** Use a `ramp_time_s` for visuals (often 0.5s for
   continuous, the full threshold for discrete). The visual can finish
   "growing" before the gameplay says "ready to fire" — that's fine,
   the visual is decoration.
6. **Don't put the charged bullet in the normal bullet pool.** It's a
   different entity with different behavior. Give it its own pool of 2-4.

## 9. Porting checklist (in order)

1. Add the 6 attributes to your player (or weapon) class.
2. Wire the press / release edges from your input system
   (`on_charge_pressed()`, `on_charge_released()`).
3. Implement the `update()` order: snapshot, clear edges, accumulate-or-reset.
4. Pick a `CHARGE_TIME_S` value for each weapon that uses the mechanic.
5. Add Branch D (release-fired) dispatch.
6. Add the muzzle orb renderer (start with the outer ring only, add the
   body + core + pulse in passes).
7. Write a `ChargedBullet`-style entity for the release-time projectile.
8. Add the audio (hum + release at minimum).
9. Test: hold key 0.5x threshold → no release fire. Hold 1.5x → release
   fires. Quick tap → no release fire. Switch weapons mid-charge →
   charge resets.

The kit's tests cover #1, #2, #3, #6, and #7. Add your own for #4, #5,
and #9 once you've wired them into your game.
