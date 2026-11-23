import React, {useContext} from 'react';
import type {Legibility, Style} from './types';
import type {Layout} from './layout';
import {MaskCtx} from './draw';

// Contraste solo donde hace falta: legibility.py marca cada página con halo, scrim u outline y una fuerza 0..1.
// "outline" no dibuja fondo: Captions.tsx le pone contorno a las palabras.

export const Backdrop: React.FC<{lg: Legibility; L: Layout; id: string; opacity: number}> = ({lg, L, id, opacity}) => {
  const mask = useContext(MaskCtx);
  if (!lg || mask || lg.mode === 'outline' || opacity <= 0.001) return null;
  const k = Math.max(0, Math.min(1, lg.strength));
  const cy = L.top + L.blockH / 2;
  if (lg.mode === 'scrim') {
    const padX = L.fs * 0.45;
    const padY = L.fs * 0.28;
    return (
      <rect
        x={L.left - padX}
        y={L.top - padY}
        width={L.blockW + 2 * padX}
        height={L.blockH + 2 * padY}
        rx={L.fs * 0.3}
        fill={`rgba(0,0,0,${(0.22 + 0.33 * k).toFixed(3)})`}
        opacity={opacity}
      />
    );
  }
  // halo: una mancha oscura y difusa detrás del bloque, sin bordes
  return (
    <g opacity={opacity}>
      <defs>
        <radialGradient id={id}>
          <stop offset="0%" stopColor="#000" stopOpacity={0.2 + 0.35 * k} />
          <stop offset="60%" stopColor="#000" stopOpacity={0.1 + 0.2 * k} />
          <stop offset="100%" stopColor="#000" stopOpacity={0} />
        </radialGradient>
      </defs>
      <ellipse cx={L.cx} cy={cy} rx={L.blockW / 2 + L.fs * 1.4} ry={L.blockH / 2 + L.fs * 1.1} fill={`url(#${id})`} />
    </g>
  );
};

/** El estilo con contorno añadido si la página lo pide (modo outline). */
export function withOutline(st: Style, lg: Legibility): Style {
  if (!lg || lg.mode !== 'outline') return st;
  const w = 0.03 + 0.05 * Math.max(0, Math.min(1, lg.strength));
  if (st.stroke && st.stroke.width >= w) return st;
  return {...st, stroke: {width: w, color: st.stroke?.color ?? 'rgba(0,0,0,0.9)'}};
}
