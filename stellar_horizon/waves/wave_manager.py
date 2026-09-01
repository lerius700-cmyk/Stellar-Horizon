"""Wave scheduler: reads JSON, schedules spawns over time."""
from __future__ import annotations

import json
from pathlib import Path

from src.movement import BezierPath, HybridPath, PathFollower

from stellar_horizon.entities.enemy import Enemy, EnemyKind
from stellar_horizon.waves.bezier_horizontal import (
    path_boss_entry,
    path_boomerang,
    path_figure_eight,
    path_kamikaze_dive,
    path_loop_horizontal,
    path_pull_back,
    path_s_right_to_left,
    path_sine_bend,
    path_staircase,
    path_top_dive,
    path_ufo_entry,
    path_zigzag_exit_top,
)
from stellar_horizon.waves.formations_h import (
    boomerang_arc,
    diamond_pointing_left,
    line_horizontal,
    phalanx_box,
    rotating_ring,
    swept_wing,
    train_chain,
    v_pointing_left,
    wedge_pointing_left,
)
from stellar_horizon.waves.wave_specs import WaveSpec


# Default movement per enemy kind per wave (length 5: waves 1-5).
# When a wave JSON spawn doesn't specify path/formation, the defaults are used.
# UFO and KAMIKAZE keep their custom paths (ufo_entry, kamikaze_dive) per design spec.
_KIND_DEFAULTS_BY_WAVE: list[dict] = [
    # Wave 1 — intro
    {
        EnemyKind.SCOUT:    {"path": "sine_bend",         "formation": "line_horizontal"},
        EnemyKind.CRUISER:  {"path": "s_right_to_left",   "formation": "boomerang_arc"},
        EnemyKind.HEAVY:    {"path": "staircase",         "formation": "phalanx_box"},
        EnemyKind.BOMBER:   {"path": "s_right_to_left",   "formation": "train_chain"},
        EnemyKind.UFO:      {"path": "ufo_entry",         "formation": "line_horizontal"},
        EnemyKind.KAMIKAZE: {"path": "kamikaze_dive",     "formation": "v_pointing_left"},
    },
    # Wave 2 — scouts + cruisers
    {
        EnemyKind.SCOUT:    {"path": "figure_eight",      "formation": "line_horizontal"},
        EnemyKind.CRUISER:  {"path": "s_right_to_left",   "formation": "boomerang_arc"},
        EnemyKind.HEAVY:    {"path": "staircase",         "formation": "phalanx_box"},
        EnemyKind.BOMBER:   {"path": "s_right_to_left",   "formation": "train_chain"},
        EnemyKind.UFO:      {"path": "ufo_entry",         "formation": "line_horizontal"},
        EnemyKind.KAMIKAZE: {"path": "kamikaze_dive",     "formation": "v_pointing_left"},
    },
    # Wave 3 — heavies join
    {
        EnemyKind.SCOUT:    {"path": "boomerang",         "formation": "v_pointing_left"},
        EnemyKind.CRUISER:  {"path": "sine_bend",         "formation": "boomerang_arc"},
        EnemyKind.HEAVY:    {"path": "s_right_to_left",   "formation": "phalanx_box"},
        EnemyKind.BOMBER:   {"path": "s_right_to_left",   "formation": "train_chain"},
        EnemyKind.UFO:      {"path": "ufo_entry",         "formation": "line_horizontal"},
        EnemyKind.KAMIKAZE: {"path": "kamikaze_dive",     "formation": "v_pointing_left"},
    },
    # Wave 4 — bombers introduced
    {
        EnemyKind.SCOUT:    {"path": "sine_bend",         "formation": "v_pointing_left"},
        EnemyKind.CRUISER:  {"path": "s_right_to_left",   "formation": "swept_wing"},
        EnemyKind.HEAVY:    {"path": "staircase",         "formation": "phalanx_box"},
        EnemyKind.BOMBER:   {"path": "s_right_to_left",   "formation": "swept_wing"},
        EnemyKind.UFO:      {"path": "ufo_entry",         "formation": "line_horizontal"},
        EnemyKind.KAMIKAZE: {"path": "kamikaze_dive",     "formation": "v_pointing_left"},
    },
    # Wave 5 — UFO + kamikaze
    {
        EnemyKind.SCOUT:    {"path": "figure_eight",      "formation": "line_horizontal"},
        EnemyKind.CRUISER:  {"path": "sine_bend",         "formation": "boomerang_arc"},
        EnemyKind.HEAVY:    {"path": "s_right_to_left",   "formation": "phalanx_box"},
        EnemyKind.BOMBER:   {"path": "s_right_to_left",   "formation": "train_chain"},
        EnemyKind.UFO:      {"path": "ufo_entry",         "formation": "line_horizontal"},
        EnemyKind.KAMIKAZE: {"path": "kamikaze_dive",     "formation": "v_pointing_left"},
    },
]

