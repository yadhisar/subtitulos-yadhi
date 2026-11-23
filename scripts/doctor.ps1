# Revisa que todo lo necesario para subtitulos-yadhi este instalado.
#   .\scripts\doctor.ps1
# Imprime [OK] / [FALTA] / [AVISO] y, para lo que falta, el comando winget que lo instala.
# Termina con codigo 0 si no falta nada obligatorio, 1 si falta algo.

$ErrorActionPreference = 'Continue'
$repo = Split-Path -Parent $PSScriptRoot
$missing = 0

function Ok($m) { Write-Host "[OK]    $m" -ForegroundColor Green }
function Falta($m, $fix) { Write-Host "[FALTA] $m" -ForegroundColor Red; if ($fix) { Write-Host "        -> $fix" -ForegroundColor Yellow }; $script:missing++ }
function Aviso($m) { Write-Host "[AVISO] $m" -ForegroundColor Yellow }

function Find-Tool($name, $extra) {
    $c = Get-Command $name -ErrorAction SilentlyContinue
    if ($c) { return $c.Source }
    foreach ($p in $extra) { if ($p -and (Test-Path $p)) { return $p } }
    return $null
}

Write-Host "subtitulos-yadhi: revision del sistema ($repo)`n"

# ffmpeg / ffprobe
foreach ($t in 'ffmpeg', 'ffprobe') {
    $p = Find-Tool $t @()
    if ($p) {
        $v = (& $p -hide_banner -version 2>$null | Select-Object -First 1)
        Ok "$t  $v"
    } else { Falta "$t no esta en el PATH" "winget install -e --id Gyan.FFmpeg   (luego abre una terminal nueva)" }
}

# node >= 18 y npm
$node = Find-Tool 'node' @("$env:ProgramFiles\nodejs\node.exe")
if ($node) {
    $nv = (& $node --version).Trim()
    $major = [int]($nv.TrimStart('v').Split('.')[0])
    if ($major -ge 18) { Ok "node $nv" } else { Falta "node $nv es muy viejo (se necesita 18 o mas)" "winget install -e --id OpenJS.NodeJS.LTS" }
} else { Falta "node no esta instalado" "winget install -e --id OpenJS.NodeJS.LTS" }
$npm = Find-Tool 'npm' @("$env:ProgramFiles\nodejs\npm.cmd")
if ($npm) { Ok "npm" } else { Falta "npm no esta instalado" "winget install -e --id OpenJS.NodeJS.LTS" }

# uv
$uv = Find-Tool 'uv' @("$env:LOCALAPPDATA\Microsoft\WinGet\Links\uv.exe", "$env:USERPROFILE\.local\bin\uv.exe")
if ($uv) { Ok "uv $((& $uv --version) -replace '^uv ','')" } else { Falta "uv no esta instalado" "winget install -e --id astral-sh.uv   (luego abre una terminal nueva)" }

# python del proyecto (.venv creado con uv sync)
$py = Join-Path $repo '.venv\Scripts\python.exe'
if (Test-Path $py) {
    $pv = (& $py -c "import sys; print(sys.version.split()[0])" 2>$null)
    $mods = (& $py -c "import faster_whisper, mediapipe, cv2, numpy, PIL; print('ok')" 2>$null)
    if ($mods -eq 'ok') { Ok ".venv con Python $pv (faster-whisper, mediapipe, opencv, numpy, pillow)" }
    else { Falta ".venv existe pero le faltan paquetes" "cd `"$repo`"; uv sync" }
} else {
    $sys = Find-Tool 'python' @()
    if (-not $sys) { Falta "python no esta instalado" "winget install -e --id Python.Python.3.12" }
    Falta "no existe .venv" "cd `"$repo`"; uv sync"
}

# modelos MediaPipe
$home_ = if ($env:SUBTITULOS_HOME) { $env:SUBTITULOS_HOME } else { Join-Path $env:LOCALAPPDATA 'subtitulos-yadhi' }
$models = Join-Path $home_ 'models'
$need = 'selfie_multiclass_256x256.tflite', 'selfie_segmenter.tflite', 'blaze_face_short_range.tflite', 'hand_landmarker.task'
$miss = @($need | Where-Object { -not (Test-Path (Join-Path $models $_)) })
if ($miss.Count -eq 0) { Ok "modelos MediaPipe en $models" }
else { Falta "faltan modelos MediaPipe: $($miss -join ', ')" "cd `"$repo`"; uv run python scripts\descargar_modelos.py" }

# modelo de whisper (se descarga solo en la primera transcripcion)
$wdir = Join-Path $models 'whisper'
if ((Test-Path $wdir) -and (Get-ChildItem $wdir -Recurse -Filter 'model.bin' -ErrorAction SilentlyContinue)) { Ok "modelo whisper descargado" }
else { Aviso "el modelo de whisper se descarga en la primera transcripcion (~1.6 GB para large-v3-turbo)" }

# plantilla Remotion
if (Test-Path (Join-Path $repo 'template\node_modules\remotion')) { Ok "template\node_modules (Remotion)" }
else { Aviso "template\node_modules no existe: se instala solo en el primer render (npm install)" }

# fuentes que piden los estilos
$fontsMissing = @()
Get-ChildItem (Join-Path $repo 'styles') -Filter *.json | ForEach-Object {
    $txt = Get-Content $_.FullName -Raw -Encoding UTF8
    [regex]::Matches($txt, '"file"\s*:\s*"([^"]+)"') | ForEach-Object {
        $f = $_.Groups[1].Value
        if (-not (Test-Path (Join-Path $repo "fonts\$f"))) { $fontsMissing += $f }
    }
}
if ($fontsMissing.Count -eq 0) { Ok "fuentes de todos los estilos en fonts\" } else { Falta "fuentes que no estan en fonts\: $(($fontsMissing | Sort-Object -Unique) -join ', ')" $null }

# GPU (opcional)
$smi = Find-Tool 'nvidia-smi' @("$env:SystemRoot\System32\nvidia-smi.exe")
if ($smi) {
    $gpu = (& $smi --query-gpu=name --format=csv,noheader 2>$null | Select-Object -First 1)
    Aviso "GPU NVIDIA detectada ($gpu): --device cuda es opcional y necesita cuBLAS + cuDNN 9 (ver README). Por defecto se usa CPU."
}

Write-Host ""
if ($missing -eq 0) { Write-Host "Todo listo." -ForegroundColor Green; exit 0 }
Write-Host "Faltan $missing cosa(s). Instala lo de arriba y vuelve a correr .\scripts\doctor.ps1" -ForegroundColor Red
exit 1
