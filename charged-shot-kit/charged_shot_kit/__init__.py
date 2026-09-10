"""charged_shot_kit — drop-in charge mechanic for any 2D shmup.

A self-contained, engine-agnostic package implementing a Megaman-style
charge-and-release fire mechanic. See DESIGN.md in the repo root for
the full design rationale.

Submodules:
  state           — ChargedShotState (the 6 attributes + update logic)
  orb             — ShipChargeOrb.draw() (3-layer procedural muzzle FX)
  charged_bullet  — ChargedBullet (FSM, pool, collision protocol)

Example wiring is in examples/full_demo.py.
"""
from .state import ChargedShotState
from .orb import draw as draw_charge_orb
from .charged_bullet import ChargedBullet, State as ChargedBulletState

__all__ = [
    "ChargedShotState",
    "draw_charge_orb",
    "ChargedBullet",
    "ChargedBulletState",
]
