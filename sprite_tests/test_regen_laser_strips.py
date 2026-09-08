"""Tests for sprite_tests/regen_laser_strips.py postprocess."""
from __future__ import annotations

import io
from pathlib import Path
from PIL import Image

from sprite_tests.regen_laser_strips import (
    split_strip_to_frames,
    crop_to_content,
    assemble_sheet,
    save_reference,
    process_strip,
    main,
)


def _make_test_strip() -> Image.Image:
    """Build a 174x42 strip with a known sprite in each 29x7 column.

    Column 0 (frames 0): single red pixel at (10, 3) (relative).
    Column 1 (frame 1): a horizontal red line of 5 pixels.
    Column 2 (frame 2): a 5x3 red rectangle.
    Column 3 (frame 3): a circle-ish blob (5x5).
    Column 4 (frame 4): the horizontal line.
    Column 5 (frame 5): single pixel.
    """
    strip = Image.new("RGBA", (174, 42), (255, 255, 255, 255))
    for col in range(6):
        x0 = col * 29
        if col in (0, 5):
            strip.putpixel((x0 + 10, 3), (255, 0, 0, 255))
        elif col in (1, 4):
            for dx in range(5):
                strip.putpixel((x0 + 8 + dx, 3), (255, 0, 0, 255))
        elif col == 2:
            for dy in range(3):
                for dx in range(5):
                    strip.putpixel((x0 + 8 + dx, 2 + dy), (255, 0, 0, 255))
        else:  # col == 3
            for dy in range(5):
                for dx in range(5):
                    if (dx - 2) ** 2 + (dy - 2) ** 2 <= 4:
                        strip.putpixel((x0 + 8 + dx, 1 + dy), (255, 0, 0, 255))
    return strip


def test_split_strip_to_frames_returns_6():
    strip = _make_test_strip()
    frames = split_strip_to_frames(strip)
    assert len(frames) == 6
    for f in frames:
        assert f.size == (29, 7)


def test_crop_to_content_keeps_visible_sprite():
    # 29x7 frame with a single red pixel at (10, 3)
    frame = Image.new("RGBA", (29, 7), (255, 255, 255, 255))
    frame.putpixel((10, 3), (255, 0, 0, 255))
    cropped = crop_to_content(frame)
    # bounding box of the red pixel with 1px padding is 11x3 (9..10, 2..3)
    # padded by 1 in each direction -> (8, 2, 11, 4) -> 3 wide, 2 tall
    assert cropped.getpixel((1, 0))[0] == 255  # still red somewhere
    assert cropped.getpixel((0, 0))[3] == 0    # transparent corner


def test_assemble_sheet_produces_174x7():
    frames = [Image.new("RGBA", (29, 7), (0, 0, 0, 0)) for _ in range(6)]
    sheet = assemble_sheet(frames)
    assert sheet.size == (174, 7)


def test_save_reference_writes_first_frame(tmp_path: Path):
    frames = [Image.new("RGBA", (29, 7), (0, 0, 0, 0)) for _ in range(6)]
    frames[0].putpixel((5, 3), (255, 0, 0, 255))
    out = tmp_path / "ref.png"
    save_reference(frames, out)
    assert out.exists()
    ref = Image.open(out)
    assert ref.size == (29, 7)
    assert ref.getpixel((5, 3)) == (255, 0, 0, 255)


def test_process_strip_writes_sheet_and_reference(tmp_path: Path):
    """End-to-end: 174x42 white-bg strip with a known sprite
    in frame 0 should produce a 174x7 sheet + 29x7 reference."""
    in_path = tmp_path / "strip.png"
    out_dir = tmp_path / "out"

    # Build a synthetic 174x42 strip with one red dot in frame 0.
    strip = Image.new("RGBA", (174, 42), (255, 255, 255, 255))
    for dx in range(10, 20):
        strip.putpixel((dx, 3), (255, 0, 0, 255))
    strip.save(str(in_path))

    sheet_path, ref_path = process_strip(in_path, out_dir, "laser_test")

    assert sheet_path == out_dir / "laser_test_sheet.png"
    assert ref_path == out_dir / "laser_test.png"
    assert sheet_path.exists()
    assert ref_path.exists()
    sheet = Image.open(sheet_path)
    ref = Image.open(ref_path)
    assert sheet.size == (174, 7)
    assert ref.size == (29, 7)
    # Sheet has visible red pixels (the 10-dot row survives the
    # postprocess). We don't assert the exact position because the
    # crop+recenter shifts it (see crop_to_content + _center_paste).
    sheet_red = sum(1 for p in sheet.getdata() if p[0] > 200 and p[1] < 50)
    assert sheet_red > 0, "expected red pixels in the postprocessed sheet"
    # Reference (frame 0) has at least one red pixel somewhere.
    ref_red = sum(1 for p in ref.getdata() if p[0] > 200 and p[1] < 50)
    assert ref_red > 0, "expected red pixels in the reference frame"


def test_main_prints_usage_on_wrong_argv(capsys):
    """main(argv) should print usage to stderr and return 1 on wrong argc."""
    rc = main(["regen_laser_strips"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "Usage" in captured.err
    assert "input_strip.png" in captured.err


def test_main_strips_suffix_to_derive_name(tmp_path: Path, capsys):
    """main(argv) should strip '_strip' suffix to derive the laser name."""
    in_path = tmp_path / "laser_42_strip.png"
    out_dir = tmp_path / "out"
    # Write a minimal valid strip so process_strip can run.
    Image.new("RGBA", (174, 42), (255, 255, 255, 255)).save(str(in_path))

    rc = main(["regen_laser_strips", str(in_path), str(out_dir)])

    assert rc == 0
    captured = capsys.readouterr()
    assert "laser_42_sheet.png" in captured.out
    assert "laser_42.png" in captured.out
    assert (out_dir / "laser_42_sheet.png").exists()
    assert (out_dir / "laser_42.png").exists()
