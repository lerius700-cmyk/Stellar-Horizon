"""Tests for ChargedShotState. These tests pin the invariants that the
DESIGN.md doc relies on — the snapshot in `last_charge_complete` and
the one-frame lifetime of the press/release edges are the two
invariants that, if broken, silently break the mechanic.
"""
import pytest

from charged_shot_kit import ChargedShotState


# ---------------------------------------------------------------------------
# Edges: True on the single frame, cleared on the next update.
# ---------------------------------------------------------------------------

def test_on_pressed_marks_edge():
    s = ChargedShotState()
    assert s.charge_pressed_this_frame is False
    s.on_pressed()
    assert s.charge_pressed_this_frame is True


def test_on_released_marks_edge():
    s = ChargedShotState()
    assert s.charge_released_this_frame is False
    s.on_released()
    assert s.charge_released_this_frame is True


def test_edges_cleared_after_one_update():
    """Edges live for exactly one update cycle. After update(), the
    flags must be False again, even if `held` is still True. This is
    the invariant that prevents double-firing on a long press.
    """
    s = ChargedShotState()
    s.on_pressed()
    s.on_released()
    assert s.charge_pressed_this_frame is True
    assert s.charge_released_this_frame is True
    s.update(dt=1 / 60, held=False, threshold=1.0)
    assert s.charge_pressed_this_frame is False
    assert s.charge_released_this_frame is False


# ---------------------------------------------------------------------------
# Accumulation: charge_time grows while held, resets when not held.
# ---------------------------------------------------------------------------

def test_charge_time_accumulates_while_held():
    s = ChargedShotState()
    for _ in range(6):
        s.update(dt=1 / 60, held=True, threshold=1.0)
    assert s.charge_time == pytest.approx(6 / 60, rel=1e-6)
    assert s.charging is True


def test_charge_time_resets_when_released():
    s = ChargedShotState()
    for _ in range(60):
        s.update(dt=1 / 60, held=True, threshold=1.0)
    assert s.charge_time == pytest.approx(1.0, rel=1e-6)
    s.update(dt=1 / 60, held=False, threshold=1.0)
    assert s.charge_time == 0.0
    assert s.charging is False


def test_charge_complete_flips_at_threshold():
    """charge_complete is True iff charge_time >= threshold (for
    threshold > 0). 50% of the threshold: False. 100%+: True.
    """
    s = ChargedShotState()
    threshold = 1.0
    # 50% charge: 30 frames * 1/60s = 0.5s, should be below 1.0.
    for _ in range(30):
        s.update(dt=1 / 60, held=True, threshold=threshold)
    assert s.charge_time == pytest.approx(0.5, rel=1e-6)
    assert s.charge_complete is False
    # Push past 100% (another 60 frames -> 1.5s total, > 1.0s).
    for _ in range(60):
        s.update(dt=1 / 60, held=True, threshold=threshold)
    assert s.charge_time >= threshold
    assert s.charge_complete is True


# ---------------------------------------------------------------------------
# Continuous weapons: threshold=0.0 always means "complete while held".
# ---------------------------------------------------------------------------

def test_continuous_weapon_charge_complete_immediately():
    """Weapons with threshold=0.0 (beams, streams) want charge_complete
    to be True the instant the key goes down — the held bool IS the
    trigger, not a time gate.
    """
    s = ChargedShotState()
    s.update(dt=1 / 60, held=True, threshold=0.0)
    assert s.charge_complete is True
    assert s.charge_time == pytest.approx(1 / 60)
    # charge_time still accumulates for visual ramp purposes; doesn't
    # affect the gameplay logic.


# ---------------------------------------------------------------------------
# No-charge weapons: threshold=None means the mechanic is a no-op.
# ---------------------------------------------------------------------------

def test_none_threshold_skips_accumulation():
    """For weapons with no charge behavior (tap-only), threshold=None
    should leave charge_time at 0 and charge_complete at False even
    while the key is held. The held bool is still updated so other
    systems can read `charging` (e.g. UI that shows "charging" even
    on a tap-only weapon — not recommended, but supported).
    """
    s = ChargedShotState()
    for _ in range(120):
        s.update(dt=1 / 60, held=True, threshold=None)
    assert s.charge_time == 0.0
    assert s.charge_complete is False
    assert s.charging is True  # held is still reflected


# ---------------------------------------------------------------------------
# The critical snapshot invariant: last_charge_complete on release frame.
# ---------------------------------------------------------------------------

def test_snapshot_captures_pre_reset_complete():
    """THE most important test. On the release frame:
      - held is False (player let go)
      - update() resets charge_complete to False
      - BUT the dispatch code wants to know "did they reach the
        threshold before releasing?"
    The snapshot `last_charge_complete` is the answer. Without it,
    the release-shot dispatch branch can never fire a charged shot.
    """
    s = ChargedShotState()
    # Charge past the threshold.
    for _ in range(70):  # 70/60 = 1.166s, > 1.0s
        s.update(dt=1 / 60, held=True, threshold=1.0)
    assert s.charge_complete is True
    # Release frame. The player lets go this frame.
    s.update(dt=1 / 60, held=False, threshold=1.0)
    # charge_complete is reset...
    assert s.charge_complete is False
    # ...but the snapshot preserved the answer.
    assert s.last_charge_complete is True
    # And charge_time is 0 too — clean state for the next press.
    assert s.charge_time == 0.0


def test_release_after_tap_does_not_fire():
    """A quick tap (no time to reach threshold) should leave
    last_charge_complete False. The release-shot dispatch branch
    checks this flag — a tap should not fire a charged shot.
    """
    s = ChargedShotState()
    # 100ms tap (well below a 1.0s threshold).
    for _ in range(6):
        s.update(dt=1 / 60, held=True, threshold=1.0)
    s.update(dt=1 / 60, held=False, threshold=1.0)
    assert s.charge_complete is False
    assert s.last_charge_complete is False


def test_release_after_release_does_not_fire():
    """Releasing after a previous release should not preserve the old
    snapshot. Each press is independent.
    """
    s = ChargedShotState()
    # First press: full charge, release.
    for _ in range(70):
        s.update(dt=1 / 60, held=True, threshold=1.0)
    s.update(dt=1 / 60, held=False, threshold=1.0)
    assert s.last_charge_complete is True
    # Some time passes, no key held.
    for _ in range(30):
        s.update(dt=1 / 60, held=False, threshold=1.0)
    # Second press: only a quick tap, then release.
    for _ in range(3):
        s.update(dt=1 / 60, held=True, threshold=1.0)
    s.update(dt=1 / 60, held=False, threshold=1.0)
    # The second release should NOT have last_charge_complete True —
    # the second press didn't reach the threshold.
    assert s.last_charge_complete is False


# ---------------------------------------------------------------------------
# Extra spawn timer: for the continuous-stream pattern (Branch C).
# ---------------------------------------------------------------------------

def test_extra_spawn_timer_advances_and_resets():
    s = ChargedShotState()
    s.tick_extra_spawn_timer(0.5)
    s.tick_extra_spawn_timer(0.5)
    assert s.extra_spawn_timer == pytest.approx(1.0)
    s.update(dt=1 / 60, held=False, threshold=0.0)
    assert s.extra_spawn_timer == 0.0  # reset on release


def test_extra_spawn_timer_persists_while_held():
    s = ChargedShotState()
    s.tick_extra_spawn_timer(0.5)
    s.update(dt=1 / 60, held=True, threshold=0.0)
    # Still held; the timer should NOT reset on the held branch.
    assert s.extra_spawn_timer == pytest.approx(0.5)
