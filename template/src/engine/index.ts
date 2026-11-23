import type React from 'react';
import type {CaptionsFile, CBig, CPage, Frame, Layer, Legibility, Style} from './types';
import type {Layout, WordSpec} from './layout';
import type {PageTiming, WordState} from './time';

export * from './types';
export * from './ease';
export * from './time';
export * from './fonts';
export * from './layout';
export * from './draw';
export * from './legibility';

export type PageProps = {
  st: Style;
  f: Frame;
  page: CPage;
  pageIndex: number;
  L: Layout;
  t: PageTiming;
  frame: number;
  /** cuadros desde que empezó la página */
  since: number;
  /** cuadros que le quedan a la página */
  left: number;
  ws: WordState[];
  captions: CaptionsFile;
  layer: Layer;
  lg: Legibility;
};

export type BigProps = {st: Style; f: Frame; big: CBig[]; frame: number; layer: Layer};

/** Lo que exporta cada estilo en template/src/styles/<nombre>.tsx */
export type StyleDef = {
  /** Fuente/tamaño por palabra (palabra clave en otra fuente, números más grandes...). */
  spec?: (page: CPage, st: Style) => WordSpec[];
  Page: React.FC<PageProps>;
  /** Palabra gigante (estilos "detrás"). */
  Big?: React.FC<BigProps>;
};

/** Reemplaza cada {auto: "accent", fallback} del estilo por el color de acento sacado del video (legibility.py). */
export function resolveColors<T>(o: T, palette?: {accent?: string}): T {
  if (Array.isArray(o)) return o.map((x) => resolveColors(x, palette)) as T;
  if (o && typeof o === 'object') {
    const r = o as Record<string, any>;
    if (r.auto === 'accent' && typeof r.fallback === 'string') return (palette?.accent ?? r.fallback) as T;
    const out: Record<string, any> = {};
    for (const [k, v] of Object.entries(r)) out[k] = resolveColors(v, palette);
    return out as T;
  }
  return o;
}
