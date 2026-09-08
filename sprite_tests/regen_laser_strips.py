"""Postprocess AI-generated laser strip into a sprite sheet + reference.

Spec: docs/superpowers/specs/2026-09-08-visual-polish-v3-design.md section 3.

The AI generation produces a 174x42 strip (6 frames of 29x7 side-by-side
on a white background). This module:

1. Splits the strip into 6 individual 29x7 frames.
2. For each frame: floodfill from (0,0) makes white transparent, then
   crop to the non-transparent bounding box (with 1px padding), and
   re-paste onto a transparent 29x7 canvas centered.
3. Concatenates the 6 frames horizontally -> 174x7 sheet.
4. Saves the first frame as a 29x7 reference.

Usage (from the cmdline):
    python -m sprite_tests.regen_laser_strips <input_strip.png> <output_dir>

Usage (from Python):
    from sprite_tests.regen_laser_strips import process_strip
    sheet, reference = process_strip("input.png", "output_dir")
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

from PIL import Image


FRAME_W = 29
FRAME_H = 7
N_FRAMES = 6
STRIP_W = FRAME_W * N_FRAMES  # 174
STRIP_H = FRAME_H * 6          # 42 (AI may produce 7 or 42; we crop to 42)


def split_strip_to_frames(strip: Image.Image) -> List[Image.Image]:
    """Split a 174xN strip into 6 frames of 29x7.

    Accepts strips where the height is >= 7. The first 7 rows are used.
    """
    if strip.size[0] != STRIP_W:
        raise ValueError(
            f"Expected strip width {STRIP_W}, got {strip.size[0]}"
        )
    if strip.size[1] < FRAME_H:
        raise ValueError(
            f"Expected strip height >= {FRAME_H}, got {strip.size[1]}"
        )
    frames = []
    for i in range(N_FRAMES):
        col = strip.crop((i * FRAME_W, 0, (i + 1) * FRAME_W, FRAME_H))
        frames.append(col)
    return frames


def crop_to_content(frame: Image.Image) -> Image.Image:
    """Remove white background and crop to non-transparent content + 1px pad.

    Returns a tight RGBA image. The output may be smaller than 29x7.
    """
    if frame.mode != "RGBA":
        frame = frame.convert("RGBA")
    # Floodfill from (0, 0) with transparent — white becomes alpha 0.
    # (PIL's ImageDraw.floodfill operates in-place.)
    from PIL import ImageDraw
    work = frame.copy()
    ImageDraw.floodfill(work, (0, 0), value=(0, 0, 0, 0))
    # Find bounding box of non-zero alpha.
    bbox = work.getbbox()  # returns (left, top, right, bottom) or None
    if bbox is None:
        # Frame is fully white — return an empty transparent image.
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    left, top, right, bottom = bbox
    # 1px padding on left/right/bottom, no top padding (keeps the
    # top of the visible sprite at row 0 of the cropped output).
    left = max(0, left - 1)
    top = max(0, top)
    right = min(frame.size[0], right + 1)
    bottom = min(frame.size[1], bottom + 1)
    return work.crop((left, top, right, bottom))


def _center_paste(canvas: Image.Image, content: Image.Image) -> None:
    """Paste `content` centered on `canvas` (in place). canvas is 29x7."""
    cw, ch = canvas.size
    iw, ih = content.size
    x = (cw - iw) // 2
    y = (ch - ih) // 2
    canvas.alpha_composite(content, (x, y))


def assemble_sheet(frames: List[Image.Image]) -> Image.Image:
    """Concatenate 6 processed 29x7 frames into a 174x7 sheet."""
    if len(frames) != N_FRAMES:
        raise ValueError(f"Expected {N_FRAMES} frames, got {len(frames)}")
    sheet = Image.new("RGBA", (STRIP_W, FRAME_H), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        # f is already 29x7 with transparent background.
        sheet.paste(f, (i * FRAME_W, 0))
    return sheet


def save_reference(frames: List[Image.Image], out_path: Path) -> None:
    """Save the first frame as a 29x7 reference PNG."""
    if len(frames) == 0:
        raise ValueError("frames list is empty")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(str(out_path), format="PNG")


def process_strip(in_path: Path, out_dir: Path, name: str) -> Tuple[Path, Path]:
    """Full pipeline: read strip -> sheet + reference.

    Returns (sheet_path, reference_path).
    `name` is the laser archetype name (e.g. "laser_01").
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    strip = Image.open(str(in_path))
    if strip.mode != "RGBA":
        strip = strip.convert("RGBA")
    raw_frames = split_strip_to_frames(strip)
    # Each frame: crop to content, re-center on transparent 29x7.
    processed: List[Image.Image] = []
    for f in raw_frames:
        cropped = crop_to_content(f)
        canvas = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
        _center_paste(canvas, cropped)
        processed.append(canvas)
    sheet = assemble_sheet(processed)
    sheet_path = out_dir / f"{name}_sheet.png"
    sheet.save(str(sheet_path), format="PNG")
    ref_path = out_dir / f"{name}.png"
    processed[0].save(str(ref_path), format="PNG")
    return sheet_path, ref_path


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(f"Usage: {argv[0]} <input_strip.png> <output_dir>", file=sys.stderr)
        return 1
    in_path = Path(argv[1])
    out_dir = Path(argv[2])
    # Derive name from input filename: "laser_01_strip.png" -> "laser_01".
    stem = in_path.stem
    if stem.endswith("_strip"):
        name = stem[:-6]
    else:
        name = stem
    sheet, ref = process_strip(in_path, out_dir, name)
    print(f"Sheet: {sheet}")
    print(f"Reference: {ref}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
