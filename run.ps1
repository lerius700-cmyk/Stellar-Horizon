# STELLAR HORIZON - launcher (PowerShell)
# Doble click para jugar. Cerrá con ESC o Q en el juego.

$env:PYTHONPATH = $PSScriptRoot
Set-Location $PSScriptRoot
python -m stellar_horizon.main
