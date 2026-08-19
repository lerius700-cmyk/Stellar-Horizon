@echo off
REM STELLAR HORIZON - launcher
REM Doble click para jugar. Cerrá con ESC o Q en el juego.

setlocal
set PYTHONPATH=%~dp0
cd /d %~dp0
python -m stellar_horizon.main
endlocal
