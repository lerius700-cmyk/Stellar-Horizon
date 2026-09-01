"""Procedural engine flame renderer.

Draws animated engine flames using pygame primitives (no sprite assets needed).
Each flame has 4 pre-rendered frames (small/medium/large/varying shape) and
animates at 12 FPS. The flame color is configurable per ship type.

Usage:
    flame = EngineFlame(base_color=(255, 100, 100))
    # each frame:
    flame.update(dt)
    flame.render(surface, ship_x, ship_y, size_scale=1.5)
"""
from __future__ import annotations

import pygame

_FRAME_INTERVAL_S = 1.0 / 12.0  # 12 FPS animation
_FRAME_COUNT = 4
_BASE_SIZE = 8  # base flame size in pixels (before size_scale)

# Per-frame size progression (relative to base). 0.6 = small, 1.0 = full.
_FRAME_PROGRESSIONS = (0.6, 0.8, 1.0, 0.7)


class EngineFlame:
    """Procedural engine flame. Pre-renders 4 frames, animates between them."""

    def __init__(self, base_color: tuple[int, int, int]) -> None:
        self.base_color = base_color
        self._frame = 0
        self._time_acc = 0.0
        # Pre-render 4 frames as small surfaces (cached to avoid per-frame cost)
        self._frames: list[pygame.Surface] = [
            self._render_frame(i) for i in range(_FRAME_COUNT)
        ]

    def update(self, dt: float) -> None:
        """Advance the animation. Returns None."""
        self._time_acc += dt
        while self._time_acc >= _FRAME_INTERVAL_S:
            self._time_acc -= _FRAME_INTERVAL_S
            self._frame = (self._frame + 1) % _FRAME_COUNT

    def render(self, surface: pygame.Surface, x: float, y: float,
               size_scale: float = 1.0) -> None:
        """Draw the current flame frame at (x, y) with the given size multiplier.

        `x, y` is the anchor point (e.g. back of the ship). The flame is drawn
        centered on (x, y) and offset slightly upward (flames go up from the engine).
        """
        frame = self._frames[self._frame]
        # Scale the frame if size_scale differs from 1.0
        if size_scale != 1.0:
            new_w = max(1, int(frame.get_width() * size_scale))
            new_h = max(1, int(frame.get_height() * size_scale))
            scaled = pygame.transform.scale(frame, (new_w, new_h))
        else:
            scaled = frame
        # Anchor: the flame bottom (back of ship) is at (x, y), flame extends upward
        blit_x = int(x - scaled.get_width() / 2)
        blit_y = int(y - scaled.get_height() * 0.7)
        surface.blit(scaled, (blit_x, blit_y))

    def _render_frame(self, frame_index: int) -> pygame.Surface:
        """Pre-render one flame frame as a small transparent surface.

        The flame is drawn as a teardrop: a series of concentric circles
        that grow toward the bottom (where the engine is) and taper upward.
        """
        size = _BASE_SIZE
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        r, g, b = self.base_color
        # Bright core color (lighter) and outer color (base)
        core_color = (min(255, r + 60), min(255, g + 60), min(255, b + 60))
        outer_color = self.base_color
        progress = _FRAME_PROGRESSIONS[frame_index % _FRAME_COUNT]
        for i in range(size, 0, -1):
            t = i / size  # 1.0 (outer) -> 0.0 (center)
            if t > progress:
                continue  # this layer is outside the visible flame
            # Color: outer -> core as t decreases
            color = (
                int(outer_color[0] * t + core_color[0] * (1 - t)),
                int(outer_color[1] * t + core_color[1] * (1 - t)),
                int(outer_color[2] * t + core_color[2] * (1 - t)),
            )
            # Position: center the flame at the bottom of the surface
            cx = size / 2
            cy = size - i  # bottom of surface = bottom of flame
            radius = max(1, int(i / 2))
            pygame.draw.circle(surf, color, (int(cx), int(cy)), radius)
        return surf
