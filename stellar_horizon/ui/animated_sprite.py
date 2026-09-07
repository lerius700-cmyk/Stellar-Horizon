"""Animated sprite wrapper: loads a horizontal frame strip and cycles
through it at a configurable FPS.

The sprite sheet is a single PNG containing N frames arranged left
to right, all of the same width and height. The class owns a frame
counter and an elapsed-time accumulator; callers call update(dt) once
per frame and get_current_surface() to retrieve the current frame's
pygame.Surface.

If the sheet is missing or unreadable the class returns a 1x1 magenta
surface so the caller can still draw something (and the bug is
visible at a glance).
"""
from __future__ import annotations

import pygame


class AnimatedSprite:
    """One-AnimatedSprite-per-entity: loads a sheet and cycles frames.

    Args:
        path: filesystem path to the sprite sheet PNG.
        frame_w, frame_h: per-frame size in pixels.
        frame_count: how many frames the sheet contains.
        fps: target frame rate. With fps=12 each frame shows for
            ~83ms which is the classic 16-bit game pace.
    """

    def __init__(
        self,
        path: str,
        frame_w: int,
        frame_h: int,
        frame_count: int,
        fps: float = 12.0,
    ) -> None:
        self.frame_w = frame_w
        self.frame_h = frame_h
        self.frame_count = frame_count
        self.frame_duration = 1.0 / max(1.0, fps)
        self._elapsed: float = 0.0
        self._index: int = 0
        # Cache the subsurface per frame so we don't re-slice every draw.
        self._frames: list[pygame.Surface] = []
        self._loaded = False
        try:
            raw = pygame.image.load(path)
            # convert_alpha() requires an actual display mode. In
            # headless / dummy mode it raises "No video mode has been
            # set". Fall back to the raw loaded surface (which still
            # has alpha from the PNG) if convert_alpha fails.
            try:
                sheet = raw.convert_alpha()
            except pygame.error:
                sheet = raw
            for i in range(frame_count):
                rect = pygame.Rect(i * frame_w, 0, frame_w, frame_h)
                self._frames.append(sheet.subsurface(rect).copy())
            self._loaded = True
        except (pygame.error, FileNotFoundError):
            # Fall back to a 1x1 magenta surface so the bug is obvious.
            surf = pygame.Surface((max(1, frame_w), max(1, frame_h)),
                                  pygame.SRCALPHA)
            surf.fill((255, 0, 255, 255))
            self._frames = [surf] * frame_count

    def update(self, dt: float) -> None:
        """Advance the animation timer; wrap to the next frame when full."""
        self._elapsed += dt
        # Loop in case dt was huge (e.g. first frame after a long pause).
        while self._elapsed >= self.frame_duration:
            self._elapsed -= self.frame_duration
            self._index = (self._index + 1) % self.frame_count

    def get_current_surface(self) -> pygame.Surface:
        return self._frames[self._index]

    def share_state_with(self) -> "AnimatedSprite":
        """Return a new AnimatedSprite that shares the frame data
        (same _frames list, same loaded flag) but has independent
        _elapsed and _index. Used for kind-name aliases in
        GameplayScene so that test code iterating .values() gets
        independent timing per alias."""
        clone = AnimatedSprite.__new__(AnimatedSprite)
        clone.frame_w = self.frame_w
        clone.frame_h = self.frame_h
        clone.frame_count = self.frame_count
        clone.frame_duration = self.frame_duration
        clone._frames = self._frames  # shared list reference
        clone._loaded = self._loaded
        clone._elapsed = 0.0  # independent state
        clone._index = 0
        return clone

    @property
    def loaded(self) -> bool:
        return self._loaded
