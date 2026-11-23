// Formatos de datos compartidos con los scripts de Python (ver docs/ARCHITECTURE.md).

export type CWord = {
  text: string;
  startMs: number;
  endMs: number;
  line?: number;
  emphasis?: boolean;
  reason?: string | null;
  num?: boolean;
};

export type Legibility = {mode: 'halo' | 'scrim' | 'outline'; strength: number} | null;

/** `y`: centro del bloque en % del alto (placement.py). null/ausente = position.y del estilo. */
export type CPage = {startMs: number; endMs: number; y?: number | null; words: CWord[]; legibility?: Legibility};

/** Palabra gigante de los estilos "detrás". `front`: va delante de la persona (números, tomas no aptas). */
export type CBig = {text: string; startMs: number; endMs: number; front?: boolean; page?: number};

export type CaptionsFile = {
  version: number;
  video: {width: number; height: number; fps: number; durationMs: number};
  style: string;
  pages: CPage[];
  big?: CBig[];
  cuts?: number[];
  palette?: {accent?: string};
};

export type FontSpec = {family: string; file: string; weight: number};
export type AutoColor = {auto: 'accent'; fallback: string};

/** Un estilo (styles/<nombre>.json). Tamaños en % del alto del cuadro; sombras en px a 1080 de alto. */
export type Style = {
  name: string;
  font: FontSpec;
  emphasisFont?: FontSpec;
  numberFont?: FontSpec;
  case: 'upper' | 'sentence' | 'lower';
  size: number;
  lineHeight?: number;
  letterSpacing?: number;
  color: string;
  dimColor?: string;
  activeColor?: string;
  stroke?: {width: number; color: string} | null;
  shadow?: {x: number; y: number; blur: number; color: string} | null;
  position: {y: number; marginX: number; flex?: [number, number]};
  page: Record<string, number>;
  anim: Record<string, any> & {type: string};
  behind?: {
    enabled: boolean;
    bigFont?: FontSpec;
    bigColor?: string;
    bigY?: number;
    bigWidth?: number;
    bigMaxSize?: number;
    frontY?: number;
    frontWidth?: number;
    frontMaxSize?: number;
  };
  legibility?: {mode: 'halo' | 'scrim' | 'outline'; max: number};
};

export type Layer = 'all' | 'behind' | 'front' | 'mask';

/** Geometría del cuadro. */
export type Frame = {W: number; H: number; fps: number; wide: boolean};
