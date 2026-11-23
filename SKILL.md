---
name: subtitulos-yadhi
description: "Subtitula videos en local con subtítulos animados estilo TikTok/Reels, resalta precios y palabras clave, pone texto detrás de la persona, permite elegir tipografías y colores, y exporta SRT. Úsalo cuando pidan subtítulos, captions o 'subtitula este video'."
---

# subtitulos-yadhi

Subtítulos animados para videos verticales de una persona hablando a cámara. Todo corre en esta PC
(faster-whisper, MediaPipe, Remotion y ffmpeg): sin API keys, sin subir nada.

## Cómo correrlo

Trabaja SIEMPRE desde la carpeta de este skill, en PowerShell, con TODAS las rutas entre comillas (suelen tener
espacios y tildes).

```powershell
cd "$env:USERPROFILE\.claude\skills\subtitulos-yadhi"
.\subtitulos.ps1 "C:\ruta\video.mp4" [opciones]
```

## Pasos (en este orden)

1. **Revisar el sistema:** `.\scripts\doctor.ps1`. Si falta algo, dale a la persona el comando winget que imprime y
   no sigas hasta que esté. Si faltan modelos: `uv run python scripts\descargar_modelos.py`.
2. **Transcribir y LEER el transcript:**
   `.\subtitulos.ps1 "C:\...\video.mp4" --stop-after transcribe --vocab "nombres, marcas, lugares"`
   Lee el texto completo. Corrige nombres, marcas y lugares mal escritos:
   - si whisper no conoce un nombre, añádelo a `--vocab` (vuelve a transcribir);
   - si lo escribió mal de forma fija, usa `--replace 'oido=Mostrado'` (repetible).
   Solo ortografía y nombres: NUNCA reescribas lo que dijo la persona.
3. **Agrupar:** la misma línea con `--stop-after group` (y los mismos `--vocab`/`--replace`). Imprime las páginas con
   los highlights automáticos y su motivo.
4. **Elegir TÚ los highlights** con `scripts\emphasis.py` sobre el `video.captions.json`:
   ```powershell
   uv run python scripts\emphasis.py "C:\...\video.captions.json" --show
   uv run python scripts\emphasis.py "C:\...\video.captions.json" --pick '5:S/ 1,800 millones=precio' --drop '3:rápido'
   ```
   Prioridad: 1) números, precios, %, fechas; 2) nombres, marcas y lugares; 3) palabra de contraste o remate
   ("nunca", "gratis", "nadie", "pierdes"); 4) el tema, la primera vez.
   Máximo 1 por página (2 si la página tiene 5+ palabras), nunca stopwords, cada uno con su razón.
   En PowerShell usa comillas SIMPLES para montos con `S/` y `$`.
5. **Renderizar** con lo editado, con el estilo, tipografía y colores que pidieron:
   `.\subtitulos.ps1 "C:\...\video.mp4" --captions "C:\...\video.captions.json" --style bottom --font "Bebas Neue" --palette neon`
6. **ABRIR `video.preview.jpg` y revisarlo** (con la herramienta de leer imágenes) antes de responder:
   - se lee en pantalla de teléfono (contraste, tamaño, la tipografía elegida no queda ilegible);
   - el texto está dentro de la zona segura (franjas rojas de la hoja: arriba 17 %, abajo 20 %, derecha 12 %);
   - no tapa la cara;
   - los highlights son los correctos.
   Lee también el JSON final (`ok`, `warnings`, `notes`). Si algo falla, corrige (highlights, `--placement`,
   `--style`, `--size`, `--legibility`) y vuelve al paso 5.
7. Responde con la ruta del `.subtitulado.mp4` final (y del `.srt`), el estilo, tipografía y colores usados, y los
   avisos que queden.

## Estilos, tipografías y colores

| estilo | qué hace |
|---|---|
| `glide` (por defecto) | sans blanca bold; palabra clave en letra caligráfica grande; números en serif itálica |
| `bottom` | mayúsculas grandes abajo al centro, palabra por palabra, palabra clave en amarillo |
| `karaoke` | la línea completa visible; la palabra que se dice cambia al color de acento |
| `keyword` | palabra gigante DETRÁS de la persona, línea pequeña delante |

- Tipografías: `--font`, `--emphasis-font`, `--big-font`. 50 familias incluidas (`--list-fonts`); cualquier otra de
  Google Fonts se baja sola con su nombre exacto. Peso con `"Familia:800"`.
- Colores: `--color`, `--accent` (o `auto`), `--stroke` (o `none`), `--palette` (`--list-palettes`). Nombres en
  español o inglés, o hex.
- Tamaño y mayúsculas: `--size 1.2`, `--case upper|lower|sentence`.

Si no nombran estilo, usa `glide` y menciona los otros y que pueden elegir letra y colores.

## Otras opciones

`--lang es` · `--vocab "..."` · `--replace oido=Mostrado` · `--aspect 9:16|1:1|4:5|16:9|source` (9:16 por defecto:
si el video no es vertical se recorta al centro) · `--emphasis auto|numbers|off` · `--emphasis-words '...'` ·
`--behind auto|on|off` · `--placement auto|off` · `--cuts auto|off` · `--legibility auto|off` ·
`--model large-v3-turbo|medium|small` · `--device cpu|cuda` · `--out-dir "C:\..."`

## Reglas

- Nunca subir el video ni usar APIs pagas: todo es local.
- No forzar "detrás" (`--behind on`) en paneos rápidos, cámara en mano o primeros planos: el recorte se nota.
  Con `--behind auto` el programa decide por toma y lo explica en `notes`.
- En `keyword`, los números nunca van detrás (dígitos tapados cambian el sentido).
- No reescribir lo que dijo la persona: solo ortografía, nombres y cifras (los números hablados pasan a cifras solos).
- La transcripción se guarda en caché por archivo: cambiar de estilo, letra o color no vuelve a transcribir.
- Si `--device cuda` falla, el programa sigue en CPU con un aviso: no es un error.
