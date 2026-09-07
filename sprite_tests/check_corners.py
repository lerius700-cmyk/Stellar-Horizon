"""Check what's in the non-transparent corners."""
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
DST = HERE.parent / "stellar_horizon" / "assets" / "sprites_v2"

for f in sorted(DST.glob("*.png")):
    img = Image.open(f).convert("RGBA")
    w, h = img.size
    px = img.load()
    corners = [
        ("TL", 0, 0),
        ("TR", w - 1, 0),
        ("BL", 0, h - 1),
        ("BR", w - 1, h - 1),
    ]
    bad = []
    for name, x, y in corners:
        p = px[x, y]
        if p[3] != 0:
            bad.append((name, p))
    if bad:
        print(f"{f.name}: {bad}")
