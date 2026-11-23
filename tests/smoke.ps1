# Smoke test sin video: agrupa tests\sample-words.json con cada estilo de styles\ y renderiza un PNG por estilo
# en las capas all y mask. Falla si algun PNG sale vacio.
#   .\tests\smoke.ps1
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$out = Join-Path $repo 'tests\out\smoke'
$env:PYTHONUTF8 = '1'

& uv run --project $repo python (Join-Path $repo 'tests\smoke_prep.py') $out
if ($LASTEXITCODE -ne 0) { throw "smoke_prep fallo" }

& node (Join-Path $repo 'template\render.mjs') --batch (Join-Path $out 'jobs.json')
if ($LASTEXITCODE -ne 0) { throw "render fallo" }

& uv run --project $repo python (Join-Path $repo 'tests\smoke_prep.py') $out --check
if ($LASTEXITCODE -ne 0) { Write-Host "SMOKE: FALLA" -ForegroundColor Red; exit 1 }
Write-Host "SMOKE: OK  (PNGs en $out)" -ForegroundColor Green
exit 0
