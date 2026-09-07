"""Generate 6-frame laser sprite sheets from the 5 existing singles.

Each sheet is 6 × 29 = 174 px wide, 7 px tall. Frames vary in
alpha (0.85..1.0) to read as 'energy' — same procedural approach
as generate_sheets.py but truncated to 6 frames and limited to
laser singles (29x7 each).

Output: laser_0N_sheet.png in stellar_horizon/assets/sprites_v2/
"""
from __future__ import annotations

import os
from pathlib import Path

# Force headless so PIL doesn't need a display
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from PIL import Image, ImageEnhance

ASSETS = Path(__file__).resolve().parent.parent / "stellar_horizon" / "assets" / "sprites_v2"
FRAME_W = 29
FRAME_H = 7
FRAME_COUNT = 6
FRAME_FPS = 12


def make_laser_sheet(single: Image.Image) -> Image.Image:
    """Build a 6-frame 174x7 sheet from a 29x7 laser single.
    
    Frames vary in alpha (0.85..1.0) to read as 'energy', using a
    sine-like pattern. Lasers are never scaled (they'd look wrong
    stretched at 29x7). The single is already at 29x7; we just
    modulate alpha and composite 6 frames.
    """
    # The single is already 29x7. Confirm.
    if single.size != (FRAME_W, FRAME_H):
        # Resize if needed
        single = single.resize((FRAME_W, FRAME_H), Image.LANCZOS)
    base = single.convert("RGBA")
    
    sheet = Image.new("RGBA", (FRAME_W * FRAME_COUNT, FRAME_H), (0, 0, 0, 0))
    for i in range(FRAME_COUNT):
        # Alpha pulse pattern: 0.85, 0.92, 1.0, 1.0, 0.92, 0.85 (peak in middle)
        # This gives a "pulse" feel as the bullet flies
        if i < FRAME_COUNT / 2:
            alpha_f = 0.85 + 0.15 * (i / (FRAME_COUNT / 2 - 1))
        else:
            alpha_f = 1.0 - 0.15 * ((i - FRAME_COUNT / 2) / (FRAME_COUNT / 2 - 1))
        alpha_mult = int(255 * alpha_f)
        # Multiply alpha channel
        r, g, b, a = base.split()
        a = a.point(lambda p: int(p * (alpha_mult / 255.0)))
        frame = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
        frame.paste(base, (0, 0))
        frame.putalpha(a)
        sheet.paste(frame, (i * FRAME_W, 0), frame)
    return sheet


def main() -> None:
    generated = []
    for i in range(1, 6):
        single_path = ASSETS / f"laser_0{i}.png"
        if not single_path.exists():
            print(f"  SKIP: {single_path.name} not found")
            continue
        single = Image.open(single_path).convert("RGBA")
        sheet = make_laser_sheet(single)
        out_path = ASSETS / f"laser_0{i}_sheet.png"
        sheet.save(out_path, "PNG", optimize=True)
        print(f"  {single_path.name}  ->  {out_path.name}  {sheet.size[0]}x{sheet.size[1]}")
        generated.append(out_path)
    print(f"\nGenerated {len(generated)} sheets ({FRAME_COUNT} frames each)")


if __name__ == "__main__":
    main()
