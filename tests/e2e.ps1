# Prueba de punta a punta, sin microfono ni material con derechos:
#  1. crea con ffmpeg un clip 1080x1920 de 10 s (con audio) en una carpeta CON ESPACIOS Y TILDES
#  2. corre subtitulos.py con un words.json de prueba (--words) para no depender de whisper
#  3. verifica con ffprobe tamano, fps, duracion (+-1 cuadro) y audio; que existan .srt, .captions.json y preview.jpg;
#     y que verify devuelva ok=true (los warnings se muestran explicados)
#   .\tests\e2e.ps1 [-Style glide]
param([string]$Style = 'glide')
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$env:PYTHONUTF8 = '1'
$dir = Join-Path $env:TEMP ("prueba subt" + [char]0x00ED + "tulos")
$clip = Join-Path $dir 'clip de prueba.mp4'
New-Item -ItemType Directory -Force $dir | Out-Null
Remove-Item -Force -ErrorAction SilentlyContinue (Join-Path $dir 'clip de prueba.*')

Write-Host "1) clip de prueba: $clip"
& ffmpeg -v error -y -f lavfi -i "testsrc2=size=1080x1920:rate=30:duration=10" -f lavfi -i "sine=frequency=220:sample_rate=48000:duration=10" `
    -c:v libx264 -pix_fmt yuv420p -crf 23 -c:a aac -b:a 128k -shortest $clip
if ($LASTEXITCODE -ne 0) { throw "ffmpeg no pudo crear el clip" }

Write-Host "2) subtitulos (estilo $Style) con words de prueba"
& uv run --project $repo python (Join-Path $repo 'scripts\subtitulos.py') $clip --style $Style --words (Join-Path $repo 'tests\fixtures\e2e-words.json') --vocab "Lima, TikTok"
$code = $LASTEXITCODE

Write-Host "3) comprobaciones"
$fail = 0
function Check($cond, $msg) { if ($cond) { Write-Host "  [OK]    $msg" -ForegroundColor Green } else { Write-Host "  [FALLA] $msg" -ForegroundColor Red; $script:fail++ } }
function Probe($f) {
    $j = & ffprobe -v error -show_streams -show_format -of json $f | Out-String | ConvertFrom-Json
    $v = $j.streams | Where-Object { $_.codec_type -eq 'video' } | Select-Object -First 1
    $a = $j.streams | Where-Object { $_.codec_type -eq 'audio' } | Select-Object -First 1
    $num, $den = $v.avg_frame_rate.Split('/')
    [pscustomobject]@{ w = [int]$v.width; h = [int]$v.height; fps = [double]$num / [double]$den; dur = [double]$v.duration; audio = [bool]$a }
}
$out = Join-Path $dir 'clip de prueba.subtitulado.mp4'
Check ($code -eq 0) "subtitulos.py termino con codigo 0 (fue $code)"
Check (Test-Path $out) "existe clip de prueba.subtitulado.mp4"
if (Test-Path $out) {
    $s = Probe $clip; $o = Probe $out
    Check (($s.w -eq $o.w) -and ($s.h -eq $o.h)) "misma resolucion ($($o.w)x$($o.h))"
    Check ([math]::Abs($s.fps - $o.fps) -lt 0.01) "mismos fps ($($o.fps))"
    Check ([math]::Abs($s.dur - $o.dur) -le (1.0 / $s.fps + 0.001)) "misma duracion +-1 cuadro ($($s.dur) s vs $($o.dur) s)"
    Check ($o.audio) "tiene pista de audio"
}
foreach ($ext in 'srt', 'captions.json', 'preview.jpg') { Check (Test-Path (Join-Path $dir "clip de prueba.$ext")) "existe clip de prueba.$ext" }
$vj = Join-Path $dir '.subtitulos\clip de prueba\verify.json'
if (Test-Path $vj) {
    $v = Get-Content $vj -Raw -Encoding UTF8 | ConvertFrom-Json
    Check ($v.ok) "verify ok=true"
    foreach ($w in $v.warnings) { Write-Host "  [AVISO] $w" -ForegroundColor Yellow }
    foreach ($n in $v.notes) { Write-Host "  [nota]  $n" }
} else { Check $false "existe verify.json" }

if ($fail -eq 0) { Write-Host "E2E: OK  ($dir)" -ForegroundColor Green; exit 0 }
Write-Host "E2E: $fail falla(s)" -ForegroundColor Red
exit 1
