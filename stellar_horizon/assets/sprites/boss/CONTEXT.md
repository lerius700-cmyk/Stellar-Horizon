# boss/ — 6 boss states

## Contents

| File | Notes |
|---|---|
| `boss_idle_v1.png` + `_sheet.png` | Default idle (used most of the time) |
| `boss_telegraph_v1.png` + `_sheet.png` | Telegraph (warning before an attack) |
| `boss_charge_v1.png` + `_sheet.png` | Charge (winding up for a big attack) |
| `boss_dying_v1.png` + `_sheet.png` | Death sequence |
| `boss_alternate_a_v1.png` + `_sheet.png` | Alternate pattern A |
| `boss_alternate_b_v1.png` + `_sheet.png` | Alternate pattern B |

All boss states are 72×72, 10 frames at 8 fps.

## Cross-references

- `stellar_horizon/entities/boss.py` — Boss class.
- `stellar_horizon/scenes/gameplay.py:_draw_boss_sprite` — picks the
  right state sheet based on `boss.phase + boss.action`. Viewport clip
  is applied here too (the boss can be 80×80 native but we shrunk it 10%
  for playfield space; the clip ensures partial off-screen rendering).

## State machine

```
IDLE -> TELEGRAPH -> CHARGE -> IDLE  (loop)
       TELEGRAPH -> IDLE              (cancel)
IDLE -> DYING                         (terminal)
```

`alternate_a` and `alternate_b` are special attack patterns triggered
by the wave manager; they replace TELEGRAPH+CHARGE for those attacks.
