"""Regression test: laser long sheets must NOT be loaded in v1.6.

2026-09-08 v1.6: the 4 long sheets (laser_06..laser_09 _long_sheet.png)
were generated for v1.5 as a 'charge preview' sprite. The v1.6
redesign replaces that with a procedural ShipChargeOrb at the muzzle.
The 4 PNGs are kept on disk (per the user's decision) but the
_gameplay_ layer no longer loads them.

This test verifies the regression contract:
  - scene._laser_long_sprites is empty / absent (no AnimatedSprite
    wrapping the long sheets).
  - The long sheet names (laser_06_long, laser_07_long, ...) are NOT
    in scene._animated.
  - _load_sprites does not raise when called.
"""
from __future__ import annotations

from pathlib import Path


def _make_scene():
    from stellar_horizon.audio.midi_player import MidiPlayer
    from stellar_horizon.scenes.gameplay import GameplayScene
    s = GameplayScene(
        MidiPlayer(),
        Path("stellar_horizon/waves/waves_act1.json"),
        Path("stellar_horizon/assets"),
    )
    s.on_enter()
    return s


def test_long_sprites_dict_is_empty() -> None:
    s = _make_scene()
    # 2026-09-08 v1.6: _laser_long_sprites was removed. The
    # attribute may not exist at all, or be an empty dict.
    long_sprites = getattr(s, "_laser_long_sprites", {})
    assert not long_sprites, (
        f"_laser_long_sprites should be empty/absent, got {long_sprites!r}"
    )


def test_long_sheet_names_not_in_animated() -> None:
    s = _make_scene()
    # The 4 long sheet names should NOT be in self._animated.
    for n in ("laser_06_long", "laser_07_long", "laser_08_long",
             "laser_09_long"):
        assert n not in s._animated, (
            f"{n} should not be loaded -- v1.6 uses ShipChargeOrb"
        )


def test_long_sheets_remain_on_disk() -> None:
    # Sanity: the 4 PNGs are still on disk (per the user's decision
    # to keep them). This guards against accidental deletion.
    bullets_dir = Path("stellar_horizon/assets/sprites/bullets")
    for fname in ("laser_06_long_sheet.png", "laser_07_long_sheet.png",
                  "laser_08_long_sheet.png", "laser_09_long_sheet.png"):
        path = bullets_dir / fname
        assert path.exists(), f"{path} should still exist on disk"
        assert path.stat().st_size > 0, f"{path} should be non-empty"
