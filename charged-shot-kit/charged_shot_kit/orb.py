"""ShipChargeOrb — the 3-layer muzzle orb that visualizes the charge.

Pure procedural pygame drawing. No sprites, no images, no external
assets. The orb is drawn each frame with `pygame.draw.circle` on a
per-pixel alpha surface, so the cost is dominated by Python-side
overhead (a handful of circles per frame) — negligible.

See DESIGN.md section 5 for the visual rationale. The TL;DR is:

  - Outer ring: weapon color, always visible (immediate "I'm charging"
    feedback at growth=0).
  - Body: weapon color shifted toward plasma cyan. Appears at growth
    >= 25%. Reads as "energy building up" rather than "a colored disc".
  - White hot core: small white disc, appears at growth >= 50%, pulses
    at growth >= 85% for the "ready to release" cue.

Per-weapon customization:

  - `ORB_RING_COLOR[weapon]` overrides the ring color. Defaults are
    orange / white / magenta / cyan to match the four canonical
    "energy weapon" colors of a shmup.
  - `RAMP_TIME_S[weapon]` overrides the visual ramp. Continuous weapons
    (beams, streams) use a short 0.5s ramp; discrete weapons use the
    full gameplay threshold.
  - `PULSE_WEAPONS` controls which weapons get the "ready" pulse. By
    default, all release-charge weapons + the continuous beam pulse;
    the piercing stream does not (the stream itself is the cue).

If your game has more than 4 weapon archetypes, just add entries to
those dicts.
"""
from __future__ import annotations

import math

import pygame

# ---------------------------------------------------------------------------
# Per-weapon palette. Override these in your game if you have a different
# weapon color scheme. Keys are weapon IDs (ints or strings — the type
# doesn't matter, just be consistent with the keys you pass to `draw`).
# ---------------------------------------------------------------------------

# Outer ring color (RGB). Choose a hot, saturated color per weapon.
ORB_RING_COLOR: dict = {
    0: (255, 140, 42),    # orange (continuous beam)
    1: (255, 255, 255),   # white (release-charge: Megaman bolt)
    2: (255, 106, 180),   # magenta (release-charge: boomerang)
    3: (140, 246, 255),   # cyan (continuous piercing stream)
}

# Plasma cyan, used to blend the body color. The "body" is the ring
# color shifted toward this so the orb reads as plasma, not as a flat
# colored disc.
_PLASMA_CYAN: tuple[int, int, int] = (100, 220, 255)
_BODY_CYAN_MIX: float = 0.55  # 55% cyan + 45% ring color


def _shift_toward_cyan(rgb: tuple[int, int, int],
                       mix: float = _BODY_CYAN_MIX) -> tuple[int, int, int]:
    """Blend `rgb` with `_PLASMA_CYAN`. mix=0.55 means the body color
    is 55% cyan + 45% ring color — enough cyan to read as plasma
    without erasing the weapon's identity.
    """
    r, g, b = rgb
    cr, cg, cb = _PLASMA_CYAN
    return (
        int(r * (1 - mix) + cr * mix),
        int(g * (1 - mix) + cg * mix),
        int(b * (1 - mix) + cb * mix),
    )


def _body_color(weapon) -> tuple[int, int, int]:
    """Body color = ring color shifted toward plasma cyan. Falls back
    to a generic cyan if the weapon has no ring color entry.
    """
    ring = ORB_RING_COLOR.get(weapon)
    if ring is None:
        return _PLASMA_CYAN
    return _shift_toward_cyan(ring)


# ---------------------------------------------------------------------------
# Geometry constants. All in pixels.
# ---------------------------------------------------------------------------

RING_BASE: float = 3.0     # starting ring radius at charge_time=0
RING_MAX: float = 38.0     # hard cap on ring radius
BODY_RATIO: float = 0.78   # body radius as fraction of ring radius
CORE_RATIO: float = 0.32   # white core radius as fraction of ring radius

# Body / core activation thresholds (as fraction of full ramp time).
# Below these, the layer is invisible.
BODY_ACTIVATION_FRAC: float = 0.25
CORE_ACTIVATION_FRAC: float = 0.50

# Pulse at full charge: when growth01 >= PULSE_ACTIVATION_FRAC and the
# weapon is in PULSE_WEAPONS, modulate alpha by sin().
PULSE_ACTIVATION_FRAC: float = 0.85
PULSE_SPEED_HZ: float = 8.0     # pulse frequency
PULSE_DEPTH: float = 0.18       # peak alpha modulation (0..1)


# ---------------------------------------------------------------------------
# Per-weapon visual ramp time. Override per game. Continuous weapons
# (beams, streams) want a SHORT visual ramp (0.5s) so the orb reaches
# full size fast — the held bool is the trigger, not a time gate.
# Discrete weapons (release-charge) can use the full charge time so the
# player sees the orb grow throughout the charge.
# ---------------------------------------------------------------------------

