import {staticFile} from 'remotion';
import type {FontSpec} from './types';

const loaded = new Set<string>();

/** Todo objeto {family, file, weight} dentro del JSON del estilo es una fuente que se carga desde fonts/. */
export function fontSpecs(o: unknown, out: FontSpec[] = []): FontSpec[] {
  if (o && typeof o === 'object') {
    const r = o as Record<string, any>;
    if (typeof r.file === 'string' && typeof r.family === 'string') out.push(r as FontSpec);
    else for (const v of Object.values(r)) fontSpecs(v, out);
  }
  return out;
}

/** Carga las fuentes locales (sin red). El render espera a que estén listas antes de capturar cada cuadro. */
export async function loadFonts(style: unknown) {
  await Promise.all(
    fontSpecs(style).map(async (f) => {
      const key = `${f.family}|${f.file}`;
      if (loaded.has(key)) return;
      const face = new FontFace(f.family, `url(${staticFile(f.file)})`, {weight: String(f.weight)});
      await face.load();
      document.fonts.add(face);
      loaded.add(key);
    }),
  );
  await document.fonts.ready;
}

export const cssFont = (f: FontSpec, sizePx: number) => `${f.weight} ${sizePx}px "${f.family}"`;
