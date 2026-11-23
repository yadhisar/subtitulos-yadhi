// Curvas de animación. Todo es función pura del número de cuadro: nada de estado entre cuadros.

export const clamp01 = (x: number) => (x < 0 ? 0 : x > 1 ? 1 : x);
export const mix = (a: number, b: number, k: number) => a + (b - a) * k;
export const easeOut = (x: number) => 1 - Math.pow(1 - clamp01(x), 3);
export const easeIn = (x: number) => Math.pow(clamp01(x), 2);
export const easeInOut = (x: number) => {
  const t = clamp01(x);
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
};
/** Sobrepasa un poco y vuelve (k=1.1 es un rebote suave). */
export const easeOutBack = (x: number, k = 1.70158) => {
  const t = clamp01(x);
  const c3 = k + 1;
  return 1 + c3 * Math.pow(t - 1, 3) + k * Math.pow(t - 1, 2);
};

/** Opacidad de una entrada: 0 antes de empezar, sube en `dur` cuadros. */
export const fadeIn = (since: number, dur: number) => (since < 0 ? 0 : easeOut((since + 1) / Math.max(1, dur)));
/** Opacidad de una salida: 1 hasta los últimos `dur` cuadros, luego baja a 0. */
export const fadeOut = (left: number, dur: number) => clamp01(left / Math.max(1, dur));

/** "#rrggbb" + alfa -> rgba(). Si no es hex, lo devuelve igual. */
export function withAlpha(color: string, a: number) {
  const m = /^#?([0-9a-f]{6})$/i.exec(color.trim());
  if (!m) return color;
  const n = parseInt(m[1], 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

/** Mezcla dos colores hex. */
export function colorMix(k: number, a: string, b: string) {
  const pa = /^#?([0-9a-f]{6})$/i.exec(a.trim());
  const pb = /^#?([0-9a-f]{6})$/i.exec(b.trim());
  if (!pa || !pb) return k < 0.5 ? a : b;
  const na = parseInt(pa[1], 16);
  const nb = parseInt(pb[1], 16);
  const ch = (n: number, s: number) => (n >> s) & 255;
  const c = (s: number) => Math.round(mix(ch(na, s), ch(nb, s), clamp01(k)));
  return `rgb(${c(16)},${c(8)},${c(0)})`;
}
