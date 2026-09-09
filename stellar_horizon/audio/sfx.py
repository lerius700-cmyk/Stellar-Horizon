"""SFX wrapper around Void-Hunter's `src.audio.synth` (AudioEngine).

This module exposes a small surface (`play_event`, `engine`) so
gameplay code doesn't need to know about the underlying mixer.
The engine is lazy-initialized on first use so the game boots fast
and headless tests can swap it out via `set_engine()`.

The AudioEngine itself pre-bakes 30+ SFX from the synth catalog
(one-shots for shoot/hit/explode/bomb) plus 7 thruster loops
added in the Stellar Horizon audio pass.

v1.7: added 4 new event names for the ChargedDisc (weapon 1, white
piercing) audio. The .wav files are PLACEHOLDERS -- the actual
generation is scheduled for a follow-up synth pass. The events
are dispatched via play_event() as normal; if the synth catalog
doesn't have the name yet, the call is a silent no-op (the
try/except in play_event handles it). The constants here are
the single source of truth for the event names so the gameplay
scene and the synth pass can both reference them.

  CHARGE_HUM_WHITE        -- 1.0s loop, sine 200Hz -> 800Hz, vol 0.3
  CHARGED_RELEASE         -- 0.25s sine sweep 1200Hz -> 200Hz, vol 0.7
  CHARGED_HIT             -- 0.08s white noise 4-8kHz, vol 0.5
  CHARGED_HIT_SECONDARY   -- 0.04s pop, vol 0.3
"""
from __future__ import annotations

from typing import Optional


# v1.7: ChargedDisc audio event names. Centralized here so the
# gameplay scene can import them by name and the synth pass can
# iterate over the same list to generate the .wav files.
CHARGE_HUM_WHITE: str = "charge_hum_white"
CHARGED_RELEASE: str = "charged_release"
CHARGED_HIT: str = "charged_hit"
CHARGED_HIT_SECONDARY: str = "charged_hit_secondary"

# Set of all v1.7 event names -- convenience for "fire all charged
# disc events" iteration (e.g., the synth pass that pre-bakes
# the .wav files).
CHARGED_DISC_EVENTS: frozenset[str] = frozenset({
    CHARGE_HUM_WHITE,
    CHARGED_RELEASE,
    CHARGED_HIT,
    CHARGED_HIT_SECONDARY,
})


_engine: Optional["object"] = None  # src.audio.synth.AudioEngine


def _get_engine():
    """Lazy-init the audio engine. Returns None if the synth can't
    be loaded (e.g. no display in headless CI)."""
    global _engine
    if _engine is not None:
        return _engine
    try:
        from stellar_horizon._systems.audio.synth import AudioEngine  # type: ignore
        _engine = AudioEngine()
    except Exception:
        _engine = None
    return _engine


def set_engine(engine) -> None:
    """Override the engine (used by tests to inject a mock)."""
    global _engine
    _engine = engine


def engine():
    """Return the active engine (lazy-initialized). May be None
    if the synth failed to load (headless / no audio device)."""
    return _get_engine()


def play_event(name: str, volume: float = 1.0) -> None:
    """Best-effort one-shot SFX dispatch. No-op if synth can't be
    loaded or the name is unknown."""
    eng = _get_engine()
    if eng is None:
        return
    try:
        eng.play_sfx(name, volume=volume)
    except Exception:
        pass
