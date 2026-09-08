"""Player entity — horizontal fighter controlled by WASD/Arrows + Spacebar."""
from __future__ import annotations

import pygame

from stellar_horizon.fx.engine_flames import EngineFlame


class Player:
    SPEED = 165.0
    SHOOT_COOLDOWN_S = 0.10
    BULLET_OFFSET_X = 12
    IFRAMES_FRAMES = 30
    INVULN_FRAMES_PER_HIT = 30
    BOUND_X_MIN = 8
    BOUND_X_MAX = 472
    BOUND_Y_MIN = 16
    BOUND_Y_MAX = 254
    START_X = 40.0

    # Per-weapon tuning. `weapon` is an int 0..9 chosen by the
    # gameplay scene via set_weapon(); the same index is used to
    # pick a laser_NN sprite and a cooldown / muzzle velocity.
    WEAPON_COOLDOWN_S = (
        0.10,  # 0 yellow plasma
        0.10,  # 1 red pulse
        0.07,  # 2 blue ion (very fast)
        0.18,  # 3 green acid (slow, heavy)
        0.12,  # 4 purple void
        0.14,  # 5 orange fireball
        0.09,  # 6 white piercing (fast, long range)
        0.11,  # 7 pink heart
        0.13,  # 8 cyan ice
        0.10,  # 9 rainbow streak
    )
    WEAPON_BULLET_SPEED = (
        480.0,
        460.0,
        700.0,
        380.0,
        440.0,
        400.0,
        800.0,
        460.0,
        420.0,
        600.0,
    )

    # Max-lives constants. `MAX_LIVES` is the starting cap (3).
    # Gold rings can push it up to `MAX_LIVES_ABSOLUTE` (9) in two
    # +3 stacks: 3 -> 6 -> 9. `max_lives` is the runtime cap.
    MAX_LIVES = 3
    MAX_LIVES_ABSOLUTE = 9
    # Gold ring count needed per stack gain.
    GOLD_RINGS_PER_STACK = 3

    # 2026-09-08 v1.5: charge mechanic. Per-weapon charge time in
    # seconds. None = no charge behavior (tap-only). Weapons 5/8 use
    # 0.0 to mean "continuous (charge time doesn't gate the behavior)".
    # 2026-09-08: weapons 6/7 use 1.2s/1.5s to fully charge before the
    # release-time charged shot spawns.
    CHARGE_TIME_S: tuple[float | None, ...] = (
        None,  # 0 yellow plasma — tap-only
        None,  # 1 red pulse — tap-only
        None,  # 2 blue ion — tap-only
        None,  # 3 green acid — tap-only
        None,  # 4 purple void — tap-only
        0.0,   # 5 orange fireball — continuous beam (no threshold)
        1.2,   # 6 white piercing — Megaman charged shot at full charge
        1.5,   # 7 magenta heart — boomerang at full charge
        0.0,   # 8 cyan ice — continuous piercing stream
        None,  # 9 rainbow streak — tap-only
    )
    # 2026-09-08 v1.5: per-weapon stream spawn interval (for weapon 8).
    PIERCING_SPAWN_INTERVAL_S: tuple[float, ...] = (
        0.0, 0.0, 0.0, 0.0, 0.0,
        0.0, 0.0, 0.0,
        1.5,  # 8 cyan ice — every 1.5s while held
        0.0,
    )

    __slots__ = (
        "x", "y", "vx", "vy", "lives", "max_lives", "shoot_cooldown",
        "invulnerable_frames", "alive", "firing", "thrusting", "bullets",
        "weapon", "_now",
        "gold_stacks", "gold_rings_collected",
        # VFX (visual polish)
        "flame",  # EngineFlame
        "fx",     # FxLayer reference for trail emission
        "_trail_thrust_cooldown",  # seconds until next thrust-trail emit
        # Hit/death sequence (visual polish)
        "hit_flash",    # seconds remaining of red flash
        "dying",        # bool - in death animation
        "dying_time",   # seconds elapsed in death sequence
        "dead",         # bool - death animation complete
        # 2026-09-08 v1.5: charge mechanic state
        "fire_pressed_this_frame",  # bool - true only on the KEYDOWN frame
        "fire_released_this_frame", # bool - true only on the KEYUP frame
        "charge_time",              # seconds fire has been held (0 if not)
        "charge_complete",          # bool - charge_time >= CHARGE_TIME_S[weapon]
        "_piercing_spawn_timer",    # seconds since last piercing spawn
    )

    def __init__(self, screen_rect: pygame.Rect) -> None:
        self.x: float = self.START_X
        self.y: float = float(screen_rect.centery)
        self.vx: float = 0.0
        self.vy: float = 0.0
        self.lives: int = self.MAX_LIVES
        # Runtime cap. Grows by 3 each time the player collects 3
        # gold rings (up to MAX_LIVES_ABSOLUTE).
        self.max_lives: int = self.MAX_LIVES
        self.shoot_cooldown: float = 0.0
        self.invulnerable_frames: int = 0
        self.alive: bool = True
        self.firing: bool = False
        self.thrusting: bool = False
        self.bullets: list = []
        self.weapon: int = 0
        # Scene time, written by update() so _spawn_bullet can stamp
        # the new bullet with `spawn_time` for the VFX to use.
        self._now: float = 0.0
        # Gold ring stack tracking. `gold_rings_collected` counts
        # total gold rings (used to decide when to bump `max_lives`).
        # `gold_stacks` is the derived count (0, 1, or 2).
        self.gold_rings_collected: int = 0
        self.gold_stacks: int = 0
        # VFX (visual polish)
        self.flame = EngineFlame(base_color=(100, 200, 255))  # cyan
        self.fx = None  # FxLayer injected by GameplayScene on_enter
        self._trail_thrust_cooldown: float = 0.0
        # Hit/death sequence state
        self.hit_flash: float = 0.0
        self.dying: bool = False
        self.dying_time: float = 0.0
        self.dead: bool = False
        # 2026-09-08 v1.5: charge mechanic state (reset every frame)
        self.fire_pressed_this_frame: bool = False
        self.fire_released_this_frame: bool = False
        self.charge_time: float = 0.0
        self.charge_complete: bool = False
        self._piercing_spawn_timer: float = 0.0

    def set_weapon(self, weapon: int) -> None:
        """Switch to a new weapon (0..9). No-op if already on it."""
        if 0 <= weapon < len(self.WEAPON_COOLDOWN_S) and weapon != self.weapon:
            self.weapon = weapon
            # 2026-09-08 v1.5: switching weapons cancels any in-progress
            # charge (so the new weapon's charge state starts clean).
            self.charge_time = 0.0
            self.charge_complete = False
            self._piercing_spawn_timer = 0.0
            # Mark as released so a held key on the previous weapon
            # doesn't fire a charged shot for the new weapon.
            self.fire_released_this_frame = True

    def on_fire_pressed(self) -> None:
        """Called by the scene on the KEYDOWN frame of the fire key.
        Marks the press so update() can dispatch the tap/charge logic.
        """
        self.fire_pressed_this_frame = True

    def on_fire_released(self) -> None:
        """Called by the scene on the KEYUP frame of the fire key.
        Marks the release so update() can fire charged shots (weapons
        6, 7) or end the beam (weapon 5) or stop the stream (weapon 8).
        """
        self.fire_released_this_frame = True

    def update(self, dt: float, keys, bullets_pool, now: float = 0.0) -> None:
        if self.dying:
            # Death sequence: tick timer, skip all normal logic
            self.dying_time += dt
            if self.dying_time >= 1.5:
                self.dead = True
            return
        if not self.alive:
            return
        # 2026-09-08 v1.5: edge-trigger flags from gameplay.py. These
        # are set by on_fire_pressed/on_fire_released on the KEYDOWN/
        # KEYUP frames, and consumed/reset here at the start of update.
        pressed_this_frame = self.fire_pressed_this_frame
        released_this_frame = self.fire_released_this_frame
        self.fire_pressed_this_frame = False
        self.fire_released_this_frame = False
        # Cache the scene time so _spawn_bullet can stamp the bullet
        # with the same value the VFX will read later.
        self._now = now
        # `keys` is normally a pygame ScancodeWrapper from
        # pygame.key.get_pressed(). Tests sometimes pass a plain dict
        # with only a few entries; use .get() with a False default so
        # missing keys don't raise.
        def _k(k: int) -> bool:
            try:
                return bool(keys[k])
            except (KeyError, IndexError, TypeError):
                return False
        dx = int(_k(pygame.K_d) or _k(pygame.K_RIGHT)) - int(_k(pygame.K_a) or _k(pygame.K_LEFT))
        dy = int(_k(pygame.K_s) or _k(pygame.K_DOWN))  - int(_k(pygame.K_w) or _k(pygame.K_UP))
        if dx and dy:
            inv = 0.7071067811865475
            self.vx = dx * self.SPEED * inv
            self.vy = dy * self.SPEED * inv
            self.thrusting = True
        elif dx or dy:
            self.vx = dx * self.SPEED
            self.vy = dy * self.SPEED
            self.thrusting = True
        else:
            self.vx = self.vy = 0.0
            self.thrusting = False
        self.x = max(self.BOUND_X_MIN, min(self.BOUND_X_MAX, self.x + self.vx * dt))
        self.y = max(self.BOUND_Y_MIN, min(self.BOUND_Y_MAX, self.y + self.vy * dt))
        self.shoot_cooldown = max(0.0, self.shoot_cooldown - dt)
        # 2026-09-08 v1.5: charge mechanic. Update charge_time and
        # charge_complete based on whether fire is held. This runs
        # BEFORE the bullet-spawn block so the spawn decision can
        # read the current charge state.
        charge_threshold = self.CHARGE_TIME_S[self.weapon] if self.weapon < len(self.CHARGE_TIME_S) else None
        if self.firing:
            # Held: accumulate charge time.
            if charge_threshold is not None:
                self.charge_time += dt
                # `charge_complete` is true once we've hit the threshold
                # (or immediately for threshold=0.0 continuous weapons).
                if charge_threshold <= 0.0:
                    self.charge_complete = True
                else:
                    self.charge_complete = self.charge_time >= charge_threshold
        else:
            # Released (or never pressed): no charge, but the
            # fire_released_this_frame flag was already captured at
            # the top of update() — the scene sets it on KEYUP. The
            # charged-shot dispatch (weapons 6, 7) happens at the
            # bottom of this update.
            self.charge_time = 0.0
            self.charge_complete = False
            self._piercing_spawn_timer = 0.0
        # 2026-09-08 v1.5: per-weapon fire dispatch.
        #   - Weapons 0-4, 9: tap-only (existing behavior).
        #   - Weapon 5 (orange fire): continuous beam while held.
        #   - Weapon 6 (white piercing): tap = bolt, release-after-full-charge = megaman bolt.
        #   - Weapon 7 (magenta heart): tap = heart, release-after-full-charge = boomerang.
        #   - Weapon 8 (cyan ice): while held, every 1.5s spawn 1 piercing crystal.
        # 2026-09-08 v1.5: weapon 8 (cyan ice) piercing-stream timer.
        # This runs every frame the fire key is held, regardless of
        # whether the bullet pool has an open slot — the timer should
        # always advance so the next available slot spawns on time.
        if self.firing and self.weapon == 8:
            spawn_interval = self.PIERCING_SPAWN_INTERVAL_S[self.weapon]
            if spawn_interval > 0.0:
                self._piercing_spawn_timer += dt
                if self._piercing_spawn_timer >= spawn_interval:
                    if bullets_pool and self.shoot_cooldown <= 0.0:
                        self._spawn_bullet(bullets_pool)
                        self._piercing_spawn_timer = 0.0
        if self.firing and self.shoot_cooldown <= 0.0 and bullets_pool:
            if self.weapon == 5:
                # Continuous beam: spawn one small bolt per frame at the
                # muzzle. The actual BEAM entity is a future addition;
                # for v1.5 the "beam" is rendered as a stream of small
                # bolts that share the weapon's archetype sprite.
                self._spawn_bullet(bullets_pool)
                self.shoot_cooldown = 0.04  # ~25 bolts/s for a dense beam
            elif self.weapon == 8:
                # Piercing stream spawn was already handled above (the
                # timer advances outside the bullets_pool check, but
                # the actual spawn needs an open slot). Nothing to do
                # here.
                pass
            else:
                # All other weapons: normal cooldown-based tap fire.
                self._spawn_bullet(bullets_pool)
                # Cooldown matches the currently equipped weapon so
                # switching to a faster weapon (e.g. blue ion) immediately
                # changes the cadence.
                self.shoot_cooldown = self.WEAPON_COOLDOWN_S[self.weapon]
        # 2026-09-08 v1.5: charged-shot dispatch on release. For
        # weapons 6 (white piercing) and 7 (magenta heart), holding
        # the fire key past the charge threshold enables a release-
        # triggered "charged shot" — a single big bullet with extra
        # damage and/or special behavior (Megaman bolt, boomerang).
        # `released_this_frame` is set by the scene on KEYUP.
        if released_this_frame and self.weapon in (6, 7) and bullets_pool:
            threshold = self.CHARGE_TIME_S[self.weapon] if self.weapon < len(self.CHARGE_TIME_S) else None
            # Only fire the charged shot if the player actually
            # charged (otherwise a quick tap just fires the normal
            # shot via the cooldown path above, and the release here
            # is a no-op).
            if threshold is not None and threshold > 0.0 and self.charge_complete:
                self._spawn_bullet(bullets_pool)
                # Short cooldown so the charged shot doesn't stack
                # with a follow-up normal shot.
                self.shoot_cooldown = 0.4
        if self.invulnerable_frames > 0:
            self.invulnerable_frames -= 1
        if self.hit_flash > 0:
            self.hit_flash = max(0.0, self.hit_flash - dt)
        # --- Visual polish: 2-layer trail ---
        # Capa 1: aura tenue SIEMPRE (intensity 0.30, no requiere thrusting)
        if self.alive and self.fx is not None:
            self.fx.emit_trail(self.x - 6, self.y, (100, 200, 255), intensity=0.30)
        # Capa 2: destello brillante al moverse, throttled a ~30Hz
        if self.alive and self.thrusting and self.fx is not None:
            self._trail_thrust_cooldown -= dt
            if self._trail_thrust_cooldown <= 0.0:
                self.fx.emit_trail(self.x - 6, self.y, (200, 230, 255), intensity=1.0)
                self._trail_thrust_cooldown = 1.0 / 30.0

    def take_hit(self, amount: int = 1) -> None:
        """Apply `amount` damage from a single hit.

        Boss damage is 2 (contact AND bullets) so the player has to
        manage their life budget carefully. Enemy bullets are 1,
        kamikaze contact is 2 (already handled by the caller calling
        take_hit() once per damage point).
        """
        if not self.alive or self.invulnerable_frames > 0 or self.dying:
            return
        self.lives -= amount
        self.hit_flash = 0.3  # visual hit feedback
        if self.lives <= 0:
            self.lives = 0
            # Start death sequence: alive=False but `dying=True` keeps update
            # running for the death animation. The GameplayScene waits
            # for `dead=True` before transitioning to game-over.
            self.alive = False
            self.dying = True
            self.dying_time = 0.0
            if self.fx is not None:
                self.fx.emit_player_death(self.x, self.y)
        else:
            self.invulnerable_frames = self.INVULN_FRAMES_PER_HIT
            if self.fx is not None:
                self.fx.emit_player_hit(self.x, self.y)

    def heal(self, amount: int) -> int:
        """Restore up to `amount` lives, capped at max_lives.

        Returns the actual amount healed (0 if already full).
        """
        if not self.alive:
            return 0
        before = self.lives
        self.lives = min(self.max_lives, self.lives + amount)
        return self.lives - before

    def collect_gold_ring(self) -> bool:
        """Register a gold ring pickup. Returns True if this pickup
        bumped the max_lives cap (i.e. just completed a stack).
        """
        self.gold_rings_collected += 1
        stacks_earned = self.gold_rings_collected // self.GOLD_RINGS_PER_STACK
        new_stacks = min(stacks_earned, 2)  # cap at 2 stacks
        if new_stacks > self.gold_stacks:
            self.gold_stacks = new_stacks
            # Each stack adds 3 lives to the cap (3 -> 6 -> 9).
            self.max_lives = min(self.MAX_LIVES_ABSOLUTE,
                                 self.MAX_LIVES + 3 * self.gold_stacks)
            return True
        return False

    def collect_silver_ring(self) -> None:
        """Silver ring: heal 1, no stack progress."""
        self.heal(1)

    def hitbox(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - 4), int(self.y - 4), 8, 8)

    def _spawn_bullet(self, bullets_pool) -> None:
        from stellar_horizon.entities.bullet import PlayerBullet
        # 2026-09-06 polish: dedicated `laser_fire` SFX (fast sawtooth
        # pitch drop) plays on every shot. The legacy `shoot` /
        # `shoot_charged` blips are still dispatched right after for
        # per-weapon variety (light vs heavy feel) — the synth plays
        # them on top of the laser, blending into a richer "zap".
        from stellar_horizon.audio import sfx
        sfx.play_event("laser_fire")
        sfx_name = "shoot_charged" if self.weapon in (3, 5, 7) else "shoot"
        for b in bullets_pool:
            if not b.alive:
                # 2026-09-06 visual polish v2: delegate the per-shot
                # state reset to PlayerBullet.spawn(). This is the
                # Task 5 review fix — the previous direct field
                # mutations didn't set weapon_archetype or reset
                # frame_elapsed/frame_index, so the 6-frame sheet
                # animation would never start on a re-spawned pool
                # slot.
                b.spawn(
                    x=self.x + self.BULLET_OFFSET_X,
                    y=self.y,
                    vx=self.WEAPON_BULLET_SPEED[self.weapon],
                    vy=0.0,
                    weapon=self.weapon,
                    spawn_time=self._now,
                )
                # Fire SFX (best-effort: no-op if audio is down).
                from stellar_horizon.audio import sfx
                sfx.play_event(sfx_name)
                return
