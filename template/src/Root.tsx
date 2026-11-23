import React from 'react';
import {Composition} from 'remotion';
import {Captions} from './Captions';
import type {CaptionsFile, Style} from './engine';

const empty: CaptionsFile = {version: 1, video: {width: 1080, height: 1920, fps: 30, durationMs: 1000}, style: 'glide', pages: []};

// Tamaño, fps y duración salen de captions.json: el overlay calza cuadro a cuadro con el video.
export const Root: React.FC = () => (
  <Composition
    id="Captions"
    component={Captions as React.FC<any>}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={30}
    defaultProps={{captions: empty, style: {} as Style, layer: 'all'}}
    calculateMetadata={({props}: {props: any}) => {
      const v = (props.captions as CaptionsFile).video;
      return {
        width: Math.round(v.width),
        height: Math.round(v.height),
        fps: v.fps,
        durationInFrames: Math.max(1, Math.ceil((v.durationMs * v.fps) / 1000 - 1e-6)),
      };
    }}
  />
);
