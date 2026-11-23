# .\subtitulos.ps1 "C:\ruta con espacios\video.mp4" [--style glide]
# Envuelve: uv run python scripts\subtitulos.py <argumentos>
$env:PYTHONUTF8 = '1'
& uv run --project $PSScriptRoot python (Join-Path $PSScriptRoot 'scripts\subtitulos.py') @args
exit $LASTEXITCODE
