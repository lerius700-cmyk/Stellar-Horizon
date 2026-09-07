"""Verify alpha channel of processed PNGs."""
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
DST = HERE.parent / "stellar_horizon" / "assets" / "sprites_v2"

for f in sorted(DST.glob("*.png")):
    img = Image.open(f).convert("RGBA")
    w, h = img.size
    px = img.load()
    # Check the 4 corners
    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    corner_info = [(x, y, px[x, y]) for x, y in corners]
    n_transparent_corners = sum(1 for _, _, p in corner_info if p[3] == 0)
    print(f"{f.name}  corners transparent: {n_transparent_corners}/4  top-left: {corner_info[0][2]}")
