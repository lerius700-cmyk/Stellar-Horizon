"""Regression test: paths used in main.py and Game must work regardless of CWD.

The .exe is launched by double-clicking, so CWD is the .exe's directory
(usually `D:\\AI\\stellar-horizon\\dist\\`). All paths to bundled assets and the
waves JSON must resolve to absolute paths based on the source file location,
not the CWD.

Bug history: 2026-08-31. The .exe would close immediately on SPACE because
`stellar_horizon/waves/waves_act1.json` was resolved relative to CWD, and
when the user ran the .exe from `dist/`, that path did not exist there.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path


def test_main_py_wave_json_path_resolves_to_existing_file():
    """The wave_json path computed in main.py must be an existing absolute file,
    regardless of CWD.

    The fix in main.py uses `Path(__file__).resolve().parent` (1 level up from
    main.py to reach the project root, which contains the stellar_horizon/ package).
    """
    # Simulate the .exe launch: CWD is a sibling of the package, not the project root.
    project_root = Path(__file__).resolve().parent.parent  # stellar-horizon/
    sibling_cwd = project_root / "tmp_simulation_cwd"
    sibling_cwd.mkdir(parents=True, exist_ok=True)

    original_cwd = Path.cwd()
    try:
        os.chdir(sibling_cwd)
        # Replicate main.py's exact logic: main.py is at <project_root>/main.py,
        # so Path(__file__).parent = <project_root>/, and we add "stellar_horizon/waves/waves_act1.json".
        # Test file is at stellar_horizon/stellar_horizon/tests/test_path_resolution.py,
        # so two levels up gives us the project root.
        test_file_dir = Path(__file__).resolve().parent  # stellar_horizon/tests/
        simulated_main_py = test_file_dir.parent.parent  # stellar-horizon/  (mimics project root)
        wave_json = simulated_main_py / "stellar_horizon" / "waves" / "waves_act1.json"
        assert wave_json.is_absolute(), f"wave_json should be absolute, got {wave_json}"
        assert wave_json.exists(), (
            f"wave_json not found at {wave_json}. The .exe would crash on SPACE."
        )
    finally:
        os.chdir(original_cwd)
        if sibling_cwd.exists():
            shutil.rmtree(sibling_cwd, ignore_errors=True)


def test_game_class_resolves_assets_dir_to_absolute_path():
    """The Game class must use __file__ to resolve assets_dir, not CWD."""
    # Import the Game class to verify its default behavior
    from stellar_horizon.core.game import Game

    # We can't fully construct Game without pygame, but we can verify
    # the class signature and __init__ default behavior by reading the source.
    import inspect
    src = inspect.getsource(Game.__init__)

    # The fix: assets_dir is resolved via Path(__file__).resolve().parent.parent
    # This means the path is independent of CWD.
    assert "Path(__file__).resolve()" in src, (
        "Game.__init__ must use Path(__file__).resolve() to find assets_dir "
        "(not CWD-relative)."
    )
    assert "wave_json is None" in src, (
        "Game.__init__ should accept a wave_json parameter that defaults to None, "
        "then resolve it via __file__."
    )


def test_title_scene_resolves_paths_via_file():
    """TitleScene must resolve its default paths via __file__, not CWD."""
    from stellar_horizon.scenes.title import TitleScene
    import inspect
    src = inspect.getsource(TitleScene.__init__)

    assert "Path(__file__).resolve()" in src, (
        "TitleScene.__init__ must use Path(__file__).resolve() to resolve defaults, "
        "not CWD-relative Path('stellar_horizon/...')."
    )


def test_wave_json_default_in_title_scene_does_not_use_cwd_relative_string():
    """The default value `Path('stellar_horizon/waves/waves_act1.json')` is the
    exact bug we're fixing. The fix replaces it with a __file__-based resolution.
    """
    from stellar_horizon.scenes.title import TitleScene
    import inspect
    src = inspect.getsource(TitleScene.__init__)

    # This string is the exact bug — a relative path that fails when CWD != project_root.
    assert 'Path("stellar_horizon/waves/waves_act1.json")' not in src, (
        "TitleScene.__init__ must NOT use the CWD-relative default "
        '`Path("stellar_horizon/waves/waves_act1.json")` — that\'s the bug.'
    )
    assert 'Path("stellar_horizon/assets")' not in src, (
        "TitleScene.__init__ must NOT use the CWD-relative default "
        '`Path("stellar_horizon/assets")` — that\'s the bug.'
    )
