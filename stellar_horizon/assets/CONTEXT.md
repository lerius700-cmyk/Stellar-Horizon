# Stellar Horizon — Assets "Mapa de Piso"

> **For agentic workers:** This is the entry point for the `stellar_horizon/assets/`
> area. Read this first when working on art, sprites, or any binary asset.

## TL;DR

The `assets/` folder holds the binary game data: sprite sheets, backgrounds,
MIDI music. All sprite sheets are loaded by `GameplayScene._load_sprites()` in
`stellar_horizon/scenes/gameplay.py`, which uses a prefix-based resolver
`self._sprite_path(name)` to map a sprite name to its file path.

## Layout

```
assets/
├── CONTEXT.md                 ← you are here
├── backgrounds/               ← bg_*.png, parallax layers
├── midi/                      ← *.mid music files
└── sprites/                   ← all animated sheets
    ├── CONTEXT.md             ← naming conventions, dims, frame counts
    ├── bullets/               ← 5 laser archetypes + 2 legacy bullets
    ├── player/                ← 5 player variants + 1 thrust
    ├── enemies/               ← 6 kinds (scout, cruiser, heavy, bomber, ufo, kamikaze)
    ├── boss/                  ← 6 states (idle, telegraph, charge, dying, alt_a, alt_b)
    └── _deprecated/           ← files no longer loaded; do not delete
```

## Loader entry point

- `stellar_horizon/scenes/gameplay.py:170 _load_sprites()` — loads the whole
  animated cache.
- `stellar_horizon/scenes/gameplay.py:_sprite_path()` — prefix-based resolver.
  See `sprites/CONTEXT.md` for the naming convention.
- `StellarHorizon.spec:8` — PyInstaller globs the entire `assets/` tree. No
  change needed when adding new sub-folders.

## Adding new assets

1. Place the PNG in the appropriate sub-folder (`bullets/`, `player/`,
   `enemies/{kind}/`, `boss/`). If you don't know where, see the
   `sprites/CONTEXT.md` naming convention.
2. If the new asset represents a new kind or category, update the loader
   code in `gameplay.py` (add to `animated_names` or similar) AND the
   relevant sub-folder's `CONTEXT.md`.
3. If the new asset replaces an old one, move the old one to
   `_deprecated/` with a brief note in `_deprecated/CONTEXT.md`.
4. Run the test suite: `pytest stellar_horizon/tests/ -q`.

## Cross-references

- Game scenes: `stellar_horizon/scenes/` (uses `_animated[name]` to draw).
- Sprite animator: `stellar_horizon/ui/animated_sprite.py` (AnimatedSprite
  class, frame timing).
- VFX params: `stellar_horizon/fx/bullet_vfx.py` (per-weapon visual identity).
- Spec: `docs/superpowers/specs/2026-09-08-visual-polish-v3-design.md`.
- Plan: `docs/superpowers/plans/2026-09-08-visual-polish-v3.md`.

## Deprecated

See `sprites/_deprecated/CONTEXT.md` for the list of files that are no
longer loaded but kept on disk for reference.
