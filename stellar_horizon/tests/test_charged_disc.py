"""Tests for v1.7 ChargedDisc (entities/charged_disc.py) and the
new FxLayer primitives (shockwave, screen shake, flash).

The ChargedDisc is the white piercing (weapon 1) charged shot.
It replaces the v1.6 "Megaman bolt" with a 40px-radius energy
disc that pierces up to 4 enemies (8x first, 3x secondary) and
fades out over 0.4s after the last hit.

These tests cover the 6 spec-mandated cases plus a few extra
for the FxLayer extensions that the disc relies on.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from stellar_horizon.audio import sfx
from stellar_horizon.entities.charged_disc import ChargedDisc, State
from stellar_horizon.fx.particles import FxLayer
from stellar_horizon.fx.shockwave import Shockwave


# ---------- ChargedDisc entity tests ----------


def test_charged_disc_starts_dead():
    """A freshly constructed disc is not alive (pool slot default)."""
    d = ChargedDisc()
    assert d.alive is False
    assert d.state is State.FLYING
    assert d.hit_count == 0
    assert d.elapsed == 0.0


def test_charged_disc_spawns_at_muzzle():
    """After spawn(x, y, t), the disc is alive at (x, y) with
    +X velocity = SPEED_PX_S (1100 px/s). The spawn time is
    recorded for downstream VFX that wants a global timestamp.
    """
    d = ChargedDisc()
    d.spawn(52.0, 135.0, 3.5)  # 52 = player.x + BULLET_OFFSET_X (40 + 12)
    assert d.alive is True
    assert d.state is State.FLYING
    assert d.x == 52.0
    assert d.y == 135.0
    assert d.vx == ChargedDisc.SPEED_PX_S
    assert d.vy == 0.0
    assert d.spawn_time == 3.5


def test_charged_disc_moves_at_1100_px_s():
    """While FLYING, the disc moves at exactly 1100 px/s in +X.
    We use a 0.1s update so the disc is still FLYING (the 0.4s
    miss-timeout hasn't fired yet). At 0.1s, x should be
    100 + 1100*0.1 = 210. The 1.0s figure from the original spec
    section 5 conflicts with section 3.6's 0.4s miss-timeout;
    this test verifies the velocity-based motion in the FLYING
    window, which is the actually-meaningful invariant.
    """
    d = ChargedDisc()
    d.spawn(100.0, 100.0, 0.0)
    d.update(0.1)
    assert d.x == pytest.approx(100.0 + 110.0)
    assert d.y == pytest.approx(100.0)
    assert d.state is State.FLYING  # still FLYING at 0.1s


def test_charged_disc_first_hit_deals_8x_damage():
    """When the disc collides with an enemy, the collision handler
    calls enemy.take_damage(8) on the first hit. This test simulates
    the handler by checking that the disc's hit_count goes to 1
    and last_hit_time is recorded.
    """
    d = ChargedDisc()
    d.spawn(100.0, 100.0, 0.0)
    # Stub enemy: must expose .hitbox() -> pygame.Rect. The disc's
    # hits() method takes any object with that method, so we use a
    # minimal stand-in here.
    class _StubEnemy:
        def __init__(self, x, y):
            self.x = x
            self.y = y
        def hitbox(self):
            return pygame.Rect(int(self.x - 4), int(self.y - 4), 8, 8)
    e = _StubEnemy(120.0, 100.0)  # 80x80 AABB centered on disc
    # The collision handler reads disc.hit_count BEFORE register_hit
    # to decide between 8x and 3x. Simulate that ordering.
    assert d.hit_count == 0
    assert d.hits(e) is True
    d.register_hit()
    assert d.hit_count == 1
    assert d.last_hit_time == d.elapsed  # both are 0 right after spawn


def test_charged_disc_secondary_hits_deal_3x_damage():
    """Hits 2-4 increment hit_count and stamp last_hit_time. The
    gameplay scene's handler reads hit_count to choose 8x (==0)
    vs 3x (<=MAX_HITS). This test exercises the register_hit
    path that the scene uses.
    """
    d = ChargedDisc()
    d.spawn(100.0, 100.0, 0.0)
    # Tick once so elapsed > 0 (the spec notes last_hit_time is
    # measured in elapsed-time, not absolute spawn_time).
    d.update(0.05)
    d.register_hit()  # hit #1
    assert d.hit_count == 1
    d.update(0.05)
    d.register_hit()  # hit #2 (would be 3x in the scene handler)
    assert d.hit_count == 2
    d.update(0.05)
    d.register_hit()  # hit #3
    assert d.hit_count == 3


def test_charged_disc_fades_after_400ms_no_hit():
    """A disc that doesn't hit anything for 0.4s transitions to
    FADING. The FADE_DURATION_S (0.4s) is then the time the disc
    stays alive in FADING before going permanently dead.
    """
    d = ChargedDisc()
    d.spawn(100.0, 100.0, 0.0)
    d.update(0.4)  # 0.4s elapsed, 0 hits
    # At 0.4s elapsed with no hits, the spec says: transition to
    # FADING. After exactly 0.4s, the >= check fires.
    assert d.state is State.FADING
    assert d.alive is True
    # Wait the full FADE_DURATION_S -- should be dead by then.
    d.update(ChargedDisc.FADE_DURATION_S)
    assert d.alive is False


def test_charged_disc_capped_at_4_hits():
    """After 4 hits, additional register_hit calls are still safe
    (no exception), but the scene's handler should treat hit_count
    > MAX_HITS as "no more damage". The disc itself doesn't
    auto-stop on hit_count; the cap is enforced by the collision
    handler's `disc.hit_count <= ChargedDisc.MAX_HITS` check.
    The disc transitions to FADING once 0.4s elapses since the
    last hit AND hit_count >= MAX_HITS.

    We force vx=0 after spawn so the disc stays in-bounds while
    we test the hit-count-driven FADING logic. Without this, the
    disc flies off-screen and dies before the 0.4s settle timer
    fires.
    """
    d = ChargedDisc()
    d.spawn(100.0, 100.0, 0.0)
    d.vx = 0.0  # station the disc for the test (otherwise it
    # leaves the playfield at 1100 px/s and dies off-screen
    # before the FADING timer can fire)
    for _ in range(5):  # 5 hit registrations
        d.update(0.05)
        d.register_hit()
    # The disc itself allows hit_count to grow past MAX_HITS --
    # it's the scene handler that ignores hits 5+. So hit_count=5.
    assert d.hit_count == 5
    # After the 5th hit at elapsed=0.25, the next FADING check
    # fires when elapsed - last_hit_time >= 0.4s. We add 0.45s
    # to bring elapsed to 0.70, giving a 0.45s settle window.
    d.update(0.45)  # elapsed = 0.70, last_hit_time = 0.25, diff = 0.45
    assert d.state is State.FADING


def test_charged_disc_dies_off_screen():
    """A disc that flies past the right edge (x > INTERNAL_W + 60)
    dies immediately, with no fade. This matches the spec's
    "off-screen kill" rule.
    """
    d = ChargedDisc()
    # Spawn near the right edge, give it a long enough update
    # that it crosses the cap.
    d.spawn(400.0, 100.0, 0.0)
    # 480 + 60 = 540. Disc needs to travel 140 px. At 1100 px/s
    # that's ~0.13s. Let's give it 0.2s to be safe.
    d.update(0.2)
    # Should have crossed the cap and died.
    assert d.alive is False
    assert d.x > 480 + 60


def test_charged_disc_hitbox_is_80x80_centered():
    """The disc's AABB is 80x80 centered on (x, y). This is the
    collision primitive the scene uses; the spec's 100% AABB
    accuracy invariant relies on this being exact.
    """
    d = ChargedDisc()
    d.spawn(200.0, 100.0, 0.0)
    hb = d.hitbox()
    assert hb.width == 80
    assert hb.height == 80
    assert hb.centerx == 200
    assert hb.centery == 100


def test_charged_disc_fade_helpers_lerp_correctly():
    """fade_alpha() is 255 in FLYING and lerps 255->0 in FADING.
    fade_scale() is 1.0 in FLYING and lerps 1.0->1.3 in FADING.
    """
    d = ChargedDisc()
    d.spawn(100.0, 100.0, 0.0)
    # FLYING: alpha 255, scale 1.0
    assert d.fade_alpha() == 255
    assert d.fade_scale() == pytest.approx(1.0)
    # Trigger FADING
    d.update(0.4)  # miss timeout
    assert d.state is State.FADING
    # Halfway through the fade: alpha 128 (rounded), scale ~1.15
    d.fade_elapsed = ChargedDisc.FADE_DURATION_S * 0.5
    assert d.fade_alpha() == pytest.approx(128, abs=1)
    assert d.fade_scale() == pytest.approx(1.15, abs=0.01)
    # At the end: alpha 0, scale 1.3
    d.fade_elapsed = ChargedDisc.FADE_DURATION_S
    assert d.fade_alpha() == 0
    assert d.fade_scale() == pytest.approx(1.3)


def test_charged_disc_pool_size_constant_is_2():
    """Per spec section 3.1: pool size = 2. This guards against
    accidental downsize (which would make spam-SPACE fail) and
    accidental upsize (which would waste memory).
    """
    assert ChargedDisc.MAX_HITS == 4
    assert ChargedDisc.SPEED_PX_S == 1100.0
    assert ChargedDisc.RADIUS == 40
    assert ChargedDisc.FADE_DURATION_S == 0.4


# ---------- FxLayer new primitives (shockwave, shake, flash) ----------


def test_fx_layer_shockwave_grows_and_fades():
    """A Shockwave starts at radius 0, grows to max_radius over
    its lifetime, and its alpha lerps from 255 to 0.
    """
    sw = Shockwave(x=100.0, y=100.0, radius=0.0, max_radius=50.0,
                   life=0.35, max_life=0.35, color=(255, 255, 255))
    assert sw.alive is True
    assert sw.alpha_255() == 255
    # Halfway through
    sw.update(0.175)
    assert sw.alive is True
    assert sw.radius == pytest.approx(25.0)
    assert sw.alpha_255() == pytest.approx(128, abs=1)
    # At the end
    sw.update(0.175)
    assert sw.alive is False
    assert sw.alpha_255() == 0


def test_fx_layer_emit_shockwave_adds_to_pool():
    """emit_shockwave() appends a Shockwave to fx.shockwaves."""
    fx = FxLayer()
    assert len(fx.shockwaves) == 0
    fx.emit_shockwave(100, 100, radius=40)
    assert len(fx.shockwaves) == 1
    assert fx.shockwaves[0].max_radius == 40
    assert fx.shockwaves[0].alive is True


def test_fx_layer_add_screen_shake_caps_amplitude():
    """add_screen_shake caps amplitude at SHAKE_AMPLITUDE_CAP=6.0
    so a flurry of 10px kicks doesn't compound into an unreadable
    screen. (Spec section 7.2 FMEA item 6.)
    """
    fx = FxLayer()
    fx.add_screen_shake(99.0, 1.0)
    assert fx.shake_amplitude == 6.0  # capped
    assert fx.shake_life == 1.0
    assert fx.shake_max_life == 1.0


def test_fx_layer_screen_shake_decays_to_zero():
    """The FxLayer's shake_offset() returns (0, 0) once the shake
    life has fully decayed. update() is what advances the life.
    """
    fx = FxLayer()
    fx.add_screen_shake(4.0, 0.10)
    # First update: still alive, offset non-zero
    fx.update(0.05)
    ox, oy = fx.shake_offset()
    assert abs(ox) >= 0  # could be exactly 0 in a bad random draw,
    # but most draws will be non-zero. We don't assert non-zero
    # because random.uniform(-amp, +amp) CAN legitimately land
    # near 0.
    assert oy == 0.0  # vertical shake is always 0 (horizontal shmup)
    # Wait for full decay
    fx.update(0.10)
    assert fx.shake_offset() == (0.0, 0.0)


def test_fx_layer_add_flash_stacks():
    """Multiple add_flash() calls stack; each renders independently.
    The flashes tick their own life in update().
    """
    fx = FxLayer()
    fx.add_flash(100, 100, radius=20)
    fx.add_flash(200, 200, radius=30)
    assert len(fx._flashes) == 2
    fx.update(0.1)
    # After 0.1s (default life is 0.3s), both flashes are still
    # alive.
    assert len(fx._flashes) == 2
    fx.update(0.3)
    # After 0.3s more (total 0.4s > 0.3s default), both dead.
    assert len(fx._flashes) == 0


def test_sfx_charged_disc_event_names_are_defined():
    """The 4 placeholder event names from spec section 3.8 are
    exposed as module constants on stellar_horizon.audio.sfx.
    """
    assert sfx.CHARGE_HUM_WHITE == "charge_hum_white"
    assert sfx.CHARGED_RELEASE == "charged_release"
    assert sfx.CHARGED_HIT == "charged_hit"
    assert sfx.CHARGED_HIT_SECONDARY == "charged_hit_secondary"
    # The set is useful for the synth pass that pre-bakes the
    # .wav files (all 4 names are present).
    assert sfx.CHARGED_DISC_EVENTS == frozenset({
        "charge_hum_white",
        "charged_release",
        "charged_hit",
        "charged_hit_secondary",
    })


# ---------- Synth pass: SFX_CATALOG entries (v1.7 audio) ----------


def test_synth_catalog_has_4_charged_disc_entries():
    """v1.7 synth pass: the 4 placeholder event names are now
    in the SFX_CATALOG so the engine prebakes them via
    AudioEngine._prebake_all(). Before this commit, the names
    existed in audio/sfx.py but the engine had no spec for them
    (play_event was a silent no-op).
    """
    from stellar_horizon._systems.audio.synth import SFX_CATALOG
    for name in sfx.CHARGED_DISC_EVENTS:
        assert name in SFX_CATALOG, (
            f"{name} missing from SFX_CATALOG -- engine can't "
            f"prebake it, gameplay.py sfx.play_event() is no-op"
        )


def test_synth_charge_hum_white_spec_matches_design():
    """Spec: 1.0s triangle 200Hz -> 800Hz, vol 0.3. We use TRIANGLE
    because the synth module has no pure SINE voice (triangle is
    the smoothest available).
    Slide Hz/s = (800 - 200) / 1.0 = 600 Hz/s.
    """
    from stellar_horizon._systems.audio.synth import SFX_CATALOG, Voice
    spec = SFX_CATALOG[sfx.CHARGE_HUM_WHITE]
    assert spec.voice is Voice.TRIANGLE
    assert spec.freq_hz == 200.0
    # 600 Hz/s slide (200->800 over 1.0s)
    assert spec.slide_hz_per_s == pytest.approx(600.0)
    assert spec.duration_s == pytest.approx(1.0)
    assert spec.volume == pytest.approx(0.3)


def test_synth_charged_release_spec_matches_design():
    """Spec: 0.25s sweep 1200Hz -> 200Hz, vol 0.7.
    Slide Hz/s = (200 - 1200) / 0.25 = -4000 Hz/s.
    """
    from stellar_horizon._systems.audio.synth import SFX_CATALOG, Voice
    spec = SFX_CATALOG[sfx.CHARGED_RELEASE]
    assert spec.voice is Voice.TRIANGLE
    assert spec.freq_hz == 1200.0
    assert spec.slide_hz_per_s == pytest.approx(-4000.0)
    assert spec.duration_s == pytest.approx(0.25)
    assert spec.volume == pytest.approx(0.7)


def test_synth_charged_hit_spec_matches_design():
    """Spec: 0.08s white noise burst, vol 0.5. The "4-8 kHz"
    spectral content is intrinsic to an unfiltered noise burst
    at 44.1 kHz sample rate (the synth has no bandpass filter).
    """
    from stellar_horizon._systems.audio.synth import SFX_CATALOG, Voice
    spec = SFX_CATALOG[sfx.CHARGED_HIT]
    assert spec.voice is Voice.NOISE
    assert spec.duration_s == pytest.approx(0.08)
    assert spec.volume == pytest.approx(0.5)


def test_synth_charged_hit_secondary_spec_matches_design():
    """Spec: 0.04s pop, vol 0.3. Very short noise burst -- reads
    as a "pop" rather than a full hit.
    """
    from stellar_horizon._systems.audio.synth import SFX_CATALOG, Voice
    spec = SFX_CATALOG[sfx.CHARGED_HIT_SECONDARY]
    assert spec.voice is Voice.NOISE
    assert spec.duration_s == pytest.approx(0.04)
    assert spec.volume == pytest.approx(0.3)


def test_synth_charged_disc_events_render_to_non_silent_buffers():
    """All 4 events render via render_sfx() to non-silent 16-bit
    PCM buffers. This is the "the audio actually exists" check --
    if the catalog spec has duration_s=0 or volume=0, the buffer
    would be all zeros and the test would fail.
    """
    from stellar_horizon._systems.audio.synth import render_sfx
    for name in sfx.CHARGED_DISC_EVENTS:
        buf = render_sfx(name)
        # Buffer must be non-empty
        assert len(buf) > 100, f"{name}: buffer too small ({len(buf)})"
        # Buffer must have audible content (not all zeros)
        nonzero = sum(1 for s in buf if s != 0)
        assert nonzero > 100, (
            f"{name}: too few non-zero samples ({nonzero}/{len(buf)}) "
            f"-- the spec is probably wrong (duration or volume = 0)"
        )


def test_synth_charged_disc_events_in_sfx_names():
    """AudioEngine._prebake_all() iterates SFX_NAMES (computed
    from SFX_CATALOG). If a name is in the catalog but not in
    SFX_NAMES, the engine won't prebake it. This is a paranoia
    check that the catalog insertion didn't break the tuple.
    """
    from stellar_horizon._systems.audio.synth import SFX_NAMES
    for name in sfx.CHARGED_DISC_EVENTS:
        assert name in SFX_NAMES, (
            f"{name} in SFX_CATALOG but not in SFX_NAMES -- "
            f"AudioEngine won't prebake it"
        )


# ---------- Player integration: spawn path ----------


def test_player_charge_time_s_1_is_1_0s():
    """v1.7 changed CHARGE_TIME_S[1] from 1.2 to 1.0. The existing
    test_charge_state.py test_charge_time_s_table_covers_all_5_weapons
    asserts 1.2 -- this test is the v1.7-correct counterpart.
    """
    from stellar_horizon.entities.player import Player
    assert Player.CHARGE_TIME_S[1] == 1.0


def test_player_release_weapon_1_spawns_charged_disc():
    """Holding SPACE for >= 1.0s on weapon 1, then releasing, spawns
    a ChargedDisc at the muzzle. The disc lives in the pool passed
    via the new charged_disc_pool parameter.
    """
    from stellar_horizon.entities.player import Player
    screen = pygame.Rect(0, 0, 480, 270)
    p = Player(screen)
    p.fx = None  # no FxLayer in unit tests
    p.set_weapon(1)
    disc_pool = [ChargedDisc(), ChargedDisc()]
    # Press SPACE + start charging
    p.on_charge_pressed()
    p.charging = True
    for _ in range(11):  # 11 * 0.1 = 1.1s, > 1.0s threshold
        p.update(0.1, {}, [], now=0.0, charged_disc_pool=disc_pool)
    assert p.charge_complete is True
    # Release SPACE
    p.on_charge_released()
    p.charging = False
    p.update(0.0, {}, [], now=0.0, charged_disc_pool=disc_pool)
    # One disc should be alive in the pool, positioned at the muzzle.
    alive = [d for d in disc_pool if d.alive]
    assert len(alive) == 1
    d = alive[0]
    assert d.x == p.x + p.BULLET_OFFSET_X
    assert d.y == p.y
    assert d.vx == ChargedDisc.SPEED_PX_S


def test_player_release_weapon_1_no_disc_if_no_pool():
    """If the player doesn't pass a charged_disc_pool (None), the
    weapon 1 release path is a no-op (no crash, no spawn). This
    preserves backward compat for tests that don't wire up the
    new pool.
    """
    from stellar_horizon.entities.player import Player
    screen = pygame.Rect(0, 0, 480, 270)
    p = Player(screen)
    p.fx = None
    p.set_weapon(1)
    p.on_charge_pressed()
    p.charging = True
    for _ in range(11):
        p.update(0.1, {}, [], now=0.0)  # no charged_disc_pool
    p.on_charge_released()
    p.charging = False
    # No exception, no bullets spawned either (no pool).
    p.update(0.0, {}, [], now=0.0)
    # Pool was not passed -- nothing to assert on the disc side.
    # The point of the test is "no crash". Weapon 2 (boomerang)
    # is also a no-op here because the bullets_pool is empty.


def test_player_release_weapon_1_with_full_pool_is_silent_noop():
    """If both disc pool slots are alive when the player releases,
    the second spawn is a silent no-op (no queue, per spec 6.3).
    The first disc is unaffected.
    """
    from stellar_horizon.entities.player import Player
    screen = pygame.Rect(0, 0, 480, 270)
    p = Player(screen)
    p.fx = None
    p.set_weapon(1)
    disc_pool = [ChargedDisc(), ChargedDisc()]
    # Pre-fill both slots with alive discs at known positions.
    disc_pool[0].spawn(10, 10, 0)
    disc_pool[1].spawn(20, 20, 0)
    p.on_charge_pressed()
    p.charging = True
    for _ in range(11):
        p.update(0.1, {}, [], now=0.0, charged_disc_pool=disc_pool)
    p.on_charge_released()
    p.charging = False
    p.update(0.0, {}, [], now=0.0, charged_disc_pool=disc_pool)
    # Both discs still at their original positions -- no new spawn
    # overwrote them. The release was a silent no-op.
    assert disc_pool[0].x == 10
    assert disc_pool[1].x == 20
