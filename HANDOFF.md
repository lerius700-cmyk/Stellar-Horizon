# HANDOFF — Stellar-Horizon session 2026-09-06

**Para:** próximo agente o sesión que retome este proyecto
**Status:** estable, todo pusheado, `main` en `d997c84`
**Tests:** 380 pass / 0 fail / 0 errors

## TL;DR

Stellar-Horizon es un shoot-em-up 16-bit horizontal, 480×270 internal, pygame stdlib-only. El proyecto está en `D:\AI\stellar-horizon\`. El último release público es **v1.1.0** (tag en `91def31`), pero el `main` está **17 commits adelante** con bugs críticos arreglados (path resolution + PyInstaller spec) y polish visual (engine flames más chicos + comet trails en enemigos).

## Estado del código

| | |
|---|---|
| Tag `v1.1.0` en GitHub | 17 commits atrás de `main` |
| `main` HEAD | `d997c84` |
| Tests | 380 pass, 0 fail, 0 errors |
| Build local | `dist/StellarHorizon.exe` rebuilt 6 sep 2026 (14.17 MB) |
| Zip local | `StellarHorizon-v1.1.0-win64.zip` (13.97 MB) |
| Asset en GitHub Release | **OBSOLETO** — sigue siendo el pre-path-fix |

## Lo que SÍ está hecho (no tocar)

1. **Path resolution bug** (`85293e4`) — `main.py` y `Game.__init__` resuelven `wave_json` y `assets_dir` via `Path(__file__)`, no CWD. **Crítico**: cualquier código nuevo que cargue archivos de runtime DEBE usar `Path(__file__).resolve().parent`, nunca `Path("stellar_horizon/...")`.

2. **PyInstaller spec** (`f8c5e12`) — `StellarHorizon.spec` declara `datas=[..., ('stellar_horizon/waves', 'stellar_horizon/waves'), ...]`. Si agregás runtime data en otra carpeta, **agregala al spec** y agregá un regression-guard test (`stellar_horizon/tests/test_post_refactor_exe.py`).

3. **`_last_dt` init** (`953f643`) — `GameplayScene._last_dt` se inicializa a 0.0 en `__init__` para que el primer `draw()` post-transición no crashee con `AttributeError`. **Patrón**: cualquier atributo leído en `draw()` debe inicializarse en `__init__`.

4. **Engine flame + trail** (`d997c84`) — flames más chicos + comet-tail en enemigos. Tests en `test_enemy_light_trail.py` (14 tests).

5. **42 regression-guard tests** — `test_post_refactor_*.py` cubre: estructura, imports, spec de PyInstaller. Si tocás la estructura, ejecutá la suite completa.

## Lo que PENDIENTE (orden de prioridad)

### 🔴 1. Subir el .exe fresh al release de GitHub

El asset en https://github.com/lerius700-cmyk/Stellar-Horizon/releases/tag/v1.1.0 es el binario pre-path-fix — **crashea al usuario cuando presiona SPACE**.

Tienes el fresh: `StellarHorizon-v1.1.0-win64.zip` (13.97 MB, 6 sep 2026). Para subirlo:

**Opción A (sin token) — drag-replace manual:**
1. Ve a la release page
2. Edit release → borra el `.zip` viejo → arrastra el nuevo
3. Update

**Opción B (con fine-grained token) — vía API:**

El usuario tiene `STELLAR_HORIZON_TOKEN` configurado (PowerShell session o User-scope). Script:
```powershell
$token = $env:STELLAR_HORIZON_TOKEN
$h = @{ Authorization = "token $token"; Accept = 'application/vnd.github+json' }
$rel = Invoke-RestMethod -Headers $h -Uri "https://api.github.com/repos/lerius700-cmyk/Stellar-Horizon/releases/tags/v1.1.0"
foreach ($a in $rel.assets) {
    if ($a.name -like '*.zip') {
        Invoke-RestMethod -Method Delete -Headers $h -Uri "https://api.github.com/repos/lerius700-cmyk/Stellar-Horizon/releases/assets/$($a.id)" | Out-Null
    }
}
$zip = 'D:\AI\stellar-horizon\StellarHorizon-v1.1.0-win64.zip'
$upH = $h.Clone(); $upH['Content-Type'] = 'application/zip'
$result = Invoke-WebRequest -Method Post -Headers $upH -InFile $zip -Uri "https://uploads.github.com/repos/lerius700-cmyk/Stellar-Horizon/releases/$($rel.id)/assets?name=StellarHorizon-v1.1.0-win64.zip"
$result.Content | ConvertFrom-Json  # verify browser_download_url
```

### 🟡 2. Regenerar el token como fine-grained

El usuario tiene un classic PAT (admin/maintain/push/triage/pull) en su env var. Dijo "luego hago eso" sobre regenerar como fine-grained (scope: solo Stellar-Horizon, Contents: R&W). **No urgente** — el classic funciona, solo tiene scope más amplio que el necesario. URL: https://github.com/settings/tokens?type=beta

### 🟢 3. Limpiar dead code en `_systems/`

`stellar_horizon/_systems/` tiene módulos dead code (audio.music, entities.*, fx.*, ui.*, utils.*, roguelike.*) que se movieron desde `src/` durante el SF+SM refactor pero no se usan. Si querés un codebase más limpio, borrarlos. **Bajo prioridad** — no afecta runtime.

## Comandos clave

| Acción | Comando (cwd = `D:\AI\stellar-horizon`) |
|---|---|
| Tests completos | `.\.venv\Scripts\python.exe -m pytest stellar_horizon/tests/` |
| Validar imports | `.\.venv\Scripts\python.exe main.py --check` |
| Headless playthrough (200s) | `.\.venv\Scripts\python.exe headless_playthrough.py 200` |
| Capturar frame | `.\.venv\Scripts\python.exe capture_flame_frame.py out.png` |
| Build .exe | `.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean StellarHorizon.spec` |
| Empaquetar zip | `Compress-Archive -Path dist\StellarHorizon.exe -DestinationPath StellarHorizon-v1.1.0-win64.zip -Force` |

## Archivos importantes

```
D:\AI\stellar-horizon\
├── AGENTS.md              ← onboarding para futuros agentes (SÍ leer primero)
├── CONTEXT.md             ← estado + última sesión (este archivo lo complementa)
├── HANDOFF.md             ← este archivo (pendientes específicos)
├── main.py                ← entry point (Path(__file__)-based path resolution)
├── StellarHorizon.spec    ← PyInstaller build manifest (datas= lista runtime deps)
├── stellar_horizon/
│   ├── core/              ← Game, SceneManager
│   ├── entities/          ← Player, Enemy (con _trail), Boss, Bullet, PowerUp
│   ├── scenes/            ← TitleScene, GameplayScene (con _last_dt, _draw_enemy_trail), GameOverScene
│   ├── fx/                ← particles, engine_flames (5px base), screen_shake, dust, bullet_vfx
│   ├── audio/             ← MidiPlayer, sfx, ThrusterManager
│   ├── ui/                ← Hud, AnimatedSprite, Background, MountainLayer
│   ├── waves/             ← WaveManager, formations, JSON
│   ├── _systems/          ← foundational lib (movement, synth, particle_engine) + dead code
│   ├── tools/             ← refactor scripts
│   ├── assets/            ← backgrounds, midi, sprites (runtime data)
│   └── tests/             ← 380 tests across 30+ files
├── headless_playthrough.py  ← engine playthrough test (200s Act 1 + boss)
├── capture_flame_frame.py   ← visual frame capture for size tuning
├── capture_with_trail.py    ← visual frame capture for trail
└── dist/StellarHorizon.exe  ← 14.17 MB, rebuilt 6 sep 2026
```

## Convenciones críticas (no violar)

1. **Path resolution via `__file__`** — nunca CWD-relative. El bug original de v1.1.0 fue exactamente esto.
2. **No `image_synthesize`** — no disponible en este entorno. VFX es procedural (pygame primitives) o sprite sheets en `assets/sprites/`. Si necesitás un sprite nuevo, pedírselo al usuario.
3. **Particle kinds** — solo importar de `stellar_horizon._systems.systems.particle_engine`. Hay `P_SPARK=0 ... P_WAKE=18`. **No existe `P_SHARD`**.
4. **No auto zip / version** — el usuario controla release cadence. Solo buildear + zippear cuando él lo pida.
5. **No print de tokens** — release scripts loguean LENGTH only. Si el user pega un token en chat, **NO** hacer nada que lo exponga.
6. **`__slots__` en entity classes** — `Player`, `Enemy`, `Bullet` usan `__slots__` para memory bound. Si agregás atributo, agregalo a `__slots__` también.
7. **Headless tests** — el `conftest.py` setea `SDL_VIDEODRIVER=dummy` y pre-inicializa pygame. Sin esto, tests crashean con "no fast renderer" o "mixer not initialized".

## Cuando el usuario vuelva

1. Lee este HANDOFF.md (es lo primero que deberías abrir)
2. Lee `AGENTS.md` (context del proyecto)
3. Lee `CONTEXT.md` (estado de la última sesión)
4. Preguntale qué quiere hacer — los pendientes obvios son los 3 listados arriba
5. Si vas a tocar código, corré `pytest stellar_horizon/tests/` antes para confirmar baseline (380 pass)
