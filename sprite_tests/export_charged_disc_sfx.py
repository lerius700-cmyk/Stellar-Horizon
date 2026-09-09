"""Export the 4 ChargedDisc SFX to .wav files for A/B testing.

The synth module renders SFX in-memory (16-bit mono PCM via
array.array). The engine wraps them as pygame.mixer.Sound and
never touches disk. But for offline review -- listening on a
media player, comparing pitches, etc. -- it's useful to have
the actual .wav artifacts.

This script writes the 4 ChargedDisc events to:
  D:/AI/stellar-horizon/sprite_tests/captures/sfx_charged_disc_<name>.wav

Output format: 16-bit signed PCM, mono, 44.1 kHz (matches
MIXER_SAMPLE_RATE from stellar_horizon._systems.core.settings).

Usage: python export_charged_disc_sfx.py [output_dir]
"""
from __future__ import annotations

import os
import sys
import wave
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# Local imports must come AFTER the SDL env vars so the dummy
# mixer doesn't blow up if no audio device is available.
from stellar_horizon._systems.audio.synth import (
    MIXER_SAMPLE_RATE,
    render_sfx,
)
from stellar_horizon.audio import sfx


def _write_wav(path: Path, samples: list[int], sample_rate: int) -> None:
    """Write a 16-bit signed mono PCM .wav file from a list of
    int16 samples. Uses Python's stdlib `wave` module (no numpy).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)  # 16-bit
        w.setframerate(sample_rate)
        # wave.writeframes() wants a bytes-like object. array.array
        # has .tobytes() for this purpose, but we accept a list
        # so the function is independent of the renderer's choice.
        w.writeframes(b"".join(
            int(s).to_bytes(2, byteorder="little", signed=True)
            for s in samples
        ))


def main() -> None:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "D:/AI/stellar-horizon/sprite_tests/captures"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output dir: {out_dir}")
    print(f"Sample rate: {MIXER_SAMPLE_RATE} Hz, 16-bit signed mono")
    print()
    for name in sorted(sfx.CHARGED_DISC_EVENTS):
        buf = render_sfx(name)
        path = out_dir / f"sfx_charged_disc_{name}.wav"
        _write_wav(path, list(buf), MIXER_SAMPLE_RATE)
        # Quick stats: peak amplitude (for "is it audible" check)
        peak = max(abs(s) for s in buf) if buf else 0
        nonzero = sum(1 for s in buf if s != 0)
        print(f"  {name:25s} -> {path.name}  "
              f"{len(buf):6d} samples  "
              f"{100*nonzero/len(buf):.1f}% non-zero  "
              f"peak={peak/32767:.2f}")
    print()
    print("Done. Open the .wav files in any media player to A/B test.")


if __name__ == "__main__":
    main()
