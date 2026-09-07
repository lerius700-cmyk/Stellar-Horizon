"""Procedural 10-frame sheet generator.

Takes each single PNG in assets/sprites_v2/ and produces a horizontal
10-frame sheet (10 × frame_w wide, frame_h tall) with subtle per-frame
transformations that read as "alive motion":

  Frame 0: identity
  Frame 1: Y-bob +1
  Frame 2: scale 1.04 (engine pulse)
  Frame 3: Y-bob -1, color brighter
  Frame 4: scale 1.06 (charge)
  Frame 5: Y-bob +2 (thrust)
  Frame 6: scale 1.04 + brightness up
  Frame 7: Y-bob +1
  Frame 8: color dimmer
  Frame 9: identity (loop)

Frame sizes:
  - boss_*: 96x96 (was 48 in legacy)
  - laser_*: 48x16 (projectile shape, no scale)
  - everything else: 64x64 (was 16-32 in legacy)

Output: <name>_sheet.png in assets/sprites_v2/
"""
from __future__ import annotations

from pathlib import Path
from PIL import Image

DST = Path(__file__).resolve().parent.parent / "stellar_horizon" / "assets" / "sprites_v2"

# Per-name frame size (W x H). 10 frames stacked horizontally.
# 2026-09-06: shrunk 10% from previous (player 32->29, enemy 32->29,
# boss 80->72) to give more space in the playfield and reduce the
# boss clipping during entry. The AI single is at 1024x1024, so the
# extra downscaling preserves detail while taking less screen real
# estate.
SIZES = {
    "boss": (72, 72),
    "laser": (29, 7),
    "player": (29, 29),
}


def frame_size_for(name: str) -> tuple[int, int]:
    if name.startswith("boss_"):
        return SIZES["boss"]
    if name.startswith("laser_"):
        return SIZES["laser"]
    if name.startswith("player_"):
        return SIZES["player"]
    return (29, 29)


def build_frames(single: Image.Image, fw: int, fh: int) -> list[Image.Image]:
    """Build 10 frames from a single sprite, with subtle per-frame variation.
    Lasers get NO scale (they'd look wrong stretched); everything else does.
    """
    is_laser = fw < fh or (fw, fh) == SIZES["laser"]

    # Downscale once to a clean 2x the frame size (so we have headroom for
    # scale-up without resampling artifacts).
    base_w, base_h = fw * 2, fh * 2
    base = single.resize((base_w, base_h), Image.LANCZOS).convert("RGBA")

    def make_frame(
        y_off: int = 0,
        scale: float = 1.0,
        bright: float = 1.0,
        sat: float = 1.0,
    ) -> Image.Image:
        # Apply scale
        if is_laser:
            scaled = base
        else:
            if abs(scale - 1.0) > 0.001:
                new_w = int(base_w * scale)
                new_h = int(base_h * scale)
                scaled = base.resize((new_w, new_h), Image.LANCZOS)
            else:
                scaled = base
        # Apply brightness + saturation
        if abs(bright - 1.0) > 0.001 or abs(sat - 1.0) > 0.001:
            r, g, b, a = scaled.split()
            # Brightness
            if abs(bright - 1.0) > 0.001:
                from PIL import ImageEnhance
                scaled = ImageEnhance.Brightness(scaled).enhance(bright)
            if abs(sat - 1.0) > 0.001:
                from PIL import ImageEnhance
                scaled = ImageEnhance.Color(scaled).enhance(sat)
        # Center onto a frame of size (fw, fh) with y_off
        frame = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
        if is_laser:
            x_paste = (fw - scaled.width) // 2
            y_paste = (fh - scaled.height) // 2 + y_off
        else:
            x_paste = (fw - scaled.width) // 2
            y_paste = (fh - scaled.height) // 2 + y_off
        frame.paste(scaled, (x_paste, y_paste), scaled)
        return frame

    # Frame 0: identity
    # Frame 1: bob down
    # Frame 2: engine pulse
    # Frame 3: bob up, brighter
    # Frame 4: charge
    # Frame 5: thrust bob
    # Frame 6: pulse + bright
    # Frame 7: bob down
    # Frame 8: dimmer
    # Frame 9: identity (loop)
    if is_laser:
        # Lasers: subtle alpha pulse to read as "energy"
        frames = []
        for i in range(10):
            alpha = int(255 * (0.85 + 0.15 * ((i % 4) / 4.0)))
            fr = make_frame()
            # Multiply alpha channel
            r, g, b, a = fr.split()
            a = a.point(lambda p: int(p * (alpha / 255.0)))
            fr.putalpha(a)
            frames.append(fr)
        return frames
    else:
        return [
            make_frame(),
            make_frame(y_off=1),
            make_frame(scale=1.04, bright=1.10),
            make_frame(y_off=-1, bright=1.15),
            make_frame(scale=1.06, bright=1.20),
            make_frame(y_off=2, scale=1.03),
            make_frame(scale=1.04, bright=1.12, sat=1.10),
            make_frame(y_off=1, bright=1.05),
            make_frame(bright=0.85, sat=0.90),
            make_frame(),
        ]


def make_sheet(single: Image.Image, fw: int, fh: int) -> Image.Image:
    frames = build_frames(single, fw, fh)
    sheet = Image.new("RGBA", (fw * 10, fh), (0, 0, 0, 0))
    for i, fr in enumerate(frames):
        sheet.paste(fr, (i * fw, 0), fr)
    return sheet


def main() -> None:
    singles = sorted(p for p in DST.glob("*.png") if not p.stem.endswith("_sheet"))
    if not singles:
        print("No single PNGs found in", DST)
        return
    print(f"Generating 10-frame sheets for {len(singles)} singles -> {DST}")
    for s in singles:
        try:
            img = Image.open(s).convert("RGBA")
            fw, fh = frame_size_for(s.stem)
            sheet = make_sheet(img, fw, fh)
            out = DST / f"{s.stem}_sheet.png"
            sheet.save(out, "PNG", optimize=True)
            print(f"  {s.name}  -> {out.name}  {fw * 10}x{fh}")
        except Exception as e:
            print(f"  {s.name}  FAILED: {e}")


if __name__ == "__main__":
    main()
