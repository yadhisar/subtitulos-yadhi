import React from 'react';
import {Word, Xf, dropShadow, easeOutBack, f30, fadeIn, fadeOut, isNum, joinFilters, mix, px, styleShadow, withAlpha} from '../engine';
import type {PageProps, StyleDef} from '../engine';

// Sans blanca bold que entra palabra por palabra; la palabra clave (highlight) en script caligráfica grande y del
// color de acento, creciendo desde su esquina izquierda sobre la misma línea base. Los números van en serif itálica
// (la script no tiene cifras bonitas).

const Page: React.FC<PageProps> = ({st, f, page, L, ws, left}) => {
  const a = st.anim;
  const accent = st.activeColor ?? '#F5E663';
  const out = fadeOut(left, f30(a.pageOut ?? 3, f.fps));
  const sh = styleShadow(st, f);
  const glow = joinFilters(dropShadow(f, 0, 0, 7, withAlpha(accent, a.glow ?? 0.45)), sh);
  return (
    <Xf opacity={out}>
      {L.words.map((box, i) => {
        const s = ws[i].since;
        if (page.words[i].emphasis) {
          if (s < 0) return null;
          const k = easeOutBack((s + 1) / f30(a.scriptIn ?? 6, f.fps), 1.3);
          return <Word key={i} box={box} fill={accent} opacity={fadeIn(s, f30(2, f.fps))} scale={mix(a.scriptFrom ?? 0.15, 1, k)} origin="baseline-left" filter={glow} />;
        }
        const op = fadeIn(s, f30(a.wordIn ?? 3, f.fps));
        return <Word key={i} box={box} fill={st.color} opacity={op} dy={(1 - op) * px(f, 8)} filter={sh} stroke={st.stroke} />;
      })}
    </Xf>
  );
};

export const glide: StyleDef = {
  spec: (page, st) =>
    page.words.map((w) =>
      !w.emphasis
        ? {}
        : isNum(w) && st.numberFont
          ? {font: st.numberFont, size: st.anim.numberScale ?? 1.6}
          : {font: st.emphasisFont ?? st.font, size: st.anim.scriptScale ?? 2.6},
    ),
  Page,
};
