"""Capture screenshots of the demo at key states for visual evidence.

Headless — no display required. Renders 4 frames into 4 separate
files showing the charge mechanic in different states:
  1. idle (no charge)
  2. charging at 30% (orb body visible, core not)
  3. charging at 95% (full orb with pulse)
  4. mid-flight disc + impact

Run with:
    python capture_evidence.py
"""
from __future__ import annotations

import os
import sys
import math
import random

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from charged_shot_kit import ChargedBullet, ChargedShotState, draw_charge_orb


INTERNAL_W = 480
INTERNAL_H = 270
SCALE = 3
WINDOW_W = INTERNAL_W * SCALE
WINDOW_H = INTERNAL_H * SCALE


class _Player:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.weapon = 2
        self.charge_state = ChargedShotState()


class _Enemy:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.hp = 3
        self.alive = True

    def hitbox(self):
        return pygame.Rect(int(self.x - 8), int(self.y - 8), 16, 16)


def _draw_demo_frame(player, charged_pool, enemies, scene_time,
                     show_orb_manually=None):
    """Render one frame. `show_orb_manually` overrides the orb draw
    so we can fake different charge levels (the demo's update loop
    is the normal path, but for evidence captures we want static
    states at exact charge levels).
    """
    internal = pygame.Surface((INTERNAL_W, INTERNAL_H))
    internal.fill((10, 14, 26))
    # Grid.
    for x in range(0, INTERNAL_W, 24):
        pygame.draw.line(internal, (20, 24, 36), (x, 0), (x, INTERNAL_H))
    for y in range(0, INTERNAL_H, 24):
        pygame.draw.line(internal, (20, 24, 36), (0, y), (INTERNAL_W, y))
    # Enemies.
    for e in enemies:
        if e.alive:
            pygame.draw.rect(internal, (180, 80, 100), e.hitbox())
    # Charged discs.
    for b in charged_pool:
        if not b.alive:
            continue
        r = int(b.RADIUS * b.fade_scale() / 2)
        size = r * 2 + 4
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        alpha = b.fade_alpha()
        pygame.draw.circle(s, (255, 255, 255, alpha),
                           (size // 2, size // 2), r, 2)
        pygame.draw.circle(s, (180, 220, 255, alpha // 2),
                           (size // 2, size // 2), r - 4)
        internal.blit(s, (int(b.x - size // 2), int(b.y - size // 2)))
    # Player.
    points = [
        (int(player.x - 6), int(player.y + 4)),
        (int(player.x - 6), int(player.y - 4)),
        (int(player.x + 8), int(player.y)),
    ]
    pygame.draw.polygon(internal, (220, 240, 255), points)
    # Orb.
    if show_orb_manually is not None:
        charge_time, charging = show_orb_manually
        draw_charge_orb(
            internal, player.x + 10, player.y,
            weapon=player.weapon,
            charge_time=charge_time,
            charging=charging,
            now=scene_time,
        )
    # HUD label.
    font = pygame.font.SysFont("monospace", 12)
    label = font.render("charged_shot_kit — visual evidence", True, (200, 220, 240))
    internal.blit(label, (4, 4))
    return internal


def main():
    pygame.init()
    window = pygame.display.set_mode((WINDOW_W, WINDOW_H))

    # Frame 1: idle, no charge.
    player = _Player(60, INTERNAL_H // 2)
    enemies = [_Enemy(300 + i * 30, 60 + i * 30) for i in range(4)]
    charged_pool = []
    frame1 = _draw_demo_frame(player, charged_pool, enemies,
                              scene_time=0.0,
                              show_orb_manually=(0.0, False))
    frame1_scaled = pygame.transform.scale(frame1, (WINDOW_W, WINDOW_H))
    pygame.image.save(frame1_scaled, os.path.join(_HERE, "evidence_01_idle.png"))

    # Frame 2: charging at 30% (body visible, core not).
    player.charge_state.charge_time = 0.30  # 30% of 1.0s threshold
    player.charge_state.charging = True
    frame2 = _draw_demo_frame(player, charged_pool, enemies,
                              scene_time=0.10,
                              show_orb_manually=(0.30, True))
    frame2_scaled = pygame.transform.scale(frame2, (WINDOW_W, WINDOW_H))
    pygame.image.save(frame2_scaled, os.path.join(_HERE, "evidence_02_charge_30pct.png"))

    # Frame 3: charging at 95% (full orb with pulse phase peak).
    player.charge_state.charge_time = 0.95
    frame3 = _draw_demo_frame(player, charged_pool, enemies,
                              scene_time=1.0 / 32,  # pulse peak
                              show_orb_manually=(0.95, True))
    frame3_scaled = pygame.transform.scale(frame3, (WINDOW_W, WINDOW_H))
    pygame.image.save(frame3_scaled, os.path.join(_HERE, "evidence_03_charge_95pct.png"))

    # Frame 4: mid-flight disc, just hit an enemy, second hit incoming.
    player.charge_state.charge_time = 0.0
    player.charge_state.charging = False
    charged_pool = [ChargedBullet(), ChargedBullet()]
    charged_pool[0].spawn(x=180, y=player.y, now=0.0)
    charged_pool[0].state = "FLYING"  # already FLYING by default
    charged_pool[0].register_hit()    # first hit registered
    charged_pool[0].elapsed = 0.05
    charged_pool[0].x = 180  # position it where the enemy was
    frame4 = _draw_demo_frame(player, charged_pool, enemies,
                              scene_time=0.0)
    frame4_scaled = pygame.transform.scale(frame4, (WINDOW_W, WINDOW_H))
    pygame.image.save(frame4_scaled, os.path.join(_HERE, "evidence_04_disc_flying.png"))

    # Frame 5: FADING disc (the "burst" before disappearance).
    charged_pool[0].state = "FADING"
    charged_pool[0].fade_elapsed = 0.20  # halfway through fade
    charged_pool[0].vx = 0
    charged_pool[0].x = 250
    frame5 = _draw_demo_frame(player, charged_pool, enemies,
                              scene_time=0.0)
    frame5_scaled = pygame.transform.scale(frame5, (WINDOW_W, WINDOW_H))
    pygame.image.save(frame5_scaled, os.path.join(_HERE, "evidence_05_disc_fading.png"))

    # Composite: 5 frames in a 5x1 grid for the README.
    composite = pygame.Surface((WINDOW_W, WINDOW_H * 5))
    for i, frame in enumerate([frame1, frame2, frame3, frame4, frame5]):
        composite.blit(pygame.transform.scale(frame, (WINDOW_W, WINDOW_H)),
                       (0, i * WINDOW_H))
    pygame.image.save(composite, os.path.join(_HERE, "evidence_composite.png"))

    print("Captured 5 evidence frames + composite in", _HERE)
    for name in ("evidence_01_idle.png",
                 "evidence_02_charge_30pct.png",
                 "evidence_03_charge_95pct.png",
                 "evidence_04_disc_flying.png",
                 "evidence_05_disc_fading.png",
                 "evidence_composite.png"):
        path = os.path.join(_HERE, name)
        size = os.path.getsize(path) if os.path.exists(path) else 0
        print(f"  {name}  {size:,} bytes")


if __name__ == "__main__":
    main()
