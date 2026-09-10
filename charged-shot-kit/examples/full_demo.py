"""full_demo.py — a runnable pygame demo of the charged_shot_kit.

A complete, self-contained example showing the full mechanic in action:
  - Player ship (a small triangle you control with WASD / arrows)
  - Three weapons, switchable with 1 / 2 / 3:
      1: Basic tap-fire (B key only — no charge)
      2: Continuous beam (B for bullets, SPACE for beam while held)
      3: Release-charge (B for bullets, SPACE + release for a piercing disc)
  - Dummy enemies (gray squares) you can shoot
  - The 3-layer muzzle orb while SPACE is held on weapon 2 or 3
  - Piercing discs on weapon 3, with FSM FLYING -> FADING visible

Run with:
    python examples/full_demo.py

No external assets. No numpy. No dependencies beyond pygame.

The dispatch in `_update_player_weapon()` is the canonical example of
the 4-branch pattern from DESIGN.md section 3. Read that function
top-to-bottom; everything else is bookkeeping.
"""
from __future__ import annotations

import math
import os
import sys

# Make the parent dir (where charged_shot_kit/ lives) importable when
# running this file directly: `python examples/full_demo.py`.
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

import pygame

from charged_shot_kit import ChargedBullet, ChargedShotState, draw_charge_orb


# ---------------------------------------------------------------------------
# Constants — keep the demo self-contained, no external settings file.
# ---------------------------------------------------------------------------

INTERNAL_W = 480
INTERNAL_H = 270
SCALE = 3
WINDOW_W = INTERNAL_W * SCALE
WINDOW_H = INTERNAL_H * SCALE
FPS = 60
DT = 1.0 / FPS

# Colors
BG_COLOR = (10, 14, 26)
PLAYER_COLOR = (220, 240, 255)
BULLET_COLOR = (255, 240, 180)
DISC_COLOR = (255, 255, 255)
ENEMY_COLOR = (180, 80, 100)
BEAM_COLOR = (255, 140, 42)

# Per-weapon config. Three categories exercised in the demo:
#   weapon 0: tap-only (B key, no charge)
#   weapon 1: continuous beam (SPACE held)
#   weapon 2: release-charge disc (SPACE held, then released at full)
WEAPONS = {
    0: {
        "name": "BASIC",
        "color": (255, 240, 180),
        "charge_time_s": None,        # no charge behavior
        "tap_fire": True,
        "is_continuous": False,
        "is_release": False,
        "tap_cooldown_s": 0.12,
    },
    1: {
        "name": "BEAM",
        "color": (255, 140, 42),
        "charge_time_s": 0.0,         # continuous (held bool is trigger)
        "tap_fire": True,
        "is_continuous": True,
        "is_release": False,
        "tap_cooldown_s": 0.14,
    },
    2: {
        "name": "MEGAMAN",
        "color": (255, 255, 255),
        "charge_time_s": 1.0,         # release after 1.0s hold
        "tap_fire": True,
        "is_continuous": False,
        "is_release": True,
        "tap_cooldown_s": 0.10,
    },
}

# Pool sizes
PLAYER_BULLET_POOL = 32
CHARGED_BULLET_POOL = 2
ENEMY_COUNT = 5


# ---------------------------------------------------------------------------
# Minimal "entity" classes. Plain pygame.Surface blits, no sprites.
# ---------------------------------------------------------------------------

class Player:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.speed = 165.0
        self.hp = 3
        self.tap_cooldown = 0.0
        # The kit's state. Six attributes + snapshot.
        self.charge_state = ChargedShotState()
        # Active beam (weapon 1). Just an (alive, x1, y1, x2, y2).
        self.beam_alive = False
        self.beam_end_x = 0.0
        self.beam_end_y = 0.0
        # Weapon switch
        self.weapon = 0

    def hitbox(self):
        return pygame.Rect(int(self.x - 6), int(self.y - 6), 12, 12)

    def muzzle(self):
        return (self.x + 10, self.y)


