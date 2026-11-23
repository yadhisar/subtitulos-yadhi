import type {CPage, Frame} from './types';
import {clamp01} from './ease';

/** ms -> cuadro (piso, con épsilon para que 1000 ms a 24 fps sea justo el cuadro 24). */
export const msToF = (ms: number, fps: number) => Math.floor((ms * fps) / 1000 + 1e-6);
/** Duración pensada a 30 fps -> cuadros al fps real del video (mínimo 1). */
export const f30 = (n: number, fps: number) => Math.max(1, Math.round((n * fps) / 30));

export type PageTiming = {s: number; e: number; wordS: number[]; wordE: number[]};

export function pageTimings(pages: CPage[], fps: number): PageTiming[] {
  return pages.map((p) => {
    const s = msToF(p.startMs, fps);
    const e = Math.max(msToF(p.endMs, fps), s + 1);
    const wordS = p.words.map((w) => msToF(w.startMs, fps));
    const wordE = p.words.map((w, k) => Math.max(msToF(w.endMs, fps), wordS[k] + 1));
    return {s, e, wordS, wordE};
  });
}

export type WordState = {
  state: 'upcoming' | 'active' | 'spoken';
  /** 0..1 mientras se dice la palabra. */
  progress: number;
  /** cuadros desde que empezó la palabra (negativo antes). */
  since: number;
};

export function wordStates(t: PageTiming, frame: number): WordState[] {
  return t.wordS.map((s, i) => {
    const e = t.wordE[i];
    const state = frame < s ? 'upcoming' : frame >= e ? 'spoken' : 'active';
    return {state, progress: clamp01((frame - s) / (e - s)), since: frame - s};
  });
}

export const frameInfo = (W: number, H: number, fps: number): Frame => ({W, H, fps, wide: W > H});
/** px pensados a 1080 de alto -> px en este cuadro. */
export const px = (f: Frame, v: number) => (v * f.H) / 1080;
