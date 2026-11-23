import React, {useEffect, useMemo, useState} from 'react';
import {AbsoluteFill, cancelRender, continueRender, delayRender, useCurrentFrame, useVideoConfig} from 'remotion';
import {Backdrop, MaskCtx, fadeIn, fadeOut, f30, frameInfo, layoutPage, loadFonts, pageTimings, resolveColors, withOutline, wordStates} from './engine';
import type {CaptionsFile, Layer, Style} from './engine';
import {REGISTRY} from './styles';

// Un SVG a pantalla completa con fondo transparente. Cada cuadro es función pura de `frame`.
// Capas:  all = todo · behind = solo palabras grandes que van detrás de la persona
//         front = línea pequeña + palabras grandes que van delante · mask = todo en blanco sobre negro

export const Captions: React.FC<{captions: CaptionsFile; style: Style; layer: Layer}> = ({captions, style, layer}) => {
  const st = useMemo(() => resolveColors(style, captions.palette), [style, captions]);
  const frame = useCurrentFrame();
  const {width, height, fps} = useVideoConfig();
  const [handle] = useState(() => delayRender('subtitulos-yadhi: cargando fuentes', {timeoutInMilliseconds: 60000}));
  const [ready, setReady] = useState(false);
  useEffect(() => {
    loadFonts(st)
      .then(() => {
        setReady(true);
        continueRender(handle);
      })
      .catch((err) => cancelRender(err));
  }, []);

  const f = useMemo(() => frameInfo(width, height, fps), [width, height, fps]);
  const def = REGISTRY[st.anim?.type] ?? REGISTRY[st.name];
  const timings = useMemo(() => pageTimings(captions.pages, fps), [captions, fps]);
  const layouts = useMemo(() => {
    if (!ready || !def) return [];
    return captions.pages.map((p) => layoutPage(p, withOutline(st, p.legibility ?? null), f, {specs: def.spec?.(p, st)}));
  }, [ready, captions, st, f, def]);
  if (!ready) return null;
  if (!def) throw new Error(`no hay componente registrado para el estilo "${st.anim?.type ?? st.name}" (template/src/styles/index.ts)`);

  const mask = layer === 'mask';
  const drawPage = layer === 'all' || layer === 'front' || mask;
  let page: React.ReactNode = null;
  if (drawPage) {
    const idx = timings.findIndex((t) => frame >= t.s && frame < t.e);
    if (idx >= 0) {
      const t = timings[idx];
      const p = captions.pages[idx];
      const lg = p.legibility ?? null;
      const pst = withOutline(st, lg);
      const P = def.Page;
      const since = frame - t.s;
      const left = t.e - frame;
      const bgOp = Math.min(fadeIn(since, f30(3, fps)), fadeOut(left, f30(3, fps)));
      page = (
        <g>
          <Backdrop lg={lg} L={layouts[idx]} id={`lg${idx}`} opacity={bgOp} />
          <P st={pst} f={f} page={p} pageIndex={idx} L={layouts[idx]} t={t} frame={frame} since={since} left={left} ws={wordStates(t, frame)} captions={captions} layer={layer} lg={lg} />
        </g>
      );
    }
  }
  const all = captions.big ?? [];
  const bigList = layer === 'behind' ? all.filter((b) => !b.front) : layer === 'front' ? all.filter((b) => b.front) : all;
  const BigC = def.Big;
  const big = BigC && st.behind?.enabled && bigList.length ? <BigC st={st} f={f} big={bigList} frame={frame} layer={layer} /> : null;

  return (
    <AbsoluteFill style={{background: mask ? '#000' : 'transparent'}}>
      <MaskCtx.Provider value={mask}>
        <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} xmlns="http://www.w3.org/2000/svg" style={{overflow: 'visible'}}>
          {big}
          {page}
        </svg>
      </MaskCtx.Provider>
    </AbsoluteFill>
  );
};