# Fallback used when a kind has no entry in the wave's defaults (e.g. future kind added).
_KIND_FALLBACK: dict = {
    EnemyKind.SCOUT:    {"path": "s_right_to_left", "formation": "line_horizontal"},
    EnemyKind.CRUISER:  {"path": "s_right_to_left", "formation": "v_pointing_left"},
    EnemyKind.HEAVY:    {"path": "s_right_to_left", "formation": "diamond_pointing_left"},
    EnemyKind.BOMBER:   {"path": "s_right_to_left", "formation": "line_horizontal"},
    EnemyKind.UFO:      {"path": "ufo_entry",       "formation": "line_horizontal"},
    EnemyKind.KAMIKAZE: {"path": "kamikaze_dive",   "formation": "v_pointing_left"},
}


_PATH_BUILDERS = {
    "s_right_to_left": lambda kw: path_s_right_to_left(y_offset=kw.get("path_y_offset", 0)),
    "top_dive":         lambda kw: path_top_dive(side=kw.get("path_side", "right")),
    "zigzag_exit_top":  lambda kw: path_zigzag_exit_top(),
    "boss_entry":       lambda kw: path_boss_entry(),
    "ufo_entry":        lambda kw: path_ufo_entry(y_offset=kw.get("path_y_offset", 0)),
    "kamikaze_dive":    lambda kw: path_kamikaze_dive(y_offset=kw.get("path_y_offset", 0)),
    # New paths (Task 1)
    "sine_bend":        lambda kw: path_sine_bend(),
    "figure_eight":     lambda kw: path_figure_eight(),
    "boomerang":        lambda kw: path_boomerang(),
    "staircase":        lambda kw: path_staircase(),
    "loop_horizontal":  lambda kw: path_loop_horizontal(),
    "pull_back":        lambda kw: path_pull_back(),
}

_FORMATION_BUILDERS = {
    "v_pointing_left":       lambda count, spacing: v_pointing_left(count, spacing),
    "line_horizontal":       lambda count, spacing: line_horizontal(count, spacing),
    "diamond_pointing_left": lambda count, spacing: diamond_pointing_left(count, spacing),
    "wedge_pointing_left":   lambda count, spacing: wedge_pointing_left(count, spacing),
    # New formations (Task 2)
    "phalanx_box":           lambda count, spacing: phalanx_box(count, spacing),
    "swept_wing":            lambda count, spacing: swept_wing(count, spacing),
    "train_chain":           lambda count, spacing: train_chain(count, spacing),
    "boomerang_arc":         lambda count, spacing: boomerang_arc(count, spacing),
    "rotating_ring":         lambda count, spacing: rotating_ring(count, spacing),
}

_KIND_MAP = {
    "scout":     EnemyKind.SCOUT,
    "cruiser":   EnemyKind.CRUISER,
    "heavy":     EnemyKind.HEAVY,
    "bomber":    EnemyKind.BOMBER,
    "ufo":       EnemyKind.UFO,
    "kamikaze":  EnemyKind.KAMIKAZE,
}


def _path_to_hybrid(path) -> HybridPath:
    if isinstance(path, HybridPath):
        return path
    if isinstance(path, BezierPath):
        dur = max(0.5, path.length_estimate / 80.0)
        return HybridPath([path], [dur])
    return HybridPath([path], [4.0])


