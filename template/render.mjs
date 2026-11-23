#!/usr/bin/env node
// Renderiza SOLO la capa de subtítulos, transparente (ProRes 4444 con alfa). ffmpeg la compone después.
//
//   node render.mjs --captions captions.json --style style.json [--layer all|behind|front|mask] --out overlay.mov
//   node render.mjs --captions captions.json --style style.json --layer all --still 45 --png cuadro.png
//   node render.mjs --batch trabajos.json      (varios renders con un solo bundle; lista de objetos con las mismas claves)
//
// Rutas con espacios y tildes: pásalas entre comillas; aquí se resuelven con path.resolve.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const fontsDir = path.resolve(here, '..', 'fonts');

function parseArgs(argv) {
  const o = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) continue;
    const k = a.slice(2);
    const v = argv[i + 1] != null && !argv[i + 1].startsWith('--') ? argv[++i] : 'true';
    o[k] = v;
  }
  return o;
}
const die = (m) => {
  console.error(`ERROR: ${m}`);
  process.exit(1);
};
const args = parseArgs(process.argv.slice(2));
const origCwd = process.cwd();
const rp = (p) => path.resolve(origCwd, p);
// Remotion guarda su Chrome Headless Shell en <cwd>\.remotion: siempre template\, para bajarlo una sola vez
process.chdir(here);
const readJson = (p) => JSON.parse(fs.readFileSync(rp(p), 'utf8').replace(/^﻿/, ''));

let jobs;
if (args.batch) {
  jobs = readJson(args.batch);
  if (!Array.isArray(jobs) || !jobs.length) die('--batch debe ser una lista de trabajos');
} else {
  if (!args.captions || !args.style || (!args.out && !args.png)) {
    die('uso: node render.mjs --captions <captions.json> --style <style.json> [--layer all|behind|front|mask] --out <overlay.mov>\n' +
        '     opcional: --still <cuadro> --png <archivo.png>  --concurrency n  --frames a-b');
  }
  jobs = [{captions: args.captions, style: args.style, layer: args.layer, out: args.out, still: args.still, png: args.png, frames: args.frames}];
}

// fuentes locales: si un estilo pide una que no está en fonts/, se avisa antes de abrir Chrome
const fontSpecs = (o, out = []) => {
  if (o && typeof o === 'object') {
    if (typeof o.file === 'string' && typeof o.family === 'string') out.push(o);
    else for (const v of Object.values(o)) fontSpecs(v, out);
  }
  return out;
};

if (!fs.existsSync(path.join(here, 'node_modules', 'remotion'))) {
  console.error('Primera vez: instalando Remotion en template\\node_modules (npm install, tarda 1-2 minutos)...');
  const r = spawnSync('npm', ['install', '--no-audit', '--no-fund'], {cwd: here, stdio: 'inherit', shell: true});
  if (r.status !== 0) die('npm install falló');
}

const {bundle} = await import('@remotion/bundler');
const {renderMedia, renderStill, selectComposition} = await import('@remotion/renderer');

const t0 = Date.now();
// La primera vez Remotion descarga solo su Chrome Headless Shell (~100 MB) antes de renderizar.
// El bundle es una copia temporal del renderizador: se borra siempre al terminar.
const bundleDir = fs.mkdtempSync(path.join(os.tmpdir(), 'subtitulos-bundle-'));
const cleanup = () => {
  try {
    fs.rmSync(bundleDir, {recursive: true, force: true});
  } catch {}
};
process.on('exit', cleanup);
for (const sig of ['SIGINT', 'SIGTERM']) process.on(sig, () => {
  cleanup();
  process.exit(1);
});
const serveUrl = await bundle({
  entryPoint: path.join(here, 'src', 'index.ts'),
  publicDir: fontsDir,
  outDir: bundleDir,
  enableCaching: false,
  // la concatenación de módulos de webpack falla con algunos re-exports; sin ella el bundle es igual de válido
  webpackOverride: (c) => ({...c, optimization: {...(c.optimization ?? {}), concatenateModules: false}}),
});

const results = [];
for (const job of jobs) {
  const layer = job.layer ?? 'all';
  if (!['all', 'behind', 'front', 'mask'].includes(layer)) die('--layer debe ser all, behind, front o mask');
  const captions = readJson(job.captions);
  const style = readJson(job.style);
  for (const f of fontSpecs(style)) {
    if (!fs.existsSync(path.join(fontsDir, f.file))) die(`no está la fuente ${path.join(fontsDir, f.file)}`);
  }
  const inputProps = {captions, style, layer};
  const composition = await selectComposition({serveUrl, id: 'Captions', inputProps, logLevel: 'error'});
  const t1 = Date.now();
  if (job.still != null) {
    const out = rp(job.png ?? job.out);
    fs.mkdirSync(path.dirname(out), {recursive: true});
    await renderStill({composition, serveUrl, inputProps, frame: Math.min(Number(job.still), composition.durationInFrames - 1), imageFormat: 'png', output: out, logLevel: 'error', overwrite: true});
    results.push({out, layer, frames: 1, seconds: +((Date.now() - t1) / 1000).toFixed(1)});
  } else {
    const out = rp(job.out);
    fs.mkdirSync(path.dirname(out), {recursive: true});
    let frameRange = null;
    if (job.frames) {
      const [a, b] = String(job.frames).split('-').map(Number);
      frameRange = [a, b ?? a];
    }
    let last = -1;
    await renderMedia({
      composition,
      serveUrl,
      inputProps,
      codec: 'prores',
      proResProfile: '4444',
      pixelFormat: 'yuva444p10le',
      imageFormat: 'png',
      muted: true,
      overwrite: true,
      outputLocation: out,
      concurrency: job.concurrency ?? (args.concurrency ? Number(args.concurrency) : null),
      frameRange,
      logLevel: 'error',
      onProgress: ({progress}) => {
        const pct = Math.floor(progress * 10) * 10;
        if (pct !== last) {
          last = pct;
          process.stderr.write(`  render ${layer}: ${pct}%\n`);
        }
      },
    });
    const frames = frameRange ? frameRange[1] - frameRange[0] + 1 : composition.durationInFrames;
    results.push({out, layer, frames, seconds: +((Date.now() - t1) / 1000).toFixed(1)});
  }
}
console.log(JSON.stringify({results, seconds: +((Date.now() - t0) / 1000).toFixed(1)}));
