# charged-shot-kit

> A drop-in, self-contained reference implementation of a
> Megaman-style charged-shot mechanic for any 2D shoot-em-up.
>
> Standalone. No dependencies on Stellar Horizon. Just `pygame` and
> the Python stdlib. No images, no audio files, no external assets.

## What's here

| File | Lines | Role |
|---|---|---|
| `DESIGN.md` | ~330 | The design doc. Read this first if you're porting. |
| `charged_shot_kit/state.py` | ~120 | `ChargedShotState` — the 6 attributes that drive the mechanic. |
| `charged_shot_kit/orb.py` | ~150 | `draw_charge_orb` — 3-layer procedural muzzle FX. |
| `charged_shot_kit/charged_bullet.py` | ~190 | `ChargedBullet` — FSM FLYING→FADING, pool, collision protocol. |
| `examples/full_demo.py` | ~330 | Runnable pygame demo with 3 weapons (tap / continuous beam / release disc). |
| `tests/test_state.py` | ~190 | Edges, accumulation, reset, the snapshot invariant. |
| `tests/test_orb.py` | ~110 | Layer activation thresholds, pulse modulation. |
| `tests/test_charged_bullet.py` | ~190 | FSM transitions, off-screen kill, damage model, pool pattern. |

Total: ~1,600 lines, including docstrings and tests.

## Quick start

### 1. Run the demo

```bash
pip install pygame
python examples/full_demo.py
```

The demo gives you a player ship (WASD to move) and 3 weapons
(switch with `1` / `2` / `3`):

- **Weapon 1 (BASIC)**: B = tap fire. SPACE is a no-op.
- **Weapon 2 (BEAM)**: B = tap fire. SPACE held = continuous beam.
- **Weapon 3 (MEGAMAN)**: B = tap fire. SPACE held + release = piercing disc.

The 3-layer muzzle orb appears on weapons 2 and 3 while SPACE is held.
A charge bar at the top-left shows the charge progress on weapon 3.
Release at full charge (≥1.0s) to fire a piercing disc that hits up to
4 enemies (8× first, 3× secondary) and fades over 0.4s.

### 2. Read the design doc

Open `DESIGN.md`. It covers the mental model, the state attributes,
the 4 dispatch branches, the per-weapon table, the visual layers,
the FSM, the audio, the pitfalls, and a porting checklist.

### 3. Drop the kit into your game

```python
from charged_shot_kit import (
    ChargedShotState,
    draw_charge_orb,
    ChargedBullet,
)
```

Wire the 6 attributes into your player (or weapon), call `update()`
once per frame, then read `charge_released_this_frame` and
`last_charge_complete` in your dispatch branch. The rest is style.

## Tests

```bash
python -m pytest tests/ -v
```

All tests run headless (no display required) — `tests/conftest.py`
sets `SDL_VIDEODRIVER=dummy`.

## License

Public domain. Use however you want. Attribution appreciated but not
required.
