# subtitulos-yadhi

Subtítulos animados estilo TikTok / Reels / Shorts para videos de una persona hablando a cámara, **100 % en tu PC con
Windows**: sin API keys, sin suscripciones, sin subir tu video a ningún lado.

- Transcribe en español (u otro idioma) con tiempos por palabra.
- Pasa los números hablados a cifras: "cinco mil soles" → **S/ 5,000**, "cuarenta por ciento" → **40%**.
- Resalta precios, nombres y palabras clave (o eliges tú cuáles).
- Esquiva la cara y las manos, y respeta la zona segura de TikTok.
- Puede poner una palabra gigante **detrás de la persona**.
- **50 tipografías incluidas** y cualquier otra de Google Fonts con un flag; colores con nombre, hex o paletas.
- Exporta `.srt` y un `captions.json` editable.

Funciona como comando (`subtitulos`) y como skill de [Claude Code](https://claude.com/claude-code).
Inspirado en [Subtle](https://github.com/0xpratzyy/subtle) (MIT), reescrito desde cero para Windows.

| entra | sale (junto al video) |
|---|---|
| `video.mp4` | `video.subtitulado.mp4`: H.264, mismo tamaño, fps, duración y audio |
| | `video.srt`: subtítulos para subir aparte |
| | `video.captions.json`: editable (texto, tiempos, highlights) para volver a renderizar |
| | `video.preview.jpg`: hoja de contacto con 6-9 cuadros y la zona segura dibujada |

## Instalación

Windows 10/11 y PowerShell. Instala las herramientas con winget y abre una terminal nueva:

```powershell
winget install -e --id Gyan.FFmpeg
winget install -e --id OpenJS.NodeJS.LTS
winget install -e --id Python.Python.3.12
winget install -e --id astral-sh.uv
```

(Alternativas: Chocolatey `choco install ffmpeg nodejs-lts python312 uv`, o los instaladores de cada web.
Sirve Python 3.11, 3.12 o 3.13.)

Clona el repo e instala:

```powershell
git clone https://github.com/yadhisar/subtitulos-yadhi.git
cd subtitulos-yadhi
uv sync                                        # entorno de Python (faster-whisper, mediapipe, opencv, numpy, pillow)
uv run python scripts\descargar_modelos.py     # modelos de MediaPipe (~25 MB)
.\scripts\doctor.ps1                           # revisa todo; si falta algo te dice el comando para instalarlo
```

La primera vez que renderiza instala Remotion en `template\` (`npm install`) y baja su Chrome Headless Shell. La
primera transcripción baja el modelo de whisper `large-v3-turbo` (~1.6 GB). Después funciona sin internet.
Modelos y caché quedan en `%LOCALAPPDATA%\subtitulos-yadhi` (cámbialo con `SUBTITULOS_HOME`).

> Si PowerShell no deja correr scripts: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

## Uso

```powershell
.\subtitulos.ps1 "C:\Mis videos\video.mp4"                                  # estilo glide, 9:16
.\subtitulos.ps1 "C:\Mis videos\video.mp4" --style bottom --palette tiktok
.\subtitulos.ps1 "C:\Mis videos\video.mp4" --font "Bebas Neue" --accent rosa
.\subtitulos.ps1 "C:\Mis videos\video.mp4" --style keyword                  # palabra gigante detrás de ti
.\subtitulos.ps1 "C:\Mis videos\video.mp4" --vocab "Ana, Canva" --emphasis-words 'S/ 1,800 millones, gratis'
.\subtitulos.ps1 --list-styles
.\subtitulos.ps1 --list-fonts
.\subtitulos.ps1 --list-palettes
```

`subtitulos.cmd` hace lo mismo desde cmd. Pon siempre las rutas entre comillas; para montos con `S/` o `$` usa
comillas **simples** en PowerShell (con dobles, `$100` se lee como variable).

## Estilos

| estilo | cómo se ve |
|---|---|
| **glide** (por defecto) | sans blanca bold palabra por palabra; la palabra clave en letra caligráfica grande; números en serif itálica |
| **bottom** | MAYÚSCULAS grandes con contorno, abajo al centro, palabra por palabra con "pop"; la clave en amarillo |
| **karaoke** | la línea completa en blanco tenue; la palabra que se dice cambia al color de acento |
| **keyword** | una palabra gigante detrás de la persona y la línea pequeña delante; los números van delante |

Cualquier estilo se combina con cualquier tipografía y color (abajo). Para crear estilos nuevos, mira
[docs/AGREGAR_ESTILO.md](docs/AGREGAR_ESTILO.md).

## Tipografías

El repo trae **50 familias** (licencia OFL o Apache, en `fonts\`). `--list-fonts` las muestra todas:

| tipo | familias |
|---|---|
| sans | Inter, Montserrat, Poppins, Roboto, Open Sans, Lato, Nunito, Raleway, Work Sans, DM Sans, Manrope, Plus Jakarta Sans, Outfit, Rubik, Figtree, Lexend |
| display | Anton, Bebas Neue, Oswald, Archivo Black, Barlow Condensed, League Spartan, Bricolage Grotesque, Teko, Alfa Slab One |
| serif | Playfair Display, DM Serif Display, Lora, Merriweather, Instrument Serif, Abril Fatface, Libre Baskerville |
| script | Pinyon Script, Great Vibes, Dancing Script, Pacifico, Satisfy, Caveat, Kalam, Permanent Marker, Shadows Into Light |
| divertidas | Luckiest Guy, Bangers, Fredoka, Lilita One, Titan One, Bowlby One, Chewy |
| mono | Space Mono, JetBrains Mono |

```powershell
--font "Bebas Neue"            # tipografía del texto
--font "Poppins:800"           # con peso (100-900); también "Poppins ExtraBold" o "Lora:700i" (itálica)
--emphasis-font "Pacifico"     # tipografía de la palabra resaltada
--big-font "Anton"             # tipografía de la palabra gigante (keyword)
```

**Cualquier otra de [fonts.google.com](https://fonts.google.com)** se baja sola la primera vez que la uses con
`--font "Nombre Exacto"` (un TTF estático por peso, con su licencia). También puedes bajarla antes:

```powershell
uv run python scripts\fuentes.py --add "Rubik Mono One"
uv run python scripts\fuentes.py --add "Poppins" --weights 300,600 --italic
```

## Colores

```powershell
--color blanco                 # color del texto
--accent rosa                  # color del highlight; "auto" = un color sacado del video
--accent "#FF4FA3"             # cualquier hex
--stroke negro                 # contorno (o none)
--palette tiktok               # paleta completa; los flags sueltos mandan sobre la paleta
--size 1.2                     # 20 % más grande
--case upper                   # upper, lower o sentence
```

Colores con nombre: blanco, negro, rojo, amarillo, naranja, verde, lima, menta, celeste, azul, turquesa, morado,
violeta, rosa, fucsia, coral, dorado, plateado, gris, crema, neon (también en inglés).

Paletas: `clasico`, `tiktok`, `neon`, `lima`, `menta`, `oceano`, `cielo`, `morado`, `rosa`, `pastel`, `fuego`, `rojo`,
`dorado`, `crema`, `noche`, `oscuro` (texto negro con contorno blanco, para fondos claros) y `auto`.
Agrega las tuyas en [`colores.json`](colores.json).

Si re-renderizas con `--captions` sin flags de color o tipografía, se usan los de la vez anterior.

## Todas las opciones

| opción | qué hace |
|---|---|
| `--style` | `glide`, `bottom`, `karaoke`, `keyword` o la ruta de un `.json` |
| `--font`, `--emphasis-font`, `--big-font` | tipografías (ver arriba) |
| `--color`, `--accent`, `--stroke`, `--palette` | colores (ver arriba) |
| `--size`, `--case` | tamaño (multiplicador) y mayúsculas/minúsculas |
| `--lang` | idioma (defecto `es`) |
| `--vocab "A, B"` | nombres y marcas que whisper debe conocer (también se priorizan como highlight) |
| `--replace oido=Mostrado` | corrige una palabra o frase mal transcrita (repetible) |
| `--aspect` | `9:16` (defecto), `1:1`, `4:5`, `16:9`, `source`; si no coincide, se recorta al centro |
| `--emphasis` | `auto` (defecto), `numbers` (solo cifras), `off` |
| `--emphasis-words` | palabras a resaltar sí o sí |
| `--behind` | `auto` (decide por toma), `on`, `off`; solo estilos "detrás" |
| `--placement` | `auto` (esquiva cara y manos), `off` |
| `--cuts` | `auto` (detecta cortes de toma), `off` |
| `--legibility` | `auto` (halo, fondo o contorno solo donde no se lee), `off` |
| `--model` | `large-v3-turbo` (defecto), `medium`, `small` (más rápido, menos preciso) |
| `--device` | `cpu` (defecto) o `cuda` |
| `--stop-after` | `transcribe` o `group`, para revisar antes de renderizar |
| `--captions archivo.json` | re-renderiza desde un captions.json editado, sin volver a transcribir |
| `--out-dir` | otra carpeta de salida |

Variables de entorno opcionales: `SUBTITULOS_MODEL`, `SUBTITULOS_DEVICE` (`cpu`/`cuda`), `SUBTITULOS_HOME`.

## Revisar y corregir antes del render final

```powershell
.\subtitulos.ps1 "C:\...\video.mp4" --stop-after transcribe --vocab "Ana, Canva"   # lee el texto
.\subtitulos.ps1 "C:\...\video.mp4" --stop-after group --vocab "Ana, Canva"        # páginas + highlights
uv run python scripts\emphasis.py "C:\...\video.captions.json" --show
uv run python scripts\emphasis.py "C:\...\video.captions.json" --pick '4:S/ 5,000=precio' --drop '2:rápido'
.\subtitulos.ps1 "C:\...\video.mp4" --captions "C:\...\video.captions.json"
```

También puedes abrir `video.captions.json` en un editor: cambia el texto, los tiempos (`startMs`, `endMs`) o
`emphasis`, guarda y vuelve a correr con `--captions`. La transcripción queda en caché por archivo: cambiar de estilo,
letra o color no vuelve a transcribir.

## Usarlo con Claude Code (skill)

El skill tiene que estar en `%USERPROFILE%\.claude\skills\subtitulos-yadhi`. Con un junction el repo se queda donde
está y los cambios se ven al instante:

```powershell
New-Item -ItemType Junction -Path "$env:USERPROFILE\.claude\skills\subtitulos-yadhi" -Target "C:\ruta\a\subtitulos-yadhi"
```

O clona el repo directamente en esa carpeta y corre `uv sync` ahí. Reinicia Claude Code y pídele, por ejemplo:

> subtitula "C:\Mis videos\video.mp4" con estilo bottom, letra Bebas Neue y paleta neon

Claude sigue [SKILL.md](SKILL.md): revisa el sistema, transcribe y lee el texto, corrige nombres, elige los
highlights, renderiza y revisa la hoja de contacto antes de responderte.

## CUDA (opcional)

Por defecto todo corre en CPU (`int8`). Con una NVIDIA, `--device cuda` transcribe en `float16`, varias veces más
rápido, pero CTranslate2 necesita **cuBLAS para CUDA 12 y cuDNN 9**:

```powershell
uv pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

Luego añade al `PATH` las carpetas `bin` de esos paquetes (en `.venv\Lib\site-packages\nvidia\...`) o copia sus DLL junto
a `.venv\Scripts\python.exe`. Si falta algo, el programa avisa y sigue en CPU.

## Límites

- "Detrás de ti" funciona mejor con **una persona y cámara fija**. En primeros planos, paneos o recortes inestables la
  palabra grande pasa delante sola (se explica en `notes`).
- El borde del recorte se nota en **cabello fino y manos rápidas**.
- La zona segura usa márgenes aproximados de TikTok (arriba 17 %, abajo 20 %, derecha 12 %).
- whisper puede equivocarse con nombres propios: usa `--vocab` y `--replace`.
- Solo Windows (las rutas, los wrappers y doctor.ps1 están pensados para PowerShell).

## Pruebas

```powershell
.\scripts\doctor.ps1
uv run python -m pytest tests      # números, páginas, highlights, ubicación, colores y tipografías
.\tests\smoke.ps1                  # un PNG por estilo y por combinación de letra/color, sin video
.\tests\e2e.ps1                    # clip 1080x1920 en una carpeta con espacios y tildes, de punta a punta
```

## Licencias

- Código: [MIT](LICENSE).
- Tipografías: SIL Open Font License o Apache 2.0, cada una con su licencia en `fonts\`.
- **Remotion** tiene su propia licencia: es gratis para personas, organizaciones sin fines de lucro y empresas de hasta
  3 personas; las empresas más grandes necesitan una licencia de empresa
  ([remotion.dev/license](https://www.remotion.dev/license)).
- Detalle de terceros en [THIRD_PARTY.md](THIRD_PARTY.md). Gracias a
  [Subtle](https://github.com/0xpratzyy/subtle) (MIT) por la idea y la arquitectura.
