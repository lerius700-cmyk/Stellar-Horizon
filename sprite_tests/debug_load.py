"""Debug: what path is the loader actually using?"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
pygame.init()

from pathlib import Path
from stellar_horizon.audio.midi_player import MidiPlayer
from stellar_horizon.scenes.gameplay import GameplayScene

s = GameplayScene(MidiPlayer(),
                  Path("stellar_horizon/waves/waves_act1.json"),
                  Path("stellar_horizon/assets"))
s._load_sprites()
print("assets_dir:", s.assets_dir)
print("wave_json:", s.wave_json)
print()
print("--- animated cache ---")
for k in sorted(s._animated):
    a = s._animated[k]
    print(f"  {k}  loaded={a._loaded}  frames={a.frame_count}  size={a.frame_w}x{a.frame_h}")
print()
print("--- boss anims ---")
for k, a in s._boss_anims.items():
    print(f"  {k}  loaded={a._loaded}  frames={a.frame_count}  size={a.frame_w}x{a.frame_h}")
print()
print("--- laser sprites ---")
for k, surf in s._laser_sprites.items():
    print(f"  {k}  size={surf.get_width()}x{surf.get_height()}")
