# stellar_horizon/tests/test_destruction_render.py
"""Tests for the destruction animation FxLayer surface.
"""
from __future__ import annotations


def test_fxlayer_emit_smoke_creates_p_smoke_particle():
    # FxLayer.emit_smoke(x, y) should add a P_SMOKE particle
    # to its internal particle list. We construct an FxLayer
    # directly (no display needed) and verify the count goes
    # up after emission.
    from stellar_horizon.fx.particles import FxLayer
    from stellar_horizon._systems.systems.particle_engine import P_SMOKE

    fx = FxLayer()
    initial_count = sum(1 for p in fx.particles if p.kind == P_SMOKE)
    fx.emit_smoke(100.0, 50.0)
    new_count = sum(1 for p in fx.particles if p.kind == P_SMOKE)
    assert new_count == initial_count + 1, (
        f"expected 1 new P_SMOKE particle, got {new_count - initial_count}"
    )


def test_fxlayer_emit_smoke_overrides_color_to_gray():
    # The destruction-fall smoke should be gray (180, 180, 180)
    # to read as a smoke trail, not the engine-default (120, 120, 140)
    # which is the explosion-smoke color.
    from stellar_horizon.fx.particles import FxLayer
    from stellar_horizon._systems.systems.particle_engine import P_SMOKE

    fx = FxLayer()
    fx.emit_smoke(100.0, 50.0)
    smokes = [p for p in fx.particles if p.kind == P_SMOKE]
    assert len(smokes) == 1
    p = smokes[0]
    assert p.x == 100.0
    assert p.y == 50.0
    assert p.color == (180, 180, 180), (
        f"emit_smoke should override color to gray, got {p.color}"
    )


def test_destruction_render_produces_visible_ship_after_burst():
    # 2026-09-06 destruction-fall: after the 0.15s death
    # burst, the rendered frame should show the ship's IDLE
    # sprite (not the death sheet) at the enemy's current
    # position. To validate that _draw_enemy_sprite is
    # actually consulting e.current_dying_sheet() (not just
    # hardcoding enemy_{kind}_death_v1), we monkey-patch
    # the method to return a sentinel sprite name and
    # verify the sentinel pixels appear in the rendered
    # frame. Pre-fix: the sentinel is ignored and the
    # death sheet is drawn; the sentinel pixels are
    # missing. Post-fix: the sentinel is drawn.
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    from pathlib import Path
    from stellar_horizon.audio.midi_player import MidiPlayer
    from stellar_horizon.entities.enemy import Enemy
    from stellar_horizon.entities.player import Player
    from stellar_horizon.scenes.gameplay import GameplayScene
    from stellar_horizon.ui.backgrounds import Background
    from stellar_horizon.waves.wave_manager import WaveManager

    pygame.init()
    try:
        s = GameplayScene(
            MidiPlayer(),
            Path("stellar_horizon/waves/waves_act1.json"),
            Path("stellar_horizon/assets"),
        )
        s._load_sprites()
        # Bridge: GameplayScene.__init__ leaves self.background = None,
        # self.player = None, and self.wave_manager = None (all set in
        # on_enter()). The brief's test only calls _load_sprites(), so
        # without these inits the draw path crashes (background.draw,
        # player.alive) or skips the enemy (wave_manager guard at
        # gameplay.py:628) before the pixel check can run. Initialize
        # real instances: Background, Player (parked off-screen so it
        # doesn't contribute to the count), and a WaveManager that
        # holds the dying enemy in spawned_enemies for the draw loop.
        s.background = Background(
            Path("stellar_horizon/assets/backgrounds/act1_asteroid_belt.png")
        )
        s.player = Player(pygame.Rect(0, 0, 480, 270))
        s.player.x = -100.0
        s.player.y = -100.0
        s.wave_manager = WaveManager(
            Path("stellar_horizon/waves/waves_act1.json")
        )

        # Spawn a scout at a known position.
        e = Enemy()
        e.kind = "scout"
        e.on_spawn()
        e.x = 240.0
        e.y = 100.0
        e.alive = True
        e.hp = 1
        e.sprite_name = "enemy_scout_v1"
        s.wave_manager.spawned_enemies = [e]

        # Build a sentinel sprite with a unique marker color
        # (magenta 255,0,255 on every pixel). We register it
        # in the scene's animated cache under a sentinel name
        # and override the enemy's current_dying_sheet to
        # return that name. If the draw code calls the
        # method, the sentinel will be drawn and the magenta
        # pixels will appear; if the draw code hardcodes
        # enemy_scout_death_v1, the magenta pixels will be
        # absent and the test fails.
        SENTINEL_NAME = "test_destruction_sentinel_sprite"
        sentinel = pygame.Surface((29, 29), pygame.SRCALPHA)
        sentinel.fill((255, 0, 255, 255))
        # Wrap the static surface in a minimal stand-in for
        # AnimatedSprite so the draw code's
        # anim.get_current_surface() and anim._index calls
        # work. The simplest approach: replace the
        # scene's animated dict entry with a tiny shim
        # that exposes get_current_surface() and _index.
        class _SentinelAnim:
            def __init__(self, surf):
                self._surface = surf
                self._index = 0
            def get_current_surface(self):
                return self._surface
        s._animated[SENTINEL_NAME] = _SentinelAnim(sentinel)
        # Also provide a silhouette entry so the draw code
        # doesn't fall back to a different silhouette and
        # blacken our sentinel via a 1.08x scale offset.
        s._silhouettes[("enemy", SENTINEL_NAME)] = [sentinel]
        # Override the enemy's current_dying_sheet to
        # return the sentinel. After 0.20s of dying,
        # current_dying_sheet normally returns the ship
        # sheet; we force the sentinel so we can detect
        # whether the draw code consults the method.
        # Enemy has __slots__ so we patch the class method
        # (and restore it after the test).
        import stellar_horizon.entities.enemy as _enemy_mod
        _orig_cds = _enemy_mod.Enemy.current_dying_sheet
        _enemy_mod.Enemy.current_dying_sheet = lambda self: SENTINEL_NAME

        # Kill the enemy and tick past the burst window.
        # Brief comment: "0.20s of update = 20 frames at
        # 0.01s". Using 0.01 (matching the brief's stated
        # 0.20s window) keeps the ship on-screen; the
        # shipped 0.05 would let gravity push the ship
        # past y=295 in 1.0s and clear alive=False.
        e.take_damage(1)
        for _ in range(20):
            e.update(0.01, player=None)

        # Render the scene.
        surface = pygame.Surface((480, 270))
        s.draw(surface)

        # Count magenta (255, 0, 255) pixels in a 60x60
        # box around the enemy's position. If the draw
        # code consulted current_dying_sheet, the sentinel
        # was drawn and we expect ~29*29 = 841 magenta
        # pixels. If the draw code hardcoded the death
        # sheet name, no magenta is present and the count
        # is 0.
        magenta_count = 0
        for dx in range(-30, 30):
            for dy in range(-30, 30):
                px, py = int(e.x) + dx, int(e.y) + dy
                if 0 <= px < 480 and 0 <= py < 270:
                    r, g, b, a = surface.get_at((px, py))
                    if r == 255 and g == 0 and b == 255 and a > 0:
                        magenta_count += 1
        assert magenta_count >= 400, (
            f"expected >= 400 magenta sentinel pixels (draw code "
            f"must consult current_dying_sheet()), got {magenta_count}"
        )
    finally:
        # Restore the patched method.
        if _orig_cds is not None:
            _enemy_mod.Enemy.current_dying_sheet = _orig_cds
        pygame.quit()
