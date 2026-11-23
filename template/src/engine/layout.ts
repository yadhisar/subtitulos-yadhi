import type {CPage, CWord, FontSpec, Frame, Style} from './types';
import {cssFont} from './fonts';

// Medidas reales con canvas (las fuentes ya están cargadas cuando se llama).
let ctx: CanvasRenderingContext2D | null = null;
const c2d = () => (ctx ??= document.createElement('canvas').getContext('2d')!);

export function textWidth(text: string, font: FontSpec, fs: number, ls = 0) {
  const c = c2d();
  c.font = cssFont(font, fs);
  return c.measureText(text).width + ls * fs * Math.max(0, [...text].length - 1);
}

const capCache = new Map<string, number>();
/** Altura de mayúscula como fracción del tamaño, medida en la "H" real de la fuente. */
export function capHeight(font: FontSpec) {
  const key = `${font.family}|${font.weight}`;
  let v = capCache.get(key);
  if (v == null) {
    const c = c2d();
    c.font = cssFont(font, 200);
    v = c.measureText('H').actualBoundingBoxAscent / 200;
    if (!(v > 0.3)) v = 0.7;
    capCache.set(key, v);
  }
  return v;
}

export const spaceWidth = (font: FontSpec, fs: number) => textWidth('n n', font, fs) - textWidth('nn', font, fs);

export const isNum = (w: CWord) => !!w.num || /\d/.test(w.text);

/** Aplica mayúsculas/minúsculas sin tocar montos ("S/ 5,000" nunca pasa a "s/ 5,000"). */
export function applyCase(text: string, c: Style['case'], num = false) {
  if (num) return text;
  if (c === 'upper') return text.toLocaleUpperCase('es');
  if (c === 'lower') return text.toLocaleLowerCase('es');
  return text;
}

/** Zona horizontal permitida en px: márgenes del estilo y, en vertical, el 12 % derecho libre (botones de TikTok). */
export function safeX(st: Style, f: Frame): [number, number] {
  const m = st.position.marginX;
  const right = f.wide ? m : Math.max(m, 12);
  return [(f.W * m) / 100, f.W * (1 - right / 100)];
}

export const baseFontSize = (sizePct: number, f: Frame) => (sizePct / 100) * f.H * (f.wide ? 1.35 : 1);

export type WordSpec = {font?: FontSpec; size?: number; text?: string};
export type WordBox = {i: number; text: string; font: FontSpec; fs: number; left: number; w: number; cx: number; line: number; baseline: number; ascent: number};
export type Layout = {fs: number; words: WordBox[]; cx: number; cy: number; top: number; left: number; blockW: number; blockH: number; capH: number};
export type LayoutOpts = {specs?: WordSpec[]; y?: number; sizePct?: number};

/** Mide una página, la achica si no entra entre márgenes y devuelve una caja por palabra. */
export function layoutPage(page: CPage, st: Style, f: Frame, o: LayoutOpts = {}): Layout {
  const specs = page.words.map((_, i) => o.specs?.[i] ?? {});
  const texts = page.words.map((w, i) => specs[i].text ?? applyCase(w.text, st.case, isNum(w)));
  const fonts = specs.map((s) => s.font ?? st.font);
  const muls = specs.map((s) => s.size ?? 1);
  const ls = st.letterSpacing ?? 0;
  const ids = [...new Set(page.words.map((w) => w.line ?? 0))].sort((a, b) => a - b);
  const lineOf = page.words.map((w) => ids.indexOf(w.line ?? 0));
  const [xl, xr] = safeX(st, f);
  const avail = xr - xl;
  let fs = baseFontSize(o.sizePct ?? st.size, f);

  const measure = (size: number) => {
    const widths = texts.map((t, i) => textWidth(t, fonts[i], size * muls[i], ls));
    const space = spaceWidth(st.font, size);
    const lineW = ids.map((_, li) => {
      const idx = texts.map((_, i) => i).filter((i) => lineOf[i] === li);
      return idx.reduce((s, i) => s + widths[i], 0) + space * Math.max(0, idx.length - 1);
    });
    return {widths, space, lineW};
  };
  let m = measure(fs);
  for (let k = 0; k < 3 && Math.max(...m.lineW) > avail; k++) {
    fs *= (avail / Math.max(...m.lineW)) * 0.99;
    m = measure(fs);
  }

  const capH = capHeight(st.font) * fs;
  const desc = fs * 0.3;
  const gap = fs * ((st.lineHeight ?? 1.2) - 1);
  const asc = ids.map((_, li) =>
    Math.max(...texts.map((_, i) => (lineOf[i] === li ? capHeight(fonts[i]) * fs * muls[i] : 0))),
  );
  const blockH = asc.reduce((s, a) => s + a + desc, 0) + gap * (ids.length - 1);
  const cx = (xl + xr) / 2;
  const cy = (f.H * (o.y ?? page.y ?? st.position.y)) / 100;
  const top = cy - blockH / 2;
  const blockW = Math.max(...m.lineW);
  const words: WordBox[] = [];
  let yy = top;
  ids.forEach((_, li) => {
    const baseline = yy + asc[li];
    let x = cx - m.lineW[li] / 2;
    texts.forEach((t, i) => {
      if (lineOf[i] !== li) return;
      words[i] = {i, text: t, font: fonts[i], fs: fs * muls[i], left: x, w: m.widths[i], cx: x + m.widths[i] / 2, line: li, baseline, ascent: capHeight(fonts[i]) * fs * muls[i]};
      x += m.widths[i] + m.space;
    });
    yy += asc[li] + desc + gap;
  });
  return {fs, words, cx, cy, top, left: cx - blockW / 2, blockW, blockH, capH};
}

/** Tamaño para que una palabra ocupe `widthPx` sin pasar de `maxFs`. */
export function fitWord(text: string, font: FontSpec, widthPx: number, maxFs: number) {
  const w100 = textWidth(text, font, 100);
  const fs = Math.min(maxFs, (100 * widthPx) / Math.max(1, w100));
  return {fs, w: textWidth(text, font, fs)};
}
