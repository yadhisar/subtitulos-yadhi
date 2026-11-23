import type {StyleDef} from '../engine';
import {glide} from './glide';
import {bottom} from './bottom';
import {karaoke} from './karaoke';
import {keyword} from './keyword';

/** anim.type del JSON del estilo -> componente que lo dibuja. Una línea por estilo (ver docs/AGREGAR_ESTILO.md). */
export const REGISTRY: Record<string, StyleDef> = {
  glide,
  bottom,
  karaoke,
  keyword,
};
