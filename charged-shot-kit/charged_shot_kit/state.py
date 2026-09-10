"""ChargedShotState — the six attributes that drive a Megaman-style
charge mechanic on the player (or weapon) object.

This module is engine-agnostic. It depends only on Python stdlib. Drop
it into any pygame / SDL / custom-2D game. See DESIGN.md for the
rationale.

Usage outline (see examples/full_demo.py for a runnable example):

    from charged_shot_kit import ChargedShotState

    state = ChargedShotState()

    # In your input handler, on KEYDOWN for the charge key:
    state.on_pressed()

    # In your input handler, on KEYUP for the charge key:
    state.on_released()

    # In your per-frame update, BEFORE anything that dispatches on
    # the release edge:
    state.update(dt=dt, held=keys[CHARGE_KEY], threshold=current_weapon.charge_time_s)

    # In your per-frame update, in the dispatch section:
    if state.charge_released_this_frame and current_weapon.is_release_charge:
        if state.last_charge_complete:
            spawn_charged_projectile(...)
            state.cooldown = 0.4

The single most important rule: read `state.last_charge_complete`, NOT
`state.charge_complete`, when dispatching on the release frame. On the
release frame, `state.charging` is already False, so the `update()`
method has just reset `charge_complete` to False. The snapshot taken
before the reset preserves the "yes, they reached the threshold" answer.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChargedShotState:
    """Six attributes that capture everything a charge mechanic needs.

    All fields are public for transparency — the other agent reading
    your code can introspect any of them without a getter. Mutate them
    in the methods (`on_pressed`, `on_released`, `update`) so the
    invariants documented below hold.

    Invariants (held by `update`):
      - If `charging` is True, `charge_time` is non-decreasing within
        the press.
      - If `charging` is False, `charge_time` is exactly 0.0.
      - If `charging` is False, `charge_complete` is exactly False.
      - `charge_pressed_this_frame` and `charge_released_this_frame`
        are each True on at most one frame per actual edge event.
      - `last_charge_complete` equals the pre-reset value of
        `charge_complete` from the previous frame.
    """

    # Held state. Cheap to set every frame from the input poll.
    charging: bool = False

    # Edges. True on the single frame the matching transition happened.
    # Cleared by `update` after one frame, so consumers must read them
    # in the same `update` cycle they were set.
    charge_pressed_this_frame: bool = False
    charge_released_this_frame: bool = False

    # Accumulator. Seconds the key has been held this press. Reset to 0
    # every frame the key is up.
    charge_time: float = 0.0

    # Derived flag. True iff `charge_time >= threshold` (or threshold is
    # 0.0, meaning "continuous"). Cheap to read in the dispatch branch.
    charge_complete: bool = False

    # Snapshot of `charge_complete` taken BEFORE `update` resets it.
    # This is the only correct way to ask "did the player reach the
    # threshold before releasing?" on the release frame.
    last_charge_complete: bool = False

    # Optional auxiliary timer. The continuous-stream weapon (fire every
    # N seconds while held) needs a separate timer that the dispatch
    # branch can read and reset independently of `charge_time`. Not all
    # games need it; if you don't, just leave it at 0.0 and ignore it.
    extra_spawn_timer: float = 0.0

    def on_pressed(self) -> None:
        """Mark the press edge. Call this on the KEYDOWN frame of the
        charge key. The flag is consumed by the next `update` call.
        """
        self.charge_pressed_this_frame = True

    def on_released(self) -> None:
        """Mark the release edge. Call this on the KEYUP frame of the
        charge key. The flag is consumed by the next `update` call.
        """
        self.charge_released_this_frame = True

    def update(self, dt: float, held: bool, threshold: float | None) -> None:
        """Per-frame tick. MUST be called once per frame, BEFORE the
        dispatch code that reads `charge_released_this_frame` or
        `last_charge_complete`.

        Args:
            dt: seconds since last frame. Typically 1/60 to 1/120.
            held: True iff the charge key is currently held. Wire this
                from your input poll (e.g. `keys[pygame.K_SPACE]`).
            threshold: per-weapon charge time in seconds. Three
                semantic categories:
                  - None  -> the weapon has no charge behavior. The
                    `charging` flag is still updated (so other systems
                    can read it), but `charge_time` and
                    `charge_complete` stay at 0 / False.
                  - 0.0   -> "continuous". `charge_complete` is
                    always True while held; the weapon is "ready" the
                    instant the key goes down. Use this for beams and
                    continuous streams where the held boolean IS the
                    trigger, not a time gate.
                  - >0.0  -> "release-after-full-charge". `charge_complete`
                    is True only once `charge_time >= threshold`. The
                    dispatch branch should fire the charged shot on
                    the release edge AND only if `last_charge_complete`
                    was True.
        """
        # 1. Snapshot charge_complete BEFORE we possibly reset it.
        # The release frame's `held` is already False, so without this
        # snapshot the dispatch branch can't tell "they held long
        # enough" from "they tapped".
        self.last_charge_complete = self.charge_complete

        # 2. Consume the edges. They live for exactly one frame.
        self.charge_pressed_this_frame = False
        self.charge_released_this_frame = False

        # 3. Accumulate or reset. The order matters: reset on the
        # `not held` branch is unconditional (a fresh press starts
        # from 0, not from the previous press's residue).
        if held:
            self.charging = True
            if threshold is not None:
                self.charge_time += dt
                if threshold <= 0.0:
                    # Continuous weapons: threshold is 0.0 but the
                    # weapon still "charges" — the held bool is what
                    # gates the behavior. Mark complete so the
                    # dispatch can read it as "ready".
                    self.charge_complete = True
                else:
                    self.charge_complete = self.charge_time >= threshold
        else:
            self.charging = False
            self.charge_time = 0.0
            self.charge_complete = False
            # Reset the extra timer too — if the player released, any
            # partial interval resets. (The continuous-stream weapon
            # can re-arm by holding again.)
            self.extra_spawn_timer = 0.0

    def tick_extra_spawn_timer(self, dt: float) -> None:
        """Advance the auxiliary timer. The dispatch branch checks
        `extra_spawn_timer >= interval` and resets it to 0 after a
        spawn. Call this from `update` ONLY for weapons that use the
        continuous-stream pattern (Branch C in DESIGN.md).
        """
        self.extra_spawn_timer += dt


__all__ = ["ChargedShotState"]