def _build_enemies(spawn: dict, sprite_picker=None) -> list[Enemy]:
    """Build the enemies for a single spawn entry, including chain expansion.

    If `chain_count >= 2`, the spawn is expanded into N independent chain links,
    each with its own set of formation_count enemies. The chain_count is clamped
    to 1-5.

    Args:
        spawn: dict from the wave JSON (formation/path/enemy_kind/chain_count).
        sprite_picker: optional callable `kind -> str` that returns the
            sprite variant name to assign to each enemy. If None, the
            enemy leaves sprite_name empty and the draw code falls back
            to the kind's default sprite.
    """
    chain_count = int(spawn.get("chain_count", 1))
    if chain_count < 1:
        chain_count = 1
    if chain_count > 5:
        import logging
        logging.warning("chain_count %d clamped to 5 (max)", chain_count)
        chain_count = 5

    formation_obj = _FORMATION_BUILDERS[spawn["formation"]](spawn["formation_count"], 18.0)
    # Dynamic formations return an object with .offsets(); static ones return a list.
    if hasattr(formation_obj, "offsets") and callable(formation_obj.offsets):
        offsets = formation_obj.offsets()
    else:
        offsets = formation_obj
    raw_path = _PATH_BUILDERS[spawn["path"]](spawn)
    hybrid = _path_to_hybrid(raw_path)
    kind = _KIND_MAP[spawn["enemy_kind"]]
    # Pick one sprite variant per spawn (not per enemy) so a 5-V
    # formation looks coherent — all five scouts wear the same paint.
    sprite_name = ""
    if sprite_picker is not None:
        sprite_name = sprite_picker(spawn["enemy_kind"]) or ""

    enemies: list[Enemy] = []
    for _chain_index in range(chain_count):
        for dx, dy in offsets:
            e = Enemy()
            e.kind = kind
            e.sprite_name = sprite_name
            e.on_spawn()
            follower = PathFollower(hybrid)
            e.attach_path(follower, slot_dx=dx, slot_dy=dy)
            enemies.append(e)
    return enemies


class WaveManager:
    def __init__(self, json_path: Path, sprite_picker=None) -> None:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        self.act: int = data["act"]
        self.act_name: str = data.get("act_name", f"Act {self.act}")
        self.background: str = data["background"]
        self.midi_track: str = data["midi_track"]
        self.boss_spec: dict | None = data.get("boss")
        self.waves: list[WaveSpec] = [
            WaveSpec(id=w["id"], duration_s=w["duration_s"], spawns=w.get("spawns", []))
            for w in data["waves"]
        ]
        self.current_wave_index: int = 0
        self.elapsed_s: float = 0.0
        self.spawn_queue: list[tuple[float, list[Enemy]]] = []
        self.spawned_enemies: list[Enemy] = []
        self.wave_complete: bool = False
        # Optional callable (kind -> sprite_name) for visual variants.
        self._sprite_picker = sprite_picker
        # FxLayer reference (set by GameplayScene). Used to emit chain
        # spawn glow VFX when an FTL chain link appears.
        self.fx = None

    def begin(self) -> None:
        self.spawned_enemies.clear()
        self.spawn_queue.clear()
        self.elapsed_s = 0.0
        self.wave_complete = False
        if self.current_wave_index >= len(self.waves):
            return
        wave = self.waves[self.current_wave_index]
        for spawn in wave.spawns:
            chain_count = int(spawn.get("chain_count", 1))
            chain_delay_s = float(spawn.get("chain_delay_s", 0.5))
            if chain_count < 1:
                chain_count = 1
            if chain_count > 5:
                import logging
                logging.warning(
                    "chain_count %d clamped to 5 (max) in wave '%s'",
                    chain_count, wave.id,
                )
                chain_count = 5
            # The spawn's enemies are partitioned by chain link: each link has
            # formation_count enemies, in order. Total = chain_count * formation_count.
            enemies = _build_enemies(spawn, self._sprite_picker)
            per_link = spawn["formation_count"]
            for k in range(chain_count):
                start_idx = k * per_link
                end_idx = start_idx + per_link
                link_enemies = list(enemies[start_idx:end_idx])
                self.spawn_queue.append(
                    (spawn["delay_s"] + k * chain_delay_s, link_enemies)
                )
                # Visual polish: emit a chain spawn glow for each link
                # so the player sees where each train car materializes.
                if self.fx is not None and link_enemies:
                    e0 = link_enemies[0]
                    # Approximate spawn position (off-screen right + first enemy's y)
                    self.fx.emit_chain_spawn_glow(520.0, e0.y, k, chain_count)
        self.spawn_queue.sort(key=lambda x: x[0])

    def update(self, dt: float) -> list[Enemy]:
        new_spawns: list[Enemy] = []
        while self.spawn_queue and self.elapsed_s >= self.spawn_queue[0][0]:
            _, enemies = self.spawn_queue.pop(0)
            for e in enemies:
                self.spawned_enemies.append(e)
            new_spawns.extend(enemies)
        self.spawned_enemies = [e for e in self.spawned_enemies if e.alive]
        self.elapsed_s += dt
        if not self.spawn_queue and not self.spawned_enemies:
            self.wave_complete = True
        return new_spawns

    def next_wave(self) -> bool:
        self.current_wave_index += 1
        if self.current_wave_index >= len(self.waves):
            return False
        self.begin()
        return True