class Bullet:
    """Normal tap-fire bullet. Different from ChargedBullet — this is
    the cheap projectile from B-key spam.
    """
    __slots__ = ("x", "y", "alive", "speed", "color")

    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.alive = False
        self.speed = 0.0
        self.color = (255, 255, 255)


class Enemy:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.hp = 3
        self.alive = True

    def hitbox(self):
        return pygame.Rect(int(self.x - 8), int(self.y - 8), 16, 16)


# ---------------------------------------------------------------------------
# The 4-branch dispatch. THIS is the canonical example of the
# pattern from DESIGN.md section 3. Read it top-to-bottom.
# ---------------------------------------------------------------------------

def update_player(player, dt, keys, events, bullets, charged_pool,
                  enemies, scene_time):
    """Per-frame player logic. Order is intentional:
      1. Process input edges (KEYDOWN/KEYUP -> state flags).
      2. Read held state from poll (keys[SPACE]).
      3. Update the ChargedShotState (snapshot + accumulate or reset).
      4. Branch A: tap fire (B).
      5. Branch C: continuous-charge behavior (weapon 1 beam).
      6. Branch D: release-charge behavior (weapon 2 disc).
      7. Tick the beam (weapon 1).
    """
    weapon_cfg = WEAPONS[player.weapon]
    threshold = weapon_cfg["charge_time_s"]

    # 1. Process input edges from the events list.
    for ev in events:
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_SPACE:
            player.charge_state.on_pressed()
        elif ev.type == pygame.KEYUP and ev.key == pygame.K_SPACE:
            player.charge_state.on_released()
        elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_b:
            player.charge_state.on_pressed()  # for tap fire, reuse the flag
        # 1/2/3 weapon switch.
        elif ev.type == pygame.KEYDOWN and ev.key in (pygame.K_1, pygame.K_2, pygame.K_3):
            new_w = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2}[ev.key]
            if new_w != player.weapon:
                player.weapon = new_w
                # Reset beam state — beam is per-weapon.
                player.beam_alive = False

    # 2. Held states.
    held_charge = keys[pygame.K_SPACE]
    held_tap = keys[pygame.K_b]

    # 3. Update the kit state. This snapshot+accumulate-or-reset
    #    function is the single most important call in the dispatch.
    player.charge_state.update(
        dt=dt,
        held=held_charge,
        threshold=threshold,
    )

    # Movement (independent of charge).
    dx = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(keys[pygame.K_a] or keys[pygame.K_LEFT])
    dy = int(keys[pygame.K_s] or keys[pygame.K_DOWN]) - int(keys[pygame.K_w] or keys[pygame.K_UP])
    if dx and dy:
        inv = 0.7071067811865475
        player.x += dx * player.speed * inv * dt
        player.y += dy * player.speed * inv * dt
    else:
        player.x += dx * player.speed * dt
        player.y += dy * player.speed * dt
    player.x = max(16, min(INTERNAL_W - 16, player.x))
    player.y = max(16, min(INTERNAL_H - 16, player.y))

    # Cooldowns.
    player.tap_cooldown = max(0.0, player.tap_cooldown - dt)

    # ------------------------------------------------------------------
    # BRANCH A: Tap fire (B key). Cooldown-based, weapon-agnostic.
    # ------------------------------------------------------------------
    if held_tap and player.tap_cooldown <= 0.0 and weapon_cfg["tap_fire"]:
        muzzle_x, muzzle_y = player.muzzle()
        for b in bullets:
            if not b.alive:
                b.x = muzzle_x
                b.y = muzzle_y
                b.speed = 480.0
                b.color = weapon_cfg["color"]
                b.alive = True
                break
        player.tap_cooldown = weapon_cfg["tap_cooldown_s"]

    # ------------------------------------------------------------------
    # BRANCH C: Continuous-charge behavior. Weapon 1 (beam).
    # While SPACE is held, the beam is alive; the beam end tracks
    # the nearest enemy in line of fire.
    # ------------------------------------------------------------------
    if weapon_cfg["is_continuous"]:
        if held_charge:
            mx, my = player.muzzle()
            # Find nearest enemy in the +X direction, within max length
            # and a vertical tolerance.
            max_end = mx + 200
            best_x, best_y = max_end, my
            for e in enemies:
                if not e.alive:
                    continue
                if e.x < mx - 4 or e.x > max_end:
                    continue
                if abs(e.y - my) > 32:
                    continue
                if e.x < best_x:
                    best_x, best_y = e.x, e.y
            player.beam_alive = True
            player.beam_end_x = best_x
            player.beam_end_y = best_y
            # Damage the enemy in the strip.
            if best_x < max_end:
                for e in enemies:
                    if e.alive and abs(e.y - my) < 32 and mx < e.x < max_end:
                        e.hp -= 1
                        if e.hp <= 0:
                            e.alive = False
        else:
            player.beam_alive = False

    # ------------------------------------------------------------------
    # BRANCH D: Release-charge behavior. Weapon 2 (Megaman disc).
    # On the release frame AND if the snapshot was True, spawn a
    # ChargedBullet from the pool.
    # ------------------------------------------------------------------
    if (weapon_cfg["is_release"]
            and player.charge_state.charge_released_this_frame
            and player.charge_state.last_charge_complete):
        muzzle_x, muzzle_y = player.muzzle()
        for slot in charged_pool:
            if not slot.alive:
                slot.spawn(x=muzzle_x, y=muzzle_y, now=scene_time)
                break
        player.tap_cooldown = 0.4  # short cooldown post-release

    # Update the normal bullets.
    for b in bullets:
        if b.alive:
            b.x += b.speed * dt
            if b.x > INTERNAL_W + 8:
                b.alive = False
            # Hit enemies.
            for e in enemies:
                if e.alive and b.alive:
                    if abs(b.x - e.x) < 8 and abs(b.y - e.y) < 8:
                        e.hp -= 1
                        if e.hp <= 0:
                            e.alive = False
                        b.alive = False
                        break

    # Update charged bullets. The pool handles its own FSM.
    for b in charged_pool:
        if b.alive:
            b.update(dt, world_width=INTERNAL_W)
            # Collision: b.hits(e) AND register_hit + damage.
            for e in enemies:
                if e.alive and b.hits(e):
                    damage = b.damage_for_hit()
                    e.hp -= damage
                    if e.hp <= 0:
                        e.alive = False
                    b.register_hit()
                    break  # one enemy per frame per bullet


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------

