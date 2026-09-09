"""Player entity — horizontal fighter controlled by WASD/Arrows +
B (metralleta / tap fire) and Space (cargado / charge mechanic).

v1.6 control scheme:
  B (tap)         -> tier-1 basic bullet per weapon (cooldown-based)
  SPACE (hold+rel)-> tier-2 charged shot per weapon (charge mechanic)
                     or continuous beam for weapon 0
  WASD / arrows   -> movement
"""
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

    # Per-weapon tuning. `weapon` is an int 0..4 chosen by the
    # gameplay scene via set_weapon(); the same index is used to
    # pick a laser_NN sprite and a cooldown / muzzle velocity.
    # 2026-09-08 v1.5 final: 5 weapons only. The original v1.4 10-
    # weapon set was reduced -- the 5 "basic" archetypes (yellow
    # plasma, red pulse, blue ion, green acid, purple void) were
    # removed because the 4 charged archetypes (orange fire, white
    # piercing, magenta heart, cyan ice) read as the "real" arsenal,
    # and the original rainbow streak was kept as the 5th slot as a
    # simple tap-only fallback.
    # Mapping (new slot -> archetype):
    #   0 orange fire      (was old slot 5, archetype 6) -- beam on SPACE
    #   1 white piercing   (was old slot 6, archetype 7) -- Megaman bolt
    #   2 magenta heart    (was old slot 7, archetype 8) -- boomerang
    #   3 cyan ice         (was old slot 8, archetype 5) -- piercing stream
    #   4 rainbow streak   (was old slot 9, archetype 4) -- tap-only
    WEAPON_COOLDOWN_S = (
        0.14,  # 0 orange fire (B = bullets, SPACE = beam)
        0.09,  # 1 white piercing (B = basic, SPACE = Megaman bolt on release)
        0.11,  # 2 magenta heart (B = basic, SPACE = boomerang on release)
        0.13,  # 3 cyan ice (B = basic, SPACE = piercing crystals every 1.5s)
        0.10,  # 4 rainbow streak (B = tap-only, SPACE = no-op)
    )
    WEAPON_BULLET_SPEED = (
        400.0,  # 0 orange fire basic
        800.0,  # 1 white piercing -- very fast
        460.0,  # 2 magenta heart
        420.0,  # 3 cyan ice
        600.0,  # 4 rainbow streak
    )

    # Max-lives constants. `MAX_LIVES` is the starting cap (3).
    # Gold rings can push it up to `MAX_LIVES_ABSOLUTE` (9) in two
    # +3 stacks: 3 -> 6 -> 9.
    MAX_LIVES = 3
    MAX_LIVES_ABSOLUTE = 9
    # Gold ring count needed per stack gain.
    GOLD_RINGS_PER_STACK = 3

    # 2026-09-08 v1.5: charge mechanic. Per-weapon charge time in
    # seconds. None = no charge behavior (tap-only). Weapons 0/3 use
    # 0.0 to mean "continuous (charge time doesn't gate the behavior)".
    # Weapons 1/2 use 1.2s/1.5s to fully charge before the
    # release-time charged shot spawns.
    # 2026-09-08 v1.6: charge is on SPACE key (was on the fire key
    # in v1.5). Threshold semantics unchanged.
    CHARGE_TIME_S: tuple[float | None, ...] = (
        0.0,   # 0 orange fire      -- continuous beam
        1.2,   # 1 white piercing   -- Megaman charged shot at full charge
        1.5,   # 2 magenta heart    -- boomerang at full charge
        0.0,   # 3 cyan ice         -- continuous piercing stream
        None,  # 4 rainbow streak   -- tap-only (SPACE is no-op)
    )
    # 2026-09-08 v1.5: per-weapon stream spawn interval (for weapon 3).
    PIERCING_SPAWN_INTERVAL_S: tuple[float, ...] = (
        0.0,  # 0 (unused: beam, not stream)
        0.0,  # 1
        0.0,  # 2
        1.5,  # 3 cyan ice -- every 1.5s while SPACE is held
        0.0,  # 4
    )

    __slots__ = (
        "x", "y", "vx", "vy", "lives", "max_lives", "shoot_cooldown",
        "invulnerable_frames", "alive", "firing", "charging", "thrusting",
        "bullets", "weapon", "_now",
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
        # 2026-09-08 v1.5 -> v1.6: charge mechanic state.
        # `firing` and `tap_pressed_this_frame` / `tap_released_this_frame`
        # are bound to the B key (metralleta). `charging` and
        # `charge_pressed_this_frame` / `charge_released_this_frame` are
        # bound to SPACE (charged shot).
        "tap_pressed_this_frame",     # bool - true only on the B KEYDOWN frame
        "tap_released_this_frame",    # bool - true only on the B KEYUP frame
        "charge_pressed_this_frame",  # bool - true only on SPACE KEYDOWN
        "charge_released_this_frame", # bool - true only on SPACE KEYUP
        "charge_time",                # seconds SPACE has been held (0 if not)
        "charge_complete",            # bool - charge_time >= CHARGE_TIME_S[weapon]
        "_piercing_spawn_timer",      # seconds since last piercing spawn
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
        # 2026-09-08 v1.6: split B (firing = tap) from SPACE (charging).
        self.firing: bool = False
        self.charging: bool = False
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
        # 2026-09-08 v1.6: split edge flags into B (tap) and SPACE
        # (charge). Each is reset to False at the top of update().
        self.tap_pressed_this_frame: bool = False
        self.tap_released_this_frame: bool = False
        self.charge_pressed_this_frame: bool = False
        self.charge_released_this_frame: bool = False
        self.charge_time: float = 0.0
        self.charge_complete: bool = False
        self._piercing_spawn_timer: float = 0.0

    def set_weapon(self, weapon: int) -> None:
        """Switch to a new weapon (0..4). No-op if already on it."""
        if 0 <= weapon < len(self.WEAPON_COOLDOWN_S) and weapon != self.weapon:
            self.weapon = weapon
            # 2026-09-08 v1.5: switching weapons cancels any in-progress
            # charge (so the new weapon's charge state starts clean).
            # 2026-09-08 v1.6: also mark both edges as released so a
            # held key on the previous weapon doesn't bleed into the
            # new weapon's logic.
            self.charge_time = 0.0
            self.charge_complete = False
            self._piercing_spawn_timer = 0.0
            self.tap_released_this_frame = True
            self.charge_released_this_frame = True

    def on_tap_pressed(self) -> None:
        """Called by the scene on the B KEYDOWN frame.
        Marks the press so update() can dispatch the basic-shot path.
        """
        self.tap_pressed_this_frame = True

    def on_tap_released(self) -> None:
        """Called by the scene on the B KEYUP frame.
        Marks the release so update() can reset the tap-fire state.
        """
        self.tap_released_this_frame = True

    def on_charge_pressed(self) -> None:
        """Called by the scene on the SPACE KEYDOWN frame.
        Marks the press so update() can start the charge cycle.
        """
        self.charge_pressed_this_frame = True

    def on_charge_released(self) -> None:
        """Called by the scene on the SPACE KEYUP frame.
        Marks the release so update() can fire the charged shot
        (weapons 1, 2) or end the beam (weapon 0) or stop the
        stream (weapon 3).
        """
        self.charge_released_this_frame = True

    def update(self, dt: float, keys, bullets_pool, now: float = 0.0) -> None:
        if self.dying:
            # Death sequence: tick timer, skip all normal logic
            self.dying_time += dt
            if self.dying_time >= 1.5:
                self.dead = True
            return
        if not self.alive:
            return
        # 2026-09-08 v1.6: edge-trigger flags from gameplay.py.
        # B (tap) and SPACE (charge) are independent edges.
        tap_pressed = self.tap_pressed_this_frame
        tap_released = self.tap_released_this_frame
        charge_pressed = self.charge_pressed_this_frame
        charge_released = self.charge_released_this_frame
        # Capture charge_complete BEFORE the charging-state branch
        # resets it, so the release dispatch can still see "yes, we
        # reached the threshold before the player released".
        charge_complete_before_release = self.charge_complete
        self.tap_pressed_this_frame = False
        self.tap_released_this_frame = False
        self.charge_pressed_this_frame = False
        self.charge_released_this_frame = False
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
        # 2026-09-08 v1.6: charge mechanic is driven by SPACE (charging),
        # NOT by B (firing). charge_time accumulates while SPACE is
        # held. The dispatch in the bottom of update() reads this state
        # to decide: beam (weapon 0), charged shot on release (1, 2),
        # piercing stream (3), or no-op (4).
        charge_threshold = self.CHARGE_TIME_S[self.weapon] if self.weapon < len(self.CHARGE_TIME_S) else None
        if self.charging:
            if charge_threshold is not None:
                self.charge_time += dt
                # `charge_complete` is true once we've hit the threshold
                # (or immediately for threshold=0.0 continuous weapons).
                if charge_threshold <= 0.0:
                    self.charge_complete = True
                else:
                    self.charge_complete = self.charge_time >= charge_threshold
        else:
            # SPACE released (or never pressed): reset charge state.
            # The charge_released_this_frame flag was already captured
            # at the top of update() and is dispatched below.
            self.charge_time = 0.0
            self.charge_complete = False
            self._piercing_spawn_timer = 0.0
        # 2026-09-08 v1.6: per-weapon fire dispatch.
        # B (firing) drives the tier-1 basic shot on cooldown.
        # SPACE (charging) drives the tier-2 charged behavior:
        #   - Weapon 0 (orange fire): continuous beam while held.
        #   - Weapon 1 (white piercing): release-after-full-charge = megaman bolt.
        #   - Weapon 2 (magenta heart): release-after-full-charge = boomerang.
        #   - Weapon 3 (cyan ice): while held, every 1.5s spawn 1 piercing crystal.
        #   - Weapon 4 (rainbow streak): SPACE is no-op (tap-only via B).
        # Tier-1: B held -> basic shot on cooldown.
        if self.firing and self.shoot_cooldown <= 0.0 and bullets_pool:
            self._spawn_bullet(bullets_pool)
            # Cooldown matches the currently equipped weapon so
            # switching to a faster weapon immediately changes cadence.
            self.shoot_cooldown = self.WEAPON_COOLDOWN_S[self.weapon]
        # Tier-2: SPACE held -> weapon-specific continuous behavior.
        # Weapon 3 (cyan ice) piercing-stream timer.
        if self.charging and self.weapon == 3:
            spawn_interval = self.PIERCING_SPAWN_INTERVAL_S[self.weapon]
            if spawn_interval > 0.0:
                self._piercing_spawn_timer += dt
                if self._piercing_spawn_timer >= spawn_interval:
                    if bullets_pool and self.shoot_cooldown <= 0.0:
                        self._spawn_bullet(bullets_pool, damage=2, piercing=True)
                        self._piercing_spawn_timer = 0.0
        # Tier-2: SPACE released -> fire the charged shot.
        # For weapons 1 (white piercing) and 2 (magenta heart),
        # holding SPACE past the charge threshold enables a release-
        # triggered charged shot -- a single big bullet with extra
        # damage and/or special behavior (Megaman bolt, boomerang).
        if charge_released and self.weapon in (1, 2) and bullets_pool:
            threshold = self.CHARGE_TIME_S[self.weapon] if self.weapon < len(self.CHARGE_TIME_S) else None
            # Use the captured charge_complete (pre-reset) so a
            # release after a full charge still fires the charged
            # shot. Without this, the release frame's charging=False
            # would have already reset charge_complete to False.
            if threshold is not None and threshold > 0.0 and charge_complete_before_release:
                if self.weapon == 1:
                    # Megaman charged bolt: 3x damage, normal size.
                    self._spawn_bullet(bullets_pool, damage=3)
                elif self.weapon == 2:
                    # Boomerang heart: flies out, then comes back
                    # after 0.6s. Does 2x damage on the way out
                    # AND 2x on the return.
                    self._spawn_bullet(
                        bullets_pool, damage=2, returning=True, return_at=0.6
                    )
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

    def _spawn_bullet(self, bullets_pool, damage: int = 1,
                      piercing: bool = False, returning: bool = False,
                      return_at: float = 0.6) -> None:
        """Spawn one bullet from the player.

        2026-09-08 v1.5: optional flags for charged shots.
        - damage: 1 for normal, 3 for Megaman bolt.
        - piercing: True for cyan ice piercing stream.
        - returning: True for magenta heart boomerang.
        - return_at: seconds before boomerang flips direction.
        """
        from stellar_horizon.entities.bullet import PlayerBullet
        # 2026-09-06 polish: dedicated `laser_fire` SFX (fast sawtooth
        # pitch drop) plays on every shot. The legacy `shoot` /
        # `shoot_charged` blips are still dispatched right after for
        # per-weapon variety (light vs heavy feel) -- the synth plays
        # them on top of the laser, blending into a richer "zap".
        from stellar_horizon.audio import sfx
        sfx.play_event("laser_fire")
        # Per-weapon flavor:
        #   - Charged weapons (1, 2) use a heavier blip.
        #   - Continuous beam (0) is silent here; the beam entity
        #     has its own per-tick sound.
        #   - Tap-only (4) uses the basic "shoot" blip.
        # 2026-09-08 v1.6: tier-1 B-key shot uses "shoot"; tier-2
        # charged shot (called with damage>1) uses "shoot_charged".
        if damage > 1 or piercing or returning:
            sfx.play_event("shoot_charged")
        else:
            sfx.play_event("shoot")
        # Spawn the bullet from the muzzle position (not the body).
        # Bullets always travel in +X.
        # 2026-09-08 v1.6: the bullet pool entry is reused if it
        # already has an active bullet; this is the standard pool
        # pattern.
        b = None
        for entry in bullets_pool:
            if not entry.alive:
                b = entry
                break
        if b is None:
            return
        b.spawn(
            x=self.x + self.BULLET_OFFSET_X,
            y=self.y,
            vx=self.WEAPON_BULLET_SPEED[self.weapon],
            vy=0.0,
            weapon=self.weapon,
            spawn_time=self._now,
            damage=damage,
            piercing=piercing,
            returning=returning,
            return_at=return_at,
        )
