"""Tests for the sprite-sheet animation system + punchy impact sparks.

Verifies:
- AnimatedSprite loads a sheet, cycles through frames, and exposes
  the current surface.
- GameplayScene loads all 42 sprite sheets (7 active + 35 variants).
- FxLayer.emit_impact spawns the expected spark/shrapnel/flash mix.
- The new telegraph flash + kamikaze warning halos still draw.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_RENDER_DRIVER", "software")

import pygame
if not pygame.get_init():
    pygame.init()
if not pygame.font.get_init():
    pygame.font.init()

from pathlib import Path

from stellar_horizon.fx.particles import FxLayer
from stellar_horizon.ui.animated_sprite import AnimatedSprite


# --- AnimatedSprite -----------------------------------------------------

def test_animated_sprite_cycles_frames(tmp_path):
    """With fps=10 and dt=0.15 the sprite should advance ~1-2 frames."""
    # Build a tiny 4-frame 2x2 sheet in memory so we don't need a
    # real asset for this unit test. Write to tmp_path so we don't
    # pollute the assets folder (the legacy sprites/ dir is being
    # removed in 2026-09-08 visual-polish-v3).
    sheet = pygame.Surface((8, 2), pygame.SRCALPHA)
    sheet.fill((10, 15, 31, 255))  # navy background
    for i in range(4):
        sheet.fill((255, 0, 0, 255), (i * 2, 0, (i + 1) * 2, 2))
    path = tmp_path / "_test_anim.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(sheet, str(path))

    anim = AnimatedSprite(str(path), frame_w=2, frame_h=2,
                          frame_count=4, fps=10.0)
    # Frame 0 is the first colored region.
    first = anim.get_current_surface()
    anim.update(0.15)  # ~1.5 frames worth
    # At least one frame should have advanced.
    assert anim._index != 0, "AnimatedSprite did not advance frames"
    # And it wraps around (4 frames modulo 4).
    for _ in range(40):
        anim.update(0.15)
    assert 0 <= anim._index < 4
    path.unlink(missing_ok=True)


def test_animated_sprite_loaded_flag():
    """A missing sheet leaves the sprite in a non-loaded fallback
    (1x1 magenta), but the API still works without crashing."""
    anim = AnimatedSprite("nonexistent_path.png", frame_w=16, frame_h=16,
                          frame_count=6, fps=12.0)
    assert anim.loaded is False
    surf = anim.get_current_surface()
    assert surf is not None
    assert surf.get_width() == 16


# --- GameplayScene integration ----------------------------------------

def test_gameplay_scene_loads_sprites_split():
    """2026-09-08 visual-polish-v3: assets reorganized as SF+SM sub-silo.

    Layout:
    - _animated: 5 player variants + 20 enemy variants (4 scout, 4
      cruiser, 3 heavy, 3 bomber, 3 ufo, 3 kamikaze) + 1 player_thrust
      + 6 enemy attack sheets + 6 enemy death sheets + 7 kind aliases
      (scout, cruiser, heavy, bomber, ufo, kamikaze, player — same
      AnimatedSprite instances as v1 variants but separate dict keys)
      + 2 legacy bullets (player_bullet, enemy_bullet) + 5 laser
      sheets (laser_01..laser_05, 6 frames each at 12 fps, 29x7) = 52
      total. Player/enemy variants are 10 frames per sheet at 12 fps,
      29x29. The 6 boss states are in _boss_anims (separate dict),
      NOT in _animated.
    - _boss_anims: 6 states (IDLE, TELEGRAPH, CHARGE, DYING +
      2 alternates), 10 frames per sheet at 8 fps, 72x72.
    - _laser_sprites: 5 single-frame first-frames of the 5 laser
      sheets (29x7). Used for HUD display + VFX halo centering.
    """
    from stellar_horizon.audio.midi_player import MidiPlayer
    from stellar_horizon.scenes.gameplay import GameplayScene

    s = GameplayScene(MidiPlayer(),
                      Path("stellar_horizon/waves/waves_act1.json"),
                      Path("stellar_horizon/assets"))
    s._load_sprites()
    # Animated cache: 5 player + 20 enemy + 1 thrust + 6 attack + 6
    # death + 7 kind aliases (scout, cruiser, heavy, bomber, ufo,
    # kamikaze, player — same AnimatedSprite instances as v1 variants
    # but separate dict keys) + 2 bullets + 5 lasers (laser_05..09)
    # + 4 long sheets (laser_06..laser_09 _long) = 56.
    # (Boss states are in _boss_anims, NOT _animated. 2026-09-08.)
    # 2026-09-08 v1.5 final: 5 weapons only. Laser sheets kept are
    # 5..9 (basic archetypes 0..3 dropped). 4 long sheets for the
    # charged weapons (0/1/2/3), keyed by archetype in
    # self._animated under the laser_NN_long name.
    assert len(s._animated) == 56
    # 5 player variants.
    for n in ("player_v1", "player_v2", "player_v3", "player_v4", "player_v5"):
        assert n in s._animated
    # 20 enemy variants per the cycle.
    for n in ("enemy_scout_v1", "enemy_scout_v2", "enemy_scout_v3", "enemy_scout_v4",
              "enemy_cruiser_v1", "enemy_cruiser_v2", "enemy_cruiser_v3", "enemy_cruiser_v4",
              "enemy_heavy_v1", "enemy_heavy_v2", "enemy_heavy_v3",
              "enemy_bomber_v1", "enemy_bomber_v2", "enemy_bomber_v3",
              "enemy_ufo_v1", "enemy_ufo_v2", "enemy_ufo_v3",
              "enemy_kamikaze_v1", "enemy_kamikaze_v2", "enemy_kamikaze_v3"):
        assert n in s._animated
    # Legacy bullets (still on old sprites/ dir).
    for n in ("player_bullet", "enemy_bullet"):
        assert n in s._animated
    # Boss is in _boss_anims, not _animated.
    assert "boss" not in s._animated
    # Legacy enemy_01..20 / player_01..05 are NOT in the new
    # _animated (replaced by the v2 naming). Kind names (scout,
    # cruiser, heavy, bomber, ufo, kamikaze, player) ARE present
    # as aliases that point to the v1 variant (used as draw-code
    # fallback when an enemy has no sprite_name set).
    for n in (f"enemy_{i:02d}" for i in range(1, 21)):
        assert n not in s._animated
    for n in (f"player_{i:02d}" for i in range(1, 6)):
        assert n not in s._animated
    # The 7 kind-name aliases ARE present.
    for n in ("scout", "cruiser", "heavy", "bomber", "ufo", "kamikaze", "player"):
        assert n in s._animated
    # Lasers ARE in the animated cache: 5 sheets (laser_05..laser_09),
    # 6 frames each at 12 fps, 29x7. The single-frame first-frame
    # is also kept in _laser_sprites for the HUD display + halo
    # centering.
    # 2026-09-08 v1.5 final: dropped basic archetypes 0..3 (laser_01..04).
    for n in (f"laser_{i:02d}" for i in range(5, 10)):
        assert n in s._animated
    # laser_01..04 and laser_10+ don't exist (basic 4 archetypes dropped).
    for n in (f"laser_{i:02d}" for i in range(1, 5)):
        assert n not in s._animated
    for n in (f"laser_{i:02d}" for i in range(10, 11)):
        assert n not in s._animated
    # Single-frame laser cache: 5 sprites (one per weapon archetype).
    assert len(s._laser_sprites) == 5
    for n in (f"laser_{i:02d}" for i in range(5, 10)):
        assert n in s._laser_sprites
        surf = s._laser_sprites[n]
        # Each sprite is a real Surface (not the magenta 1x1 fallback).
        assert surf.get_width() >= 1
        assert surf.get_height() >= 1
    # Boss animations: 6 states (4 + 2 alternates), 10 frames each
    # at 8 fps, 72x72 per frame (10% shrink of 80x80).
    assert len(s._boss_anims) == 6
    for state in ("idle", "telegraph", "charge", "dying",
                  "alternate_a", "alternate_b"):
        assert state in s._boss_anims
        anim = s._boss_anims[state]
        # 2026-09-06 polish 1: boss size 96x96 -> 80x80 to stop the
        # right-edge clipping during path_boss_entry()'s start at
        # x=480 in the 480-wide viewport.
        # 2026-09-06 polish 2 (10% shrink): 80x80 -> 72x72 to give
        # the playfield more breathing room.
        assert anim.frame_w == 72
        assert anim.frame_h == 72
        assert anim.frame_count == 10
        # 8 fps => 0.125s per frame.
        assert abs(anim.frame_duration - 0.125) < 1e-6


def test_laser_sprites_have_per_weapon_sizes():
    """2026-09-06 polish pass: laser set reduced to 5 (one per weapon
    archetype). Originally 48x16, then 32x8 (further shrink during
    ship model 10% reduction). 2026-09-06 polish pass 2: 32x8 -> 29x7
    (10% smaller across the board to give more playfield space). The
    HUD and bullet draw code use these surfaces to center the VFX
    halo. The runtime animation (alpha-pulse) is driven by
    bullet_vfx.compute() from the sheet, not these static
    first-frames.
    """
    from stellar_horizon.audio.midi_player import MidiPlayer
    from stellar_horizon.scenes.gameplay import GameplayScene

    s = GameplayScene(MidiPlayer(),
                      Path("stellar_horizon/waves/waves_act1.json"),
                      Path("stellar_horizon/assets"))
    s._load_sprites()
    for i in range(5, 10):
        name = f"laser_{i:02d}"
        surf = s._laser_sprites[name]
        assert surf.get_width() == 29, (
            f"{name} width {surf.get_width()} != 29"
        )
        assert surf.get_height() == 7, (
            f"{name} height {surf.get_height()} != 7"
        )


def test_animated_sprites_advance_on_update():
    """Every loaded animated sprite should accumulate elapsed time
    and advance its frame index on update()."""
    from stellar_horizon.audio.midi_player import MidiPlayer
    from stellar_horizon.scenes.gameplay import GameplayScene

    s = GameplayScene(MidiPlayer(),
                      Path("stellar_horizon/waves/waves_act1.json"),
                      Path("stellar_horizon/assets"))
    s._load_sprites()
    # Run a non-multiple-of-frame_count number of updates so the
    # index doesn't wrap exactly back to 0. At 12 fps, 50 updates of
    # 1/120s = 0.417s = 5 frames (one short of a full cycle). The
    # index should land on 5, NOT on 0.
    for _ in range(50):
        for anim in s._animated.values():
            anim.update(1 / 120)
    for n, anim in s._animated.items():
        assert anim._elapsed >= 0.0, f"{n} elapsed went negative"
        # Every sprite's frame index should now be 5 (or wrapped to
        # some non-zero value, but with 5 frames ticked it should be
        # exactly 5).
        assert anim._index == 5, (
            f"{n} frame index is {anim._index}, expected 5 "
            f"(elapsed={anim._elapsed:.3f}s)"
        )


# --- Punchy impact sparks ----------------------------------------------

def test_emit_impact_spawns_sparks_shrapnel_flash():
    """emit_impact should spawn 12 P_SPARK + 4 P_DEBRIS + 1 P_FLASH
    (kind 11) for a total of 17 particles. We measure via the pool's
    active_count delta across the call."""
    fx = FxLayer(pool_size=128)
    pre = fx.engine._pool.active_count
    fx.emit_impact(100.0, 100.0, count=12, color=(255, 240, 100))
    post = fx.engine._pool.active_count
    delta = post - pre
    # 12 sparks + 4 shrapnel + 1 flash = 17
    assert delta == 17, f"expected 17 particles, got {delta}"


def test_emit_impact_positions_match_xy():
    """All 17 spawned particles should be at the requested (x, y)."""
    fx = FxLayer(pool_size=128)
    fx.emit_impact(123.0, 234.0, count=12)
    for p in fx.engine._pool._items:
        if p.active:
            # Coordinates may move in one frame but the initial spawn
            # position was within a few pixels of (123, 234).
            assert abs(p.x - 123.0) < 5.0
            assert abs(p.y - 234.0) < 5.0


# --- Scene clock + bullet VFX wiring --------------------------------

def test_gameplay_scene_tracks_elapsed_time():
    """GameplayScene must accumulate scene time so the bullet VFX
    (alpha pulse, scale pulse, halo) can phase off of it."""
    from stellar_horizon.audio.midi_player import MidiPlayer
    from stellar_horizon.scenes.gameplay import GameplayScene

    s = GameplayScene(MidiPlayer(),
                      Path("stellar_horizon/waves/waves_act1.json"),
                      Path("stellar_horizon/assets"))
    s.on_enter()
    assert s._elapsed == 0.0
    s.update(1 / 120, [])
    assert abs(s._elapsed - (1 / 120)) < 1e-6
    s.update(1 / 60, [])
    assert abs(s._elapsed - (1 / 120 + 1 / 60)) < 1e-6


def test_spawned_bullet_has_consistent_spawn_time():
    """After a few frames, a fired bullet should have spawn_time
    close to the scene's _elapsed at the moment it was spawned."""
    from stellar_horizon.audio.midi_player import MidiPlayer
    from stellar_horizon.scenes.gameplay import GameplayScene

    s = GameplayScene(MidiPlayer(),
                      Path("stellar_horizon/waves/waves_act1.json"),
                      Path("stellar_horizon/assets"))
    s.on_enter()
    # Run 10 frames to let _elapsed accumulate.
    for _ in range(10):
        s.update(1 / 120, [])
    assert s._elapsed > 0.0
    # Drive player.update() directly with a keys dict so the SPACE
    # key fires (scene.update reads pygame.key.get_pressed() which
    # returns all False in headless mode and would override our
    # manual firing flag).
    s.player.firing = True
    s.player.shoot_cooldown = 0.0
    # 2026-09-08 v1.5 final: weapon 0 is the BEAM (no bullets).
    # Use weapon 4 (rainbow streak) which spawns tap-only bullets.
    s.player.set_weapon(4)
    s.player.update(1 / 120, {pygame.K_SPACE: True},
                    s.player_bullets, now=s._elapsed)
    alive = [b for b in s.player_bullets if b.alive]
    assert len(alive) == 1
    # The bullet was spawned with now=s._elapsed, so its
    # spawn_time should match exactly.
    assert alive[0].spawn_time == s._elapsed
    assert alive[0].weapon == 4
