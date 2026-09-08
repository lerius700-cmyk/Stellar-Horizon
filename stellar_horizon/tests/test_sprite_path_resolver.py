"""Unit tests for GameplayScene._sprite_path() resolver.

Spec: docs/superpowers/specs/2026-09-08-visual-polish-v3-design.md section 4.
"""
from __future__ import annotations

import pytest
from pathlib import Path

from stellar_horizon.scenes.gameplay import GameplayScene


@pytest.fixture
def scene():
    """Construct a GameplayScene with a mocked assets_dir.

    We do NOT call on_enter() — this avoids pygame display + audio init.
    The resolver only needs assets_dir.
    """
    s = GameplayScene.__new__(GameplayScene)
    s.assets_dir = Path("D:/AI/stellar-horizon/stellar_horizon/assets")
    return s


def test_resolves_boss_name(scene):
    p = scene._sprite_path("boss_idle_v1")
    assert p == scene.assets_dir / "sprites" / "boss" / "boss_idle_v1_sheet.png"


def test_resolves_player_name(scene):
    p = scene._sprite_path("player_v1")
    assert p == scene.assets_dir / "sprites" / "player" / "player_v1_sheet.png"


def test_resolves_player_thrust(scene):
    p = scene._sprite_path("player_thrust_v1")
    assert p == scene.assets_dir / "sprites" / "player" / "player_thrust_v1_sheet.png"


def test_resolves_enemy_with_kind_subfolder(scene):
    p = scene._sprite_path("enemy_scout_v1")
    assert p == scene.assets_dir / "sprites" / "enemies" / "scout" / "enemy_scout_v1_sheet.png"
    p = scene._sprite_path("enemy_heavy_attack_v1")
    assert p == scene.assets_dir / "sprites" / "enemies" / "heavy" / "enemy_heavy_attack_v1_sheet.png"
    p = scene._sprite_path("enemy_kamikaze_v1_v2")
    assert p == scene.assets_dir / "sprites" / "enemies" / "kamikaze" / "enemy_kamikaze_v1_v2_sheet.png"


def test_resolves_laser_name(scene):
    # 2026-09-08 v1.5: 9 laser sheets (laser_01..laser_09), not just 5.
    for i in range(1, 10):
        p = scene._sprite_path(f"laser_{i:02d}")
        assert p == scene.assets_dir / "sprites" / "bullets" / f"laser_{i:02d}_sheet.png"


def test_resolves_legacy_bullets(scene):
    p = scene._sprite_path("player_bullet")
    assert p == scene.assets_dir / "sprites" / "bullets" / "player_bullet_sheet.png"
    p = scene._sprite_path("enemy_bullet")
    assert p == scene.assets_dir / "sprites" / "bullets" / "enemy_bullet_sheet.png"


def test_unknown_prefix_raises_value_error(scene):
    with pytest.raises(ValueError, match="unknown sprite name"):
        scene._sprite_path("xyz_unknown_thing")


def test_malformed_enemy_name_raises_value_error(scene):
    # "enemy_" alone has no kind, no variant. Used to raise IndexError
    # from name.split("_")[1]; should raise ValueError instead.
    with pytest.raises(ValueError, match="malformed enemy name"):
        scene._sprite_path("enemy_")
