import React from 'react';
import {Word, Xf, applyCase, capHeight, easeOutBack, f30, fadeIn, fadeOut, fitWord, layoutPage, msToF, px, safeX, styleShadow} from '../engine';
import type {BigProps, CBig, Frame, PageProps, Style, StyleDef, WordBox} from '../engine';

// Una palabra gigante detrás de la persona (capa "behind": ffmpeg pone a la persona encima) y la línea pequeña
// delante. Los números van delante, más abajo y más angostos, para que se lean completos y no tapen la cara.

const bare = (s: string) => s.replace(/[^\p{L}\p{N}]+/gu, '').toLowerCase();

function bigBox(b: CBig, st: Style, f: Frame): WordBox {
  const bh = st.behind!;
  const font = bh.bigFont ?? st.font;
  const text = applyCase(b.text, 'upper', /\d/.test(b.text));
  const [xl, xr] = safeX(st, f);
  const width = ((xr - xl) * (b.front ? bh.frontWidth ?? 74 : bh.bigWidth ?? 92)) / 100;
  const maxFs = (f.H * (b.front ? bh.frontMaxSize ?? 11 : bh.bigMaxSize ?? 24)) / 100;
  const {fs, w} = fitWord(text, font, width, maxFs);
  const cy = (f.H * (b.front ? bh.frontY ?? 70 : bh.bigY ?? 30)) / 100;
  const ascent = capHeight(font) * fs;
  const left = (xl + xr) / 2 - w / 2;
  return {i: 0, text, font, fs, left, w, cx: left + w / 2, line: 0, baseline: cy + ascent / 2, ascent};
}

const Big: React.FC<BigProps> = ({st, f, big, frame}) => {
  const a = st.anim;
  return (
    <>
      {big.map((b, k) => {
        const s = msToF(b.startMs, f.fps);
        const e = Math.max(msToF(b.endMs, f.fps), s + 1);
        if (frame < s || frame >= e) return null;
        const box = bigBox(b, st, f);
        const kk = easeOutBack((frame - s + 1) / f30(a.bigIn ?? 6, f.fps), a.overshoot ?? 1.12);
        const dir = k % 2 === 0 ? -1 : 1; // alterna: baja desde arriba / sube desde abajo
        const dy = dir * f.H * ((a.slide ?? 6) / 100) * (1 - kk);
        const op = Math.min(fadeIn(frame - s, f30(2, f.fps)), fadeOut(e - frame, f30(a.bigOut ?? 3, f.fps)));
        return (
          <Xf key={k} dy={dy} opacity={op} filter={b.front ? styleShadow(st, f) : undefined}>
            <Word box={box} fill={st.behind!.bigColor ?? st.activeColor ?? st.color} />
          </Xf>
        );
      })}
    </>
  );
};

const Page: React.FC<PageProps> = ({st, f, page, pageIndex, ws, captions, frame}) => {
  const a = st.anim;
  const bigs = (captions.big ?? []).filter((b) => b.page === pageIndex).map((b) => bare(b.text));
  const keep = page.words.map((w) => !bigs.includes(bare(w.text)));
  const small = {...page, words: page.words.filter((_, i) => keep[i])};
  if (!small.words.length) return null;
  const L = layoutPage(small, st, f);
  const idx = page.words.map((_, i) => i).filter((i) => keep[i]);
  // si en este cuadro hay una palabra grande DELANTE, la línea pequeña se sube para no tocarla
  let lift = 0;
  for (const b of captions.big ?? []) {
    const s = msToF(b.startMs, f.fps);
    const e = Math.max(msToF(b.endMs, f.fps), s + 1);
    if (!b.front || frame < s || frame >= e) continue;
    const box = bigBox(b, st, f);
    const bigTop = box.baseline - box.ascent;
    const gap = L.fs * 0.6;
    lift = Math.min(lift, bigTop - gap - (L.top + L.blockH));
  }
  return (
    <Xf filter={styleShadow(st, f)} dy={lift}>
      {L.words.map((box, j) => {
        const i = idx[j];
        const op = fadeIn(ws[i].since, f30(a.smallIn ?? 4, f.fps));
        const em = !!page.words[i].emphasis;
        return <Word key={i} box={box} fill={em ? st.activeColor ?? st.color : st.color} opacity={op} dy={(1 - op) * px(f, (a.smallRise ?? 1.2) * 10)} stroke={st.stroke} />;
      })}
    </Xf>
  );
};

export const keyword: StyleDef = {Page, Big};
