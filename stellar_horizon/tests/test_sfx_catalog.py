# stellar_horizon/tests/test_sfx_catalog.py
"""Smoke tests for the SFX catalog entries.

Covers the two SFX added in the 2026-09-06 polish pass:
  - `laser_fire`: dedicated sawtooth sweep for the player laser.
  - `enemy_explode`: dedicated noise burst for the enemy death event.

Also covers the gameplay wiring:
  - `play_event` accepts a `volume` kwarg (used to halve the
    bullet-vs-ship hit SFX).
"""
from __future__ import annotations

import pytest


def test_sfx_catalog_has_laser_fire_and_enemy_explode():
    # 2026-09-06 polish: new SFX for the player laser and the
    # standard enemy explosion. Both must be present in the
    # catalog so the engine pre-bakes them on startup.
    from stellar_horizon._systems.audio.synth import SFX_CATALOG
    assert "laser_fire" in SFX_CATALOG, "missing laser_fire SFX"
    assert "enemy_explode" in SFX_CATALOG, "missing enemy_explode SFX"


def test_sfx_laser_fire_is_sawtooth_sweep():
    # The laser_fire SFX should use a sawtooth voice and have a
    # strong negative pitch slide so it reads as a "zap" / sweep,
    # not as a flat beep.
    from stellar_horizon._systems.audio.synth import SFX_CATALOG, Voice
    spec = SFX_CATALOG["laser_fire"]
    assert spec.voice == Voice.SAW, (
        f"laser_fire voice should be SAW, got {spec.voice}"
    )
    assert spec.slide_hz_per_s < -1000, (
        f"laser_fire needs a strong downward pitch slide "
        f"(< -1000 Hz/s), got {spec.slide_hz_per_s}"
    )


def test_sfx_enemy_explode_is_noise_burst():
    # The enemy_explode SFX should use a noise voice and have a
    # longer duration than the short hit beep.
    from stellar_horizon._systems.audio.synth import SFX_CATALOG, Voice
    spec = SFX_CATALOG["enemy_explode"]
    assert spec.voice == Voice.NOISE, (
        f"enemy_explode voice should be NOISE, got {spec.voice}"
    )
    assert spec.duration_s > 0.4, (
        f"enemy_explode should be > 0.4s for the tail, got {spec.duration_s}"
    )


def test_play_event_accepts_volume_kwarg():
    # The sfx.play_event function must accept a `volume` kwarg so
    # callers can dampen individual events (used to halve the hit
    # SFX in gameplay.py).
    from stellar_horizon.audio import sfx
    # Set a dummy engine so play_event doesn't fall through to the
    # lazy initializer (which would try to load the mixer in a
    # headless test).
    class _FakeEngine:
        def play_sfx(self, name, volume=1.0):
            self.last_name = name
            self.last_volume = volume
            return True
    fake = _FakeEngine()
    sfx.set_engine(fake)
    sfx.play_event("hit", volume=0.5)
    assert fake.last_name == "hit"
    assert fake.last_volume == 0.5
    sfx.set_engine(None)