RAMP_TIME_S: dict = {
    0: 0.5,   # orange beam
    1: 1.0,   # white (matches default gameplay threshold)
    2: 1.5,   # magenta
    3: 0.5,   # cyan stream
}

# Which weapons get the "ready" pulse at full charge. By default:
# all release-charge weapons + the continuous beam. The piercing
# stream (weapon 3) does not pulse — the stream itself is the cue.
PULSE_WEAPONS: frozenset = frozenset({0, 1, 2})


# ---------------------------------------------------------------------------
# Public draw function. Call this once per frame, AFTER the player
# sprite is drawn (so the orb is on top of the muzzle).
# ---------------------------------------------------------------------------

def draw(surface: pygame.Surface, muzzle_x: float, muzzle_y: float,
         weapon, charge_time: float, charging: bool,
         now: float = 0.0) -> None:
    """Render the charge orb centered at (muzzle_x, muzzle_y).

    The orb is invisible when `charging` is False AND `charge_time`
    is 0 (i.e. the player has not held the key this session). After
    the key is released, the orb disappears on the next frame because
    `ChargedShotState.update` resets `charge_time` to 0.

    Args:
        surface: the pygame surface to draw on (your screen).
        muzzle_x, muzzle_y: world-space coordinates of the muzzle
            (where bullets emerge from the ship).
        weapon: the current weapon ID. Used to look up the ring
            color and ramp time.
        charge_time: seconds the charge key has been held. Driven by
            `ChargedShotState.charge_time`.
        charging: True iff the key is currently held. Drawn false
            for a single frame at most — see `ChargedShotState`.
        now: scene clock in seconds. Used for the pulse phase. Pass
            the same clock you pass to other animated elements.
    """
    # No-op when the player isn't charging AND the accumulator is 0.
    # (ChargedShotState resets charge_time to 0 the frame the key
    # goes up, so the orb disappears cleanly.)
    if not charging and charge_time <= 0.0:
        return
    if weapon not in ORB_RING_COLOR:
        return
    ring_color = ORB_RING_COLOR[weapon]
    body_color = _body_color(weapon)
    ramp = RAMP_TIME_S.get(weapon, 1.0)
    # Visual growth fraction: 0.0 at key-down, 1.0 at `ramp` seconds.
    growth01 = max(0.0, min(1.0, charge_time / ramp))
    # Layer radii.
    ring_r = RING_BASE + growth01 * (RING_MAX - RING_BASE)
    body_r = ring_r * BODY_RATIO
    core_r = ring_r * CORE_RATIO
    # Alpha envelopes. Below the activation fraction, the layer is
    # invisible. Above, it ramps to full.
    body_frac = max(0.0, min(1.0,
        (growth01 - BODY_ACTIVATION_FRAC) / (1.0 - BODY_ACTIVATION_FRAC)
    ))
    core_frac = max(0.0, min(1.0,
        (growth01 - CORE_ACTIVATION_FRAC) / (1.0 - CORE_ACTIVATION_FRAC)
    ))
    # Pulse at full charge: 1.0 +/- PULSE_DEPTH at PULSE_SPEED_HZ.
    pulse = 1.0
    if weapon in PULSE_WEAPONS and growth01 >= PULSE_ACTIVATION_FRAC:
        pulse = 1.0 - PULSE_DEPTH + PULSE_DEPTH * (
            0.5 + 0.5 * math.sin(now * 2 * math.pi * PULSE_SPEED_HZ)
        )
    # Build a per-pixel-alpha surface, recreate per frame. The orb is
    # small (<= 80px square at full size), so the cost is negligible
    # compared to the alternative of caching and invalidating.
    size = int(ring_r * 2 + 4)
    orb = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2
    # 1) Outer ring: 2px outline, weapon color, alpha-pulsed at full.
    ring_alpha = int(200 * pulse)
    pygame.draw.circle(
        orb, (*ring_color, ring_alpha),
        (cx, cy), int(ring_r), 2,
    )
    # 2) Body: filled disc, cyan-shifted color, alpha-gated by body_frac.
    if body_frac > 0.0 and body_r > 0:
        body_alpha = int(180 * body_frac * pulse)
        pygame.draw.circle(
            orb, (*body_color, body_alpha),
            (cx, cy), int(body_r),
        )
    # 3) White hot core: small filled disc, white, alpha-gated by core_frac.
    if core_frac > 0.0 and core_r > 0:
        core_alpha = int(255 * core_frac * pulse)
        pygame.draw.circle(
            orb, (255, 255, 255, core_alpha),
            (cx, cy), int(core_r),
        )
    # Center the orb on the muzzle.
    surface.blit(orb, (int(muzzle_x - size // 2), int(muzzle_y - size // 2)))


__all__ = [
    "ORB_RING_COLOR", "RAMP_TIME_S", "PULSE_WEAPONS",
    "BODY_ACTIVATION_FRAC", "CORE_ACTIVATION_FRAC",
    "PULSE_ACTIVATION_FRAC", "PULSE_SPEED_HZ", "PULSE_DEPTH",
    "draw",
]
