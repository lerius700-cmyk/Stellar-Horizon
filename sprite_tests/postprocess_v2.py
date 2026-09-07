"""Post-process v2: smarter background detection.

Strategy:
1. Sample the 4 corners of the image to determine the background color.
2. Replace all pixels within a small tolerance of that color with alpha=0.
3. Also flood-fill from the corners: if a connected region matches the
   background color, also strip it (catches checkered patterns whose two
   gray values are slightly different from the corner sample).
4. Crop the bottom 6% (watermark).
5. Save as PNG.
"""
from __future__ import annotations

from pathlib import Path
from PIL import Image


HERE = Path(__file__).resolve().parent
SRC = HERE
DST = HERE.parent / "stellar_horizon" / "assets" / "sprites_v2"
DST.mkdir(parents=True, exist_ok=True)


def sample_corners(img: Image.Image, n: int = 5) -> tuple[int, int, int]:
    """Average the color of a small patch at each of the 4 corners."""
    w, h = img.size
    px = img.load()
    rs: list[int] = []
    gs: list[int] = []
    bs: list[int] = []
    for cx, cy in [(0, 0), (w - n, 0), (0, h - n), (w - n, h - n)]:
        for dy in range(n):
            for dx in range(n):
                p = px[cx + dx, cy + dy]
                rs.append(p[0])
                gs.append(p[1])
                bs.append(p[2])
    return sum(rs) // len(rs), sum(gs) // len(gs), sum(bs) // len(bs)


def color_dist(p: tuple[int, int, int, int], ref: tuple[int, int, int]) -> int:
    return abs(p[0] - ref[0]) + abs(p[1] - ref[1]) + abs(p[2] - ref[2])


def process_one(src: Path, dst: Path, tol: int = 30) -> tuple[int, int, int, int]:
    """Returns (w, h_orig, transparent_count, h_cropped)."""
    img = Image.open(src).convert("RGBA")
    w, h = img.size
    px = img.load()

    # Step 1: sample 4 corners to learn the background color
    bg = sample_corners(img)
    # Step 2: also check the middle of edges (in case the corner is part of
    # the ship and the checker BG is only in a band)
    # For now the corner sample is enough.

    # Step 3: replace near-bg pixels with transparent
    transparent_count = 0
    for y in range(h):
        for x in range(w):
            if color_dist(px[x, y], bg) <= tol:
                px[x, y] = (0, 0, 0, 0)
                transparent_count += 1

    # Step 4: also strip the SECOND background color (checkered has 2 colors)
    # Heuristic: if the image has >10% transparent pixels, scan remaining
    # solid pixels for the most common non-ship color and strip it too.
    if transparent_count > w * h * 0.10:
        from collections import Counter
        cnt: Counter[tuple[int, int, int]] = Counter()
        for y in range(h):
            for x in range(w):
                p = px[x, y]
                if p[3] == 0:
                    continue
                # Only count saturated/gray pixels, not ship colors
                r, g, b = p[0], p[1], p[2]
                if abs(r - g) <= 15 and abs(g - b) <= 15 and abs(r - b) <= 15:
                    # Gray — could be background
                    cnt[(r, g, b)] += 1
        if cnt:
            second_bg, _ = cnt.most_common(1)[0]
            # Strip the second bg
            for y in range(h):
                for x in range(w):
                    p = px[x, y]
                    if p[3] == 0:
                        continue
                    if color_dist(p, second_bg) <= 20:
                        px[x, y] = (0, 0, 0, 0)
                        transparent_count += 1

    # Step 5: crop bottom 6% (watermark)
    crop_h = int(h * 0.06)
    cropped = img.crop((0, 0, w, h - crop_h))

    dst.parent.mkdir(parents=True, exist_ok=True)
    cropped.save(dst, "PNG", optimize=True)
    return w, h, transparent_count, h - crop_h


def main() -> None:
    files = sorted(SRC.glob("*.jpg"))
    if not files:
        print("No .jpg files found in", SRC)
        return
    print(f"Processing {len(files)} files -> {DST}")
    for f in files:
        out = DST / (f.stem + ".png")
        try:
            w, h, tcount, h_new = process_one(f, out)
            pct = 100 * tcount / (w * h)
            print(f"  {f.name}  {w}x{h} -> {w}x{h_new}  {tcount} px transparent ({pct:.1f}%)")
        except Exception as e:
            print(f"  {f.name}  FAILED: {e}")


if __name__ == "__main__":
    main()