def draw_player(surface, player):
    # Tiny triangle.
    points = [
        (int(player.x - 6), int(player.y + 4)),
        (int(player.x - 6), int(player.y - 4)),
        (int(player.x + 8), int(player.y)),
    ]
    pygame.draw.polygon(surface, PLAYER_COLOR, points)


def draw_bullets(surface, bullets):
    for b in bullets:
        if b.alive:
            pygame.draw.circle(surface, b.color,
                               (int(b.x), int(b.y)), 2)


def draw_charged(surface, pool):
    """Draw the charged bullets as circles with the fade scale/alpha
    applied. The state machine is `b.fade_alpha()` (0..255) and
    `b.fade_scale()` (1.0..1.3).
    """
    for b in pool:
        if not b.alive:
            continue
        alpha = b.fade_alpha()
        scale = b.fade_scale()
        r = max(1, int(b.RADIUS * scale / 2))  # 40 -> 20px base, scaled
        # Build a per-pixel-alpha surface for the alpha.
        size = r * 2 + 4
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        # Outer ring
        pygame.draw.circle(s, (255, 255, 255, alpha),
                           (size // 2, size // 2), r, 2)
        # Inner body (slightly cyan-shifted white)
        pygame.draw.circle(s, (180, 220, 255, alpha // 2),
                           (size // 2, size // 2), r - 4)
        surface.blit(s, (int(b.x - size // 2), int(b.y - size // 2)))


def draw_enemies(surface, enemies):
    for e in enemies:
        if e.alive:
            pygame.draw.rect(surface, ENEMY_COLOR,
                             e.hitbox())


def draw_beam(surface, player):
    if not player.beam_alive:
        return
    mx, my = player.muzzle()
    pygame.draw.line(surface, BEAM_COLOR,
                     (int(mx), int(my)),
                     (int(player.beam_end_x), int(player.beam_end_y)),
                     4)
    # Glow
    pygame.draw.line(surface, (255, 200, 100),
                     (int(mx), int(my)),
                     (int(player.beam_end_x), int(player.beam_end_y)),
                     8)


def draw_hud(surface, player, scene_time):
    """Tiny HUD: weapon name + charge bar."""
    weapon = WEAPONS[player.weapon]
    font = pygame.font.SysFont("monospace", 12)
    name_surf = font.render(
        f"[1/2/3] {weapon['name']}  (B = tap, SPACE = charge)",
        True, (200, 220, 240))
    surface.blit(name_surf, (4, 4))
    # Charge bar (only for weapons that have a charge time).
    if weapon["charge_time_s"] is not None and weapon["charge_time_s"] > 0.0:
        charge_frac = min(1.0, player.charge_state.charge_time / weapon["charge_time_s"])
        bar_w = 60
        bar_h = 4
        x, y = 4, 22
        pygame.draw.rect(surface, (60, 60, 80), (x, y, bar_w, bar_h))
        pygame.draw.rect(surface, weapon["color"],
                         (x, y, int(bar_w * charge_frac), bar_h))
    # HP
    hp_surf = font.render(f"HP: {player.hp}", True, (200, 220, 240))
    surface.blit(hp_surf, (INTERNAL_W - 50, 4))


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    pygame.init()
    pygame.display.set_mode((WINDOW_W, WINDOW_H))
    clock = pygame.time.Clock()
    internal = pygame.Surface((INTERNAL_W, INTERNAL_H))
    window = pygame.display.get_surface()

    player = Player(60, INTERNAL_H // 2)
    bullets = [Bullet() for _ in range(PLAYER_BULLET_POOL)]
    charged_pool = [ChargedBullet() for _ in range(CHARGED_BULLET_POOL)]
    # Spawn enemies on the right side of the screen.
    enemies = [Enemy(330 + i * 28, 60 + (i * 35) % (INTERNAL_H - 80))
               for i in range(ENEMY_COUNT)]

    scene_time = 0.0
    running = True
    while running:
        events = pygame.event.get()
        for ev in events:
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                running = False
        keys = pygame.key.get_pressed()

        # Dispatch.
        update_player(
            player, DT, keys, events,
            bullets, charged_pool, enemies, scene_time,
        )

        # Draw.
        internal.fill(BG_COLOR)
        # Grid (subtle, for the retro feel).
        for x in range(0, INTERNAL_W, 24):
            pygame.draw.line(internal, (20, 24, 36), (x, 0), (x, INTERNAL_H))
        for y in range(0, INTERNAL_H, 24):
            pygame.draw.line(internal, (20, 24, 36), (0, y), (INTERNAL_W, y))
        draw_beam(internal, player)
        draw_enemies(internal, enemies)
        draw_bullets(internal, bullets)
        draw_charged(internal, charged_pool)
        draw_player(internal, player)
        # The muzzle orb. Drawn AFTER the player so it sits on top of
        # the ship's nose. Skips itself if not charging.
        mx, my = player.muzzle()
        draw_charge_orb(
            internal, mx, my,
            weapon=player.weapon,
            charge_time=player.charge_state.charge_time,
            charging=player.charge_state.charging,
            now=scene_time,
        )
        draw_hud(internal, player, scene_time)
        # Scale up to window.
        scaled = pygame.transform.scale(internal, (WINDOW_W, WINDOW_H))
        window.blit(scaled, (0, 0))
        pygame.display.flip()

        scene_time += DT
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
