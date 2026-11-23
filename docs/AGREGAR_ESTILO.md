# Cómo agregar un estilo

Un estilo tiene dos partes:

1. **`styles\<nombre>.json`**: los datos (fuente, tamaño, colores, posición, cómo se arman las páginas).
2. **`template\src\styles\<tipo>.tsx`**: cómo se dibuja y anima. Varios JSON pueden usar el mismo `.tsx`
   (por ejemplo, un `mi-marca.json` puede usar el dibujo de `bottom`).

> Para solo cambiar letra o colores no hace falta un estilo nuevo: usa `--font`, `--accent`, `--palette`, etc.
> (ver README). Un estilo nuevo sirve para guardar una combinación que usas siempre o cambiar posición y ritmo.

## Opción A: variante de un estilo que ya existe (solo JSON)

Es lo más común (otros colores, otra fuente, otra altura).

```powershell
Copy-Item styles\bottom.json styles\mi-marca.json
```

Edita `styles\mi-marca.json`:
- `"name": "mi-marca"` (igual que el nombre del archivo)
- `font`: `{family, file, weight}` con cualquier `.ttf` de `fonts\` (`--list-fonts`). Para una que no esté:
  `uv run python scriptsuentes.py --add "Nombre en Google Fonts"`
- `color`, `activeColor`: hex (`"#FFD60A"`) o `{"auto": "accent", "fallback": "#FFD60A"}` para usar el color
  sacado del video
- `position.y`: altura del centro del texto en % (55 = un poco debajo de la mitad); `flex` = rango en que se
  puede mover para no tapar la cara. Mantente entre 17 y 80 (zona segura de TikTok).
- `page.maxWords`, `page.maxLines`: cuántas palabras y líneas por página
- deja `"anim": {"type": "bottom", ...}` para reutilizar el dibujo de bottom

Pruébalo:

```powershell
.\tests\smoke.ps1                                  # renderiza un PNG por estilo en tests\out\smoke\
.\subtitulos.ps1 "C:\...\video.mp4" --style mi-marca
```

## Opción B: un dibujo nuevo (JSON + TSX)

1. Copia un preset parecido: `Copy-Item template\src\styles\karaoke.tsx template\src\styles\neon.tsx`
2. Cambia el nombre exportado al final: `export const neon: StyleDef = {...}`
3. Regístralo en `template\src\styles\index.ts`:
   ```ts
   import {neon} from './neon';
   export const REGISTRY = { glide, bottom, karaoke, keyword, neon };
   ```
4. Crea `styles\neon.json` (copiando uno) con `"anim": {"type": "neon", ...}`.
5. Si tu estilo usa otra fuente u otro tamaño para los highlights, decláralo en `spec` del `.tsx` **y** en
   `word_spec()` de `scripts\textbox.py` (así placement y verify miden igual que el render).
6. `cd template; npx tsc -p .` (revisa tipos) y `.\tests\smoke.ps1`.

### Lo que recibe `Page` (PageProps)

| prop | qué es |
|---|---|
| `st` | el estilo (JSON) con los colores automáticos ya resueltos |
| `f` | `{W, H, fps, wide}` |
| `page` | la página de captions.json |
| `L` | la medida: `L.words[i]` = caja de cada palabra (`left`, `w`, `baseline`, `fs`, `font`) |
| `ws[i]` | estado de cada palabra en este cuadro: `upcoming` / `active` / `spoken`, `since` (cuadros desde que empezó) |
| `since`, `left` | cuadros desde que empezó la página y cuadros que le quedan |

### Reglas del render

- Todo es función pura del cuadro: nada de `setTimeout`, `useState` para animar ni `Math.random`.
- Usa `f30(n, f.fps)` para escribir duraciones pensadas a 30 fps.
- Dibuja con `<Word box={...} fill=... />` y agrupa con `<Xf>`: así la capa `mask` (blanco sobre negro) sale sola.
- Un estilo "detrás" exporta además `Big` (la palabra gigante) y pone `"behind": {"enabled": true, ...}` en su JSON.
