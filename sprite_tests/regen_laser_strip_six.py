"""Right-align variant of regen_laser_strips for laser_06 (shard with explicit head on right).

Same pipeline as regen_laser_strips but instead of centering the cropped content
on a 29x7 canvas, we right-align it so the crystal head sits on the right edge
of each frame and the motion-blur trail extends to the left.

Usage:
    python -m sprite_tests.regen_laser_strip_six <input_strip.png> <output_dir> [name]
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageDraw


FRAME_W = 29
FRAME_H = 7
N_FRAMES = 6
STRIP_W = FRAME_W * N_FRAMES  # 174


def clean_gray_pixels(img: Image.Image) -> Image.Image:
    """Clear near-gray pixels (AI watermark anti-aliasing) to transparent.

    Keeps saturated pixels (cyan crystals) and the dark crystal outline.
    A pixel is treated as gray/watermark if:
      - max(r,g,b) - min(r,g,b) < 30 (near-equal channels), OR
      - r > 220 and g > 240 and b > 240 (very light, low-saturation, likely
        watermark edge anti-aliasing rather than crystal highlight).
    """
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    work = img.copy()
    px = work.load()
    for y in range(work.size[1]):
        for x in range(work.size[0]):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            # Pure black is the crystal outline; keep it.
            if r < 30 and g < 30 and b < 30:
                continue
            # Near-equal channels (gray / watermark anti-aliasing).
            if max(r, g, b) - min(r, g, b) < 30:
                px[x, y] = (0, 0, 0, 0)
                continue
            # Light-but-desaturated: r too high for cyan core (#88FFFF has r=136).
            # A genuine cyan highlight is r~200,g~250,b~250 (diff > 30 is OK).
            # A watermark edge is r~230,g~254,b~254 — diff 19-24.
            # The "gray" branch above catches those; this branch is a safety net.
            if r > 225 and g > 245 and b > 245 and (b - r) < 50:
                px[x, y] = (0, 0, 0, 0)
    return work


def split_strip_to_frames(strip: Image.Image) -> List[Image.Image]:
    if strip.size[0] != STRIP_W:
        raise ValueError(f"Expected strip width {STRIP_W}, got {strip.size[0]}")
    if strip.size[1] < FRAME_H:
        raise ValueError(f"Expected strip height >= {FRAME_H}, got {strip.size[1]}")
    return [
        strip.crop((i * FRAME_W, 0, (i + 1) * FRAME_W, FRAME_H))
        for i in range(N_FRAMES)
    ]


def crop_to_content(frame: Image.Image) -> Image.Image:
    if frame.mode != "RGBA":
        frame = frame.convert("RGBA")
    work = frame.copy()
    r, g, b, a = work.getpixel((0, 0))
    if r > 200 and g > 200 and b > 200:
        ImageDraw.floodfill(work, (0, 0), value=(0, 0, 0, 0))
    elif r < 50 and g < 50 and b < 50:
        ImageDraw.floodfill(work, (0, 0), value=(0, 0, 0, 0))
    # Aggressive cleanup: clear any remaining near-white pixels (AI watermark
    # anti-aliasing or stray gray that the floodfill from (0,0) did not reach).
    px = work.load()
    for y in range(work.size[1]):
        for x in range(work.size[0]):
            pr, pg, pb, pa = px[x, y]
            if pr > 235 and pg > 235 and pb > 235:
                px[x, y] = (0, 0, 0, 0)
    bbox = work.getbbox()
    if bbox is None:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    left, top, right, bottom = bbox
    left = max(0, left - 1)
    top = max(0, top)
    right = min(frame.size[0], right + 1)
    bottom = min(frame.size[1], bottom + 1)
    return work.crop((left, top, right, bottom))


def _right_align_paste(canvas: Image.Image, content: Image.Image) -> None:
    """Paste content right-aligned on canvas (in place). canvas is 29x7.

    The content's right edge is the head (rightmost non-transparent pixel).
    """
    cw, ch = canvas.size
    iw, ih = content.size
    x = cw - iw  # right-align
    y = (ch - ih) // 2  # vertical center
    if y < 0:
        y = 0
    canvas.alpha_composite(content, (x, y))


def assemble_sheet(frames: List[Image.Image]) -> Image.Image:
    if len(frames) != N_FRAMES:
        raise ValueError(f"Expected {N_FRAMES} frames, got {len(frames)}")
    sheet = Image.new("RGBA", (STRIP_W, FRAME_H), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        sheet.paste(f, (i * FRAME_W, 0))
    return sheet


def process_strip(in_path: Path, out_dir: Path, name: str) -> Tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    strip = Image.open(str(in_path))
    if strip.mode != "RGBA":
        strip = strip.convert("RGBA")
    # Remove AI-watermark gray artifacts before splitting into frames.
    strip = clean_gray_pixels(strip)
    raw_frames = split_strip_to_frames(strip)
    processed: List[Image.Image] = []
    for f in raw_frames:
        cropped = crop_to_content(f)
        canvas = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
        _right_align_paste(canvas, cropped)
        processed.append(canvas)
    sheet = assemble_sheet(processed)
    sheet_path = out_dir / f"{name}_sheet.png"
    sheet.save(str(sheet_path), format="PNG")
    ref_path = out_dir / f"{name}.png"
    processed[0].save(str(ref_path), format="PNG")
    return sheet_path, ref_path


def main(argv: list[str]) -> int:
    if len(argv) not in (3, 4):
        print(f"Usage: {argv[0]} <input_strip.png> <output_dir> [name]", file=sys.stderr)
        return 1
    in_path = Path(argv[1])
    out_dir = Path(argv[2])
    if len(argv) == 4:
        name = argv[3]
    else:
        stem = in_path.stem
        name = stem[:-6] if stem.endswith("_strip") else stem
    sheet, ref = process_strip(in_path, out_dir, name)
    print(f"Sheet: {sheet}")
    print(f"Reference: {ref}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
