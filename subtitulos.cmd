@echo off
rem subtitulos "C:\ruta con espacios\video.mp4" [--style glide]
setlocal
set "PYTHONUTF8=1"
uv run --project "%~dp0." python "%~dp0scripts\subtitulos.py" %*
exit /b %ERRORLEVEL%
