import React from 'react';
import {Word, Xf, easeOut, f30, fadeIn, fadeOut, mix, styleShadow} from '../engine';
import type {PageProps, StyleDef} from '../engine';

// La línea completa visible desde el inicio en un blanco tenue; cada palabra se vuelve sólida al decirse y la que
// se está diciendo toma el color de acento. Un highlight se queda en el acento y crece un poco (su espacio ya está
// reservado en la medida, así que la línea no salta).

const Page: React.FC<PageProps> = ({st, f, page, L, ws, since, left}) => {
  const a = st.anim;
  const accent = st.activeColor ?? '#3DDC97';
  const dim = st.dimColor ?? 'rgba(255,255,255,0.6)';
  const op = Math.min(fadeIn(since, f30(a.pageIn ?? 3, f.fps)), fadeOut(left, f30(a.pageOut ?? 3, f.fps)));
  const es = a.emphasisScale ?? 1.08;
  return (
    <Xf opacity={op} filter={styleShadow(st, f)}>
      {L.words.map((box, i) => {
        const w = ws[i];
        const em = !!page.words[i].emphasis;
        const k = w.since < 0 ? 0 : easeOut((w.since + 1) / f30(a.wordIn ?? 2, f.fps));
        const fill = w.state === 'upcoming' ? dim : w.state === 'active' || em ? accent : st.color;
        const sc = em ? mix(1 / es, 1, k) : 1;
        return <Word key={i} box={box} fill={fill} scale={sc} origin="baseline-center" stroke={st.stroke} />;
      })}
    </Xf>
  );
};

export const karaoke: StyleDef = {
  spec: (page, st) => page.words.map((w) => (w.emphasis ? {size: st.anim.emphasisScale ?? 1.08} : {})),
  Page,
};
