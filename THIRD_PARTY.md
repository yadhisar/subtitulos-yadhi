# Terceros

## Inspiración
- **Subtle**: https://github.com/0xpratzyy/subtle (Pratyush Rungta / Refs, licencia MIT). Se usó como referencia de
  arquitectura y de formatos (`words.json`, `captions.json`, overlay transparente + ffmpeg). El código de este repo es
  propio y está escrito para Windows (faster-whisper y MediaPipe en lugar de mlx-whisper y Apple Vision).

## Tipografías (carpeta `fonts\`)
50 familias de [Google Fonts](https://fonts.google.com), en TTF estático. Cada familia viene con su licencia en
`fonts\OFL-<Familia>.txt` (SIL Open Font License 1.1) o `fonts\LICENSE-<Familia>.txt` (Apache 2.0). La lista completa
está en `scripts\fuentes.py` (`PACK`) y se ve con `--list-fonts`. Las que bajes con `--font` o `fuentes.py --add`
también traen su licencia.

## Software que se usa (no viene incluido; se instala con winget, uv o npm)
| componente | licencia |
|---|---|
| faster-whisper / CTranslate2 | MIT |
| Modelo Whisper large-v3-turbo (OpenAI) | MIT |
| MediaPipe y sus modelos (selfie segmenter, BlazeFace, hand landmarker) | Apache 2.0 |
| OpenCV, NumPy, Pillow | Apache 2.0 / BSD / HPND |
| Remotion 4 | Remotion License: gratis para personas, organizaciones sin fines de lucro y empresas de hasta 3 personas; las demás necesitan licencia de empresa (remotion.dev/license) |
| React | MIT |
| FFmpeg (build de gyan.dev) | GPL |
