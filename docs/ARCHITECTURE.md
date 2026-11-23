# Arquitectura y formatos

Todo corre en local. El pipeline es una cadena de scripts chicos que se pasan JSON y videos por una carpeta de trabajo
(`<carpeta del video>\.subtitulos\<nombre>\`). `scripts\subtitulos.py` los orquesta; cada uno también se puede correr suelto.

```
video.mp4
 ├─ subtitulos.py  prepare_source   → source.mp4      (solo si hay que recortar a 9:16 o pasar a fps constante)
 ├─ transcribe.py                   → words.json      (faster-whisper, tiempos por palabra, caché por SHA-256)
 │   └─ numeros.py                                    (números hablados → un token: "S/ 1,800 millones")
 ├─ cuts.py                         → cortes en ms    (ffmpeg select='gt(scene,0.4)',showinfo)
 ├─ group.py                        → captions.json + .srt   (páginas de 1-2 líneas; ninguna cruza un corte)
 ├─ emphasis.py                     → captions.json   (highlights con motivo; palabra grande "big")
 ├─ subject.py                      → subject.json    (MediaPipe: cara y manos cada 250 ms)
 ├─ placement.py                    → captions.json   (pages[].y fuera de cara/manos, dentro de la zona segura)
 ├─ matte.py                        → matte.mkv + matte.json   (solo estilos "detrás": recorte de la persona)
 ├─ shots.py                        → captions.json   (por toma: ¿la palabra grande va detrás o delante?)
 ├─ legibility.py                   → captions.json   (halo/scrim/outline por página + color de acento)
 ├─ template\render.mjs             → overlay.mov     (Remotion: capa transparente ProRes 4444)
 ├─ composite.py                    → video.subtitulado.mp4   (ffmpeg)
 └─ verify.py                       → video.preview.jpg + JSON de chequeos
```

Remotion renderiza **solo la capa de texto** con canal alfa; ffmpeg compone. Chrome nunca decodifica el video, y el modo
"detrás" es una pila de capas:

```
capa 1  video original
capa 2  palabras grandes "detrás"       (overlay-behind.mov, --layer behind)
capa 3  la persona = video × matte      (matte.mkv como alfa)
capa 4  línea pequeña + grandes delante (overlay-front.mov, --layer front)
```

Sin modo detrás hay un solo overlay (`--layer all`). `--layer mask` dibuja todo el texto en blanco sobre negro
(sirve para medir qué tapa el texto).

## words.json

```json
{
  "version": 1,
  "source": {"sha256": "…", "durationMs": 20000, "fps": 30, "width": 1080, "height": 1920},
  "language": "es",
  "model": "large-v3-turbo",
  "device": "cpu",
  "words": [
    {"text": "Hola,", "startMs": 300, "endMs": 640, "prob": 0.98},
    {"text": "S/ 5,000", "startMs": 2100, "endMs": 3050, "prob": 0.91, "num": true}
  ]
}
```

- `text` sin espacios al borde; la puntuación queda pegada a la palabra.
- `num: true` marca un token que viene de numeros.py (un monto nunca se parte).
- La caché (`%LOCALAPPDATA%\subtitulos-yadhi\cache`) guarda la salida cruda de whisper; `--replace` y los números se
  aplican después, así que cambiarlos no obliga a transcribir de nuevo.

## captions.json

```json
{
  "version": 1,
  "video": {"width": 1080, "height": 1920, "fps": 30, "durationMs": 20000},
  "style": "glide",
  "cuts": [4042, 7542],
  "pages": [
    {
      "startMs": 300, "endMs": 1340, "y": 55,
      "legibility": {"mode": "halo", "strength": 0.6}, "contrast": 2.1,
      "words": [
        {"text": "En", "startMs": 300, "endMs": 420, "line": 0, "emphasis": false, "reason": null},
        {"text": "Lima", "startMs": 430, "endMs": 940, "line": 0, "emphasis": true, "reason": "nombre/marca"}
      ]
    }
  ],
  "big": [{"text": "Lima", "startMs": 430, "endMs": 1340, "front": false, "page": 0}],
  "palette": {"accent": "#7FF4FF"},
  "shots": [{"startMs": 0, "endMs": 4042, "cover": 0.31, "face": 0.22, "instability": 0.01, "behind": true, "why": []}],
  "overrides": {"font": "Bebas Neue", "palette": "neon"},
  "notes": ["…"]
}
```

| campo | quién lo escribe | qué es |
|---|---|---|
| `pages[].startMs/endMs` | group.py | la página termina cuando empieza la siguiente o 400 ms después de su última palabra (700 ms si tiene highlight); nunca se solapan ni cruzan un corte |
| `words[].line` | group.py | 0 o 1 (máx. `page.maxLines` del estilo) |
| `words[].emphasis/reason` | emphasis.py | highlight y su motivo (`número`, `nombre/marca`, `remate`, `tema`, `pedido por ti`, o el que pongas con `--pick`); `picked: true` si lo elegiste a mano |
| `pages[].y` | placement.py | centro del bloque en % del alto; `null` = `position.y` del estilo |
| `pages[].legibility` | legibility.py | tratamiento solo en las páginas que no se leen |
| `big[]` | emphasis.py / shots.py | palabra gigante de los estilos "detrás"; `front: true` = va delante |
| `palette.accent` | legibility.py | reemplaza los colores `{"auto": "accent"}` del estilo |
| `overrides` | subtitulos.py | `--font`, `--palette`, `--accent`... usados; se reusan al re-renderizar con `--captions` sin flags |

Puedes editar `captions.json` a mano (texto, highlights, tiempos) y volver a renderizar con `--captions`. Si agregas
palabras sin `line`, se recalculan las líneas.

## Estilos

Un estilo = `styles\<nombre>.json` (datos) + `template\src\styles\<tipo>.tsx` (cómo se dibuja), unidos por `anim.type`.
Ver [AGREGAR_ESTILO.md](AGREGAR_ESTILO.md).

| clave | uso |
|---|---|
| `font`, `emphasisFont`, `numberFont` | `{family, file, weight}`; `file` en `fonts\` (se cargan sin red al renderizar) |
| `case` | `upper`, `lower` o `sentence` (los montos nunca se tocan) |
| `size` | % del alto del cuadro |
| `color`, `activeColor`, `dimColor` | hex, o `{"auto": "accent", "fallback": "#…"}` para tomar el acento del video |
| `stroke`, `shadow` | contorno en em; sombra en px a 1080 de alto |
| `position` | `y` (% alto), `marginX` (% ancho), `flex: [min, max]` rango en que placement puede mover el texto |
| `page` | `maxWords`, `maxCharsPerLine`, `maxCharsPerLineWide`, `maxLines`, `minFrames`, `maxFrames`, `gapBreakMs` |
| `anim` | `type` + parámetros propios del estilo (en cuadros a 30 fps) |
| `behind` | `enabled` + geometría de la palabra grande (`bigY`, `bigWidth`, `bigMaxSize`, `frontY`…) |
| `legibility` | `mode` (`halo`, `scrim`, `outline`) y `max` (fuerza máxima) |

## Tipografías y colores en tiempo de ejecución

`scripts\personalizar.py` aplica los flags `--font`, `--emphasis-font`, `--big-font`, `--color`, `--accent`,
`--stroke`, `--palette`, `--size` y `--case` sobre el JSON del estilo antes de todo lo demás (la medida de
`textbox.py` y el render usan el estilo ya modificado). `scriptsuentes.py` resuelve `"Familia:peso"` a un archivo de
`fonts\` y, si no está, lo baja de Google Fonts (TTF estático + licencia). Los colores con nombre y las paletas viven en
`colores.json`.

## Zona segura de TikTok (vertical)

Nada de texto por encima del 17 % del alto (y = 330 en 1920), ni en el 20 % inferior, ni en el 12 % derecho.
`textbox.py` replica en Python la medida del renderizador (mismas fuentes, Pillow) para que placement y verify sepan
dónde cae el texto sin abrir Chrome.

## Contrato de render

Todo cuadro es función pura del número de cuadro (`useCurrentFrame`): sin `setTimeout`, sin estado entre cuadros,
sin `Math.random`. Las fuentes se cargan con `delayRender` antes de capturar el primer cuadro.
