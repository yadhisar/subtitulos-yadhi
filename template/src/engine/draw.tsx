import React, {createContext, useContext} from 'react';
import type {Frame, Style} from './types';
import type {WordBox} from './layout';
import {px} from './time';

/** En la capa "mask" todo se dibuja blanco sobre negro, sin sombras (sirve para medir qué tapa el texto). */
export const MaskCtx = createContext(false);

export type Origin = 'center' | 'baseline-left' | 'baseline-center';

export const Word: React.FC<{
  box: WordBox;
  fill: string;
  opacity?: number;
  scale?: number;
  origin?: Origin;
  dx?: number;
  dy?: number;
  stroke?: {width: number; color: string} | null;
  filter?: string;
  ls?: number;
}> = ({box, fill, opacity = 1, scale = 1, origin = 'baseline-center', dx = 0, dy = 0, stroke, filter, ls = 0}) => {
  const mask = useContext(MaskCtx);
  if (opacity <= 0.001) return null;
  const x = box.left + dx;
  const y = box.baseline + dy;
  const ox = origin === 'baseline-left' ? x : x + box.w / 2;
  const oy = origin === 'center' ? y - box.ascent / 2 : y;
  const tf = scale !== 1 ? `translate(${ox} ${oy}) scale(${scale}) translate(${-ox} ${-oy})` : undefined;
  const sw = stroke ? stroke.width * box.fs * 2 : 0;
  return (
    <text
      x={x}
      y={y}
      transform={tf}
      fontFamily={`"${box.font.family}"`}
      fontWeight={box.font.weight}
      fontSize={box.fs}
      letterSpacing={ls ? `${ls * box.fs}px` : undefined}
      fill={mask ? '#fff' : fill}
      opacity={opacity}
      stroke={sw ? (mask ? '#fff' : stroke!.color) : undefined}
      strokeWidth={sw || undefined}
      strokeLinejoin="round"
      paintOrder="stroke"
      style={{filter: mask ? undefined : filter, whiteSpace: 'pre'}}
    >
      {box.text}
    </text>
  );
};

/** Grupo con desplazamiento, opacidad y filtro. */
export const Xf: React.FC<{children?: React.ReactNode; dx?: number; dy?: number; opacity?: number; filter?: string}> = ({children, dx = 0, dy = 0, opacity = 1, filter}) => {
  const mask = useContext(MaskCtx);
  if (opacity <= 0.001) return null;
  return (
    <g transform={dx || dy ? `translate(${dx} ${dy})` : undefined} opacity={opacity} style={{filter: mask ? undefined : filter}}>
      {children}
    </g>
  );
};

export const dropShadow = (f: Frame, x: number, y: number, blur: number, color: string) =>
  `drop-shadow(${px(f, x).toFixed(2)}px ${px(f, y).toFixed(2)}px ${px(f, blur).toFixed(2)}px ${color})`;

export const styleShadow = (st: Style, f: Frame) => (st.shadow ? dropShadow(f, st.shadow.x, st.shadow.y, st.shadow.blur, st.shadow.color) : undefined);

export const joinFilters = (...xs: (string | undefined)[]) => xs.filter(Boolean).join(' ') || undefined;
