"""Post-process v3: aggressive gray-strip + neighbor-aware second pass.

Strategy:
1. Pass 1: any pixel where R≈G≈B (gray) AND value in 30..220 → transparent
   (catches medium grays, doesn't touch very dark outlines or very light
   highlights)
2. Pass 2: connected region analysis. For each remaining solid pixel that
   is gray, check if 4+ of its 8 neighbors are also gray and roughly
   the same value. If so, it's also background (chained expansion).
3. Crop bottom 6% (watermark).
4. Save as PNG.
"""
from __future__ import annotations

from pathlib import Path
from collections import deque
from PIL import Image


HERE = Path(__file__).resolve().parent
SRC = HERE
DST = HERE.parent / "stellar_horizon" / "assets" / "sprites_v2"
DST.mkdir(parents=True, exist_ok=True)


def is_gray(p: tuple[int, int, int, int], tol: int = 12) -> bool:
    return abs(p[0] - p[1]) <= tol and abs(p[1] - p[2]) <= tol and abs(p[0] - p[2]) <= tol


def process_one(src: Path, dst: Path) -> tuple[int, int, int, int]:
    img = Image.open(src).convert("RGBA")
    w, h = img.size
    px = img.load()

    # Pass 1: strip medium grays + pure white + pure black
    t1 = 0
    for y in range(h):
        for x in range(w):
            p = px[x, y]
            if p[3] == 0:
                continue
            r, g, b = p[0], p[1], p[2]
            # Pure white or pure black → almost certainly background
            if is_gray(p, 4) and (r <= 5 or r >= 250):
                px[x, y] = (0, 0, 0, 0)
                t1 += 1
                continue
            if is_gray(p) and 30 <= r <= 245:
                px[x, y] = (0, 0, 0, 0)
                t1 += 1

    # Pass 2: BFS from each still-solid gray pixel — if it has a large
    # connected region of gray neighbors (>=8 same-region), strip them all.
    # This catches dark grays (R<30 or R>220) and the second checker color.
    visited = [[False] * w for _ in range(h)]
    t2 = 0
    for sy in range(h):
        for sx in range(w):
            if visited[sy][sx] or px[sx, sy][3] == 0:
                continue
            p = px[sx, sy]
            if not is_gray(p, 18):
                continue
            # BFS
            ref_val = p[0]
            queue = deque([(sx, sy)])
            region: list[tuple[int, int]] = []
            while queue:
                x, y = queue.popleft()
                if x < 0 or y < 0 or x >= w or y >= h:
                    continue
                if visited[y][x]:
                    continue
                if px[x, y][3] == 0:
                    visited[y][x] = True
                    continue
                pp = px[x, y]
                if not is_gray(pp, 18):
                    continue
                if abs(pp[0] - ref_val) > 25:
                    continue
                visited[y][x] = True
                region.append((x, y))
                queue.append((x + 1, y))
                queue.append((x - 1, y))
                queue.append((x, y + 1))
                queue.append((x, y - 1))
            # If region is large AND touches the image border → background
            touches_border = (
                any(x == 0 or x == w - 1 for x, _ in region) or
                any(y == 0 or y == h - 1 for _, y in region)
            )
            if touches_border and len(region) > 200:
                for x, y in region:
                    px[x, y] = (0, 0, 0, 0)
                    t2 += 1

    # Crop bottom 6% (watermark)
    crop_h = int(h * 0.06)
    cropped = img.crop((0, 0, w, h - crop_h))
    cropped.save(dst, "PNG", optimize=True)
    return w, h, t1 + t2, h - crop_h


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
