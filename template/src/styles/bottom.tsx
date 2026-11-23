import React from 'react';
import {Word, Xf, easeOut, f30, mix, styleShadow} from '../engine';
import type {PageProps, StyleDef} from '../engine';

// Mayúsculas grandes con contorno, abajo al centro (encima del 20 % inferior que tapa TikTok).
// Cada palabra aparece en el cuadro en que se dice, con un "pop" corto; la palabra clave va en amarillo.
// El bloque se mide completo, así que la línea no se mueve mientras se va armando.

const Page: React.FC<PageProps> = ({st, f, page, L, ws}) => {
  const a = st.anim;
  return (
    <Xf filter={styleShadow(st, f)}>
      {L.words.map((box, i) => {
        const s = ws[i].since;
        if (s < 0) return null;
        const k = easeOut((s + 1) / f30(a.popIn ?? 4, f.fps));
        const em = !!page.words[i].emphasis;
        return <Word key={i} box={box} fill={em ? st.activeColor ?? '#FFD60A' : st.color} scale={mix(a.pop ?? 1.18, 1, k)} origin="center" stroke={st.stroke} />;
      })}
    </Xf>
  );
};

export const bottom: StyleDef = {Page};
