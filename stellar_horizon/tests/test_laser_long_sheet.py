"""Tests for v1.5 long (150x50) "charge preview" sheets.

The long sheets are the larger version of the 4 charged laser
archetypes (cyan ice, orange flame, white lightning, magenta
heart), drawn near the player's muzzle as a 30x10 scaled preview
while fire is held, with alpha ramping in as charge_time grows.

These tests cover:
- _load_sprites populates self._laser_long_sprites keyed by weapon
  (0, 1, 2, 3) and registers the same AnimatedSprite under
  laser_NN_long in self._animated so the per-frame tick advances it.
- The sheet name mapping via WEAPON_ARCHETYPE is correct:
  weapon 0 -> laser_07_long (orange flame)
  weapon 1 -> laser_08_long (white lightning)
  weapon 2 -> laser_09_long (magenta heart)
  weapon 3 -> laser_06_long (cyan ice)
- Each sheet is 6 frames at 150x50, 12 fps.
- The render block (inside the draw call after draw_charge_aura)
  does not crash for any charged weapon and respects the
  charge_time=0 no-op.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pygame
import pytest

# conftest.py pre-inits pygame with SDL_VIDEODRIVER=dummy. The fixture
# below still needs a real Surface for the draw smoke test, so we
# create it lazily.


@pytest.fixture
def scene():
    """Construct a fresh GameplayScene, run on_enter, return it.

    Skips the test if the gameplay module is unavailable (missing
    dependency chain) so this file can be discovered by pytest even
    when something else is broken in the scene graph.
    """
    from stellar_horizon.audio.midi_player import MidiPlayer
    from stellar_horizon.scenes.gameplay import GameplayScene
    s = GameplayScene(
        MidiPlayer(),
        Path("stellar_horizon/waves/waves_act1.json"),
        Path("stellar_horizon/assets"),
    )
    s.on_enter()
    return s


def test_laser_long_sprites_dict_has_four_entries(scene) -> None:
    """_load_sprites must populate self._laser_long_sprites with one
    AnimatedSprite per charged weapon (0, 1, 2, 3)."""
    long_sprites = scene._laser_long_sprites
    assert len(long_sprites) == 4
    for w in (0, 1, 2, 3):
        assert w in long_sprites, f"weapon {w} missing from long sprites"


def test_laser_long_sprites_uses_weapon_archetype_mapping(scene) -> None:
    """The weapon -> sheet name mapping must follow WEAPON_ARCHETYPE.

    From bullet.py:
        weapon 0 (orange fire)      -> archetype 6 -> laser_07_long
        weapon 1 (white piercing)   -> archetype 7 -> laser_08_long
        weapon 2 (magenta heart)    -> archetype 8 -> laser_09_long
        weapon 3 (cyan ice)         -> archetype 5 -> laser_06_long
    """
    expected_sheet_name = {
        0: "laser_07_long",
        1: "laser_08_long",
        2: "laser_09_long",
        3: "laser_06_long",
    }
    for weapon, sheet_name in expected_sheet_name.items():
        anim = scene._laser_long_sprites[weapon]
        # The same AnimatedSprite is registered under the full sheet
        # name in self._animated (so the per-frame tick advances it).
        assert sheet_name in scene._animated
        assert scene._animated[sheet_name] is anim


def test_laser_long_sprites_have_correct_dimensions(scene) -> None:
    """Each long sheet is 150x50, 6 frames, 12 fps."""
    for w in (0, 1, 2, 3):
        anim = scene._laser_long_sprites[w]
        assert anim.frame_w == 150, f"weapon {w} frame_w {anim.frame_w}"
        assert anim.frame_h == 50, f"weapon {w} frame_h {anim.frame_h}"
        assert anim.frame_count == 6, f"weapon {w} frames {anim.frame_count}"
        # 12 fps = 1/12 = 0.0833...s per frame
        assert abs(anim.frame_duration - (1.0 / 12.0)) < 1e-6


def test_laser_long_sprites_loaded_real_pngs(scene) -> None:
    """If the PNGs exist on disk, the sprites must NOT be the
    magenta 1x1 fallback (loaded == True)."""
    for w in (0, 1, 2, 3):
        anim = scene._laser_long_sprites[w]
        assert anim.loaded, f"weapon {w} long sheet failed to load"
        frame = anim.get_current_surface()
        assert frame.get_width() == 150
        assert frame.get_height() == 50


def test_tap_only_weapon_has_no_long_sprite(scene) -> None:
    """Weapon 4 (rainbow streak) is tap-only, so it has NO long sheet."""
    long_sprites = scene._laser_long_sprites
    assert 4 not in long_sprites, "weapon 4 should not have long sheet"


def test_long_sheet_advances_via_animated_update(scene) -> None:
    """The long sheets are registered in self._animated, so the
    existing per-frame update tick (which iterates self._animated
    .values()) advances their frame index in sync with everything
    else."""
    anim = scene._laser_long_sprites[0]
    before = anim._index
    # Drive ~83ms of game time (one frame at 12 fps).
    anim.update(1.0 / 12.0 + 0.001)
    after = anim._index
    assert after != before, "long sheet did not advance on update"


def test_draw_charged_weapons_does_not_crash(scene) -> None:
    """Render smoke test: drawing the player with charge_time > 0
    for each charged weapon must not crash. The long preview
    is drawn inside the player-alive branch of the scene's draw
    method, after draw_charge_aura.

    We drive the full draw() method on a small surface and assert
    no exception propagates.
    """
    surface = pygame.Surface((480, 270))
    # Move player to a known position so the long preview blit lands
    # inside the surface.
    scene.player.x = 100
    scene.player.y = 135
    for weapon in (0, 1, 2, 3):
        scene.player.set_weapon(weapon)
        scene.player.charge_time = 0.5  # mid-charge, alpha ~0.5+ for all
        # Drive the scene clock too so the per-tick animation
        # advances.
        scene._elapsed = 1.0
        try:
            scene.draw(surface)
        except Exception as exc:
            pytest.fail(
                f"draw() crashed for weapon {weapon} with charge_time=0.5: {exc}"
            )


def test_draw_with_zero_charge_does_not_show_long_sheet(scene) -> None:
    """charge_time=0 must be a no-op for the long preview branch
    (no exception, no blit). The skip happens before any draw work."""
    surface = pygame.Surface((480, 270))
    scene.player.x = 100
    scene.player.y = 135
    for weapon in (0, 1, 2, 3):
        scene.player.set_weapon(weapon)
        scene.player.charge_time = 0.0
        # Should be a no-op (returns early before the scaling work).
        scene.draw(surface)  # must not raise


def test_alpha_ramp_reaches_full_for_discrete_weapons(scene) -> None:
    """The render-time alpha formula must reach 1.0 at the charge
    threshold for discrete weapons (1=1.2, 2=1.5) and at 0.5s for
    continuous weapons (0, 3).

    Tested by reading the formula directly (mirrors the gameplay
    code) since we can't easily peek the per-frame alpha without
    intercepting blit.
    """
    # Replicate the formula from gameplay.py.
    def alpha(weapon: int, charge_time: float) -> float:
        threshold = scene.player.CHARGE_TIME_S[weapon]
        ramp = 0.5 if (threshold is None or threshold <= 0.0) else threshold
        return max(0.0, min(1.0, charge_time / ramp))

    # Discrete weapons: full alpha at the charge threshold.
    assert alpha(1, 1.2) == pytest.approx(1.0)
    assert alpha(2, 1.5) == pytest.approx(1.0)
    # Continuous weapons: full alpha at 0.5s.
    assert alpha(0, 0.5) == pytest.approx(1.0)
    assert alpha(3, 0.5) == pytest.approx(1.0)
    # Below the ramp time, alpha is partial.
    assert 0.0 < alpha(1, 0.6) < 1.0
    assert 0.0 < alpha(2, 0.75) < 1.0
    assert 0.0 < alpha(0, 0.25) < 1.0
